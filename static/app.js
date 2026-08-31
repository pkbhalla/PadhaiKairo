/**
 * PadhaiKairo App — app.js
 * Handles all interactivity for the NotebookLM-style two-panel dashboard.
 */

/* ── State ─────────────────────────────────────────────── */
const state = {
  user: { id: null, name: 'Student', email: '', picture: null },
  currentSubjectId: null,
  currentSubjectTitle: '',
  subjects: [],
  sources: [],
  guestMsgCount: 0,
  flashcards: [],
  fcIndex: 0,
  currentQuiz: null,
  selectedAnswers: {},
};

/* ── Init ───────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  await loadAuthStatus();
  await loadSubjects();
  await loadHomeSummary();
  document.addEventListener('keydown', handleGlobalKeys);
});

/* ── Theme ──────────────────────────────────────────────── */
function initTheme() {
  const saved = localStorage.getItem('kairo-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.innerText = saved === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.innerText = next === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('kairo-theme', next);
}

/* ── Auth ───────────────────────────────────────────────── */
async function loadAuthStatus() {
  try {
    const res = await fetch('/auth/status');
    const data = await res.json();
    if (data.authenticated) {
      state.user.name = data.name || 'Student';
      state.user.email = data.email || '';
      state.user.id = data.learnerId || (data.email ? data.email.split('@')[0].replace(/[^a-z0-9_]/gi, '') : 'guest');
      state.user.picture = data.picture || null;
    } else {
      state.user.id = 'guest';
      state.user.name = 'Guest';
      state.user.email = '';
      state.user.picture = null;
    }
  } catch (e) {
    state.user.id = 'guest';
  }

  // Update UI
  const nameEl = document.getElementById('user-name-short');
  const emailEl = document.getElementById('user-email-full');
  const avatar = document.getElementById('user-avatar');

  if (nameEl) nameEl.innerText = (state.user.name || 'Student').split(' ')[0];
  if (emailEl) emailEl.innerText = state.user.email || 'Guest';
  if (avatar) {
    if (state.user.picture) {
      avatar.innerHTML = `<img src="${state.user.picture}" alt="Avatar">`;
    } else {
      avatar.innerText = (state.user.name || 'S').charAt(0).toUpperCase();
    }
  }
}

function toggleUserDropdown() {
  const dd = document.getElementById('user-dropdown');
  if (!dd) return;
  dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
  const menu = document.getElementById('user-menu');
  const dd = document.getElementById('user-dropdown');
  if (dd && menu && !menu.contains(e.target) && !dd.contains(e.target)) {
    dd.style.display = 'none';
  }
});

/* ── Subjects (user-defined only) ──────────────────────── */
async function loadSubjects() {
  if (!state.user.id) return;
  try {
    const res = await fetch(`/courses?learner_id=${state.user.id}`);
    const data = await res.json();
    state.subjects = data.courses || [];

    const select = document.getElementById('subject-select');
    if (!select) return;

    if (state.subjects.length === 0) {
      select.innerHTML = `<option value="__new__">+ Add First Subject</option>`;
      state.currentSubjectId = null;
      state.currentSubjectTitle = '';
      state.sources = [];
      renderSourcesList();
      renderMasteryList([]);
      showEmptyHome();
      await loadNudges();
      return;
    }

    select.innerHTML = state.subjects.map(s =>
      `<option value="${s.id}">${s.title}</option>`
    ).join('') + `<option value="__new__">＋ Add New Subject</option>`;

    // Restore last selected subject or default to first
    const saved = localStorage.getItem('kairo-subject-' + state.user.id);
    const match = saved && state.subjects.find(s => s.id === saved);
    state.currentSubjectId = match ? match.id : state.subjects[0].id;
    state.currentSubjectTitle = match ? match.title : state.subjects[0].title;
    select.value = state.currentSubjectId;

    await loadSources();
    await loadMastery();
    await loadNudges();
    updateChatChips();
  } catch (e) {
    console.error('loadSubjects error:', e);
  }
}

function handleSubjectChange(id) {
  if (id === '__new__') { showAddSubjectModal(); return; }
  const match = state.subjects.find(s => s.id === id);
  if (!match) return;
  state.currentSubjectId = id;
  state.currentSubjectTitle = match.title;
  localStorage.setItem('kairo-subject-' + state.user.id, id);
  loadSources();
  loadMastery();
  loadNudges();
  updateChatChips();
  loadHomeSummary();
}

/* ── Home Summary ───────────────────────────────────────── */
async function loadHomeSummary() {
  try {
    const res = await fetch(`/home/summary?learner_id=${state.user.id}`);
    const data = await res.json();

    const greetEl = document.getElementById('home-greeting');
    const subEl = document.getElementById('home-sub');
    if (greetEl) greetEl.innerText = data.greeting || 'Welcome back!';
    if (subEl) {
      const subj = state.subjects.length;
      subEl.innerText = subj > 0
        ? `You have ${subj} active subject${subj > 1 ? 's' : ''}. Keep it up!`
        : 'Add your first subject to get started.';
    }

    setEl('stat-subjects', data.totalSubjects ?? state.subjects.length);
    setEl('stat-sources', data.totalSources ?? 0);
    setEl('stat-days', data.examDaysLeft != null ? data.examDaysLeft : '—');

    // Priority concept card
    const wrap = document.getElementById('priority-card-wrap');
    if (data.priorityConcept && data.priorityConcept.effectiveMastery < 0.7) {
      const pct = Math.round((data.priorityConcept.effectiveMastery || 0) * 100);
      setEl('priority-concept-name', data.priorityConcept.name || '—');
      setEl('priority-mastery-text', `Current mastery: ${pct}% — needs review soon`);
      if (wrap) wrap.style.display = 'block';
    } else if (wrap) {
      wrap.style.display = 'none';
    }

    // Exam pill in header
    const pill = document.getElementById('exam-pill');
    const daysText = document.getElementById('exam-days-text');
    if (data.examDaysLeft != null && pill) {
      pill.style.display = 'inline-flex';
      if (daysText) daysText.innerText = `${data.examDaysLeft} days to exam`;
      if (data.examDaysLeft <= 5) pill.classList.add('urgent');
      else pill.classList.remove('urgent');
    }

    // Show/hide empty home
    if (!data.totalSubjects || data.totalSubjects === 0) {
      showEmptyHome();
    } else {
      const emptyEl = document.getElementById('home-empty');
      if (emptyEl) emptyEl.style.display = 'none';
    }
  } catch (e) { console.error('loadHomeSummary:', e); }
}

