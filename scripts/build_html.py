from pathlib import Path

html_content = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Learning Coach | Autonomous Spaced Mastery Platform</title>
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
            <!-- Active Learner Switcher -->
            <div class="user-select-container">
                <span>👤</span>
                <select id="user-select" onchange="switchUser(this.value)">
                    <option value="priya">Priya Sharma (DBMS Course)</option>
                    <option value="rohan">Rohan Verma (Operating Systems)</option>
                    <option value="__new__">+ Create New Course / Student</option>
                </select>
            </div>

            <!-- Google Auth Status Badge -->
            <div id="auth-indicator" style="font-size: 0.8rem; font-weight: 600; padding: 0.35rem 0.75rem; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border-color);">
                Checking Google OAuth...
            </div>

            <!-- Dark / Light Mode Toggle Button -->
            <button class="theme-btn" onclick="toggleTheme()" id="theme-toggle" title="Toggle Dark/Light Mode">🌙</button>

            <!-- Autonomous Retention Guardian Trigger -->
            <button class="btn-guardian" onclick="triggerRetentionGuardian()" id="btn-guardian">⚡ Run Retention Scan</button>
        </div>
    </header>

    <!-- Navigation Tabs -->
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
        <!-- TAB 1: MASTERY & DECAY GRAPH -->
        <div id="tab-mastery" class="tab-content active grid-2">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📊 Conceptual Mastery Graph (Forgetting Curve Engine)</div>
                    <button class="btn-onboarding" onclick="showOnboardingModal()">+ Add Course / Student</button>
                </div>
                <div class="card-body" id="mastery-container">
                    <p style="color:var(--text-muted);">Loading mastery graph...</p>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">💡 How Spaced Retention Works</div>
                </div>
                <div class="card-body" style="font-size: 0.9rem; line-height: 1.6;">
                    <p>Unlike standard chatbots that treat knowledge as permanent, <strong>Agentic Learning Coach</strong> models human forgetting curves:</p>
                    <ul style="margin: 0.75rem 0 1rem 1.25rem;">
                        <li><strong>Forgetting Decay:</strong> Mastery &times; 0.5<sup>(Days / Half-Life)</sup></li>
                        <li><strong>Adaptive Half-Life:</strong> Extends from 7 to 21 days with successful recall attempts.</li>
                        <li><strong>Autonomous Action:</strong> When retention drops below 50%, the Guardian schedules a Calendar block and drafts a study nudge.</li>
                    </ul>
                    <div style="background: var(--bg-subtle); padding: 0.9rem; border-radius: 8px; border: 1px solid var(--border-color);">
                        <strong>Target Course Exam:</strong> <span id="exam-badge" style="font-weight: 700; color: var(--primary);">5 Days Left</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: SOCRATIC COACH CHAT -->
        <div id="tab-tutor" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🤖 Socratic Learning Coach (Grounded in Sources)</div>
                    <span style="font-size: 0.8rem; color: var(--text-muted);">Never gives away answers; guides your reasoning step-by-step</span>
                </div>
                <div class="card-body">
                    <div class="chat-box" id="chat-box">
                        <div class="msg msg-agent">
                            Hello! I am your <strong>Socratic Learning Coach</strong>. Ask me any conceptual question, ask for a revision plan, or request a practice quiz!
                        </div>
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

        <!-- TAB 3: STUDY GUIDES & BRIEFINGS -->
        <div id="tab-guides" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📖 Instant Study Guides & Executive Briefings</div>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="text" id="guide-topic-input" placeholder="Topic name (e.g. Normalization, Deadlocks)" style="width: 250px;">
                        <button class="btn-primary" onclick="generateStudyGuide()">⚡ Generate Guide</button>
                    </div>
                </div>
                <div class="card-body" id="guide-content" style="line-height: 1.7;">
                    <p style="color:var(--text-muted);">Select or type a topic above to generate a comprehensive NotebookLM briefing document with comparison tables and FAQs.</p>
                </div>
            </div>
        </div>

        <!-- TAB 4: FLASHCARDS -->
        <div id="tab-flashcards" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🗂️ Active Recall Flashcard Decks</div>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="text" id="flashcard-topic-input" placeholder="Topic (e.g. Normalization)" style="width: 200px;">
                        <button class="btn-primary" onclick="generateFlashcards()">Generate Deck</button>
                    </div>
                </div>
                <div class="card-body">
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Click any card to flip and test your active recall.</p>
                    <div class="flashcard-grid" id="flashcard-grid"></div>
                </div>
            </div>
        </div>

        <!-- TAB 5: PRACTICE DRILLS -->
        <div id="tab-drills" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title" id="quiz-panel-title">📝 Targeted Practice Drill</div>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="text" id="quiz-topic-input" placeholder="Topic (e.g. Normalization)" style="width: 200px;">
                        <button class="btn-primary" onclick="generateCustomQuiz()">Generate Drill</button>
                        <button class="btn-approve" onclick="submitQuiz()" id="btn-submit-quiz" style="display:none;">Submit Answers</button>
                    </div>
                </div>
                <div class="card-body" id="quiz-body">
                    <p style="color:var(--text-muted);">Click a concept from your mastery graph or enter a topic above to start a 5-question conceptual practice drill.</p>
                </div>
            </div>
        </div>

        <!-- TAB 6: RETENTION GUARDIAN & CALENDAR -->
        <div id="tab-guardian" class="tab-content grid-2">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🚨 Proactive Study Nudges (Approval Queue)</div>
                    <span style="font-size: 0.8rem; background: var(--danger-bg); color: var(--danger); padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700;">Human-in-the-Loop Gate</span>
                </div>
                <div class="card-body" id="nudges-container">
                    <p style="color:var(--text-muted);">No pending nudges in queue.</p>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">📅 Google Calendar Integration</div>
                    <button class="btn-primary" onclick="triggerCalendarPlan()">⚡ Sync Calendar Plan</button>
                </div>
                <div class="card-body">
                    <p style="font-size: 0.88rem; line-height: 1.5; margin-bottom: 1rem;">
                        Spaced revision slots backward-planned directly into your primary Google Calendar before exam day.
                    </p>
                    <div style="background: var(--bg-subtle); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color); font-size: 0.88rem;">
                        ✅ Google Calendar connected with OAuth authorization.
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 7: SOURCE MATERIALS -->
        <div id="tab-sources" class="tab-content grid-1">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📁 Course Lecture Sources & Ingested Notes</div>
                    <button class="btn-primary" onclick="showAddSourceModal()">+ Add Note / Source</button>
                </div>
                <div class="card-body" id="sources-container">
                    <p style="color:var(--text-muted);">Loading course materials...</p>
                </div>
            </div>
        </div>
    </div>

    <!-- ONBOARDING & NEW COURSE MODAL WIZARD -->
    <div class="modal-overlay" id="onboarding-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>🚀 Onboarding & Course Setup</h2>
                <button onclick="closeOnboardingModal()" style="background:none; border:none; font-size:1.5rem; color:var(--text-muted); cursor:pointer;">&times;</button>
            </div>

            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
                Select a fast preset or customize your learning journey:
            </p>

            <div class="preset-btns">
                <button class="preset-btn" onclick="selectPreset('Alex Chen', 'Machine Learning Core', 'Linear Regression, Gradient Descent, Backpropagation, Transformers, Overfitting')">🤖 ML & AI Preset</button>
                <button class="preset-btn" onclick="selectPreset('Priya Sharma', 'Database Systems', 'ER Modeling, Relational Algebra, SQL & Joins, Normalization, Transactions & ACID')">🎓 DBMS Preset</button>
                <button class="preset-btn" onclick="selectPreset('Rohan Verma', 'Operating Systems', 'Process Scheduling, Deadlocks & Sync, Virtual Memory, Paging & TLB')">💻 OS Preset</button>
            </div>

            <div class="form-group">
                <label>Student Full Name</label>
                <input type="text" id="onboard-name" placeholder="e.g. Alex Chen" value="Alex Chen">
            </div>

            <div class="form-group">
                <label>Email Address (For Calendar & Study Nudges)</label>
                <input type="email" id="onboard-email" placeholder="e.g. abhi20b02@gmail.com" value="abhi20b02@gmail.com">
            </div>

            <div class="form-group">
                <label>Course Title</label>
                <input type="text" id="onboard-course" placeholder="e.g. Machine Learning & Neural Networks" value="Machine Learning & Neural Networks">
            </div>

            <div class="form-group">
                <label>Syllabus Topics (Comma-separated)</label>
                <input type="text" id="onboard-topics" placeholder="Topic 1, Topic 2, Topic 3" value="Linear Regression, Gradient Descent, Backpropagation, Transformers, Overfitting">
            </div>

            <div class="form-group">
                <label>Exam Target Date</label>
                <input type="date" id="onboard-exam" value="2026-09-10">
            </div>

            <button class="btn-primary" style="width:100%; padding:0.8rem; font-size:1rem;" onclick="submitOnboarding()" id="btn-submit-onboard">
                ⚡ Generate Dynamic Mastery Graph & Schedule
            </button>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
"""

Path("static/index.html").write_text(html_content, encoding="utf-8")
print("index.html written successfully!")
