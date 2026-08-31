import json
from typing import Dict, Any, List, Optional
from core.gemini import generate_content_with_retry
from agents.tutor import answer_socratic_question
from agents.quizmaster import generate_quiz
from agents.planner import generate_revision_plan
from core.db import list_concepts, get_or_create_course, record_event


ROUTER_SYSTEM_INSTRUCTION = """
You are the Root Dispatcher Agent for the Agentic Learning Coach.
Determine student intent and route appropriately.
Available Actions:
- "chat": Concept questions, explanations, discussions, or general guidance.
- "quiz": User asks to be tested, take a quiz, or practice questions.
- "plan": User asks to create a study plan, schedule revision, or sync to calendar.
- "mastery": User asks about their progress, scores, or what to study next.

Return JSON with "action" (chat|quiz|plan|mastery) and "targetTopic" (string or null).
"""


def handle_coach_interaction(
    message: str,
    learner_id: str = "guest",
    course_id: str = "general"
) -> Dict[str, Any]:
    """Unified interaction handler routing student inputs to the right agent."""
    # Fast heuristic routing
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["quiz", "test me", "drill", "practice"]):
        action = "quiz"
    elif any(w in msg_lower for w in ["plan", "schedule", "calendar", "timetable", "exam on"]):
        action = "plan"
    elif any(w in msg_lower for w in ["progress", "mastery", "score", "how am i doing", "what should i study"]):
        action = "mastery"
    else:
        action = "chat"

    target_topic = None
    course = get_or_create_course(learner_id, course_id)
    course_title = course.get("title", course_id)

    if action == "chat":
        tutor_res = answer_socratic_question(
            query=message,
            learner_id=learner_id,
            course_id=course_id
        )
        return {
            "type": "chat",
            "message": tutor_res.get("response", ""),
            "grounded": tutor_res.get("grounded", False)
        }

    elif action == "quiz":
        concepts = list_concepts(learner_id, course_id)
        if not target_topic:
            if concepts:
                # Pick lowest mastery concept
                sorted_c = sorted(concepts, key=lambda x: x.get("effectiveMastery", 1.0))
                target_topic = sorted_c[0].get("name", "Core Concepts")
            else:
                target_topic = "Core Concepts"

        quiz_data = generate_quiz(
            topic=target_topic,
            num_questions=5,
            learner_id=learner_id,
            course_id=course_id
        )
        return {
            "type": "quiz",
            "message": f"I've generated a 5-question conceptual practice drill for **{target_topic}** ({course_title})!",
            "data": quiz_data
        }

    elif action == "plan":
        plan_res = generate_revision_plan(
            learner_id=learner_id,
            course_id=course_id
        )
        return {
            "type": "plan",
            "message": f"I've organized your spaced revision plan for **{course_title}**! Created {plan_res.get('totalSessions', 0)} sessions directly in your Google Calendar.",
            "data": plan_res
        }

    elif action == "mastery":
        concepts = list_concepts(learner_id, course_id)
        if not concepts:
            summary = f"You haven't registered any subtopics yet for **{course_title}**. Click '+ Add New Subject' to get started!"
        else:
            summary_lines = []
            for c in concepts:
                eff = int(c.get("effectiveMastery", 0.0) * 100)
                status = "🔴 Decayed" if eff < 50 else ("🟡 Moderate" if eff < 70 else "🟢 Strong")
                summary_lines.append(f"- **{c.get('name')}**: {eff}% ({status})")
            summary = f"Here is your real-time retention summary for **{course_title}**:\n" + "\n".join(summary_lines)

        return {
            "type": "mastery",
            "message": summary,
            "data": {"concepts": concepts}
        }

    return {
        "type": "chat",
        "message": "How can I assist your study session today?",
        "grounded": False
    }


# Backwards compatibility alias
chat_with_tutor = answer_socratic_question