function showEmptyHome() {
  const emptyEl = document.getElementById('home-empty');
  if (emptyEl) emptyEl.style.display = 'block';
}

/* ── Sources (Left Sidebar) ─────────────────────────────── */
async function loadSources() {
  if (!state.currentSubjectId) return;
  try {
    const res = await fetch(`/sources?learner_id=${state.user.id}&course_id=${state.currentSubjectId}`);
    const data = await res.json();
    state.sources = data.sources || [];
    renderSourcesList();
    updateGroundingBadge();
  } catch (e) { console.error('loadSources:', e); }
}

let activeSource = null;

function renderSourcesList() {
  const container = document.getElementById('sources-list');
  if (!container) return;

  if (state.sources.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding:1.5rem 0.5rem; gap:0.4rem;">
        <span class="empty-icon" style="font-size:1.75rem;">📂</span>
        <span class="empty-desc" style="font-size:0.78rem;">No sources yet. Add a YouTube lecture or paste your notes.</span>
      </div>`;
    return;
  }

  container.innerHTML = state.sources.map(src => {
    const icon = src.type === 'youtube_transcript' ? '📺' : src.type === 'text_note' ? '📝' : '📄';
    const badgeClass = src.type === 'youtube_transcript' ? 'badge-yt' : src.type === 'text_note' ? 'badge-note' : 'badge-doc';
    const badgeLabel = src.type === 'youtube_transcript' ? 'YouTube' : src.type === 'text_note' ? 'Notes' : 'Doc';
    const chars = src.charCount || (src.content ? src.content.length : 0);
    const title = src.title || 'Untitled Source';
    return `
      <div class="source-card" onclick="openSourceModal('${escAttr(src.id)}')" style="cursor:pointer;" title="Click to view full transcript & study notes">
        <div class="source-card-header">
          <span class="source-icon">${icon}</span>
          <span class="source-name">${truncate(title, 42)}</span>
        </div>
        <div class="source-meta">
          <span class="source-badge ${badgeClass}">${badgeLabel}</span>
          <span>${chars.toLocaleString()} chars · View ↗</span>
        </div>
      </div>`;
  }).join('');
}

function openSourceModal(sourceId) {
  const src = state.sources.find(s => s.id === sourceId);
  if (!src) return;
  activeSource = src;

  const modal = document.getElementById('view-source-modal');
  const titleEl = document.getElementById('view-source-title');
  const metaEl = document.getElementById('view-source-meta');
  const iconEl = document.getElementById('view-source-icon');
  const contentEl = document.getElementById('view-source-content');
  const linkBox = document.getElementById('view-source-link-container');
  const linkEl = document.getElementById('view-source-url');

  if (titleEl) titleEl.innerText = src.title || 'Untitled Source';
  if (iconEl) iconEl.innerText = src.type === 'youtube_transcript' ? '📺' : src.type === 'text_note' ? '📝' : '📄';
  if (metaEl) {
    const typeLabel = src.type === 'youtube_transcript' ? 'YouTube Lecture Transcript' : src.type === 'text_note' ? 'Lecture Notes' : 'Study Document';
    const chars = (src.charCount || src.content?.length || 0).toLocaleString();
    metaEl.innerText = `${typeLabel} • ${chars} characters`;
  }
  if (contentEl) contentEl.innerText = src.content || 'No content found.';

  if (src.sourceUrl) {
    if (linkBox) linkBox.style.display = 'block';
    if (linkEl) { linkEl.href = src.sourceUrl; linkEl.innerText = `🔗 ${src.sourceUrl}`; }
  } else {
    if (linkBox) linkBox.style.display = 'none';
  }

  if (modal) modal.classList.add('open');
}

function closeViewSourceModal() {
  const modal = document.getElementById('view-source-modal');
  if (modal) modal.classList.remove('open');
}

function copySourceContent() {
  if (activeSource?.content) {
    navigator.clipboard.writeText(activeSource.content).then(() => alert('Source content copied to clipboard!'));
  }
}

function generateCardsFromCurrentSource() {
  closeViewSourceModal();
  switchPanel('flashcards');
  if (activeSource?.title) {
    const input = document.getElementById('fc-topic-input');
    if (input) input.value = activeSource.title.replace('YouTube Lecture — ', '').replace('Lecture Video (', '').replace(')', '').trim();
  }
  generateFlashcards();
}

function generateGuideFromCurrentSource() {
  closeViewSourceModal();
  switchPanel('guide');
  if (activeSource?.title) {
    const input = document.getElementById('guide-topic-input');
    if (input) input.value = activeSource.title.replace('YouTube Lecture — ', '').replace('Lecture Video (', '').replace(')', '').trim();
  }
  generateStudyGuide();
}

function updateGroundingBadge() {
  const badge = document.getElementById('grounding-badge');
  if (!badge) return;
  badge.style.display = state.sources.length > 0 ? 'inline-flex' : 'none';
  badge.innerHTML = `● Grounded in ${state.sources.length} source${state.sources.length > 1 ? 's' : ''}`;
}

/* ── Add Source Drawer ──────────────────────────────────── */
function toggleAddSourceDrawer() {
  const drawer = document.getElementById('add-source-drawer');
  if (!drawer) return;
  const isOpen = drawer.classList.contains('open');
  drawer.classList.toggle('open', !isOpen);
}

function switchDrawerTab(tab) {
  document.getElementById('drawer-yt').style.display = tab === 'yt' ? 'block' : 'none';
  document.getElementById('drawer-notes').style.display = tab === 'notes' ? 'block' : 'none';
  document.getElementById('tab-yt').classList.toggle('active', tab === 'yt');
  document.getElementById('tab-notes').classList.toggle('active', tab === 'notes');
}

function onYtUrlInput() {
  const status = document.getElementById('yt-status');
  if (status) status.innerText = '';
}

async function fetchYtTranscript() {
  const url = document.getElementById('yt-url-input')?.value?.trim();
  const status = document.getElementById('yt-status');
  if (!url) { if (status) status.innerText = 'Please paste a YouTube URL.'; return; }
  if (!state.currentSubjectId) {
    if (status) status.innerText = 'Add a subject first (use + Add Subject modal).';
    return;
  }

  if (status) status.innerHTML = '⏳ Extracting captions…';
  try {
    const res = await fetch('/youtube/fetch-transcript', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (data.success) {
      if (status) status.innerHTML = `<span style="color:var(--success); font-weight:600;">✓ Extracted ${data.charCount.toLocaleString()} chars</span>`;
      const title = data.title || `YouTube Lecture — ${url.split('v=')[1]?.split('&')[0] || 'Video'}`;
      // Ingest as source
      const addRes = await fetch('/sources/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          source_type: 'youtube_transcript',
          content: data.text,
          source_url: url,
          learner_id: state.user.id,
          course_id: state.currentSubjectId
        })
      });
      const addedData = await addRes.json();
      document.getElementById('yt-url-input').value = '';
      await loadSources();
      if (addedData.id) {
        openSourceModal(addedData.id);
      }
    } else {
      if (status) status.innerHTML = `<span style="color:var(--warning);">⚠️ ${data.error || 'No captions found'}</span>`;
    }
  } catch (e) {
    if (status) status.innerText = 'Error connecting to server.';
  }
}

async function addNotesSource() {
  const content = document.getElementById('notes-input')?.value?.trim();
  const title = document.getElementById('notes-title-input')?.value?.trim() || 'Lecture Notes';
  if (!content) { alert('Please paste some notes first.'); return; }
  if (!state.currentSubjectId) { showAddSubjectModal(); return; }

  await fetch('/sources/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title, source_type: 'text_note', content,
      learner_id: state.user.id, course_id: state.currentSubjectId
    })
  });
  document.getElementById('notes-input').value = '';
  document.getElementById('notes-title-input').value = '';
  await loadSources();
  toggleAddSourceDrawer();
}

/* ── Panel Navigation ───────────────────────────────────── */
function switchPanel(panelId) {
  document.querySelectorAll('.tool-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const panel = document.getElementById('panel-' + panelId);
  const nav = document.getElementById('nav-' + panelId);
  if (panel) panel.classList.add('active');
  if (nav) nav.classList.add('active');

  // Show/hide scan button
  const scanBtn = document.getElementById('btn-run-scan');
  if (scanBtn) scanBtn.style.display = panelId === 'guardian' ? 'inline-flex' : 'none';

  // Load panel-specific data
  if (panelId === 'mastery') loadMastery();
  if (panelId === 'guardian') loadNudges();
}

/* ── Chat ───────────────────────────────────────────────── */
function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function quickPrompt(text) {
  const input = document.getElementById('chat-input');
  if (input) { input.value = text; input.focus(); sendChatMessage(); }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  appendChatMsg(text, 'user');
  input.value = '';
  input.style.height = 'auto';

  showTypingIndicator();
  state.guestMsgCount++;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        learner_id: state.user.id,
        course_id: state.currentSubjectId || 'general'
      })
    });
    const data = await res.json();
    removeTypingIndicator();
    appendChatMsg(data.message || '…', 'agent');

    if (data.type === 'quiz' && data.data?.questions) {
      switchPanel('quiz');
      renderQuiz(data.data);
    }
  } catch (e) {
    removeTypingIndicator();
    appendChatMsg('Sorry, something went wrong. Please try again.', 'agent');
  }
}

function appendChatMsg(text, role) {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  div.innerHTML = renderMarkdown(text);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function showTypingIndicator() {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = 'typing-indicator';
  el.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function updateChatChips() {
  const chips = document.getElementById('chat-chips');
  if (!chips || !state.currentSubjectTitle) return;
  const title = state.currentSubjectTitle;
  chips.innerHTML = `
    <span class="chip" onclick="quickPrompt('Explain the core concepts of ${title}')">🔍 Explain concepts</span>
    <span class="chip" onclick="quickPrompt('Quiz me on the weakest topics in ${title}')">🎯 Quiz me</span>
    <span class="chip" onclick="quickPrompt('Help me plan my ${title} revision into Google Calendar')">📅 Plan revision</span>
    <span class="chip" onclick="quickPrompt('What should I review for my ${title} exam?')">⚡ Exam focus</span>
  `;
}

/* ── Flashcards ─────────────────────────────────────────── */
async function generateFlashcards() {
  const topicInput = document.getElementById('fc-topic-input');
  const topic = topicInput?.value?.trim() || state.currentSubjectTitle || 'Core Concepts';
  const stage = document.getElementById('fc-stage');

  if (!stage) return;
  stage.innerHTML = `<div class="empty-state"><span class="empty-icon" style="font-size:2rem;">⏳</span><span class="empty-desc">Generating flashcards from your lectures…</span></div>`;

  try {
    const res = await fetch('/flashcards/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, count: 6, learner_id: state.user.id, course_id: state.currentSubjectId || 'general' })
    });
    const data = await res.json();
    state.flashcards = data.cards || [];
    state.fcIndex = 0;
    if (state.flashcards.length === 0) {
      stage.innerHTML = `<div class="empty-state"><span class="empty-icon">😕</span><span class="empty-desc">No flashcards generated. Try a more specific topic.</span></div>`;
    } else {
      renderFlashcard();
    }
  } catch (e) {
    stage.innerHTML = `<div class="empty-state"><span style="color:var(--danger);">Failed to generate flashcards.</span></div>`;
  }
}

function renderFlashcard() {
  const stage = document.getElementById('fc-stage');
  if (!stage || state.flashcards.length === 0) return;

  const card = state.flashcards[state.fcIndex];
  const total = state.flashcards.length;
  const i = state.fcIndex;

  stage.innerHTML = `
    <div class="card-counter">Card ${i + 1} of ${total} · ${card.difficulty || 'Medium'}</div>
    <div class="flashcard" id="fc-card" onclick="flipCard()">
      <div class="flashcard-inner">
        <div class="flashcard-face flashcard-front">
          <div class="card-face-label">Question</div>
          <div class="card-question">${escHtml(card.front)}</div>
          <div style="margin-top:auto; font-size:0.72rem; color:var(--text-faint);">Click or press Space to flip</div>
        </div>
        <div class="flashcard-face flashcard-back">
          <div class="card-face-label">Answer</div>
          <div class="card-answer">${escHtml(card.back)}</div>
        </div>
      </div>
    </div>
    <div class="flashcard-controls">
      <button class="flashcard-nav-btn" onclick="prevCard()" ${i === 0 ? 'disabled' : ''}>←</button>
      <span style="font-size:0.82rem; color:var(--text-muted);">${i + 1} / ${total}</span>
      <button class="flashcard-nav-btn" onclick="nextCard()" ${i === total - 1 ? 'disabled' : ''}>→</button>
    </div>
  `;
}

function flipCard() {
  const card = document.getElementById('fc-card');
  if (card) card.classList.toggle('flipped');
}

function nextCard() {
  if (state.fcIndex < state.flashcards.length - 1) {
    state.fcIndex++;
    renderFlashcard();
  }
}

function prevCard() {
  if (state.fcIndex > 0) {
    state.fcIndex--;
    renderFlashcard();
  }
}

/* ── Quiz ───────────────────────────────────────────────── */
function setQuizTopic(topic) {
  const input = document.getElementById('quiz-topic-input');
  if (input) input.value = topic;
  generateCustomQuiz();
}

async function generateCustomQuiz() {
  const input = document.getElementById('quiz-topic-input');
  const topic = input?.value?.trim() || state.currentSubjectTitle || 'Core Concepts';
  const body = document.getElementById('quiz-body');
  const submitBtn = document.getElementById('btn-submit-quiz');

  if (!body) return;
  body.innerHTML = `<div class="empty-state"><span class="empty-icon" style="font-size:2rem;">⏳</span><span class="empty-desc">Generating 5-question conceptual drill…</span></div>`;
  if (submitBtn) submitBtn.style.display = 'none';
  state.selectedAnswers = {};

  try {
    const res = await fetch('/quiz/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, num_questions: 5, learner_id: state.user.id, course_id: state.currentSubjectId || 'general' })
    });
    const data = await res.json();
    renderQuiz(data);
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><span style="color:var(--danger);">Failed to generate quiz.</span></div>`;
  }
}

