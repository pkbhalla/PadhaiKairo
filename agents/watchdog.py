from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from core.db import (
    list_concepts,
    get_or_create_learner,
    get_or_create_course,
    create_pending_nudge,
    record_event
)
from core.mastery import needs_review
from agents.quizmaster import generate_quiz
from agents.planner import generate_revision_plan
from tools.calendar_tools import create_revision_event


def run_retention_guardian_scan(
    learner_id: str,
    course_id: str
) -> Dict[str, Any]:
    """
    Autonomous Retention Guardian:
    1. Factors in remaining days to the course exam date for adaptive urgency.
    2. Recomputes live forgetting-curve retention for all concepts.
    3. Identifies decaying or due-for-review concepts based on adaptive thresholds.
    4. Proactively generates a targeted drill quiz.
    5. Drops revision blocks into Google Calendar aligned with remaining exam days.
    6. Drafts a personalized study nudge email and queues it in pendingNudges (HITL).
    """
    learner = get_or_create_learner(learner_id)
    course = get_or_create_course(learner_id, course_id)
    course_title = course.get("title", course_id)
    concepts = list_concepts(learner_id, course_id)
    
    # Resolve real learner email dynamically
    learner_email = learner.get("email")
    if not learner_email or "@" not in learner_email or "example.com" in learner_email:
        try:
            from google_auth import get_oauth_credentials, get_user_info
            creds = get_oauth_credentials()
            if creds:
                info = get_user_info(creds)
                if info.get("email"):
                    learner_email = info.get("email")
        except Exception:
            pass
    if not learner_email:
        learner_email = f"{learner_id}@gmail.com"
    
    now = datetime.now(timezone.utc)
    
    # 1. Determine exam date & remaining days
    exam_dt = None
    days_until_exam = None
    urgency_level = "normal"
    decay_threshold = 0.50

    if course.get("examDate"):
        raw_exam = course["examDate"]
        if hasattr(raw_exam, "replace"):
            exam_dt = raw_exam.replace(tzinfo=timezone.utc) if raw_exam.tzinfo is None else raw_exam
        elif isinstance(raw_exam, str):
            try:
                exam_dt = datetime.fromisoformat(raw_exam.replace("Z", "+00:00"))
            except Exception:
                pass
        
        if exam_dt:
            days_until_exam = max(0, (exam_dt - now).days)
            if days_until_exam <= 3:
                urgency_level = "critical"
                decay_threshold = 0.75  # Aggressive review for upcoming exam
            elif days_until_exam <= 7:
                urgency_level = "high"
                decay_threshold = 0.60  # Moderate exam urgency

    decayed_concepts = []
    for c in concepts:
        eff_mastery = c.get("effectiveMastery", 1.0)
        next_review = c.get("nextReviewAt")
        
        # Adaptive check based on exam proximity
        if eff_mastery < decay_threshold or needs_review(eff_mastery, next_review, now):
            decayed_concepts.append(c)

    actions_taken = []
    
    for c in decayed_concepts:
        concept_name = c.get("name", "Unknown Concept")
        eff_mastery = c.get("effectiveMastery", 0.0)
        
        # Generate targeted 5-question drill quiz
        drill_quiz = generate_quiz(
            topic=concept_name,
            num_questions=5,
            learner_id=learner_id,
            course_id=course_id
        )
        
        # Schedule Calendar Block for tomorrow
        tomorrow = now + timedelta(days=1)
        drill_start = tomorrow.replace(hour=13, minute=30, second=0, microsecond=0)
        cal_title = f"[Retention Guardian] 15-min Practice Drill: {concept_name}"
        exam_suffix = f" (Exam in {days_until_exam} days!)" if days_until_exam is not None else ""
        cal_desc = f"Proactive revision block scheduled by Retention Guardian for {course_title}{exam_suffix} because '{concept_name}' retention decayed to {int(eff_mastery*100)}%."
        
        try:
            cal_res = create_revision_event(
                title=cal_title,
                start_iso=drill_start.isoformat(),
                duration_minutes=30,
                description=cal_desc
            )
            cal_event_id = cal_res.get("id")
        except Exception as e:
            cal_event_id = f"cal-planned-{int(now.timestamp())}"

        # Draft personalized nudge email (HITL queue)
        learner_name = learner.get("name", "Learner")
        subject = f"Study Nudge: Retention booster for '{concept_name}' ({course_title}){exam_suffix}!"
        body_text = f"""Hi {learner_name},

Your Agentic Learning Coach noticed that your retention for '{concept_name}' in {course_title} has decayed to {int(eff_mastery*100)}% on your spaced repetition curve.{f" With your exam in {days_until_exam} days, strengthening this concept is high priority." if days_until_exam is not None else ""}

To keep you on track, I've prepared:
1. A targeted 5-question conceptual practice drill.
2. A 30-minute revision slot on your Google Calendar for tomorrow.

Click below in your learning dashboard to complete the drill when you're ready!

Best,
Your Agentic Learning Coach"""

        nudge_id = create_pending_nudge(
            learner_id=learner_id,
            course_id=course_id,
            course_title=course_title,
            concept_name=concept_name,
            reason=f"Retention decayed to {eff_mastery:.2f} ({urgency_level} threshold: {decay_threshold:.2f})",
            drill_quiz_id=f"drill-{concept_name.lower().replace(' ', '-')}",
            calendar_event_id=cal_event_id,
            email_draft={
                "to": learner_email,
                "subject": subject,
                "body": body_text
            }
        )
        
        actions_taken.append({
            "nudgeId": nudge_id,
            "concept": concept_name,
            "effectiveMastery": eff_mastery,
            "calendarEventId": cal_event_id,
            "drillQuestionsCount": len(drill_quiz.get("questions", []))
        })

    # Auto-sync/recompute revision plan based on current exam date
    try:
        exam_iso = exam_dt.isoformat() if exam_dt else None
        calendar_plan = generate_revision_plan(
            learner_id=learner_id,
            course_id=course_id,
            exam_date_iso=exam_iso
        )
    except Exception as e:
        calendar_plan = {"status": "skipped", "error": str(e)}

    record_event("retention_scan", {
        "learnerId": learner_id,
        "courseId": course_id,
        "scannedConcepts": len(concepts),
        "decayedCount": len(decayed_concepts),
        "nudgesQueued": len(actions_taken),
        "daysUntilExam": days_until_exam,
        "urgencyLevel": urgency_level
    })

    return {
        "status": "success",
        "scannedConceptsCount": len(concepts),
        "decayedCount": len(decayed_concepts),
        "actionsTaken": actions_taken,
        "examDaysLeft": days_until_exam,
        "urgencyLevel": urgency_level,
        "calendarPlan": calendar_plan,
        "timestamp": now.isoformat()
    }


run_nightly_decay_scan = run_retention_guardian_scan
