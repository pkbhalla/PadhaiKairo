import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.config import DEV_BYPASS, TOKEN_FILE
from core.db import (
    list_all_learners,
    get_or_create_learner,
    get_learner_profile,
    update_learner_profile,
    get_or_create_course,
    update_course,
    list_courses_for_learner,
    list_concepts,
    upsert_concept,
    list_pending_nudges,
    update_nudge_status,
    add_study_source,
    list_study_sources,
    list_flashcard_decks,
    record_event
)
from ingest import fetch_youtube_transcript, extract_youtube_video_id
from agents.coach import handle_coach_interaction
from agents.quizmaster import generate_quiz, grade_quiz
from agents.planner import generate_revision_plan
from agents.watchdog import run_retention_guardian_scan
from agents.study_guide import generate_study_guide
from agents.flashcards import generate_flashcards
from tools.gmail_tools import send_email
from google_auth import (
    get_authorization_url,
    exchange_code_for_token,
    get_oauth_credentials,
    get_user_info,
    logout as auth_logout,
    is_authenticated,
)

app = FastAPI(
    title="PadhaiKairo",
    description="Autonomous Spaced Mastery Guardian & AI Study Platform",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Pydantic Request Models
class CreateCourseRequest(BaseModel):
    learner_id: str
    learner_name: Optional[str] = "Student"
    learner_email: Optional[str] = "learner@example.com"
    course_title: str
    subtopics: List[str]
    exam_date_iso: Optional[str] = None
    lecture_notes: Optional[str] = None
    youtube_url: Optional[str] = None


class UpdateCourseRequest(BaseModel):
    learner_id: str
    course_id: str
    course_title: Optional[str] = None
    exam_date_iso: Optional[str] = None
    subtopics: Optional[List[str]] = None


class UpdateProfileRequest(BaseModel):
    learner_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    timezone: Optional[str] = None
    daily_goal_minutes: Optional[int] = 30
    study_pace: Optional[str] = "moderate"


class YouTubeFetchRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    message: str
    learner_id: str = "guest"
    course_id: str = "general"


class StudyGuideRequest(BaseModel):
    topic: str
    learner_id: str = "guest"
    course_id: str = "general"


class FlashcardsRequest(BaseModel):
    topic: str
    count: int = 6
    learner_id: str = "guest"
    course_id: str = "general"


class AddSourceRequest(BaseModel):
    title: str
    source_type: str = "text_note"
    content: str
    learner_id: str = "guest"
    course_id: str = "general"


class QuizGenerateRequest(BaseModel):
    topic: str
    num_questions: int = 5
    difficulty: str = "medium"
    learner_id: str = "guest"
    course_id: str = "general"


class QuizGradeRequest(BaseModel):
    concept_name: str
    questions: List[Dict[str, Any]]
    answers: Dict[str, int]
    learner_id: str = "guest"
    course_id: str = "general"


class PlanRequest(BaseModel):
    learner_id: str = "guest"
    course_id: str = "general"
    exam_date_iso: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """Smart root: redirect authenticated users to /app, else serve landing page."""
    if is_authenticated():
        return RedirectResponse(url="/app", status_code=302)
    landing_path = static_dir / "landing.html"
    if landing_path.exists():
        return HTMLResponse(content=landing_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>PadhaiKairo — Loading...</h1>")


@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    """Serve main app shell. Redirect to / if not authenticated."""
    if not is_authenticated():
        return RedirectResponse(url="/", status_code=302)
    app_path = static_dir / "app.html"
    if app_path.exists():
        return HTMLResponse(content=app_path.read_text(encoding="utf-8"))
    # Fallback: old index.html
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>App not found</h1>", status_code=404)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = static_dir / "favicon.ico"
    if fav_path.exists():
        return FileResponse(fav_path)
    return HTMLResponse("", status_code=404)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.2.0"}


def get_callback_uri(request: Request) -> str:
    """Dynamically determine the OAuth callback URI for local dev or Cloud Run."""
    override = os.getenv("OAUTH_REDIRECT_URI")
    if override:
        return override
    
    # Check headers for Cloud Run / HTTPS reverse proxy
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    
    if "run.app" in host:
        proto = "https"
        
    return f"{proto}://{host}/auth/callback"


# Google OAuth Routes
@app.get("/auth/login")
async def auth_login(request: Request):
    """Redirect user to Google OAuth authorization page."""
    try:
        redirect_uri = get_callback_uri(request)
        auth_url = get_authorization_url(redirect_uri=redirect_uri)
        return RedirectResponse(url=auth_url, status_code=302)
    except Exception as e:
        return HTMLResponse(
            f"<h2>OAuth Setup Error: {e}</h2><p>Please check Google OAuth client configuration.</p><a href='/'>Back to PadhaiKairo</a>",
            status_code=500
        )


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    """Handle Google OAuth callback, exchange code for token, redirect to /app."""
    if error:
        return HTMLResponse(
            f"<h2>OAuth Error: {error}</h2><a href='/'>Back to PadhaiKairo</a>",
            status_code=400
        )
    if not code:
        return RedirectResponse(url="/", status_code=302)
    try:
        redirect_uri = get_callback_uri(request)
        creds = exchange_code_for_token(code, redirect_uri=redirect_uri)
        if creds:
            info = get_user_info(creds)
            email = info.get("email")
            if email:
                lid = email.split("@")[0].replace(".", "_")
                get_or_create_learner(
                    learner_id=lid,
                    name=info.get("name") or email.split("@")[0].title(),
                    email=email
                )
        return RedirectResponse(url="/app", status_code=302)
    except Exception as e:
        return HTMLResponse(
            f"<h2>Authentication failed: {e}</h2><a href='/'>Try again</a>",
            status_code=500
        )


@app.get("/auth/logout")
async def auth_logout_endpoint():
    """Clear token and redirect to landing page."""
    auth_logout()
    return RedirectResponse(url="/", status_code=302)


@app.get("/auth/status")
async def auth_status_endpoint():
    """Returns current authentication state and user info."""
    creds = get_oauth_credentials()
    if not creds:
        return {"authenticated": False, "email": None, "name": "Guest", "learnerId": "guest"}
    try:
        info = get_user_info(creds)
        email = info.get("email")
        name = info.get("name") or (email.split("@")[0].title() if email else "Student")
        picture = info.get("picture", "")
        learner_id = email.split("@")[0].replace(".", "_") if email else "guest"
        
        if email:
            get_or_create_learner(
                learner_id=learner_id,
                name=name,
                email=email
            )
            
        return {
            "authenticated": True,
            "learnerId": learner_id,
            "email": email,
            "name": name,
            "picture": picture,
        }
    except Exception as e:
        return {"authenticated": False, "email": None, "error": str(e), "learnerId": "guest"}



@app.get("/home/summary")
async def home_summary_endpoint(learner_id: str = "guest"):
    """Return dashboard summary: greeting, priority concept, streak, exam countdown."""
    from datetime import datetime
    import random

    hour = datetime.now().hour
    if hour < 12:
        greeting_time = "Good morning"
    elif hour < 17:
        greeting_time = "Good afternoon"
    else:
        greeting_time = "Good evening"

    courses = list_courses_for_learner(learner_id)
    total_sources = 0
    priority_concept = None
    exam_days_left = None

    for course in courses:
        cid = course.get("id", "")
        concepts = list_concepts(learner_id, cid)
        sources = list_study_sources(learner_id, cid)
        total_sources += len(sources)

        if concepts:
            weakest = min(concepts, key=lambda c: c.get("effectiveMastery", 1.0))
            if priority_concept is None or weakest.get("effectiveMastery", 1.0) < priority_concept.get("effectiveMastery", 1.0):
                priority_concept = weakest
                priority_concept["courseTitle"] = course.get("title", cid)

        if not exam_days_left and course.get("examDate"):
            try:
                exam_dt = course["examDate"]
                if hasattr(exam_dt, "timestamp"):
                    days = max(0, (exam_dt.replace(tzinfo=None) - datetime.utcnow()).days)
                else:
                    days = 0
                exam_days_left = days
            except Exception:
                pass

    creds = get_oauth_credentials()
    user_name = "Student"
    if creds:
        try:
            info = get_user_info(creds)
            user_name = info.get("name", "").split()[0] if info.get("name") else "Student"
        except Exception:
            pass

    return {
        "greeting": f"{greeting_time}, {user_name}!",
        "userName": user_name,
        "totalSubjects": len(courses),
        "totalSources": total_sources,
        "examDaysLeft": exam_days_left,
        "priorityConcept": priority_concept,
    }


# YouTube Transcript Extractor Endpoint
@app.post("/youtube/fetch-transcript")
async def youtube_fetch_endpoint(req: YouTubeFetchRequest):
    """Fetch clean transcript from a YouTube URL or Video ID."""
    result = fetch_youtube_transcript(req.url)
    return result


# Dynamic Course Creation & Ingestion
@app.post("/courses/create")
async def create_course_endpoint(req: CreateCourseRequest):
    """
    Create a new course dynamically:
    1. Upsert learner profile.
    2. Register course title, subtopics, exam date.
    3. Ingest pasted lecture notes or fetch YouTube transcript.
    4. Initialize concept mastery graph for all subtopics.
    5. Schedule initial spaced revision blocks in Google Calendar.
    """
    now = datetime.now(timezone.utc)
    course_id = req.course_title.lower().replace(" ", "_").replace("&", "and")
    course_id = "".join([c for c in course_id if c.isalnum() or c == "_"])
    
    # 1. Parse or calculate exam date
    if req.exam_date_iso:
        exam_dt = datetime.fromisoformat(req.exam_date_iso.replace("Z", "+00:00"))
    else:
        exam_dt = now + timedelta(days=5)

    # 2. Register learner & course
    email = req.learner_email
    if not email or "example.com" in email:
        creds = get_oauth_credentials()
        if creds:
            try:
                info = get_user_info(creds)
                email = info.get("email") or email
            except Exception:
                pass
    if not email:
        email = f"{req.learner_id}@gmail.com"

    learner = get_or_create_learner(
        learner_id=req.learner_id,
        name=req.learner_name or "Student",
        email=email
    )
    course = get_or_create_course(
        learner_id=req.learner_id,
        course_id=course_id,
        course_data={
            "title": req.course_title,
            "examDate": exam_dt,
            "syllabusTopics": req.subtopics
        }
    )

    # 3. Ingest YouTube transcript if provided
    ingested_sources = []
    if req.youtube_url:
        yt_res = fetch_youtube_transcript(req.youtube_url)
        if yt_res.get("success") and yt_res.get("text"):
            source = add_study_source(
                learner_id=req.learner_id,
                course_id=course_id,
                title=f"{req.course_title} - Video Lecture Notes",
                source_type="youtube_transcript",
                content=yt_res.get("text"),
                source_url=req.youtube_url
            )
            ingested_sources.append(source)

    # 4. Ingest pasted notes if provided
    if req.lecture_notes:
        source = add_study_source(
            learner_id=req.learner_id,
            course_id=course_id,
            title=f"{req.course_title} - Ingested Notes",
            source_type="text_note",
            content=req.lecture_notes
        )
        ingested_sources.append(source)

    # 5. Initialize Mastery Graph for each subtopic
    created_concepts = []
    for idx, topic in enumerate(req.subtopics):
        is_decayed = (idx == 0 or idx == 2)
        days_ago = 8 if is_decayed else 2
        assessed_date = now - timedelta(days=days_ago)
        base_score = 0.75 if is_decayed else 0.88
        
        c = upsert_concept(
            learner_id=req.learner_id,
            course_id=course_id,
            concept_name=topic,
            mastery=base_score,
            attempts=2 if is_decayed else 3,
            half_life_days=10.0 if is_decayed else 21.0,
            last_assessed_at=assessed_date,
            next_review_at=assessed_date + timedelta(days=10),
            history_entry={"timestamp": assessed_date.isoformat(), "score": base_score, "masteryAfter": base_score}
        )
        created_concepts.append(c)

    # 6. Autonomous Calendar Revision Plan
    try:
        plan_res = generate_revision_plan(
            learner_id=req.learner_id,
            course_id=course_id,
            exam_date_iso=exam_dt.isoformat()
        )
    except Exception:
        plan_res = {"totalSessions": len(req.subtopics), "calendarEventsCreated": 0}

    record_event("course_created", {
        "learnerId": req.learner_id,
        "courseId": course_id,
        "courseTitle": req.course_title,
        "topicsCount": len(req.subtopics)
    })

    return {
        "status": "created",
        "courseId": course_id,
        "learner": learner,
        "course": course,
        "concepts": created_concepts,
        "sources": ingested_sources,
        "calendarPlan": plan_res
    }


# List courses for learner
@app.get("/courses")
async def list_courses_endpoint(learner_id: str = "guest"):
    courses = list_courses_for_learner(learner_id)
    return {"courses": courses}


# Update Course Details (Exam Date, Title, Subtopics)
@app.post("/courses/{course_id}/update")
@app.post("/courses/update")
async def update_course_endpoint(req: UpdateCourseRequest):
    """
    Update course details like target exam date, title, or subtopics.
    Automatically recalculates the remaining days to exam and updates the calendar revision plan.
    """
    update_data = {}
    if req.course_title:
        update_data["title"] = req.course_title
    
    exam_dt = None
    if req.exam_date_iso:
        try:
            exam_dt = datetime.fromisoformat(req.exam_date_iso.replace("Z", "+00:00"))
            update_data["examDate"] = exam_dt
        except Exception:
            pass
            
    if req.subtopics is not None:
        update_data["syllabusTopics"] = req.subtopics
        now = datetime.now(timezone.utc)
        for topic in req.subtopics:
            upsert_concept(
                learner_id=req.learner_id,
                course_id=req.course_id,
                concept_name=topic,
                mastery=0.75,
                attempts=1,
                half_life_days=14.0,
                last_assessed_at=now,
                next_review_at=now + timedelta(days=7),
                history_entry={"timestamp": now.isoformat(), "score": 0.75, "masteryAfter": 0.75}
            )

    updated_course = update_course(req.learner_id, req.course_id, update_data)
    
    # Calculate days left
    now = datetime.now(timezone.utc)
    days_left = None
    if exam_dt:
        days_left = max(0, (exam_dt - now).days)

    # Automatically recompute and sync calendar revision plan with new exam date
    plan_res = None
    if exam_dt:
        try:
            plan_res = generate_revision_plan(
                learner_id=req.learner_id,
                course_id=req.course_id,
                exam_date_iso=exam_dt.isoformat()
            )
        except Exception as e:
            plan_res = {"status": "skipped", "error": str(e)}

    record_event("course_updated", {
        "learnerId": req.learner_id,
        "courseId": req.course_id,
        "daysUntilExam": days_left
    })
    
    return {
        "status": "success",
        "course": updated_course,
        "examDaysLeft": days_left,
        "calendarPlan": plan_res
    }


# Learner Profile Management
@app.get("/learner/profile")
async def get_profile_endpoint(learner_id: str = "guest"):
    """Fetch learner profile data."""
    profile = get_learner_profile(learner_id)
    if not profile:
        profile = get_or_create_learner(learner_id)
    return {"profile": profile}


@app.post("/learner/profile")
async def update_profile_endpoint(req: UpdateProfileRequest):
    """Update learner profile settings."""
    update_data = {}
    if req.name is not None:
        update_data["name"] = req.name
    if req.email is not None:
        update_data["email"] = req.email
    if req.timezone is not None:
        update_data["timezone"] = req.timezone
    if req.daily_goal_minutes is not None:
        update_data["dailyGoalMinutes"] = req.daily_goal_minutes
    if req.study_pace is not None:
        update_data["studyPace"] = req.study_pace

    updated = update_learner_profile(req.learner_id, update_data)
    record_event("profile_updated", {"learnerId": req.learner_id})
    return {"status": "success", "profile": updated}


# Socratic Coach Chat
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    return handle_coach_interaction(
        message=req.message,
        learner_id=req.learner_id,
        course_id=req.course_id
    )


# Mastery Graph (Real-time decay engine)
@app.get("/mastery")
async def get_mastery_endpoint(learner_id: str = "guest", course_id: str = "general"):
    concepts = list_concepts(learner_id, course_id)
    course = get_or_create_course(learner_id, course_id)
    learner = get_or_create_learner(learner_id)
    return {
        "learner": learner,
        "course": course,
        "concepts": concepts
    }


# NotebookLM Study Guide Generator
@app.post("/study-guide/generate")
async def study_guide_endpoint(req: StudyGuideRequest):
    guide = generate_study_guide(
        topic=req.topic,
        learner_id=req.learner_id,
        course_id=req.course_id
    )
    return guide


# NotebookLM Spaced Flashcards
@app.post("/flashcards/generate")
async def flashcards_generate_endpoint(req: FlashcardsRequest):
    deck = generate_flashcards(
        topic=req.topic,
        count=req.count,
        learner_id=req.learner_id,
        course_id=req.course_id
    )
    return deck


@app.get("/flashcards")
async def flashcards_list_endpoint(learner_id: str = "guest", course_id: str = "general"):
    decks = list_flashcard_decks(learner_id, course_id)
    return {"decks": decks}


# Multimodal Sources Ingestion
@app.post("/sources/add")
async def add_source_endpoint(req: AddSourceRequest):
    source = add_study_source(
        learner_id=req.learner_id,
        course_id=req.course_id,
        title=req.title,
        source_type=req.source_type,
        content=req.content
    )
    return source


@app.get("/sources")
async def list_sources_endpoint(learner_id: str = "guest", course_id: str = "general"):
    sources = list_study_sources(learner_id, course_id)
    return {"sources": sources}


# Practice Quizzes
@app.post("/quiz/generate")
async def quiz_generate_endpoint(req: QuizGenerateRequest):
    quiz_data = generate_quiz(
        topic=req.topic,
        num_questions=req.num_questions,
        learner_id=req.learner_id,
        course_id=req.course_id
    )
    return quiz_data


@app.post("/quiz/grade")
async def quiz_grade_endpoint(req: QuizGradeRequest):
    grade_res = grade_quiz(
        learner_id=req.learner_id,
        course_id=req.course_id,
        concept_name=req.concept_name,
        questions=req.questions,
        user_answers=req.answers
    )
    return grade_res


# Autonomous Calendar Revision Planning
@app.post("/plan")
async def plan_endpoint(req: PlanRequest):
    plan_data = generate_revision_plan(
        learner_id=req.learner_id,
        course_id=req.course_id,
        exam_date_iso=req.exam_date_iso
    )
    return plan_data


# Human-In-The-Loop (HITL) Study Nudges
@app.get("/nudges")
async def list_nudges_endpoint(
    learner_id: str = "guest",
    course_id: Optional[str] = None,
    status: Optional[str] = "pending"
):
    nudges = list_pending_nudges(learner_id, course_id=course_id, status=status)
    return {"nudges": nudges}


@app.post("/nudges/{nudge_id}/approve")
async def approve_nudge_endpoint(nudge_id: str, learner_id: str = "guest"):
    all_nudges = list_pending_nudges(learner_id, course_id=None, status=None)
    target_nudge = next((n for n in all_nudges if n.get("id") == nudge_id), None)
    
    if not target_nudge:
        raise HTTPException(status_code=404, detail="Nudge not found")
        
    if target_nudge.get("status") == "sent":
        return {"status": "already_sent", "nudgeId": nudge_id}

    draft = target_nudge.get("emailDraft", {})
    to_email = draft.get("to")
    subject = draft.get("subject", "Learning Coach Study Nudge")
    body = draft.get("body", "")

    # Ensure to_email is resolved properly to the learner
    if not to_email or "@" not in to_email or "example.com" in to_email:
        learner_prof = get_learner_profile(learner_id)
        if learner_prof and learner_prof.get("email"):
            to_email = learner_prof.get("email")
        else:
            creds = get_oauth_credentials()
            if creds:
                try:
                    info = get_user_info(creds)
                    to_email = info.get("email") or to_email
                except Exception:
                    pass

    if not to_email or not body:
        raise HTTPException(status_code=400, detail="Invalid email draft")

    mail_res = send_email(to_email=to_email, subject=subject, body_text=body)
    update_nudge_status(nudge_id, "sent")

    return {
        "status": "approved_and_sent",
        "nudgeId": nudge_id,
        "messageId": mail_res.get("messageId"),
        "to": to_email
    }


# Autonomous Retention Guardian (Nightly scan or on-demand trigger)
@app.post("/guardian/scan")
@app.post("/internal/watchdog")
async def retention_guardian_endpoint(
    request: Request,
    learner_id: str = "guest",
    course_id: str = "general",
    authorization: Optional[str] = Header(None)
):
    is_authorized = DEV_BYPASS
    if not is_authorized and authorization:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as grequests
            token = authorization.replace("Bearer ", "").strip()
            id_info = id_token.verify_oauth2_token(token, grequests.Request())
            is_authorized = bool(id_info)
        except Exception:
            is_authorized = False

    if not is_authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")

    result = run_retention_guardian_scan(learner_id, course_id)
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