function renderQuiz(quizData) {
  state.currentQuiz = quizData;
  state.selectedAnswers = {};
  const body = document.getElementById('quiz-body');
  const titleEl = document.getElementById('quiz-title');
  const submitBtn = document.getElementById('btn-submit-quiz');

  if (titleEl) titleEl.innerHTML = `📝 Practice Quiz: ${escHtml(quizData.topic || 'Concepts')}`;
  if (submitBtn) submitBtn.style.display = 'inline-flex';

  if (!body || !quizData.questions?.length) {
    if (body) body.innerHTML = `<div class="empty-state"><span class="empty-desc">No questions generated.</span></div>`;
    return;
  }

  body.innerHTML = quizData.questions.map((q, qi) => `
    <div class="quiz-question" id="q-block-${q.id || qi}">
      <div class="q-label">Question ${qi + 1} of ${quizData.questions.length}</div>
      <div class="q-text">${escHtml(q.question)}</div>
      ${(q.options || []).map((opt, oi) => `
        <button class="option-btn" id="opt-${q.id || qi}-${oi}" onclick="selectOption(${JSON.stringify(q.id || qi)}, ${oi})">
          <strong>${String.fromCharCode(65 + oi)}.</strong> ${escHtml(opt)}
        </button>
      `).join('')}
    </div>
  `).join('');
}

