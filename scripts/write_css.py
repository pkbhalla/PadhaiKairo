from pathlib import Path

css = """
:root {
    --primary: #4F46E5;
    --primary-hover: #4338CA;
    --primary-light: #EEF2FF;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --danger-bg: #FEF2F2;
    --bg-page: #F8FAFC;
    --bg-card: #FFFFFF;
    --bg-subtle: #F1F5F9;
    --text-main: #0F172A;
    --text-muted: #64748B;
    --border-color: #E2E8F0;
    --header-bg: #FFFFFF;
}
[data-theme="dark"] {
    --bg-page: #0B0F19;
    --bg-card: #131B2E;
    --bg-subtle: #1E293B;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --border-color: #2D3748;
    --header-bg: #131B2E;
    --primary-light: #1E1E38;
    --danger-bg: #7F1D1D;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
body { background: var(--bg-page); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }
header { background: var(--header-bg); border-bottom: 1px solid var(--border-color); padding: 0.85rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
.brand { display: flex; align-items: center; gap: 0.75rem; }
.brand-logo { width: 36px; height: 36px; background: linear-gradient(135deg, var(--primary), #818CF8); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 800; font-size: 1.2rem; }
.brand-text h1 { font-size: 1.1rem; font-weight: 800; color: var(--text-main); }
.brand-text p { font-size: 0.75rem; color: var(--text-muted); }
.header-actions { display: flex; align-items: center; gap: 0.8rem; }
.user-select-container { display: flex; align-items: center; gap: 0.5rem; background: var(--bg-subtle); padding: 0.4rem 0.8rem; border-radius: 8px; border: 1px solid var(--border-color); }
select { background: transparent; border: none; color: var(--text-main); font-weight: 600; font-size: 0.85rem; outline: none; cursor: pointer; }
.theme-btn { background: var(--bg-subtle); border: 1px solid var(--border-color); color: var(--text-main); width: 36px; height: 36px; border-radius: 8px; cursor: pointer; font-size: 1.1rem; }
.btn-guardian { background: #EF4444; color: white; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 700; font-size: 0.85rem; border: none; cursor: pointer; }
.nav-tabs { background: var(--header-bg); border-bottom: 1px solid var(--border-color); padding: 0.25rem 2rem; display: flex; gap: 0.5rem; overflow-x: auto; }
.tab-item { padding: 0.75rem 1.1rem; font-size: 0.88rem; font-weight: 600; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
.tab-item:hover { color: var(--primary); }
.tab-item.active { color: var(--primary); border-bottom-color: var(--primary); }
.container { max-width: 1400px; margin: 1.5rem auto; padding: 0 1.5rem; width: 100%; flex: 1; }
.tab-content { display: none; }
.tab-content.active { display: grid; gap: 1.5rem; }
.grid-2 { grid-template-columns: 1.2fr 1fr; }
.grid-1 { grid-template-columns: 1fr; }
.card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); display: flex; flex-direction: column; overflow: hidden; }
.card-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 1rem; font-weight: 700; color: var(--text-main); }
.card-body { padding: 1.5rem; flex: 1; }
.concept-item { margin-bottom: 1.25rem; cursor: pointer; }
.concept-meta { display: flex; justify-content: space-between; font-size: 0.88rem; margin-bottom: 0.4rem; }
.progress-bar-container { height: 10px; background: var(--bg-subtle); border-radius: 6px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
.fill-healthy { background: var(--success); }
.fill-warning { background: var(--warning); }
.fill-decayed { background: var(--danger); }
.chat-box { height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 1rem; }
.msg { max-width: 85%; padding: 0.75rem 1rem; border-radius: 12px; font-size: 0.9rem; line-height: 1.5; }
.msg-user { align-self: flex-end; background: var(--primary); color: white; }
.msg-agent { align-self: flex-start; background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color); }
.chat-input-row { display: flex; gap: 0.5rem; }
input[type="text"] { flex: 1; padding: 0.7rem 1rem; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-main); border-radius: 8px; outline: none; }
button { padding: 0.6rem 1.1rem; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; font-size: 0.88rem; }
.btn-primary { background: var(--primary); color: white; }
.btn-approve { background: var(--success); color: white; padding: 0.4rem 0.8rem; }
.nudge-card { border: 1px solid var(--border-color); background: var(--danger-bg); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
.nudge-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-weight: 700; color: var(--danger); }
.nudge-body { font-size: 0.85rem; color: var(--text-main); white-space: pre-line; background: var(--bg-card); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color); margin-top: 0.5rem; }
.flashcard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; }
.flashcard { height: 200px; cursor: pointer; perspective: 1000px; }
.flashcard-inner { position: relative; width: 100%; height: 100%; transition: transform 0.6s; transform-style: preserve-3d; border-radius: 10px; border: 1px solid var(--border-color); }
.flashcard.flipped .flashcard-inner { transform: rotateY(180deg); }
.flashcard-front, .flashcard-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.flashcard-front { background: var(--bg-card); color: var(--text-main); }
.flashcard-back { background: var(--primary-light); color: var(--text-main); transform: rotateY(180deg); overflow-y: auto; text-align: left; font-size: 0.88rem; }
.quick-chips { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
.chip { background: var(--bg-subtle); padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; cursor: pointer; border: 1px solid var(--border-color); color: var(--text-main); }
"""

Path("static/styles.css").write_text(css, encoding="utf-8")
print("CSS written successfully!")
