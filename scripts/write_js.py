from pathlib import Path

js = """
let currentLearner = 'priya';
let currentCourse = 'dbms';
let currentQuizData = null;
let selectedAnswers = {};

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    document.getElementById('theme-toggle').innerText = next === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', next);
}

const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
document.getElementById('theme-toggle').innerText = savedTheme === 'dark' ? '☀️' : '🌙';

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

function switchUser(userId) {
    currentLearner = userId;
    currentCourse = (userId === 'priya') ? 'dbms' : 'os';
    document.getElementById('exam-badge').innerText = (userId === 'priya') ? '5 Days Left (Sep 03)' : '3 Days Left (Sep 01)';
    fetchMastery();
    fetchNudges();
    document.getElementById('chat-box').innerHTML = `
        <div class="msg msg-agent">Switched to <strong>${userId === 'priya' ? 'Priya Sharma (DBMS Course)' : 'Rohan Verma (Operating Systems)'}</strong>. How can I help you study today?</div>
    `;
}

async function fetchMastery() {
    try {
        const res = await fetch(`/mastery?learner_id=${currentLearner}&course_id=${currentCourse}`);
        const data = await res.json();
        renderMastery(data.concepts);
    } catch (e) { console.error(e); }
}

function renderMastery(concepts) {
    const container = document.getElementById('mastery-container');
    if (!concepts || concepts.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">No concepts found.</p>';
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
                    <span style="font-weight:600;">${c.name}</span>
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

async function fetchNudges() {
    try {
        const res = await fetch(`/nudges?learner_id=${currentLearner}&status=pending`);
        const data = await res.json();
        renderNudges(data.nudges);
    } catch (e) { console.error(e); }
}

function renderNudges(nudges) {
    const container = document.getElementById('nudges-container');
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
                    <div>🔔 Retention Alert: ${n.conceptName}</div>
                    <button class="btn-approve" onclick="approveNudge('${n.id}')">✓ Approve & Send Email</button>
                </div>
                <p style="font-size:0.8rem; color:var(--text-muted);"><strong>Reason:</strong> ${n.reason} | <strong>Calendar Event:</strong> Booked</p>
                <div class="nudge-body"><strong>Subject:</strong> ${draft.subject || ''}<hr style="border:0; border-top:1px solid var(--border-color); margin:0.35rem 0;"/>${draft.body || ''}</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

async function approveNudge(nudgeId) {
    try {
        const res = await fetch(`/nudges/${nudgeId}/approve?learner_id=${currentLearner}`, { method: 'POST' });
        const data = await res.json();
        alert(`Study nudge approved and sent via Gmail API! Message ID: ${data.messageId}`);
        fetchNudges();
    } catch (e) { alert('Approval failed: ' + e); }
}

async function triggerRetentionGuardian() {
    const btn = document.getElementById('btn-guardian');
    btn.innerText = '⏳ Scanning...';
    try {
        const res = await fetch(`/guardian/scan?learner_id=${currentLearner}&course_id=${currentCourse}`, { method: 'POST' });
        const data = await res.json();
        alert(`Retention Guardian Scan Completed!\\nScanned: ${data.scannedConceptsCount} concepts\\nDecayed: ${data.decayedCount}\\nQueued Interventions: ${data.actionsTaken.length}`);
        fetchMastery();
        fetchNudges();
    } catch (e) { alert('Scan error: ' + e); }
    finally { btn.innerHTML = '⚡ Run Retention Scan'; }
}

function handleKey(e) { if (e.key === 'Enter') sendMessage(); }
function quickPrompt(text) { document.getElementById('chat-input').value = text; sendMessage(); }

async function sendMessage() {
    const input = document.getElementById('chat-input');
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
    } catch (e) { appendMsg('Sorry, error communicating with coach.', 'msg-agent'); }
}

function appendMsg(text, className) {
    const box = document.getElementById('chat-box');
    const el = document.createElement('div');
    el.className = `msg ${className}`;
    el.innerHTML = text.replace(/\\n/g, '<br>');
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
}

async function generateStudyGuide() {
    const input = document.getElementById('guide-topic-input');
    const topic = input.value.trim() || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const contentDiv = document.getElementById('guide-content');
    contentDiv.innerHTML = '<p style="color:var(--primary);">⏳ Synthesizing study guide...</p>';
    try {
        const res = await fetch('/study-guide/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        contentDiv.innerHTML = formatMarkdown(data.contentMarkdown);
    } catch (e) { contentDiv.innerHTML = '<p style="color:var(--danger);">Failed to generate study guide.</p>'; }
}

async function generateFlashcards() {
    const input = document.getElementById('flashcard-topic-input');
    const topic = input.value.trim() || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const grid = document.getElementById('flashcard-grid');
    grid.innerHTML = '<p style="color:var(--primary);">Generating flashcards...</p>';
    try {
        const res = await fetch('/flashcards/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, count: 6, learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        renderFlashcards(data.cards);
    } catch (e) { grid.innerHTML = '<p style="color:var(--danger);">Failed to load flashcards.</p>'; }
}

function renderFlashcards(cards) {
    const grid = document.getElementById('flashcard-grid');
    if (!cards || cards.length === 0) { grid.innerHTML = '<p style="color:var(--text-muted);">No flashcards.</p>'; return; }
    grid.innerHTML = cards.map((c, i) => `
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <span style="font-size:0.75rem; color:var(--primary); font-weight:700;">CARD #${i+1}</span>
                    <p style="font-weight:600; font-size:0.95rem; margin-top:0.5rem;">${c.front}</p>
                    <span style="font-size:0.75rem; color:var(--text-muted); margin-top:auto;">Click to flip</span>
                </div>
                <div class="flashcard-back">
                    <span style="font-size:0.75rem; font-weight:700; color:var(--primary); margin-bottom:0.4rem;">EXPLANATION</span>
                    <p>${c.back}</p>
                </div>
            </div>
        </div>
    `).join('');
}

function quickQuizForConcept(name) {
    document.getElementById('quiz-topic-input').value = name;
    generateCustomQuiz();
    switchTab('drills');
}

async function generateCustomQuiz() {
    const topic = document.getElementById('quiz-topic-input').value.trim() || (currentLearner === 'priya' ? 'Normalization' : 'Deadlocks & Sync');
    const body = document.getElementById('quiz-body');
    body.innerHTML = '<p style="color:var(--primary);">⏳ Generating practice drill...</p>';
    try {
        const res = await fetch('/quiz/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, num_questions: 5, learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        renderQuiz(data);
    } catch (e) { body.innerHTML = '<p style="color:var(--danger);">Failed to load drill.</p>'; }
}

function renderQuiz(quizData) {
    currentQuizData = quizData;
    selectedAnswers = {};
    document.getElementById('quiz-panel-title').innerText = `📝 Practice Drill: ${quizData.topic}`;
    document.getElementById('btn-submit-quiz').style.display = 'inline-block';
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
    document.getElementById('quiz-body').innerHTML = html;
}

function selectOpt(qId, optIdx) {
    selectedAnswers[qId] = optIdx;
    for (let i = 0; i < 4; i++) {
        const el = document.getElementById(`opt-${qId}-${i}`);
        if (el) { el.style.background = 'var(--bg-subtle)'; el.style.borderColor = 'var(--border-color)'; el.style.color = 'var(--text-main)'; }
    }
    const active = document.getElementById(`opt-${qId}-${optIdx}`);
    if (active) { active.style.background = 'var(--primary-light)'; active.style.borderColor = 'var(--primary)'; active.style.color = 'var(--primary)'; }
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
        alert(`Quiz Graded!\\nScore: ${Math.round(result.score * 100)}% (${result.correctCount}/${result.total})\\nUpdated Mastery: ${Math.round(result.newMastery * 100)}%`);
        fetchMastery();
        document.getElementById('btn-submit-quiz').style.display = 'none';
    } catch (e) { alert('Grading error: ' + e); }
}

async function triggerCalendarPlan() {
    try {
        const res = await fetch('/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ learner_id: currentLearner, course_id: currentCourse })
        });
        const data = await res.json();
        alert(`Revision Plan Created!\\nScheduled ${data.totalSessions} sessions directly into your Google Calendar.`);
    } catch (e) { alert('Plan error: ' + e); }
}

async function fetchSources() {
    const container = document.getElementById('sources-container');
    container.innerHTML = '<p style="color:var(--primary);">Loading sources...</p>';
    try {
        const res = await fetch(`/sources?learner_id=${currentLearner}&course_id=${currentCourse}`);
        const data = await res.json();
        if (!data.sources || data.sources.length === 0) {
            container.innerHTML = `
                <div style="background:var(--bg-subtle); padding:1.5rem; border-radius:8px; border:1px solid var(--border-color);">
                    <h4>📚 Default Course Syllabus Ingested</h4>
                    <p style="font-size:0.88rem; color:var(--text-muted); margin-top:0.35rem;">5 core lecture transcripts active in course index.</p>
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
    } catch (e) { container.innerHTML = '<p style="color:var(--danger);">Failed to load sources.</p>'; }
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
    }).then(() => { alert('Source added and indexed!'); fetchSources(); });
}

function formatMarkdown(md) {
    if (!md) return '';
    return md
        .replace(/^# (.*$)/gim, '<h2>$1</h2>')
        .replace(/^## (.*$)/gim, '<h3>$1</h3>')
        .replace(/^### (.*$)/gim, '<h4>$1</h4>')
        .replace(/\\*\\*(.*)\\*\\*/gim, '<strong>$1</strong>')
        .replace(/\\*(.*)\\*/gim, '<em>$1</em>')
        .replace(/\\n/gim, '<br>');
}

fetchMastery();
fetchNudges();
"""

Path("static/app.js").write_text(js, encoding="utf-8")
print("app.js written successfully!")