function selectOption(qId, optIdx) {
  state.selectedAnswers[qId] = optIdx;
  // Reset all options for this question
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`opt-${qId}-${i}`);
    if (el) el.classList.remove('selected');
  }
  const active = document.getElementById(`opt-${qId}-${optIdx}`);
  if (active) active.classList.add('selected');
}

async function submitQuiz() {
  if (!state.currentQuiz) return;
  const submitBtn = document.getElementById('btn-submit-quiz');
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch('/quiz/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        concept_name: state.currentQuiz.concept_name || state.currentQuiz.topic,
        questions: state.currentQuiz.questions,
        answers: state.selectedAnswers,
        learner_id: state.user.id,
        course_id: state.currentSubjectId || 'general'
      })
    });
    const result = await res.json();
    const pct = Math.round((result.score || 0) * 100);

    // Show result banner
    const body = document.getElementById('quiz-body');
    const banner = document.createElement('div');
    banner.style.cssText = `
      background:${pct >= 70 ? 'var(--success-bg)' : 'var(--warning-bg)'};
      border:1px solid ${pct >= 70 ? 'var(--success-border)' : 'var(--warning-border)'};
      border-radius:var(--radius-md); padding:1rem 1.25rem; margin-bottom:1rem;
      font-weight:600; font-size:0.95rem; color:${pct >= 70 ? 'var(--success)' : 'var(--warning)'};
    `;
    banner.innerHTML = `${pct >= 70 ? '🎉' : '📈'} Score: ${pct}% (${result.correctCount}/${result.total}) · Updated Mastery: ${Math.round((result.newMastery || 0) * 100)}%`;
    if (body) body.insertBefore(banner, body.firstChild);

    if (submitBtn) submitBtn.style.display = 'none';
    await loadMastery();
  } catch (e) {
    alert('Grading error: ' + e);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

/* ── Study Guide ────────────────────────────────────────── */
async function generateStudyGuide() {
  const topicInput = document.getElementById('guide-topic-input');
  const topic = topicInput?.value?.trim() || state.currentSubjectTitle || 'Core Concepts';
  const output = document.getElementById('guide-output');
  const copyBtn = document.getElementById('btn-copy-guide');

  if (!output) return;
  output.innerHTML = `<div class="empty-state"><span class="empty-icon" style="font-size:2rem;">⏳</span><span class="empty-desc">Synthesizing study guide from your lectures…</span></div>`;
  if (copyBtn) copyBtn.style.display = 'none';

  try {
    const res = await fetch('/study-guide/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, learner_id: state.user.id, course_id: state.currentSubjectId || 'general' })
    });
    const data = await res.json();
    const md = data.contentMarkdown || '';
    output.innerHTML = `<div class="guide-content">${renderMarkdown(md)}</div>`;
    if (copyBtn) copyBtn.style.display = 'inline-flex';
  } catch (e) {
    output.innerHTML = `<div class="empty-state"><span style="color:var(--danger);">Failed to generate guide.</span></div>`;
  }
}

