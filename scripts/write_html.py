from pathlib import Path

html = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Learning Coach | NotebookLM + Spaced Mastery Guardian</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <div class="brand">
            <div class="brand-logo">🎓</div>
            <div class="brand-text">
                <h1>Agentic Learning Coach</h1>
                <p>NotebookLM + Autonomous Spaced Mastery Guardian</p>
            </div>
        </div>
        <div class="header-actions">
            <div class="user-select-container">
                <span>👤</span>
                <select id="user-select" onchange="switchUser(this.value)">
                    <option value="priya">Priya Sharma (DBMS Course)</option>
                    <option value="rohan">Rohan Verma (Operating Systems)</option>
                </select>
            </div>
            <button class="theme-btn" onclick="toggleTheme()" id="theme-toggle">🌙</button>
            <button class="btn-guardian" onclick="triggerRetentionGuardian()" id="btn-guardian">⚡ Run Retention Scan</button>
        </div>
    </header>

    <div class="nav-tabs">
        <div class="tab-item active" onclick="switchTab('mastery')">📊 Mastery & Decay Graph</div>
        <div class="tab-item" onclick="switchTab('tutor')">💬 Socratic Tutor & Coach</div>
        <div class="tab-item" onclick="switchTab('guides')">📖 Study Guides & Briefings</div>
        <div class="tab-item" onclick="switchTab('flashcards')">🗂️ Active Recall Flashcards</div>
        <div class="tab-item" onclick="switchTab('drills')">📝 Practice Quizzes</div>
        <div class="tab-item" onclick="switchTab('guardian')">🚨 Retention Guardian & Calendar</div>
        <div class="tab-item" onclick="switchTab('sources')">📁 Source Materials</div>
    </div>

    <div class="container">
        <div id="tab-mastery" class="tab-content active grid-2">
            <div class="card">
                <div class="card-header"><div class="card-title">📊 Conceptual Mastery Graph (Forgetting Curve Engine)</div></div>
                <div class="card-body" id="mastery-container"><p style="color:var(--text-muted);">Loading mastery graph...</p></div>
            </div>
            <div class="card">
                <div class="card-header"><div class="card-title">💡 How Spaced Retention Works</div></div>
                <div class="card-body" style="font-size:0.9rem; line-height:1.6;">
                    <p>Unlike standard chatbots that treat knowledge as permanent, <strong>Agentic Learning Coach</strong> models human forgetting curves:</p>
                    <ul style="margin:0.75rem 0 1rem 1.25rem;">
                        <li><strong>Forgetting Decay:</strong> Mastery &times; 0.5<sup>(Days / Half-Life)</sup></li>
                        <li><strong>Adaptive Half-Life:</strong> Extends from 7 to 21 days with successful recall attempts.</li>
                        <li><strong>Autonomous Action:</strong> When retention drops below 50%, the Guardian schedules a Calendar block and drafts a study nudge.</li>
                    </ul>
                    <div style="background:var(--bg-subtle); padding:0.9rem; border-radius:8px; border:1px solid var(--border-color);">
                        <strong>Target Course Exam:</strong> <span id="exam-badge" style="font-weight:700; color:var(--primary);">5 Days Left (Sep 03)</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-tutor" class="tab-content grid-1">
            <div class="card">
                <div class="card-header"><div class="card-title">🤖 Socratic Learning Coach (Grounded in Sources)</div></div>
                <div class="card-body">
                    <div class="chat-box" id="chat-box">
                        <div class="msg msg-agent">Hello! I am your <strong>Socratic Learning Coach</strong>. Ask me any conceptual question, ask for a revision plan, or request a practice quiz!</div>
                    </div>
                    <div class="chat-input-row">
                        <input type="text" id="chat-input" placeholder="Ask a question, request a quiz, or ask to plan revision..." onkeypress="handleKey(event)">
                        <button class="btn-primary" onclick="sendMessage()">Send</button>
                    </div>
                    <div class="quick-chips">
                        <span class="chip" onclick="quickPrompt('Why is 3NF different from BCNF?')">💡 3NF vs BCNF</span>
                        <span class="chip" onclick="quickPrompt('Why does 2PL prevent cascading aborts?')">🔒 2PL Rules</span>
                        <span class="chip" onclick="quickPrompt('Explain the 4 Coffman conditions for Deadlocks')">⚠️ Deadlock Conditions</span>
                        <span class="chip" onclick="quickPrompt('Make my study plan for Google Calendar')">📅 Plan Revision into Calendar</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-guides" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📖 Instant Study Guides & Executive Briefings</div>
                    <div style="display:flex; gap:0.5rem;">
                        <input type="text" id="guide-topic-input" placeholder="Topic name (e.g. Normalization)" style="width:220px;">
                        <button class="btn-primary" onclick="generateStudyGuide()">⚡ Generate Guide</button>
                    </div>
                </div>
                <div class="card-body" id="guide-content" style="line-height:1.7;"><p style="color:var(--text-muted);">Click Generate to create a comprehensive NotebookLM briefing document.</p></div>
            </div>
        </div>

        <div id="tab-flashcards" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🗂️ Active Recall Flashcard Decks</div>
                    <div style="display:flex; gap:0.5rem;">
                        <input type="text" id="flashcard-topic-input" placeholder="Topic (e.g. Normalization)" style="width:200px;">
                        <button class="btn-primary" onclick="generateFlashcards()">Generate Deck</button>
                    </div>
                </div>
                <div class="card-body"><div class="flashcard-grid" id="flashcard-grid"></div></div>
            </div>
        </div>

        <div id="tab-drills" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title" id="quiz-panel-title">📝 Targeted Practice Drill</div>
                    <div style="display:flex; gap:0.5rem;">
                        <input type="text" id="quiz-topic-input" placeholder="Topic (e.g. Normalization)" style="width:200px;">
                        <button class="btn-primary" onclick="generateCustomQuiz()">Generate Drill</button>
                        <button class="btn-approve" onclick="submitQuiz()" id="btn-submit-quiz" style="display:none;">Submit Answers</button>
                    </div>
                </div>
                <div class="card-body" id="quiz-body"><p style="color:var(--text-muted);">Click a concept or enter a topic to start a 5-question drill.</p></div>
            </div>
        </div>

        <div id="tab-guardian" class="tab-content grid-2">
            <div class="card">
                <div class="card-header"><div class="card-title">🚨 Proactive Study Nudges (Approval Queue)</div></div>
                <div class="card-body" id="nudges-container"><p style="color:var(--text-muted);">No pending nudges in queue.</p></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📅 Google Calendar Integration</div>
                    <button class="btn-primary" onclick="triggerCalendarPlan()">⚡ Sync Calendar Plan</button>
                </div>
                <div class="card-body">
                    <p style="font-size:0.88rem; line-height:1.5; margin-bottom:1rem;">Spaced revision slots backward-planned directly into your primary Google Calendar before exam day.</p>
                    <div style="background:var(--bg-subtle); padding:1rem; border-radius:8px; border:1px solid var(--border-color); font-size:0.88rem;">
                        ✅ Google Calendar connected to demo user account.
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-sources" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📁 Course Lecture Sources & Notes</div>
                    <button class="btn-primary" onclick="showAddSourceModal()">+ Add Note / Source</button>
                </div>
                <div class="card-body" id="sources-container"><p style="color:var(--text-muted);">Loading sources...</p></div>
            </div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
"""

Path("static/index.html").write_text(html, encoding="utf-8")
print("index.html written successfully!")
