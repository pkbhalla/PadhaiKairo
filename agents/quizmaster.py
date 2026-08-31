import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from core.gemini import generate_content_with_retry
from agents.tutor import load_course_sources
from core.db import (
    get_concept,
    upsert_concept,
    record_quiz_attempt,
    record_event,
    get_or_create_course
)
from core.mastery import compute_updated_mastery, compute_half_life_days


class QuizQuestion(BaseModel):
    id: int = Field(description="Question number 1 to 5")
    question: str = Field(description="The conceptual question stem")
    options: List[str] = Field(description="List of exactly 4 option strings")
    correct_option_index: int = Field(description="0-indexed integer (0, 1, 2, or 3)")
    explanation: str = Field(description="Clear explanation why the correct option is right")


class QuizPayload(BaseModel):
    topic: str
    questions: List[QuizQuestion]


QUIZ_SYSTEM_INSTRUCTION = """
You are the Lead Assessment Specialist for the Agentic Learning Coach.
Generate a high-yield, 5-question multiple choice conceptual practice drill based on the student's course materials.
Return strictly valid JSON adhering to the QuizPayload schema.
Ensure questions test deep conceptual understanding, trade-offs, and procedural rules.
"""


def generate_quiz(
    topic: str,
    num_questions: int = 5,
    learner_id: str = "guest",
    course_id: str = "general"
) -> Dict[str, Any]:
    """Generate a 5-question multiple choice quiz for any topic or course."""
    sources_text = load_course_sources(learner_id, course_id)
    course = get_or_create_course(learner_id, course_id)
    course_title = course.get("title", course_id)

    prompt = f"""
Generate {num_questions} multiple choice questions for the topic: '{topic}' in the course '{course_title}'.

STUDENT LECTURE TRANSCRIPTS & NOTES:
{sources_text if sources_text else "Use authoritative conceptual principles for " + topic + " in " + course_title + "."}

Ensure:
- Exactly {num_questions} questions
- 4 options per question (0-indexed correct_option_index)
- Meaningful explanations
"""
    try:
        response = generate_content_with_retry(
            contents=prompt,
            system_instruction=QUIZ_SYSTEM_INSTRUCTION,
            response_mime_type="application/json"
        )
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        data = json.loads(text.strip())
    except Exception as e:
        # Dynamic fallback matching the requested topic
        data = {
            "topic": topic,
            "questions": [
                {
                    "id": 1,
                    "question": f"What is the primary conceptual purpose of {topic} in {course_title}?",
                    "options": [
                        f"To provide an optimal, robust mathematical or structural framework for {topic}",
                        "To increase computational complexity arbitrarily without performance benefit",
                        "To bypass system memory constraints without verification",
                        "To generate redundant state transitions"
                    ],
                    "correct_option_index": 0,
                    "explanation": f"{topic} is designed to solve core computational, representational, and optimization challenges in {course_title}."
                },
                {
                    "id": 2,
                    "question": f"Which of the following best describes a key constraint or assumption in {topic}?",
                    "options": [
                        "All system states must be independent and unconstrained",
                        f"Specific operational invariants must be preserved throughout execution of {topic}",
                        "Execution order has zero effect on convergence or output validity",
                        "Data types do not need schema or dimensional alignment"
                    ],
                    "correct_option_index": 1,
                    "explanation": f"Maintaining formal invariants is critical for the correctness and convergence of {topic}."
                },
                {
                    "id": 3,
                    "question": f"What is a common pitfall or trade-off when implementing {topic}?",
                    "options": [
                        "Zero risk of underfitting, overfitting, or performance bottlenecks",
                        "Over-optimization leading to high computational overhead or variance",
                        "Instantaneous O(1) global convergence in all cases",
                        "Lack of any hyperparameter sensitivity"
                    ],
                    "correct_option_index": 1,
                    "explanation": f"A primary challenge with {topic} is balancing efficiency, variance, and generalization trade-offs."
                },
                {
                    "id": 4,
                    "question": f"How is performance or convergence evaluated in {topic}?",
                    "options": [
                        "Purely by execution time without checking loss or error metrics",
                        "By measuring error reduction, stability, and invariant preservation against a validation metric",
                        "By guessing random initialization states",
                        "By ignoring edge cases and error bounds"
                    ],
                    "correct_option_index": 1,
                    "explanation": "Evaluating loss/error metrics and invariant stability against benchmarks provides rigorous validation."
                },
                {
                    "id": 5,
                    "question": f"Which complementary technique is most frequently paired with {topic} for improved stability?",
                    "options": [
                        "Regularization, normalization, or structured indexing depending on the domain",
                        "Disabling all validation checks and logging",
                        "Random deletion of state variables",
                        "Eliminating gradient or constraint updates"
                    ],
                    "correct_option_index": 0,
                    "explanation": f"Regularization, normalization, and structured constraints significantly improve the robustness of {topic}."
                }
            ]
        }

    return {
        "topic": topic,
        "concept_name": topic,
        "questions": data.get("questions", [])
    }


def grade_quiz(
    learner_id: str,
    course_id: str,
    concept_name: str,
    questions: List[Dict[str, Any]],
    user_answers: Dict[str, int]
) -> Dict[str, Any]:
    """Grade submitted quiz, update mastery graph in Firestore, and calculate half-life."""
    total = len(questions)
    correct_count = 0
    detailed_results = []

    for q in questions:
        q_id = str(q.get("id"))
        correct_idx = q.get("correct_option_index")
        user_idx = user_answers.get(q_id)
        is_correct = (user_idx == correct_idx)
        if is_correct:
            correct_count += 1
        
        detailed_results.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "userAnswer": user_idx,
            "correctAnswer": correct_idx,
            "isCorrect": is_correct,
            "explanation": q.get("explanation")
        })

    score = (correct_count / total) if total > 0 else 0.0
    
    # Update mastery graph in Firestore
    existing_concept = get_concept(learner_id, course_id, concept_name)
    current_m = existing_concept.get("mastery", 0.5) if existing_concept else 0.5
    attempts = existing_concept.get("attempts", 0) + 1 if existing_concept else 1
    
    new_mastery = compute_updated_mastery(current_m, score, attempts)
    new_half_life = compute_half_life_days(attempts)
    
    now = datetime.now(timezone.utc)
    next_review = now + timedelta(days=new_half_life)
    
    upsert_concept(
        learner_id=learner_id,
        course_id=course_id,
        concept_name=concept_name,
        mastery=new_mastery,
        attempts=attempts,
        half_life_days=new_half_life,
        last_assessed_at=now,
        next_review_at=next_review,
        history_entry={
            "timestamp": now.isoformat(),
            "score": score,
            "masteryAfter": new_mastery
        }
    )

    record_quiz_attempt(
        learner_id=learner_id,
        course_id=course_id,
        concept_names=[concept_name],
        score=score,
        items=detailed_results
    )

    return {
        "conceptName": concept_name,
        "score": score,
        "correctCount": correct_count,
        "total": total,
        "newMastery": new_mastery,
        "newHalfLifeDays": new_half_life,
        "nextReviewDate": next_review.isoformat(),
        "detailedResults": detailed_results
    }
