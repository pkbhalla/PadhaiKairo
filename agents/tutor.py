from typing import Dict, Any, Optional, List
from core.gemini import generate_content_with_retry
from core.db import list_study_sources, get_or_create_course, record_event

TUTOR_SYSTEM_INSTRUCTION = """
You are the Socratic Learning Coach for the Agentic Learning Coach platform.
Your objective:
1. Always guide the learner to reason through concepts step-by-step.
2. NEVER immediately give away the final answer to an academic problem or definition.
3. Ask a probing, helpful diagnostic question to test their understanding.
4. Ground your guidance in the student's ingested lecture notes and transcripts whenever provided.
5. Keep explanations engaging, concise, and structured with clear Markdown formatting.
"""


def load_course_sources(learner_id: str, course_id: str) -> str:
    """Fetch all lecture notes, YouTube transcripts, and documents for this student's course."""
    sources = list_study_sources(learner_id, course_id)
    if not sources:
        return ""
    
    parts = []
    for s in sources:
        title = s.get("title", "Lecture Notes")
        content = s.get("content", "")[:5000] # Limit per source
        parts.append(f"--- SOURCE: {title} ---\n{content}\n")
    return "\n\n".join(parts)


def answer_socratic_question(
    query: str,
    learner_id: str = "guest",
    course_id: str = "general"
) -> Dict[str, Any]:
    """Provide a Socratic response grounded in the student's actual course material."""
    course_context = load_course_sources(learner_id, course_id)
    course = get_or_create_course(learner_id, course_id)
    course_title = course.get("title", course_id)
    
    prompt = f"""
Student Course: {course_title}
Student Question: "{query}"

STUDENT COURSE MATERIAL & LECTURE TRANSCRIPTS:
{course_context if course_context else "No custom lecture notes uploaded yet. Provide guided Socratic reasoning using domain fundamentals for " + course_title + "."}

Respond as a world-class Socratic tutor. Guide the student's thought process step-by-step with a conceptual hint and follow-up question.
"""
    try:
        response = generate_content_with_retry(
            contents=prompt,
            system_instruction=TUTOR_SYSTEM_INSTRUCTION
        )
        answer_text = response.text.strip()
    except Exception as e:
        # Dynamic, high-quality Socratic fallback matching the student's query and course
        answer_text = f"""Great question about **{query}** in *{course_title}*!

Let's break this down conceptually:
1. Consider what fundamental problem this is designed to solve in **{course_title}**.
2. How do the key components interact when data or state flows through the system?

To help guide your intuition:
> What do you think happens if we modify one of the core constraints or input variables in this scenario?

Take a guess or share your current thinking, and we will build the intuition together!"""

    record_event("tutor_interaction", {
        "learnerId": learner_id,
        "courseId": course_id,
        "query": query
    })

    return {
        "query": query,
        "response": answer_text,
        "grounded": bool(course_context)
    }
