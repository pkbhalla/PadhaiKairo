from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from core.config import GOOGLE_CLOUD_PROJECT, DEFAULT_TIMEZONE
from core.mastery import compute_effective_mastery, compute_half_life_days

_db_client: Optional[firestore.Client] = None


def get_db() -> firestore.Client:
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=GOOGLE_CLOUD_PROJECT)
    return _db_client


def list_all_learners() -> List[Dict[str, Any]]:
    """List all registered learners."""
    db = get_db()
    docs = db.collection("learners").stream()
    learners = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        learners.append(d)
    return learners


def get_or_create_learner(
    learner_id: str,
    name: str = "Learner",
    email: str = "learner@example.com",
    tz: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    db = get_db()
    doc_ref = db.collection("learners").document(learner_id)
    snapshot = doc_ref.get()
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        data["id"] = learner_id
        return data
    
    data = {
        "name": name,
        "email": email,
        "timezone": tz,
        "createdAt": datetime.now(timezone.utc),
    }
    doc_ref.set(data)
    data["id"] = learner_id
    return data


def list_courses_for_learner(learner_id: str) -> List[Dict[str, Any]]:
    """List all courses registered for a learner."""
    db = get_db()
    courses_ref = db.collection("learners").document(learner_id).collection("courses")
    docs = courses_ref.stream()
    courses = []
    for d in docs:
        c = d.to_dict()
        c["id"] = d.id
        courses.append(c)
    return courses


def get_or_create_course(
    learner_id: str,
    course_id: str,
    course_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    db = get_db()
    course_ref = db.collection("learners").document(learner_id).collection("courses").document(course_id)
    snapshot = course_ref.get()
    
    defaults = {
        "title": (course_data and course_data.get("title")) or course_id.replace("_", " ").title(),
        "examDate": None,
        "syllabusTopics": (course_data and course_data.get("syllabusTopics")) or [],
        "createdAt": datetime.now(timezone.utc),
    }
    
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        defaults.update(data)
        if course_data:
            course_ref.set(course_data, merge=True)
            defaults.update(course_data)
        defaults["id"] = course_id
        return defaults
    
    if course_data:
        defaults.update(course_data)
    course_ref.set(defaults)
    defaults["id"] = course_id
    return defaults


def get_learner_profile(learner_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full learner profile."""
    db = get_db()
    doc_ref = db.collection("learners").document(learner_id)
    snapshot = doc_ref.get()
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        data["id"] = learner_id
        return data
    return None


def update_learner_profile(learner_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update learner profile fields (name, email, timezone, daily_goal_mins, pace, etc.)."""
    db = get_db()
    doc_ref = db.collection("learners").document(learner_id)
    profile_data["updatedAt"] = datetime.now(timezone.utc)
    doc_ref.set(profile_data, merge=True)
    snapshot = doc_ref.get()
    data = snapshot.to_dict() or {}
    data["id"] = learner_id
    return data


def update_course(learner_id: str, course_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    course_ref = db.collection("learners").document(learner_id).collection("courses").document(course_id)
    update_data["updatedAt"] = datetime.now(timezone.utc)
    course_ref.set(update_data, merge=True)
    snapshot = course_ref.get()
    data = snapshot.to_dict() or {}
    data["id"] = course_id
    return data


# Multimodal Study Source Documents (Pasted Notes, YouTube Transcripts, PDFs)
def add_study_source(
    learner_id: str,
    course_id: str,
    title: str,
    source_type: str, # "youtube_transcript", "text_note", "pdf_summary", "doc"
    content: str,
    source_url: Optional[str] = None
) -> Dict[str, Any]:
    db = get_db()
    doc_ref = db.collection("sources").document()
    data = {
        "learnerId": learner_id,
        "courseId": course_id,
        "title": title,
        "type": source_type,
        "content": content,
        "sourceUrl": source_url or "",
        "charCount": len(content),
        "createdAt": datetime.now(timezone.utc)
    }
    doc_ref.set(data)
    data["id"] = doc_ref.id
    record_event("source_added", {"learnerId": learner_id, "courseId": course_id, "title": title, "type": source_type})
    return data


def list_study_sources(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    query = (
        db.collection("sources")
        .where(filter=FieldFilter("learnerId", "==", learner_id))
        .where(filter=FieldFilter("courseId", "==", course_id))
    )
    docs = query.stream()
    sources = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        sources.append(item)
    return sources


# Flashcard Decks Management
def save_flashcards(
    learner_id: str,
    course_id: str,
    topic: str,
    cards: List[Dict[str, str]]
) -> str:
    db = get_db()
    doc_ref = db.collection("flashcardDecks").document()
    data = {
        "learnerId": learner_id,
        "courseId": course_id,
        "topic": topic,
        "cards": cards,
        "createdAt": datetime.now(timezone.utc)
    }
    doc_ref.set(data)
    return doc_ref.id


def list_flashcard_decks(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    query = (
        db.collection("flashcardDecks")
        .where(filter=FieldFilter("learnerId", "==", learner_id))
        .where(filter=FieldFilter("courseId", "==", course_id))
    )
    docs = query.stream()
    decks = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        decks.append(item)
    return decks


def list_concepts(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    query = (
        db.collection("concepts")
        .where(filter=FieldFilter("learnerId", "==", learner_id))
        .where(filter=FieldFilter("courseId", "==", course_id))
    )
    docs = query.stream()
    concepts = []
    now = datetime.now(timezone.utc)
    for doc in docs:
        c = doc.to_dict()
        c["id"] = doc.id
        eff = compute_effective_mastery(
            mastery=c.get("mastery", 0.0),
            last_assessed_at=c.get("lastAssessedAt"),
            half_life_days=c.get("halfLifeDays", 7.0),
            current_time=now
        )
        c["effectiveMastery"] = eff
        concepts.append(c)
    return concepts


def get_concept(learner_id: str, course_id: str, concept_name: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    query = (
        db.collection("concepts")
        .where(filter=FieldFilter("learnerId", "==", learner_id))
        .where(filter=FieldFilter("courseId", "==", course_id))
        .where(filter=FieldFilter("name", "==", concept_name))
        .limit(1)
    )
    docs = list(query.stream())
    if not docs:
        return None
    c = docs[0].to_dict()
    c["id"] = docs[0].id
    c["effectiveMastery"] = compute_effective_mastery(
        mastery=c.get("mastery", 0.0),
        last_assessed_at=c.get("lastAssessedAt"),
        half_life_days=c.get("halfLifeDays", 7.0),
        current_time=datetime.now(timezone.utc)
    )
    return c


def upsert_concept(
    learner_id: str,
    course_id: str,
    concept_name: str,
    mastery: float,
    attempts: int = 1,
    half_life_days: Optional[float] = None,
    last_assessed_at: Optional[datetime] = None,
    next_review_at: Optional[datetime] = None,
    history_entry: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    db = get_db()
    existing = get_concept(learner_id, course_id, concept_name)
    now = datetime.now(timezone.utc)
    
    if half_life_days is None:
        half_life_days = compute_half_life_days(attempts)
    if last_assessed_at is None:
        last_assessed_at = now
        
    history = []
    if existing:
        doc_ref = db.collection("concepts").document(existing["id"])
        history = existing.get("history", [])
    else:
        doc_ref = db.collection("concepts").document()

    if history_entry:
        history.append(history_entry)

    data = {
        "learnerId": learner_id,
        "courseId": course_id,
        "name": concept_name,
        "mastery": float(mastery),
        "attempts": int(attempts),
        "halfLifeDays": float(half_life_days),
        "lastAssessedAt": last_assessed_at,
        "nextReviewAt": next_review_at,
        "history": history,
        "updatedAt": now,
    }
    doc_ref.set(data, merge=True)
    data["id"] = doc_ref.id
    return data


def record_quiz_attempt(
    learner_id: str,
    course_id: str,
    concept_names: List[str],
    score: float,
    items: List[Dict[str, Any]]
) -> str:
    db = get_db()
    doc_ref = db.collection("quizAttempts").document()
    data = {
        "learnerId": learner_id,
        "courseId": course_id,
        "conceptNames": concept_names,
        "score": float(score),
        "items": items,
        "createdAt": datetime.now(timezone.utc)
    }
    doc_ref.set(data)
    record_event("quiz", {"quizAttemptId": doc_ref.id, "concepts": concept_names, "score": score})
    return doc_ref.id


def create_pending_nudge(
    learner_id: str,
    concept_name: str,
    reason: str,
    drill_quiz_id: Optional[str],
    calendar_event_id: Optional[str],
    email_draft: Dict[str, str],
    course_id: Optional[str] = None,
    course_title: Optional[str] = None
) -> str:
    db = get_db()
    doc_ref = db.collection("pendingNudges").document()
    data = {
        "learnerId": learner_id,
        "courseId": course_id or "",
        "courseTitle": course_title or "",
        "conceptName": concept_name,
        "reason": reason,
        "drillQuizId": drill_quiz_id,
        "calendarEventId": calendar_event_id,
        "emailDraft": email_draft,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc)
    }
    doc_ref.set(data)
    record_event("nudge_drafted", {"nudgeId": doc_ref.id, "concept": concept_name, "reason": reason, "courseId": course_id})
    return doc_ref.id


def list_pending_nudges(
    learner_id: str,
    course_id: Optional[str] = None,
    status: Optional[str] = "pending"
) -> List[Dict[str, Any]]:
    db = get_db()
    query = db.collection("pendingNudges").where(filter=FieldFilter("learnerId", "==", learner_id))
    if course_id:
        query = query.where(filter=FieldFilter("courseId", "==", course_id))
    if status:
        query = query.where(filter=FieldFilter("status", "==", status))
    
    docs = query.stream()
    nudges = []
    for doc in docs:
        n = doc.to_dict()
        n["id"] = doc.id
        nudges.append(n)
    return nudges


def update_nudge_status(nudge_id: str, status: str) -> bool:
    db = get_db()
    doc_ref = db.collection("pendingNudges").document(nudge_id)
    snapshot = doc_ref.get()
    if not snapshot.exists:
        return False
    doc_ref.update({"status": status, "updatedAt": datetime.now(timezone.utc)})
    record_event("nudge_status", {"nudgeId": nudge_id, "newStatus": status})
    return True


def record_event(event_type: str, payload: Dict[str, Any]) -> str:
    try:
        db = get_db()
        doc_ref = db.collection("events").document()
        doc_ref.set({
            "type": event_type,
            "payload": payload,
            "createdAt": datetime.now(timezone.utc)
        })
        return doc_ref.id
    except Exception as e:
        print(f"Warning: Failed to record event {event_type}: {e}")
        return ""