function copyGuide() {
  const content = document.getElementById('guide-output')?.innerText;
  if (content) {
    navigator.clipboard.writeText(content).then(() => alert('Study guide copied to clipboard!'));
  }
}

/* ── Mastery Graph ──────────────────────────────────────── */
async function loadMastery() {
  if (!state.currentSubjectId) return;
  try {
    const res = await fetch(`/mastery?learner_id=${state.user.id}&course_id=${state.currentSubjectId}`);
    const data = await res.json();
    renderMasteryList(data.concepts || []);

    if (data.course?.examDate) {
      const days = Math.max(0, Math.round(
        (new Date(data.course.examDate) - new Date()) / 86400000
      ));
      setEl('mastery-exam-badge', `⏰ ${days} days to exam`);
    }
  } catch (e) { console.error('loadMastery:', e); }
}

function renderMasteryList(concepts) {
  const list = document.getElementById('mastery-list');
  if (!list) return;

  if (!concepts.length) {
    list.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📊</span>
        <span class="empty-title">No mastery data yet</span>
        <span class="empty-desc">Take practice quizzes to build your forgetting-curve mastery graph.</span>
      </div>`;
    return;
  }

  list.innerHTML = concepts.map(c => {
    const pct = Math.round((c.effectiveMastery || 0) * 100);
    const stClass = pct >= 70 ? 'healthy' : pct >= 40 ? 'moderate' : 'decayed';
    const fillClass = pct >= 70 ? 'fill-healthy' : pct >= 40 ? 'fill-moderate' : 'fill-decayed';
    const label = pct >= 70 ? '✓ Strong' : pct >= 40 ? '~ Moderate' : '⚠ Decayed';
    return `
      <div class="concept-row" onclick="setQuizTopic('${escAttr(c.name)}'); switchPanel('quiz');" title="Click to practice this concept">
        <div class="concept-row-header">
          <span class="concept-name">${escHtml(c.name)}</span>
          <span class="mastery-pct ${stClass}">${pct}% · ${label}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill ${fillClass}" style="width:${Math.max(3, pct)}%;"></div>
        </div>
      </div>`;
  }).join('');
}

/* ── Retention Guardian ─────────────────────────────────── */
async function runRetentionScan() {
  const btn = document.getElementById('btn-run-scan');
  if (btn) btn.innerText = '⏳ Scanning…';

  try {
    const res = await fetch(`/guardian/scan?learner_id=${state.user.id}&course_id=${state.currentSubjectId || 'general'}`, { method: 'POST' });
    const data = await res.json();
    const scanned = data.scannedConceptsCount || 0;
    const decayed = data.decayedCount || 0;
    const actions = data.actionsTaken?.length || 0;
    const daysLeft = data.examDaysLeft;
    const urgency = data.urgencyLevel || 'normal';
    const planSessions = data.calendarPlan?.scheduledRevisionSessions?.length || data.calendarPlan?.totalSessions || 0;

    const urgencyColor = urgency === 'critical' ? 'var(--danger)' : urgency === 'high' ? 'var(--warning)' : 'var(--brand)';
    const urgencyBg = urgency === 'critical' ? 'var(--danger-bg)' : urgency === 'high' ? 'var(--warning-bg)' : 'var(--brand-light)';

    const summary = document.createElement('div');
    summary.style.cssText = `background:${urgencyBg}; border:1px solid ${urgencyColor}; border-radius:var(--radius-md); padding:0.9rem 1.1rem; margin-bottom:1rem; font-size:0.85rem; color:var(--text-primary);`;
    summary.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
        <span style="font-weight:700; color:${urgencyColor}; font-size:0.9rem;">
          ⚡ Retention Scan Complete
        </span>
        <span style="background:${urgencyColor}; color:white; padding:0.15rem 0.5rem; border-radius:var(--radius-full); font-size:0.72rem; font-weight:700; text-transform:uppercase;">
          ${urgency} Urgency ${daysLeft != null ? `(${daysLeft}d to exam)` : ''}
        </span>
      </div>
      <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.4;">
        • Scanned <strong>${scanned} concepts</strong> & identified <strong>${decayed} decaying topics</strong>.<br>
        • Re-planned & synced <strong>${planSessions} revision sessions</strong> in Google Calendar across remaining days.<br>
        • Queued <strong>${actions} study nudges</strong> in your approval box below.
      </div>
    `;
    const container = document.getElementById('nudges-container');
    if (container) container.insertBefore(summary, container.firstChild);

    await loadNudges();
    await loadHomeSummary();
  } catch (e) { alert('Scan failed: ' + e); }
  finally { if (btn) btn.innerHTML = '⚡ Run Scan'; }
}

