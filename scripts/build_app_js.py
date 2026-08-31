from pathlib import Path

js_content = """
let currentLearner = 'priya';
let currentCourse = 'dbms';
let currentQuizData = null;
let selectedAnswers = {};
let allLearners = [];

// Initialize Theme from localStorage
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.innerText = savedTheme === 'dark' ? '☀️' : '🌙';
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
        const authBadge = document.getElementById('auth-indicator');
        if (data.authenticated) {
            authBadge.innerHTML = `✅ Connected as <strong>${data.email}</strong>`;
            authBadge.style.color = 'var(--success)';
        } else {
            authBadge.innerHTML = `⚠️ Running in Demo / Guest Mode`;
            authBadge.style.color = 'var(--warning)';
        }
    } catch (e) {
        console.error('Auth status check failed:', e);
    }
}

// Load and populate all learners in the profile switcher
async function loadLearnersList() {
    try {
        const res = await fetch('/learners');
        const data = await res.json();
        allLearners = data.learners || [];
        const select = document.getElementById('user-select');
        if (select && allLearners.length > 0) {
            select.innerHTML = allLearners.map(l => `
                <option value="${l.id}">${l.name} (${l.id})</option>
            `).join('') + `<option value="__new__">+ Create New Course / Student</option>`;
            select.value = currentLearner;
        }
    } catch (e) {
        console.error('Failed to load learners:', e);
    }
}

function switchUser(userId) {
    if (userId === '__new__') {
        showOnboardingModal();
        return;
    }
    currentLearner = userId;
    currentCourse = (userId === 'rohan') ? 'os' : (userId === 'priya' ? 'dbms' : userId);
    
    fetchMastery();
    fetchNudges();
    
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.innerHTML = `
            <div class="msg msg-agent">
                Switched profile to <strong>${userId}</strong>. How can I help you study today?
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
        const res = await fetch(`/mastery?learner_id=${currentLearner}&course_id=${currentCourse}`);
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
        container.innerHTML = '<p style="color:var(--text-muted);">No concepts registered yet for this course. Click "+ Create New Course" to get started.</p>';
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
            <div class="concept-item" onclick="quickQuizForConcept('${c.name}')" title="Click to launch practice drill">
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

// Fetch Pending Study Nudges (HITL Gate)
async function fetchNudges() {
    try {
        const res = await fetch(`/nudges?learner_id=${currentLearner}&status=pending`);
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
        container.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem;">✅ All concepts healthy or study nudges already approved!</p>';
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
        const res = await fetch(`/nudges/${nudgeId}/approve?learner_id=${currentLearner}`, { method: 'POST' });
        const data = await res.json();
        alert(`Study nudge approved and delivered via Gmail API!\nMessage ID: ${data.messageId}`);
        fetchNudges();
    } catch (e) {
        alert('Approval failed: ' + e);
    }
}

// Run Autonomous Retention Guardian Scan
async function triggerRetentionGuardian() {
    const btn = document.getElementById('btn-guardian');
    if (btn) btn.innerText = '⏳ Scanning...';
    try {
        const res = await fetch(`/guardian/scan?learner_id=${currentLearner}&course_id=${currentCourse}`, { method: 'POST' });
        const data = await res.json();
        alert(`Retention Guardian Scan Completed!\n• Scanned Concepts: ${data.scannedConceptsCount}\n• Decayed Concepts Detected: ${data.decayedCount}\n• Queued Interventions: ${data.actionsTaken.length}`);
        fetchMastery();
        fetchNudges();
    } catch (e) {
        alert('Scan error: ' + e);
    } finally {
        if (btn) btn.innerHTML = '⚡ Run Retention Scan';
    }
}

// Socratic Chat
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

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        appendMsg(data.message, 'msg-agent');

        if (data.type === 'quiz' && data.data && data.data.questions) {
            renderQuiz(data.data);
            switchTab('drills');
        } else if (data.type === 'plan') {
            alert(`Created ${data.data.totalSessions} revision events in your Google Calendar!`);
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

// Study Guides
async function generateStudyGuide() {
    const input = document.getElementById('guide-topic-input');
    const topic = (input && input.value.trim()) || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const contentDiv = document.getElementById('guide-content');
    if (!contentDiv) return;
    contentDiv.innerHTML = '<p style="color:var(--primary);">⏳ Synthesizing structured study guide...</p>';
    
    try {
        const res = await fetch('/study-guide/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, learner_id: currentLearner, course_id: currentCourse })
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
    const topic = (input && input.value.trim()) || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const grid = document.getElementById('flashcard-grid');
    if (!grid) return;
    grid.innerHTML = '<p style="color:var(--primary);">Generating active recall flashcards...</p>';

    try {
        const res = await fetch('/flashcards/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, count: 6, learner_id: currentLearner, course_id: currentCourse })
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
        grid.innerHTML = '<p style="color:var(--text-muted);">No flashcards generated.</p>';
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

// Quizzes
function quickQuizForConcept(conceptName) {
    const input = document.getElementById('quiz-topic-input');
    if (input) input.value = conceptName;
    generateCustomQuiz();
    switchTab('drills');
}

async function generateCustomQuiz() {
    const input = document.getElementById('quiz-topic-input');
    const topic = (input && input.value.trim()) || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const body = document.getElementById('quiz-body');
    if (!body) return;
    body.innerHTML = '<p style="color:var(--primary);">⏳ Generating 5-question conceptual practice drill...</p>';

    try {
        const res = await fetch('/quiz/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, num_questions: 5, learner_id: currentLearner, course_id: currentCourse })
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
                learner_id: currentLearner,
                course_id: currentCourse
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

// Calendar Planning
async function triggerCalendarPlan() {
    try {
        const res = await fetch('/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        alert(`Revision Plan Created!\nScheduled ${data.totalSessions} sessions directly into your Google Calendar.`);
    } catch (e) {
        alert('Plan error: ' + e);
    }
}

// Sources
async function fetchSources() {
    const container = document.getElementById('sources-container');
    if (!container) return;
    container.innerHTML = '<p style="color:var(--primary);">Loading sources...</p>';
    try {
        const res = await fetch(`/sources?learner_id=${currentLearner}&course_id=${currentCourse}`);
        const data = await res.json();
        if (!data.sources || data.sources.length === 0) {
            container.innerHTML = `
                <div style="background:var(--bg-subtle); padding:1.5rem; border-radius:8px; border:1px solid var(--border-color);">
                    <h4>📚 Course Syllabus Ingested</h4>
                    <p style="font-size:0.88rem; color:var(--text-muted); margin-top:0.35rem;">Lecture notes and syllabus indexed into knowledge base.</p>
                </div>
            `;
            return;
        }
        container.innerHTML = data.sources.map(s => `
            <div style="background:var(--bg-subtle); padding:1rem; border-radius:8px; border:1px solid var(--border-color); margin-bottom:0.75rem;">
                <strong>${s.title}</strong> (${s.type}) • ${s.charCount} characters
                <p style="font-size:0.85rem; color:var(--text-muted); margin-top:0.25rem;">${s.content.substring(0, 150)}...</p>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p style="color:var(--danger);">Failed to load sources.</p>';
    }
}

function showAddSourceModal() {
    const title = prompt('Source Title (e.g. Chapter Notes):');
    if (!title) return;
    const content = prompt('Paste your study notes / transcript:');
    if (!content) return;
    fetch('/sources/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, source_type: 'text_note', learner_id: currentLearner, course_id: currentCourse })
    }).then(() => {
        alert('Source added and indexed!');
        fetchSources();
    });
}

// Onboarding Modal Handling
function showOnboardingModal() {
    const modal = document.getElementById('onboarding-modal');
    if (modal) modal.style.display = 'flex';
}

function closeOnboardingModal() {
    const modal = document.getElementById('onboarding-modal');
    if (modal) modal.style.display = 'none';
    const select = document.getElementById('user-select');
    if (select) select.value = currentLearner;
}

function selectPreset(name, courseTitle, topicsStr) {
    document.getElementById('onboard-name').value = name;
    document.getElementById('onboard-email').value = `${name.toLowerCase().replace(' ', '')}@example.com`;
    document.getElementById('onboard-course').value = courseTitle;
    document.getElementById('onboard-topics').value = topicsStr;
}

async function submitOnboarding() {
    const name = document.getElementById('onboard-name').value.trim();
    const email = document.getElementById('onboard-email').value.trim() || 'abhi20b02@gmail.com';
    const courseTitle = document.getElementById('onboard-course').value.trim();
    const topicsRaw = document.getElementById('onboard-topics').value.trim();
    const examDate = document.getElementById('onboard-exam').value;

    if (!name || !courseTitle || !topicsRaw) {
        alert('Please fill out Name, Course Title, and Syllabus Topics.');
        return;
    }

    const learnerId = name.toLowerCase().replace(/[^a-z0-9]/g, '');
    const courseId = courseTitle.toLowerCase().replace(/[^a-z0-9]/g, '');
    const topics = topicsRaw.split(',').map(t => t.trim()).filter(Boolean);

    const btn = document.getElementById('btn-submit-onboard');
    if (btn) btn.innerText = '⏳ Initializing Dynamic Graph...';

    try {
        const res = await fetch('/onboarding/initialize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                learner_id: learnerId,
                name: name,
                email: email,
                course_id: courseId,
                course_title: courseTitle,
                syllabus_topics: topics,
                exam_date_iso: examDate ? new Date(examDate).toISOString() : null
            })
        });
        const result = await res.json();
        alert(`Course Activated!\n• Student: ${name}\n• Course: ${courseTitle}\n• Initialized Concepts: ${result.conceptsCount}\n• Calendar Revision Blocks: Scheduled`);
        closeOnboardingModal();
        await loadLearnersList();
        switchUser(learnerId);
    } catch (e) {
        alert('Initialization failed: ' + e);
    } finally {
        if (btn) btn.innerText = '⚡ Generate Dynamic Mastery Graph';
    }
}

// Markdown helper
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

// Initialization
window.addEventListener('DOMContentLoaded', () => {
    initTheme();
    checkAuthStatus();
    loadLearnersList();
    fetchMastery();
    fetchNudges();
});
"""

Path("static/app.js").write_text(js_content, encoding="utf-8")
print("app.js generated successfully!")
