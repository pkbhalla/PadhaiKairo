import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from core.config import GOOGLE_CLOUD_PROJECT, DEFAULT_TIMEZONE
from core.mastery import compute_effective_mastery, compute_half_life_days

_db_client = None
_firestore_available = True

# In-memory storage fallbacks for Cloud Run when Firestore IAM is restricted
_mem_learners: Dict[str, Any] = {}
_mem_courses: Dict[str, Dict[str, Any]] = {}
_mem_concepts: Dict[str, Dict[str, Any]] = {}
_mem_nudges: Dict[str, Dict[str, Any]] = {}
_mem_sources: Dict[str, List[Dict[str, Any]]] = {}
_mem_flashcards: Dict[str, List[Dict[str, Any]]] = {}


def get_db():
    global _db_client, _firestore_available
    if not _firestore_available:
        return None
    if _db_client is None:
        try:
            from google.cloud import firestore
            _db_client = firestore.Client(project=GOOGLE_CLOUD_PROJECT)
        except Exception as e:
            print(f"Notice: Firestore Client initialization fallback: {e}")
            _firestore_available = False
            return None
    return _db_client


def list_all_learners() -> List[Dict[str, Any]]:
    """List all registered learners."""
    db = get_db()
    if db:
        try:
            docs = db.collection("learners").stream()
            learners = []
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                learners.append(d)
            return learners
        except Exception as e:
            print(f"Notice: Firestore list_all_learners fallback: {e}")
    return list(_mem_learners.values())