async function loadNudges() {
  if (!state.user.id) return;
  try {
    const courseParam = state.currentSubjectId ? `&course_id=${encodeURIComponent(state.currentSubjectId)}` : '';
    const res = await fetch(`/nudges?learner_id=${state.user.id}&status=pending${courseParam}`);
    const data = await res.json();
    renderNudges(data.nudges || []);
  } catch (e) { console.error('loadNudges:', e); }
}

function renderNudges(nudges) {
  const container = document.getElementById('nudges-container');
  if (!container) return;

  if (!nudges.length) {
    container.innerHTML = `
      <div class="empty-state" style="padding:2rem 0;">
        <span class="empty-icon">✅</span>
        <span class="empty-title">All clear!</span>
        <span class="empty-desc">No decaying concepts or pending study nudges for ${escHtml(state.currentSubjectTitle || 'this subject')}. Run a retention scan to check forgetting curves.</span>
      </div>`;
    return;
  }

  container.innerHTML = nudges.map(n => {
    const draft = n.emailDraft || {};
    const recipient = draft.to || state.user.email || 'You';
    const courseBadge = n.courseTitle || state.currentSubjectTitle;
    return `
      <div class="nudge-card">
        <div class="nudge-header">
          <div>
            <div class="nudge-concept">
              ${courseBadge ? `<span style="font-size:0.72rem; background:var(--brand-light); color:var(--brand); padding:0.15rem 0.45rem; border-radius:var(--radius-sm); font-weight:700; margin-right:0.4rem; display:inline-block;">${escHtml(courseBadge)}</span>` : ''}
              🔔 ${escHtml(n.conceptName || '—')}
            </div>
            <div class="nudge-decay">Reason: ${escHtml(n.reason || '—')}</div>
          </div>
          <button class="btn btn-success btn-sm" onclick="approveNudge('${escAttr(n.id)}')">
            ✓ Approve & Send
          </button>
        </div>
        ${draft.subject ? `
        <div class="nudge-email-preview">
          <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.25rem;"><strong>To:</strong> ${escHtml(recipient)}</div>
          <strong>Subject:</strong> ${escHtml(draft.subject)}<br>
          <span style="color:var(--text-faint);">${escHtml((draft.body || '').substring(0, 200))}…</span>
        </div>` : ''}
      </div>`;
  }).join('');
}

async function approveNudge(nudgeId) {
  try {
    const res = await fetch(`/nudges/${nudgeId}/approve?learner_id=${state.user.id}`, { method: 'POST' });
    const data = await res.json();
    alert(`✓ Nudge approved and sent via Gmail!\nMessage ID: ${data.messageId || '—'}`);
    await loadNudges();
  } catch (e) { alert('Approval failed: ' + e); }
}

async function syncCalendarPlan() {
  try {
    const res = await fetch('/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ learner_id: state.user.id, course_id: state.currentSubjectId || 'general' })
    });
    const data = await res.json();
    alert(`📅 Revision plan synced!\n${data.totalSessions || 0} sessions added to your Google Calendar.`);
  } catch (e) { alert('Sync failed: ' + e); }
}

/* ── Add Subject Modal ──────────────────────────────────── */
function showAddSubjectModal() {
  const modal = document.getElementById('add-subject-modal');
  if (modal) modal.classList.add('open');
  // Default exam date: 14 days from now
  const dateInput = document.getElementById('modal-exam-date');
  if (dateInput && !dateInput.value) {
    const d = new Date(); d.setDate(d.getDate() + 14);
    dateInput.value = d.toISOString().slice(0, 10);
  }
}

function closeAddSubjectModal() {
  const modal = document.getElementById('add-subject-modal');
  if (modal) modal.classList.remove('open');
}

// Close on outside click
document.addEventListener('click', (e) => {
  const modal = document.getElementById('add-subject-modal');
  if (modal && e.target === modal) closeAddSubjectModal();
});

function setPreset(title, topics, ytUrl) {
  setVal('modal-subject-title', title);
  setVal('modal-subtopics', topics);
  setVal('modal-yt-url', ytUrl);
  if (ytUrl) previewModalYt();
}

