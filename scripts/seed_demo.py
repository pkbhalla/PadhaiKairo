import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import (
    get_or_create_learner,
    get_or_create_course,
    upsert_concept,
    list_concepts,
    record_event,
    add_study_source
)
from ingest import ingest_all_demo_lectures


def seed_demo_data():
    print("\n" + "="*65)
    print("SEEDING MULTI-USER DEMO DATA (PRIYA & ROHAN)")
    print("="*65)

    now = datetime.now(timezone.utc)

    # ==========================================================
    # USER 1: Priya Sharma (Course: DBMS, Exam in 5 days)
    # ==========================================================
    learner_priya = get_or_create_learner(
        learner_id="priya",
        name="Priya Sharma",
        email="abhi20b02@gmail.com",
        tz="Asia/Kolkata"
    )
    exam_priya = now + timedelta(days=5)
    course_priya = get_or_create_course(
        learner_id="priya",
        course_id="dbms",
        course_data={
            "title": "Database Management Systems (DBMS)",
            "examDate": exam_priya,
            "syllabusTopics": [
                "ER Modeling",
                "Relational Algebra",
                "SQL & Joins",
                "Normalization",
                "Transactions & ACID",
                "Indexing & B-Trees"
            ]
        }
    )
    ingest_all_demo_lectures(learner_id="priya", course_id="dbms")

    ten_days_ago = now - timedelta(days=10)
    two_days_ago = now - timedelta(days=2)
    three_days_ago = now - timedelta(days=3)
    four_days_ago = now - timedelta(days=4)

    # Priya: Decayed Normalization (0.38)
    upsert_concept(
        learner_id="priya",
        course_id="dbms",
        concept_name="Normalization",
        mastery=0.76,
        attempts=2,
        half_life_days=10.0,
        last_assessed_at=ten_days_ago,
        next_review_at=ten_days_ago + timedelta(days=10),
        history_entry={"timestamp": ten_days_ago.isoformat(), "score": 0.76, "masteryAfter": 0.76}
    )
    upsert_concept(
        learner_id="priya",
        course_id="dbms",
        concept_name="ER Modeling",
        mastery=0.90,
        attempts=3,
        half_life_days=21.0,
        last_assessed_at=two_days_ago,
        next_review_at=two_days_ago + timedelta(days=21),
        history_entry={"timestamp": two_days_ago.isoformat(), "score": 0.90, "masteryAfter": 0.90}
    )
    upsert_concept(
        learner_id="priya",
        course_id="dbms",
        concept_name="Relational Algebra",
        mastery=0.85,
        attempts=2,
        half_life_days=14.0,
        last_assessed_at=three_days_ago,
        next_review_at=three_days_ago + timedelta(days=14),
        history_entry={"timestamp": three_days_ago.isoformat(), "score": 0.85, "masteryAfter": 0.85}
    )
    upsert_concept(
        learner_id="priya",
        course_id="dbms",
        concept_name="SQL & Joins",
        mastery=0.70,
        attempts=1,
        half_life_days=7.0,
        last_assessed_at=four_days_ago,
        next_review_at=four_days_ago + timedelta(days=7),
        history_entry={"timestamp": four_days_ago.isoformat(), "score": 0.70, "masteryAfter": 0.70}
    )

    print(f"[User 1] Priya Sharma ({course_priya['title']}) seeded.")

    # ==========================================================
    # USER 2: Rohan Verma (Course: Operating Systems, Exam in 3 days)
    # ==========================================================
    learner_rohan = get_or_create_learner(
        learner_id="rohan",
        name="Rohan Verma",
        email="abhi20b02@gmail.com",
        tz="Asia/Kolkata"
    )
    exam_rohan = now + timedelta(days=3)
    course_rohan = get_or_create_course(
        learner_id="rohan",
        course_id="os",
        course_data={
            "title": "Operating Systems (OS Core)",
            "examDate": exam_rohan,
            "syllabusTopics": [
                "Process Scheduling",
                "Deadlocks & Sync",
                "Virtual Memory",
                "File Systems",
                "Paging & TLB"
            ]
        }
    )

    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    # Rohan: Decayed Deadlocks (0.42)
    upsert_concept(
        learner_id="rohan",
        course_id="os",
        concept_name="Deadlocks & Sync",
        mastery=0.84,
        attempts=2,
        half_life_days=7.0,
        last_assessed_at=seven_days_ago,
        next_review_at=seven_days_ago + timedelta(days=7),
        history_entry={"timestamp": seven_days_ago.isoformat(), "score": 0.84, "masteryAfter": 0.84}
    )
    upsert_concept(
        learner_id="rohan",
        course_id="os",
        concept_name="Process Scheduling",
        mastery=0.92,
        attempts=3,
        half_life_days=21.0,
        last_assessed_at=one_day_ago,
        next_review_at=one_day_ago + timedelta(days=21),
        history_entry={"timestamp": one_day_ago.isoformat(), "score": 0.92, "masteryAfter": 0.92}
    )
    upsert_concept(
        learner_id="rohan",
        course_id="os",
        concept_name="Virtual Memory",
        mastery=0.68,
        attempts=1,
        half_life_days=7.0,
        last_assessed_at=four_days_ago,
        next_review_at=four_days_ago + timedelta(days=7),
        history_entry={"timestamp": four_days_ago.isoformat(), "score": 0.68, "masteryAfter": 0.68}
    )

    print(f"[User 2] Rohan Verma ({course_rohan['title']}) seeded.")
    print("\nMulti-user profiles ready for seamless switching!")


if __name__ == "__main__":
    seed_demo_data()
