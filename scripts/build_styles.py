from pathlib import Path

css_content = """
:root {
    --primary: #4F46E5;
    --primary-hover: #4338CA;
    --primary-light: #EEF2FF;
    --success: #10B981;
    --success-bg: #ECFDF5;
    --warning: #F59E0B;
    --warning-bg: #FFFBEB;
    --danger: #EF4444;
    --danger-bg: #FEF2F2;
    
    /* Light Theme */
    --bg-page: #F8FAFC;
    --bg-card: #FFFFFF;
    --bg-subtle: #F1F5F9;
    --text-main: #0F172A;
    --text-muted: #64748B;
    --border-color: #E2E8F0;
    --header-bg: #FFFFFF;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03);
    --select-bg: #F1F5F9;
    --select-text: #0F172A;
}

[data-theme="dark"] {
    /* Dark Theme */
    --bg-page: #0B0F19;
    --bg-card: #131B2E;
    --bg-subtle: #1E293B;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --border-color: #2D3748;
    --header-bg: #131B2E;
    --primary-light: #1E1E38;
    --success-bg: #064E3B;
    --danger-bg: #7F1D1D;
    --warning-bg: #78350F;
    --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    --select-bg: #1E293B;
    --select-text: #F8FAFC;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

body {
    background-color: var(--bg-page);
    color: var(--text-main);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

header {
    background: var(--header-bg);
    border-bottom: 1px solid var(--border-color);
    padding: 0.75rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.brand-logo {
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg, var(--primary), #818CF8);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.2rem;
    font-weight: 800;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.brand-text h1 {
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--text-main);
    line-height: 1.2;
}

.brand-text p {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* User Switcher Dropdown with Dark Mode Compatibility */
.user-select-container {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--select-bg);
    padding: 0.4rem 0.8rem;
    border-radius: 8px;
    border: 1px solid var(--border-color);
}

select {
    background-color: var(--select-bg);
    border: none;
    color: var(--select-text);
    font-weight: 600;
    font-size: 0.88rem;
    outline: none;
    cursor: pointer;
}

option {
    background-color: var(--bg-card);
    color: var(--text-main);
}

/* Perfectly Centered Theme Button */
.theme-btn {
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    color: var(--text-main);
    width: 38px;
    height: 38px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 1.1rem;
    line-height: 1;
}

.theme-btn:hover {
    border-color: var(--primary);
}

.btn-guardian {
    background: linear-gradient(135deg, #EF4444, #DC2626);
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.85rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
}

.btn-guardian:hover {
    opacity: 0.92;
    transform: translateY(-1px);
}

.btn-onboarding {
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    color: var(--text-main);
    padding: 0.45rem 0.85rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
}

.btn-onboarding:hover {
    border-color: var(--primary);
    color: var(--primary);
}

/* Navigation Tabs */
.nav-tabs {
    background: var(--header-bg);
    border-bottom: 1px solid var(--border-color);
    padding: 0.25rem 2rem;
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
}

.tab-item {
    padding: 0.75rem 1.15rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
}

.tab-item:hover {
    color: var(--primary);
}

.tab-item.active {
    color: var(--primary);
    border-bottom-color: var(--primary);
}

.container {
    max-width: 1440px;
    margin: 1.5rem auto;
    padding: 0 1.5rem;
    width: 100%;
    flex: 1;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: grid;
    gap: 1.5rem;
}

.grid-2 {
    grid-template-columns: 1.2fr 1fr;
}

.grid-1 {
    grid-template-columns: 1fr;
}

.card {
    background: var(--bg-card);
    border-radius: 12px;
    border: 1px solid var(--border-color);
    box-shadow: var(--card-shadow);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.card-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.card-body {
    padding: 1.5rem;
    flex: 1;
}

/* Mastery Bars */
.concept-item {
    margin-bottom: 1.25rem;
}

.concept-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.88rem;
    margin-bottom: 0.4rem;
}

.concept-name {
    font-weight: 600;
    color: var(--text-main);
}

.progress-bar-container {
    height: 10px;
    background: var(--bg-subtle);
    border-radius: 6px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.fill-healthy { background: var(--success); }
.fill-warning { background: var(--warning); }
.fill-decayed { background: var(--danger); animation: pulse 2s infinite; }

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
}

/* Chat UI */
.chat-box {
    height: 380px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--bg-subtle);
    border-radius: 8px;
    border: 1px solid var(--border-color);
    margin-bottom: 1rem;
}

.msg {
    max-width: 85%;
    padding: 0.75rem 1rem;
    border-radius: 12px;
    font-size: 0.92rem;
    line-height: 1.5;
}

.msg-user {
    align-self: flex-end;
    background: var(--primary);
    color: white;
    border-bottom-right-radius: 2px;
}

.msg-agent {
    align-self: flex-start;
    background: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--border-color);
    border-bottom-left-radius: 2px;
}

.chat-input-row {
    display: flex;
    gap: 0.5rem;
}

input[type="text"], input[type="email"], input[type="date"], textarea {
    flex: 1;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-color);
    background: var(--bg-card);
    color: var(--text-main);
    border-radius: 8px;
    font-size: 0.95rem;
    outline: none;
}

input[type="text"]:focus, input[type="email"]:focus, input[type="date"]:focus, textarea:focus {
    border-color: var(--primary);
}

button {
    padding: 0.65rem 1.2rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-hover);
}

.btn-outline {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-main);
}

.btn-outline:hover {
    border-color: var(--primary);
    color: var(--primary);
}

.btn-approve {
    background: var(--success);
    color: white;
    padding: 0.45rem 0.9rem;
    font-size: 0.85rem;
}

.btn-approve:hover {
    opacity: 0.9;
}

/* Nudge Items */
.nudge-card {
    border: 1px solid var(--border-color);
    background: var(--danger-bg);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.nudge-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.nudge-title {
    font-weight: 700;
    color: var(--danger);
    font-size: 0.95rem;
}

.nudge-body {
    font-size: 0.875rem;
    color: var(--text-main);
    margin-bottom: 0.75rem;
    white-space: pre-line;
    background: var(--bg-card);
    padding: 0.75rem;
    border-radius: 6px;
    border: 1px solid var(--border-color);
}

/* Flashcards 3D Interactive UI */
.flashcard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}

.flashcard {
    height: 220px;
    perspective: 1000px;
    cursor: pointer;
}

.flashcard-inner {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;
    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    transform-style: preserve-3d;
    box-shadow: var(--card-shadow);
    border-radius: 12px;
}

.flashcard.flipped .flashcard-inner {
    transform: rotateY(180deg);
}

.flashcard-front, .flashcard-back {
    position: absolute;
    width: 100%;
    height: 100%;
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border: 1px solid var(--border-color);
}

.flashcard-front {
    background-color: var(--bg-card);
    color: var(--text-main);
}

.flashcard-back {
    background-color: var(--primary-light);
    color: var(--text-main);
    transform: rotateY(180deg);
    overflow-y: auto;
    text-align: left;
    font-size: 0.92rem;
    line-height: 1.5;
}

.quick-chips {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
    flex-wrap: wrap;
}

.chip {
    background: var(--bg-subtle);
    padding: 0.35rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    cursor: pointer;
    border: 1px solid var(--border-color);
    color: var(--text-main);
}

.chip:hover {
    border-color: var(--primary);
    color: var(--primary);
}

/* Modal Overlay */
.modal-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem;
    max-width: 600px;
    width: 90%;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.modal-header h2 {
    font-size: 1.25rem;
    font-weight: 800;
}

.form-group {
    margin-bottom: 1.25rem;
}

.form-group label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}

.preset-btns {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}

.preset-btn {
    padding: 0.4rem 0.8rem;
    font-size: 0.8rem;
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    color: var(--text-main);
    border-radius: 6px;
}

.preset-btn:hover {
    border-color: var(--primary);
    color: var(--primary);
}
"""

Path("static/styles.css").write_text(css_content, encoding="utf-8")
print("styles.css written successfully!")