async function previewModalYt() {
  const url = document.getElementById('modal-yt-url')?.value?.trim();
  const status = document.getElementById('modal-yt-status');
  if (!url) return;
  if (status) status.innerHTML = '⏳ Extracting…';
  try {
    const res = await fetch('/youtube/fetch-transcript', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (status) {
      status.innerHTML = data.success
        ? `<span style="color:var(--success); font-weight:600;">✓ Found ${data.charCount?.toLocaleString()} chars</span>`
        : `<span style="color:var(--warning);">⚠️ ${data.error || 'No captions found'}</span>`;
    }
  } catch (e) {
    if (status) status.innerText = 'Error connecting to server.';
  }
}

async function createSubject() {
  const title = document.getElementById('modal-subject-title')?.value?.trim();
  const topicsRaw = document.getElementById('modal-subtopics')?.value?.trim();
  const examDate = document.getElementById('modal-exam-date')?.value;
  const ytUrl = document.getElementById('modal-yt-url')?.value?.trim();
  const notes = document.getElementById('modal-notes')?.value?.trim();

  if (!title) { alert('Please enter a subject title.'); return; }
  if (!topicsRaw) { alert('Please enter at least one subtopic.'); return; }

  const topics = topicsRaw.split(',').map(t => t.trim()).filter(Boolean);
  const btn = document.getElementById('btn-create-subject');
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Initializing…'; }

  try {
    const payload = {
      learner_id: state.user.id,
      learner_name: state.user.name,
      learner_email: state.user.email,
      course_title: title,
      subtopics: topics,
      exam_date_iso: examDate ? new Date(examDate).toISOString() : null,
      youtube_url: ytUrl || null,
      lecture_notes: notes || null,
    };

    const res = await fetch('/courses/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (result.courseId) {
      closeAddSubjectModal();
      await loadSubjects();
      // Switch to the new subject
      state.currentSubjectId = result.courseId;
      state.currentSubjectTitle = title;
      const select = document.getElementById('subject-select');
      if (select) select.value = result.courseId;
      await loadSources();
      await loadMastery();
      await loadHomeSummary();
      switchPanel('home');
      alert(`✓ "${title}" created!\n• ${result.concepts?.length || 0} subtopics initialized\n• ${result.sources?.length || 0} sources ingested\n• Calendar revision blocks scheduled`);
    }
  } catch (e) {
    alert('Error creating subject: ' + e);
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '⚡ Generate Mastery Graph & Schedule'; }
  }
}

/* ── Edit Exam Date Modal ───────────────────────────────── */
function openEditExamModal() {
  if (!state.currentSubjectId) {
    showAddSubjectModal();
    return;
  }
  const modal = document.getElementById('edit-exam-modal');
  if (modal) modal.classList.add('open');

  setVal('edit-exam-subject-title', state.currentSubjectTitle || 'Active Subject');
  
  // Set existing exam date if available
  const match = state.subjects.find(s => s.id === state.currentSubjectId);
  const input = document.getElementById('edit-exam-date-input');
  if (input) {
    if (match && match.examDate) {
      try {
        const d = new Date(match.examDate);
        input.value = d.toISOString().slice(0, 10);
      } catch (e) {
        input.value = '';
      }
    } else {
      const d = new Date(); d.setDate(d.getDate() + 7);
      input.value = d.toISOString().slice(0, 10);
    }
  }
}

function closeEditExamModal() {
  const modal = document.getElementById('edit-exam-modal');
  if (modal) modal.classList.remove('open');
}

async function saveExamDate() {
  const dateVal = document.getElementById('edit-exam-date-input')?.value;
  if (!dateVal) { alert('Please select a target exam date.'); return; }
  if (!state.currentSubjectId) return;

  const btn = document.getElementById('btn-save-exam-date');
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Updating & Re-planning…'; }

  try {
    const examIso = new Date(dateVal).toISOString();
    const res = await fetch(`/courses/${state.currentSubjectId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learner_id: state.user.id,
        course_id: state.currentSubjectId,
        exam_date_iso: examIso
      })
    });
    const data = await res.json();

    closeEditExamModal();
    await loadSubjects();
    await loadHomeSummary();
    await loadMastery();

    const days = data.examDaysLeft != null ? data.examDaysLeft : Math.round((new Date(dateVal) - new Date()) / 86400000);
    alert(`✓ Target exam date updated!\n• ${days} days remaining\n• Calendar revision slots recalculated`);
  } catch (e) {
    alert('Error updating exam date: ' + e);
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '⚡ Update & Recalculate Revision Plan'; }
  }
}

/* ── Edit Subject Modal ─────────────────────────────────── */
function openEditSubjectModal() {
  if (!state.currentSubjectId) { showAddSubjectModal(); return; }
  const modal = document.getElementById('edit-subject-modal');
  if (modal) modal.classList.add('open');

  const match = state.subjects.find(s => s.id === state.currentSubjectId);
  setVal('edit-subject-title', state.currentSubjectTitle || '');
  
  const dateInput = document.getElementById('edit-subject-exam-date');
  if (dateInput && match?.examDate) {
    try { dateInput.value = new Date(match.examDate).toISOString().slice(0, 10); } catch(e) {}
  }

  const topicsInput = document.getElementById('edit-subject-subtopics');
  if (topicsInput && match?.syllabusTopics) {
    topicsInput.value = match.syllabusTopics.join(', ');
  }
}

function closeEditSubjectModal() {
  const modal = document.getElementById('edit-subject-modal');
  if (modal) modal.classList.remove('open');
}

async function saveSubjectEdit() {
  const title = document.getElementById('edit-subject-title')?.value?.trim();
  const dateVal = document.getElementById('edit-subject-exam-date')?.value;
  const topicsRaw = document.getElementById('edit-subject-subtopics')?.value?.trim();

  if (!title) { alert('Subject title cannot be empty.'); return; }
  const btn = document.getElementById('btn-save-subject-edit');
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Saving…'; }

  try {
    const subtopics = topicsRaw ? topicsRaw.split(',').map(t => t.trim()).filter(Boolean) : null;
    const examIso = dateVal ? new Date(dateVal).toISOString() : null;

    const res = await fetch(`/courses/${state.currentSubjectId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learner_id: state.user.id,
        course_id: state.currentSubjectId,
        course_title: title,
        exam_date_iso: examIso,
        subtopics: subtopics
      })
    });
    const data = await res.json();
    
    closeEditSubjectModal();
    state.currentSubjectTitle = title;
    await loadSubjects();
    await loadHomeSummary();
    await loadMastery();
    alert(`✓ Subject "${title}" updated successfully!`);
  } catch (e) {
    alert('Error updating subject: ' + e);
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '✓ Save Subject Changes'; }
  }
}

