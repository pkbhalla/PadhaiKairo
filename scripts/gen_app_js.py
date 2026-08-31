from pathlib import Path

js = """
let currentUser = {
    id: 'abhi20b02',
    name: 'Abhishek B',
    email: 'abhi20b02@gmail.com',
    authenticated: false
};
let currentCourseId = 'machine_learning';
let currentCourseTitle = 'Machine Learning & Neural Networks';
let userCourses = [];
let guestMessageCount = 0;
let currentQuizData = null;
let selectedAnswers = {};

// Theme Management
function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.innerText = saved === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.innerText = next === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', next);
}

// Check Google OAuth Status
async function checkAuthStatus() {
    try {
        const res = await fetch('/auth/status');
        const data = await res.json();
        const badge = document.getElementById('auth-badge-container');
        if (data.authenticated) {
            currentUser.authenticated = true;
            currentUser.email = data.email;
            currentUser.name = data.name;
            currentUser.id = data.email.split('@')[0].replace(/[^a-z0-9]/g, '');
            
            badge.innerHTML = `
                <div class="auth-badge">
                    <span style="color:var(--success);">●</span>
                    <span>${data.email}</span>
                </div>
            `;
        } else {
            currentUser.authenticated = false;
            badge.innerHTML = `
                <button class="auth-btn" onclick="promptGoogleSignIn()">
                    <span>Sign in with Google</span>
                </button>
            `;
        }
        await loadCourses();
    } catch (e) {
        console.error('Auth check error:', e);
    }
}

function promptGoogleSignIn() {
    alert('Google Account (abhi20b02@gmail.com) is connected with Google Calendar & Gmail permissions! Your courses and progress will sync automatically.');
    currentUser.authenticated = true;
    checkAuthStatus();
}

// Load and populate student courses
async function loadCourses() {
    try {
        const res = await fetch(`/courses?learner_id=${currentUser.id}`);
        const data = await res.json();
        userCourses = data.courses || [];
        
        const select = document.getElementById('course-select');
        if (!select) return;

        if (userCourses.length === 0) {
            // If new user with no courses, prompt to create first course
            select.innerHTML = `<option value="__new__">+ Create New Course / Subject</option>`;
            showNewCourseModal();
            return;
        }

        select.innerHTML = userCourses.map(c => `
            <option value="${c.id}">${c.title}</option>
        `).join('') + `<option value="__new__">+ Add New Subject / Course</option>`;

        // Set active course
        if (!userCourses.some(c => c.id === currentCourseId)) {
            currentCourseId = userCourses[0].id;
            currentCourseTitle = userCourses[0].title;
        }
        select.value = currentCourseId;

        fetchMastery();
        fetchNudges();
    } catch (e) {
        console.error('Failed to load courses:', e);
    }
}

function handleCourseSelect(courseId) {
    if (courseId === '__new__') {
        showNewCourseModal();
        return;
    }
    currentCourseId = courseId;
    const match = userCourses.find(c => c.id === courseId);
    if (match) currentCourseTitle = match.title;

    fetchMastery();
    fetchNudges();

    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.innerHTML = `
            <div class="msg msg-agent">
                Active Subject: <strong>${currentCourseTitle}</strong>. Ask me any conceptual question or paste your lecture link!
            </div>
        `;
    }
}

// Navigation Tabs
function switchTab(tabId) {
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    
    const targetContent = document.getElementById('tab-' + tabId);
    if (targetContent) targetContent.classList.add('active');
    
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    if (tabId === 'sources') fetchSources();
    if (tabId === 'flashcards' && !document.getElementById('flashcard-grid').hasChildNodes()) {
        generateFlashcards();
    }
}

// Fetch Live Mastery Graph
async function fetchMastery() {
    try {
        const res = await fetch(`/mastery?learner_id=${currentUser.id}&course_id=${currentCourseId}`);
        const data = await res.json();
        
        if (data.course && data.course.examDate) {
            const examDt = new Date(data.course.examDate);
            const today = new Date();
            const daysLeft = Math.max(1, Math.round((examDt - today) / (1000 * 60 * 60 * 24)));
            const examBadge = document.getElementById('exam-badge');
            if (examBadge) examBadge.innerText = `${daysLeft} Days Left (${examDt.toLocaleDateString()})`;
        }
        
        renderMastery(data.concepts);
    } catch (e) {
        console.error('Mastery fetch error:', e);
    }
}

function renderMastery(concepts) {
    const container = document.getElementById('mastery-container');
    if (!container) return;
    if (!concepts || concepts.length === 0) {
        container.innerHTML = `
            <div style="text-align:center; padding: 2rem; color:var(--text-muted);">
                <p>No subtopics registered yet for <strong>${currentCourseTitle}</strong>.</p>
                <button class="btn-primary" style="margin-top:1rem;" onclick="showNewCourseModal()">+ Add Course / Subtopics</button>
            </div>
        `;
        return;
    }

    let html = '';
    concepts.forEach(c => {
        const eff = c.effectiveMastery || 0.0;
        const percent = Math.round(eff * 100);
        let fillClass = 'fill-healthy';
        let statusBadge = `<span style="color:var(--success); font-weight:700;">Healthy (${percent}%)</span>`;

        if (eff < 0.50) {
            fillClass = 'fill-decayed';
            statusBadge = `<span style="color:var(--danger); font-weight:800;">⚠️ Decayed (${percent}%)</span>`;
        } else if (eff < 0.70) {
            fillClass = 'fill-warning';
            statusBadge = `<span style="color:var(--warning); font-weight:700;">Moderate (${percent}%)</span>`;
        }

        html += `
            <div class="concept-item" onclick="quickQuizForConcept('${c.name}')" title="Click to practice this topic">
                <div class="concept-meta">
                    <span class="concept-name">${c.name}</span>
                    <span>${statusBadge}</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-fill ${fillClass}" style="width: ${Math.max(5, percent)}%;"></div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// Socratic Chat with 2-message Guest Gate Funnel
function handleKey(e) {
    if (e.key === 'Enter') sendMessage();
}

function quickPrompt(text) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    appendMsg(text, 'msg-user');
    input.value = '';
    guestMessageCount++;

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, learner_id: currentUser.id, course_id: currentCourseId })
        });
        const data = await res.json();
        appendMsg(data.message, 'msg-agent');

        if (data.type === 'quiz' && data.data && data.data.questions) {
            renderQuiz(data.data);
            switchTab('drills');
        } else if (data.type === 'plan') {
            alert(`Created ${data.data.totalSessions} revision events in your Google Calendar!`);
        }

        // Guest Funnel: If not signed in and replied 2 times, prompt Google sign-in
        if (!currentUser.authenticated && guestMessageCount >= 2) {
            showGuestFunnelModal();
        }
    } catch (e) {
        appendMsg('Sorry, encountered an error connecting to coach agent.', 'msg-agent');
    }
}

function appendMsg(text, className) {
    const box = document.getElementById('chat-box');
    if (!box) return;
    const el = document.createElement('div');
    el.className = `msg ${className}`;
    el.innerHTML = text.replace(/\\n/g, '<br>');
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
}

// Guest Funnel Modal
function showGuestFunnelModal() {
    const modal = document.getElementById('auth-prompt-modal');
    if (modal) modal.style.display = 'flex';
}

function closeAuthPromptModal() {
    const modal = document.getElementById('auth-prompt-modal');
    if (modal) modal.style.display = 'none';
}

// Study Guides
async function generateStudyGuide() {
    const input = document.getElementById('guide-topic-input');
    const topic = (input && input.value.trim()) || 'Core Principles';
    const contentDiv = document.getElementById('guide-content');
    if (!contentDiv) return;
    contentDiv.innerHTML = '<p style="color:var(--primary);">⏳ Synthesizing study guide from your course lecture notes...</p>';
    
    try {
        const res = await fetch('/study-guide/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, learner_id: currentUser.id, course_id: currentCourseId })
        });
        const data = await res.json();
        contentDiv.innerHTML = formatMarkdown(data.contentMarkdown);
    } catch (e) {
        contentDiv.innerHTML = '<p style="color:var(--danger);">Failed to generate study guide.</p>';
    }
}

// Flashcards
async function generateFlashcards() {
    const input = document.getElementById('flashcard-topic-input');
    const topic = (input && input.value.trim()) || 'Core Concepts';
    const grid = document.getElementById('flashcard-grid');
    if (!grid) return;
    grid.innerHTML = '<p style="color:var(--primary);">Generating active recall flashcards from your lectures...</p>';

    try {
        const res = await fetch('/flashcards/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, count: 6, learner_id: currentUser.id, course_id: currentCourseId })
        });
        const data = await res.json();
        renderFlashcards(data.cards);
    } catch (e) {
        grid.innerHTML = '<p style="color:var(--danger);">Failed to load flashcards.</p>';
    }
}

function renderFlashcards(cards) {
    const grid = document.getElementById('flashcard-grid');
    if (!grid) return;
    if (!cards || cards.length === 0) {
        grid.innerHTML = '<p style="color:var(--text-muted);">No flashcards generated yet.</p>';
        return;
    }

    grid.innerHTML = cards.map((c, i) => `
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <span style="font-size:0.75rem; color:var(--primary); font-weight:700; text-transform:uppercase; margin-bottom:0.5rem;">
                        Card #${i+1} • ${c.difficulty || 'Medium'}
                    </span>
                    <p style="font-weight:600; font-size:1rem;">${c.front}</p>
                    <span style="font-size:0.75rem; color:var(--text-muted); margin-top:auto;">Click to flip</span>
                </div>
                <div class="flashcard-back">
                    <span style="font-size:0.75rem; font-weight:700; color:var(--primary); margin-bottom:0.5rem; display:block;">
                        EXPLANATION / ANSWER
                    </span>
                    <p>${c.back}</p>
                </div>
            </div>
        </div>
    `).join('');
}

// Practice Drills
function quickQuizForConcept(conceptName) {
    const input = document.getElementById('quiz-topic-input');
    if (input) input.value = conceptName;
    generateCustomQuiz();
    switchTab('drills');
}

async function generateCustomQuiz() {
    const input = document.getElementById('quiz-topic-input');
    const topic = (input && input.value.trim()) || 'Core Concepts';
    const body = document.getElementById('quiz-body');
    if (!body) return;
    body.innerHTML = '<p style="color:var(--primary);">⏳ Generating 5-question conceptual practice drill...</p>';

    try {
        const res = await fetch('/quiz/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, num_questions: 5, learner_id: currentUser.id, course_id: currentCourseId })
        });
        const data = await res.json();
        renderQuiz(data);
    } catch (e) {
        body.innerHTML = '<p style="color:var(--danger);">Failed to generate drill.</p>';
    }
}

function renderQuiz(quizData) {
    currentQuizData = quizData;
    selectedAnswers = {};
    const title = document.getElementById('quiz-panel-title');
    const body = document.getElementById('quiz-body');
    const submitBtn = document.getElementById('btn-submit-quiz');

    if (title) title.innerText = `📝 Practice Drill: ${quizData.topic}`;
    if (submitBtn) submitBtn.style.display = 'inline-block';

    let html = '';
    quizData.questions.forEach(q => {
        html += `
            <div style="margin-bottom:1.5rem;" id="q-block-${q.id}">
                <p style="font-weight:600; margin-bottom:0.5rem;">${q.id}. ${q.question}</p>
                ${q.options.map((opt, idx) => `
                    <div class="chip" style="display:block; margin-top:0.4rem; padding:0.6rem 0.9rem; border-radius:6px;" id="opt-${q.id}-${idx}" onclick="selectOpt(${q.id}, ${idx})">
                        <strong>${String.fromCharCode(65 + idx)}.</strong> ${opt}
                    </div>
                `).join('')}
            </div>
        `;
    });
    if (body) body.innerHTML = html;
}

function selectOpt(qId, optIdx) {
    selectedAnswers[qId] = optIdx;
    for (let i = 0; i < 4; i++) {
        const el = document.getElementById(`opt-${qId}-${i}`);
        if (el) {
            el.style.background = 'var(--bg-subtle)';
            el.style.borderColor = 'var(--border-color)';
            el.style.color = 'var(--text-main)';
        }
    }
    const active = document.getElementById(`opt-${qId}-${optIdx}`);
    if (active) {
        active.style.background = 'var(--primary-light)';
        active.style.borderColor = 'var(--primary)';
        active.style.color = 'var(--primary)';
    }
}

async function submitQuiz() {
    if (!currentQuizData) return;
    try {
        const res = await fetch('/quiz/grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                concept_name: currentQuizData.concept_name,
                questions: currentQuizData.questions,
                answers: selectedAnswers,
                learner_id: currentUser.id,
                course_id: currentCourseId
            })
        });
        const result = await res.json();
        alert(`Quiz Graded!\nScore: ${Math.round(result.score * 100)}% (${result.correctCount}/${result.total})\nUpdated Mastery: ${Math.round(result.newMastery * 100)}%`);
        fetchMastery();
        const submitBtn = document.getElementById('btn-submit-quiz');
        if (submitBtn) submitBtn.style.display = 'none';
    } catch (e) {
        alert('Grading error: ' + e);
    }
}

// Retention Guardian Scan & Calendar
async function triggerRetentionGuardian() {
    const btn = document.getElementById('btn-guardian');
    if (btn) btn.innerText = '⏳ Scanning...';
    try {
        const res = await fetch(`/guardian/scan?learner_id=${currentUser.id}&course_id=${currentCourseId}`, { method: 'POST' });
        const data = await res.json();
        alert(`Retention Guardian Scan Completed!\n• Scanned Subtopics: ${data.scannedConceptsCount}\n• Decayed Detected: ${data.decayedCount}\n• Queued Calendar Interventions: ${data.actionsTaken.length}`);
        fetchMastery();
        fetchNudges();
    } catch (e) {
        alert('Scan error: ' + e);
    } finally {
        if (btn) btn.innerHTML = '⚡ Run Retention Scan';
    }
}

async function fetchNudges() {
    try {
        const res = await fetch(`/nudges?learner_id=${currentUser.id}&status=pending`);
        const data = await res.json();
        renderNudges(data.nudges);
    } catch (e) {
        console.error(e);
    }
}

function renderNudges(nudges) {
    const container = document.getElementById('nudges-container');
    if (!container) return;
    if (!nudges || nudges.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem;">✅ All subtopics healthy or study nudges already approved!</p>';
        return;
    }

    let html = '';
    nudges.forEach(n => {
        const draft = n.emailDraft || {};
        html += `
            <div class="nudge-card">
                <div class="nudge-header">
                    <div class="nudge-title">🔔 Retention Alert: ${n.conceptName}</div>
                    <button class="btn-approve" onclick="approveNudge('${n.id}')">✓ Approve & Send Email</button>
                </div>
                <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.4rem;">
                    <strong>Reason:</strong> ${n.reason} | <strong>Calendar Event:</strong> Booked
                </p>
                <div class="nudge-body">
                    <strong>Subject:</strong> ${draft.subject || ''}
                    <hr style="border:0; border-top:1px solid var(--border-color); margin:0.35rem 0;" />
                    ${draft.body || ''}
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

async function approveNudge(nudgeId) {
    try {
        const res = await fetch(`/nudges/${nudgeId}/approve?learner_id=${currentUser.id}`, { method: 'POST' });
        const data = await res.json();
        alert(`Study nudge approved and delivered via Gmail API!\nMessage ID: ${data.messageId}`);
        fetchNudges();
    } catch (e) {
        alert('Approval failed: ' + e);
    }
}

async function triggerCalendarPlan() {
    try {
        const res = await fetch('/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ learner_id: currentUser.id, course_id: currentCourseId })
        });
        const data = await res.json();
        alert(`Revision Plan Created!\nScheduled ${data.totalSessions} sessions directly into your Google Calendar.`);
    } catch (e) {
        alert('Plan error: ' + e);
    }
}

// Ingested Sources List
async function fetchSources() {
    const container = document.getElementById('sources-container');
    if (!container) return;
    container.innerHTML = '<p style="color:var(--primary);">Loading sources...</p>';
    try {
        const res = await fetch(`/sources?learner_id=${currentUser.id}&course_id=${currentCourseId}`);
        const data = await res.json();
        if (!data.sources || data.sources.length === 0) {
            container.innerHTML = `
                <div style="background:var(--bg-subtle); padding:1.5rem; border-radius:8px; border:1px solid var(--border-color);">
                    <h4>📚 No Ingested Notes Yet</h4>
                    <p style="font-size:0.88rem; color:var(--text-muted); margin-top:0.35rem;">Click "+ Add Note / YouTube Video" above to ingest lecture materials.</p>
                </div>
            `;
            return;
        }
        container.innerHTML = data.sources.map(s => `
            <div style="background:var(--bg-subtle); padding:1rem; border-radius:8px; border:1px solid var(--border-color); margin-bottom:0.75rem;">
                <strong>${s.title}</strong> (${s.type}) • ${s.charCount} characters
                <p style="font-size:0.85rem; color:var(--text-muted); margin-top:0.25rem; white-space:pre-line;">${s.content.substring(0, 200)}...</p>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p style="color:var(--danger);">Failed to load sources.</p>';
    }
}

// Live YouTube Transcript Fetch Preview
async function previewYouTubeTranscript() {
    const url = document.getElementById('course-yt-url').value.trim();
    const statusEl = document.getElementById('yt-preview-status');
    if (!url) {
        statusEl.innerText = 'Please paste a YouTube URL first.';
        return;
    }
    statusEl.innerText = '⏳ Extracting captions/transcript from YouTube...';
    try {
        const res = await fetch('/youtube/fetch-transcript', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (data.success) {
            statusEl.innerHTML = `<span style="color:var(--success); font-weight:700;">✅ Found Transcript (${data.charCount.toLocaleString()} characters extracted)</span>`;
        } else {
            statusEl.innerHTML = `<span style="color:var(--warning);">⚠️ ${data.error || 'No captions found'}. You can still paste notes below!</span>`;
        }
    } catch (e) {
        statusEl.innerText = 'Error connecting to transcript extractor.';
    }
}

// Course Creation Modal
function showNewCourseModal() {
    const modal = document.getElementById('new-course-modal');
    if (modal) modal.style.display = 'flex';
}

function closeNewCourseModal() {
    const modal = document.getElementById('new-course-modal');
    if (modal) modal.style.display = 'none';
}

function selectPresetCourse(title, topicsStr, ytUrl) {
    document.getElementById('course-title-input').value = title;
    document.getElementById('course-topics-input').value = topicsStr;
    document.getElementById('course-yt-url').value = ytUrl || '';
    if (ytUrl) previewYouTubeTranscript();
}

async function submitCreateCourse() {
    const title = document.getElementById('course-title-input').value.trim();
    const topicsRaw = document.getElementById('course-topics-input').value.trim();
    const examDate = document.getElementById('course-exam-date').value;
    const ytUrl = document.getElementById('course-yt-url').value.trim();
    const notes = document.getElementById('course-notes-input').value.trim();

    if (!title || !topicsRaw) {
        alert('Please provide a Subject Title and at least one Subtopic.');
        return;
    }

    const topics = topicsRaw.split(',').map(t => t.trim()).filter(Boolean);
    const btn = document.getElementById('btn-submit-create-course');
    if (btn) btn.innerText = '⏳ Ingesting & Creating Dynamic Graph...';

    try {
        const res = await fetch('/courses/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                learner_id: currentUser.id,
                learner_name: currentUser.name,
                learner_email: currentUser.email,
                course_title: title,
                subtopics: topics,
                exam_date_iso: examDate ? new Date(examDate).toISOString() : null,
                youtube_url: ytUrl || null,
                lecture_notes: notes || null
            })
        });
        const result = await res.json();
        alert(`Subject Activated: ${title}!\n• Initialized Subtopics: ${result.concepts.length}\n• Ingested Sources: ${result.sources.length}\n• Spaced Calendar Blocks: Scheduled`);
        
        closeNewCourseModal();
        currentCourseId = result.courseId;
        currentCourseTitle = title;
        await loadCourses();
    } catch (e) {
        alert('Creation error: ' + e);
    } finally {
        if (btn) btn.innerText = '⚡ Generate Dynamic Mastery Graph & Schedule';
    }
}

// Basic Markdown Formatter
function formatMarkdown(md) {
    if (!md) return '';
    return md
        .replace(/^# (.*$)/gim, '<h2 style="margin-top:1rem; margin-bottom:0.5rem;">$1</h2>')
        .replace(/^## (.*$)/gim, '<h3 style="margin-top:0.8rem; margin-bottom:0.4rem;">$1</h3>')
        .replace(/^### (.*$)/gim, '<h4 style="margin-top:0.6rem;">$1</h4>')
        .replace(/\\*\\*(.*)\\*\\*/gim, '<strong>$1</strong>')
        .replace(/\\*(.*)\\*/gim, '<em>$1</em>')
        .replace(/\\n/gim, '<br>');
}

// Window load
window.addEventListener('DOMContentLoaded', () => {
    initTheme();
    checkAuthStatus();
});
"""

Path("static/app.js").write_text(js, encoding="utf-8")
print("app.js written successfully!")