def get_or_create_learner(
    learner_id: str,
    name: str = "Learner",
    email: str = "learner@example.com",
    tz: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("learners").document(learner_id)
            snapshot = doc_ref.get()
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                data["id"] = learner_id
                _mem_learners[learner_id] = data
                return data
            
            data = {
                "name": name,
                "email": email,
                "timezone": tz,
                "createdAt": datetime.now(timezone.utc),
            }
            doc_ref.set(data)
            data["id"] = learner_id
            _mem_learners[learner_id] = data
            return data
        except Exception as e:
            print(f"Notice: Firestore get_or_create_learner fallback: {e}")

    # In-memory fallback
    if learner_id in _mem_learners:
        return _mem_learners[learner_id]
    data = {
        "id": learner_id,
        "name": name,
        "email": email,
        "timezone": tz,
        "createdAt": datetime.now(timezone.utc),
    }
    _mem_learners[learner_id] = data
    return data


def list_courses_for_learner(learner_id: str) -> List[Dict[str, Any]]:
    """List all courses registered for a learner."""
    db = get_db()
    if db:
        try:
            courses_ref = db.collection("learners").document(learner_id).collection("courses")
            docs = courses_ref.stream()
            courses = []
            for d in docs:
                c = d.to_dict()
                c["id"] = d.id
                courses.append(c)
            return courses
        except Exception as e:
            print(f"Notice: Firestore list_courses fallback: {e}")

    # In-memory fallback
    user_courses = _mem_courses.get(learner_id, {})
    return list(user_courses.values())


def get_or_create_course(
    learner_id: str,
    course_id: str,
    course_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    defaults = {
        "title": (course_data and course_data.get("title")) or course_id.replace("_", " ").title(),
        "examDate": None,
        "syllabusTopics": (course_data and course_data.get("syllabusTopics")) or [],
        "createdAt": datetime.now(timezone.utc),
    }
    db = get_db()
    if db:
        try:
            course_ref = db.collection("learners").document(learner_id).collection("courses").document(course_id)
            snapshot = course_ref.get()
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
        except Exception as e:
            print(f"Notice: Firestore get_or_create_course fallback: {e}")

    # In-memory fallback
    if learner_id not in _mem_courses:
        _mem_courses[learner_id] = {}
    if course_id in _mem_courses[learner_id]:
        if course_data:
            _mem_courses[learner_id][course_id].update(course_data)
        return _mem_courses[learner_id][course_id]
    if course_data:
        defaults.update(course_data)
    defaults["id"] = course_id
    _mem_courses[learner_id][course_id] = defaults
    return defaults


def get_learner_profile(learner_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full learner profile."""
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("learners").document(learner_id)
            snapshot = doc_ref.get()
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                data["id"] = learner_id
                return data
        except Exception as e:
            print(f"Notice: Firestore get_learner_profile fallback: {e}")
    return _mem_learners.get(learner_id)


def update_learner_profile(learner_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update learner profile fields."""
    profile_data["updatedAt"] = datetime.now(timezone.utc)
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("learners").document(learner_id)
            doc_ref.set(profile_data, merge=True)
            snapshot = doc_ref.get()
            data = snapshot.to_dict() or {}
            data["id"] = learner_id
            return data
        except Exception as e:
            print(f"Notice: Firestore update_learner_profile fallback: {e}")
    if learner_id not in _mem_learners:
        _mem_learners[learner_id] = {"id": learner_id}
    _mem_learners[learner_id].update(profile_data)
    return _mem_learners[learner_id]


def update_course(learner_id: str, course_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    update_data["updatedAt"] = datetime.now(timezone.utc)
    db = get_db()
    if db:
        try:
            course_ref = db.collection("learners").document(learner_id).collection("courses").document(course_id)
            course_ref.set(update_data, merge=True)
            snapshot = course_ref.get()
            data = snapshot.to_dict() or {}
            data["id"] = course_id
            return data
        except Exception as e:
            print(f"Notice: Firestore update_course fallback: {e}")
    if learner_id not in _mem_courses:
        _mem_courses[learner_id] = {}
    if course_id not in _mem_courses[learner_id]:
        _mem_courses[learner_id][course_id] = {"id": course_id}
    _mem_courses[learner_id][course_id].update(update_data)
    return _mem_courses[learner_id][course_id]


def add_study_source(
    learner_id: str,
    course_id: str,
    title: str,
    source_type: str,
    content: str,
    source_url: Optional[str] = None
) -> Dict[str, Any]:
    import uuid
    source_id = str(uuid.uuid4())
    data = {
        "id": source_id,
        "learnerId": learner_id,
        "courseId": course_id,
        "title": title,
        "type": source_type,
        "content": content,
        "sourceUrl": source_url or "",
        "charCount": len(content),
        "createdAt": datetime.now(timezone.utc)
    }
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("sources").document(source_id)
            doc_ref.set(data)
        except Exception as e:
            print(f"Notice: Firestore add_study_source fallback: {e}")
    
    key = f"{learner_id}:{course_id}"
    if key not in _mem_sources:
        _mem_sources[key] = []
    _mem_sources[key].append(data)
    return data


def list_study_sources(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    if db:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
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
        except Exception as e:
            print(f"Notice: Firestore list_study_sources fallback: {e}")
    key = f"{learner_id}:{course_id}"
    return _mem_sources.get(key, [])


def save_flashcards(
    learner_id: str,
    course_id: str,
    topic: str,
    cards: List[Dict[str, str]]
) -> str:
    import uuid
    deck_id = str(uuid.uuid4())
    data = {
        "id": deck_id,
        "learnerId": learner_id,
        "courseId": course_id,
        "topic": topic,
        "cards": cards,
        "createdAt": datetime.now(timezone.utc)
    }
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("flashcardDecks").document(deck_id)
            doc_ref.set(data)
        except Exception as e:
            print(f"Notice: Firestore save_flashcards fallback: {e}")
    key = f"{learner_id}:{course_id}"
    if key not in _mem_flashcards:
        _mem_flashcards[key] = []
    _mem_flashcards[key].append(data)
    return deck_id


def list_flashcard_decks(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    if db:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
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
        except Exception as e:
            print(f"Notice: Firestore list_flashcard_decks fallback: {e}")
    key = f"{learner_id}:{course_id}"
    return _mem_flashcards.get(key, [])


def list_concepts(learner_id: str, course_id: str) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    db = get_db()
    if db:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            query = (
                db.collection("concepts")
                .where(filter=FieldFilter("learnerId", "==", learner_id))
                .where(filter=FieldFilter("courseId", "==", course_id))
            )
            docs = query.stream()
            concepts = []
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
        except Exception as e:
            print(f"Notice: Firestore list_concepts fallback: {e}")

    # In-memory fallback
    concepts = []
    for c in _mem_concepts.values():
        if c.get("learnerId") == learner_id and c.get("courseId") == course_id:
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
    if db:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            query = (
                db.collection("concepts")
                .where(filter=FieldFilter("learnerId", "==", learner_id))
                .where(filter=FieldFilter("courseId", "==", course_id))
                .where(filter=FieldFilter("name", "==", concept_name))
                .limit(1)
            )
            docs = list(query.stream())
            if docs:
                c = docs[0].to_dict()
                c["id"] = docs[0].id
                c["effectiveMastery"] = compute_effective_mastery(
                    mastery=c.get("mastery", 0.0),
                    last_assessed_at=c.get("lastAssessedAt"),
                    half_life_days=c.get("halfLifeDays", 7.0),
                    current_time=datetime.now(timezone.utc)
                )
                return c
        except Exception as e:
            print(f"Notice: Firestore get_concept fallback: {e}")

    # In-memory fallback
    key = f"{learner_id}:{course_id}:{concept_name}"
    if key in _mem_concepts:
        c = _mem_concepts[key]
        c["effectiveMastery"] = compute_effective_mastery(
            mastery=c.get("mastery", 0.0),
            last_assessed_at=c.get("lastAssessedAt"),
            half_life_days=c.get("halfLifeDays", 7.0),
            current_time=datetime.now(timezone.utc)
        )
        return c
    return None


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
    existing = get_concept(learner_id, course_id, concept_name)
    now = datetime.now(timezone.utc)
    
    if half_life_days is None:
        half_life_days = compute_half_life_days(attempts)
    if last_assessed_at is None:
        last_assessed_at = now
        
    history = []
    if existing:
        history = existing.get("history", [])
    if history_entry:
        history.append(history_entry)

    data = {
        "id": (existing and existing.get("id")) or f"{learner_id}_{course_id}_{concept_name}".replace(" ", "_"),
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

    db = get_db()
    if db:
        try:
            doc_ref = db.collection("concepts").document(data["id"])
            doc_ref.set(data, merge=True)
        except Exception as e:
            print(f"Notice: Firestore upsert_concept fallback: {e}")

    key = f"{learner_id}:{course_id}:{concept_name}"
    _mem_concepts[key] = data
    return data


def record_quiz_attempt(
    learner_id: str,
    course_id: str,
    concept_names: List[str],
    score: float,
    items: List[Dict[str, Any]]
) -> str:
    import uuid
    attempt_id = str(uuid.uuid4())
    data = {
        "id": attempt_id,
        "learnerId": learner_id,
        "courseId": course_id,
        "conceptNames": concept_names,
        "score": float(score),
        "items": items,
        "createdAt": datetime.now(timezone.utc)
    }
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("quizAttempts").document(attempt_id)
            doc_ref.set(data)
        except Exception as e:
            print(f"Notice: Firestore record_quiz_attempt fallback: {e}")
    return attempt_id


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
    import uuid
    nudge_id = str(uuid.uuid4())
    data = {
        "id": nudge_id,
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
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("pendingNudges").document(nudge_id)
            doc_ref.set(data)
        except Exception as e:
            print(f"Notice: Firestore create_pending_nudge fallback: {e}")
    _mem_nudges[nudge_id] = data
    return nudge_id


def list_pending_nudges(
    learner_id: str,
    course_id: Optional[str] = None,
    status: Optional[str] = "pending"
) -> List[Dict[str, Any]]:
    db = get_db()
    if db:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
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
        except Exception as e:
            print(f"Notice: Firestore list_pending_nudges fallback: {e}")

    # In-memory fallback
    results = []
    for n in _mem_nudges.values():
        if n.get("learnerId") == learner_id:
            if course_id and n.get("courseId") != course_id:
                continue
            if status and n.get("status") != status:
                continue
            results.append(n)
    return results


def update_nudge_status(nudge_id: str, status: str) -> bool:
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("pendingNudges").document(nudge_id)
            snapshot = doc_ref.get()
            if snapshot.exists:
                doc_ref.update({"status": status, "updatedAt": datetime.now(timezone.utc)})
                return True
        except Exception as e:
            print(f"Notice: Firestore update_nudge_status fallback: {e}")
    if nudge_id in _mem_nudges:
        _mem_nudges[nudge_id]["status"] = status
        _mem_nudges[nudge_id]["updatedAt"] = datetime.now(timezone.utc)
        return True
    return False


def record_event(event_type: str, payload: Dict[str, Any]) -> str:
    db = get_db()
    if db:
        try:
            doc_ref = db.collection("events").document()
            doc_ref.set({
                "type": event_type,
                "payload": payload,
                "createdAt": datetime.now(timezone.utc)
            })
            return doc_ref.id
        except Exception:
            pass
    return ""