/* ── Student Profile Modal ──────────────────────────────── */
async function openProfileModal() {
  const modal = document.getElementById('profile-modal');
  if (modal) modal.classList.add('open');

  // Load existing profile from backend
  try {
    const res = await fetch(`/learner/profile?learner_id=${state.user.id}`);
    const data = await res.json();
    const prof = data.profile || {};

    setVal('profile-name-input', prof.name || state.user.name || '');
    setVal('profile-email-input', prof.email || state.user.email || '');
    setVal('profile-tz-input', prof.timezone || 'Asia/Kolkata');
    
    const goalSel = document.getElementById('profile-goal-select');
    if (goalSel && prof.dailyGoalMinutes) goalSel.value = String(prof.dailyGoalMinutes);
    
    const paceSel = document.getElementById('profile-pace-select');
    if (paceSel && prof.studyPace) paceSel.value = prof.studyPace;
  } catch (e) {
    setVal('profile-name-input', state.user.name || '');
    setVal('profile-email-input', state.user.email || '');
  }
}

function closeProfileModal() {
  const modal = document.getElementById('profile-modal');
  if (modal) modal.classList.remove('open');
}

async function saveStudentProfile() {
  const name = document.getElementById('profile-name-input')?.value?.trim();
  const email = document.getElementById('profile-email-input')?.value?.trim();
  const tz = document.getElementById('profile-tz-input')?.value?.trim();
  const goal = parseInt(document.getElementById('profile-goal-select')?.value || '30', 10);
  const pace = document.getElementById('profile-pace-select')?.value || 'moderate';

  const btn = document.getElementById('btn-save-profile');
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Saving…'; }

  try {
    const res = await fetch('/learner/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learner_id: state.user.id,
        name: name,
        email: email,
        timezone: tz,
        daily_goal_minutes: goal,
        study_pace: pace
      })
    });
    const data = await res.json();

    if (name) state.user.name = name;
    if (email) state.user.email = email;

    // Update UI headers
    const nameEl = document.getElementById('user-name-short');
    const emailEl = document.getElementById('user-email-full');
    const paceBadge = document.getElementById('user-pace-badge');

    if (nameEl) nameEl.innerText = (state.user.name || 'Student').split(' ')[0];
    if (emailEl) emailEl.innerText = state.user.email;
    if (paceBadge) paceBadge.innerText = `Pace: ${pace.charAt(0).toUpperCase() + pace.slice(1)}`;

    closeProfileModal();
    await loadHomeSummary();
    alert('✓ Profile and learning preferences saved!');
  } catch (e) {
    alert('Error saving profile: ' + e);
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '✓ Save Profile Preferences'; }
  }
}

/* ── Global Keyboard Shortcuts ──────────────────────────── */
function handleGlobalKeys(e) {
  // Only when flashcard panel is active
  const fcPanel = document.getElementById('panel-flashcards');
  if (!fcPanel?.classList.contains('active')) return;

  if (e.key === ' ') { e.preventDefault(); flipCard(); }
  if (e.key === 'ArrowRight') nextCard();
  if (e.key === 'ArrowLeft') prevCard();
}

/* ── Utilities ──────────────────────────────────────────── */
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerText = val;
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function truncate(str, n) {
  return str.length > n ? str.slice(0, n) + '…' : str;
}

function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function renderMarkdown(md) {
  if (!md) return '';
  let html = md;

  // Convert code blocks (```lang ... ```)
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre class="code-block"><code class="lang-${lang}">${escHtml(code.trim())}</code></pre>`;
  });

  // Convert markdown tables
  html = html.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (match) => {
    const lines = match.trim().split(/\r?\n/).filter(l => l.trim());
    if (lines.length < 2) return match;
    let tableHtml = '<div class="table-responsive"><table class="md-table">';
    let isHeader = true;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (/^\|[-:\s|]+\|$/.test(line)) {
        isHeader = false;
        continue;
      }
      const cells = line.split('|').slice(1, -1).map(c => c.trim());
      if (isHeader && i === 0) {
        tableHtml += '<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
      } else {
        tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
      }
    }
    tableHtml += '</tbody></table></div>';
    return tableHtml;
  });

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>');

  // Blockquotes
  html = html.replace(/^> (.*$)/gim, '<blockquote class="md-quote">$1</blockquote>');

  // Bold & Italic (order: triple, double, single, underscores)
  html = html.replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*([^\*\n]+)\*/gim, '<em>$1</em>');
  html = html.replace(/_([^_\n]+)_/gim, '<em>$1</em>');

  // Inline code
  html = html.replace(/`([^`\n]+)`/gim, '<code class="inline-code">$1</code>');

  // Bullet Lists
  html = html.replace(/^\s*[-*•]\s+(.*$)/gim, '<li class="md-li">$1</li>');
  html = html.replace(/((?:<li class="md-li">.*?<\/li>\s*)+)/gim, '<ul class="md-ul">$1</ul>');

  // Numbered Lists
  html = html.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="md-oli">$1</li>');
  html = html.replace(/((?:<li class="md-oli">.*?<\/li>\s*)+)/gim, '<ol class="md-ol">$1</ol>');

  // Linebreaks and paragraphs
  html = html.replace(/\n\n+/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');

  return html;
}
