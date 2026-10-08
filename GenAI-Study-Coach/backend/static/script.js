// ── Dark Mode ──
const darkModeBtn = document.getElementById('darkModeBtn');

if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark');
    if (darkModeBtn) darkModeBtn.textContent = '☀️';
}

if (darkModeBtn) {
    darkModeBtn.addEventListener('click', () => {
        const isDark = document.body.classList.toggle('dark');
        darkModeBtn.textContent = isDark ? '☀️' : '🌙';
        localStorage.setItem('darkMode', isDark);
    });
}

// ── Sidebar Toggle ──
const sidebar        = document.getElementById('sidebar');
const sidebarToggle  = document.getElementById('sidebarToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            sidebar.classList.toggle('mobile-open');
            sidebarOverlay.classList.toggle('visible');
        } else {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        }
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('mobile-open');
        sidebarOverlay.classList.remove('visible');
    });
}

// Restore collapsed state on desktop
if (sidebar && localStorage.getItem('sidebarCollapsed') === 'true' && window.innerWidth > 768) {
    sidebar.classList.add('collapsed');
}

// ── Tab Switching ──
const tabBtns   = document.querySelectorAll('.sidebar-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

function switchTab(tabName) {
    tabBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tabName));
    tabPanels.forEach(panel => panel.classList.toggle('hidden', panel.id !== `panel-${tabName}`));
    localStorage.setItem('activeTab', tabName);
    // Close sidebar on mobile after selecting
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('mobile-open');
        sidebarOverlay.classList.remove('visible');
    }
}

if (tabBtns.length) {
    tabBtns.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
    const savedTab = localStorage.getItem('activeTab');
    if (savedTab && document.getElementById(`panel-${savedTab}`)) switchTab(savedTab);
}

function getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    if (ext === 'pdf')  return { icon: '📄', cls: 'pdf' };
    if (ext === 'docx') return { icon: '📝', cls: 'docx' };
    if (ext === 'txt')  return { icon: '📃', cls: 'txt' };
    return { icon: '📎', cls: 'default' };
}

// ── File State ──
let uploadedFiles = [];
const fileTagsContainer = document.getElementById('fileTagsContainer');
const fileInput = document.getElementById('fileInput');

const ALLOWED_EXTS = ['pdf', 'docx', 'txt'];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

function addFiles(files) {
    Array.from(files).forEach(f => {
        const ext = f.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTS.includes(ext)) return alert(`"${f.name}" is not supported. Use PDF, DOCX, or TXT.`);
        if (f.size > MAX_SIZE) return alert(`"${f.name}" exceeds the 10MB limit.`);
        if (!uploadedFiles.find(u => u.name === f.name)) {
            uploadedFiles.push(f);
            saveRecentDoc(decodeURIComponent(f.name));
        }
    });
    renderFileTags();
    detectTopic();
}

// ── File Input ──
if (fileInput) {
    fileInput.addEventListener('change', () => {
        addFiles(fileInput.files);
        fileInput.value = ''; // reset so same file can be re-added after removal
    });
}

// ── Drag and Drop ──
const dropZone = document.getElementById('dropZone');
if (dropZone) {
    ['dragenter', 'dragover'].forEach(evt =>
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('drag-over'); })
    );
    ['dragleave', 'drop'].forEach(evt =>
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); })
    );
    dropZone.addEventListener('drop', e => addFiles(e.dataTransfer.files));
}

// ── Recent Docs ──
const RECENT_DOCS_KEY = 'recentDocs';
const MAX_RECENT = 5;
const recentDocsSection = document.getElementById('recentDocsSection');
const recentDocsList = document.getElementById('recentDocsList');

function getRecentDocs() {
    return JSON.parse(localStorage.getItem(RECENT_DOCS_KEY) || '[]');
}

function saveRecentDoc(name) {
    const docs = getRecentDocs().filter(d => d !== name);
    docs.unshift(name);
    localStorage.setItem(RECENT_DOCS_KEY, JSON.stringify(docs.slice(0, MAX_RECENT)));
    renderRecentDocs();
}

function renderRecentDocs() {
    if (!recentDocsSection || !recentDocsList) return;
    const docs = getRecentDocs();
    if (!docs.length) { recentDocsSection.classList.add('hidden'); return; }
    recentDocsSection.classList.remove('hidden');
    recentDocsList.innerHTML = docs.map(name =>
        `<button class="recent-doc-btn" title="${name}">${name}</button>`
    ).join('');
}

renderRecentDocs();

// ── Char Count ──
const notesArea = document.getElementById('notes');
const charCount = document.getElementById('charCount');
if (notesArea && charCount) {
    notesArea.addEventListener('input', () => {
        const len = notesArea.value.length;
        charCount.textContent = len > 0 ? `${len.toLocaleString()} chars` : '0 chars';
        charCount.style.color = len > 50000 ? '#dc3545' : len > 20000 ? '#ffc107' : '#aaa';
    });
}

// ── Topic Detection Badge ──
const topicBadgeRow = document.getElementById('topicBadgeRow');
const topicBadge = document.getElementById('topicBadge');
const topicDetecting = document.getElementById('topicDetecting');
let topicDebounceTimer = null;
let topicDetectionPromise = null;

function detectTopic() {
    if (!topicBadgeRow || !uploadedFiles.length) {
        if (topicBadgeRow) topicBadgeRow.classList.add('hidden');
        topicDetectionPromise = null;
        return;
    }
    clearTimeout(topicDebounceTimer);
    topicDetectionPromise = new Promise(resolve => {
        topicDebounceTimer = setTimeout(async () => {
            topicBadgeRow.classList.remove('hidden');
            topicBadge.textContent = '';
            topicDetecting.classList.remove('hidden');

            try {
                const fd = new FormData();
                uploadedFiles.forEach(f => fd.append('file', f));
                const notes = document.getElementById('notes');
                if (notes && notes.value.trim()) fd.append('text', notes.value.trim());

                const res = await fetch('/detect-topic', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.topic) {
                    topicBadge.textContent = '🏷️ ' + data.topic;
                    topicDetecting.classList.add('hidden');
                }
            } catch {
                topicDetecting.classList.add('hidden');
            }
            resolve();
        }, 600);
    });
}

// ── Summarize with SSE Streaming ──
const summarizeBtn      = document.getElementById('summarizeBtn');
const loadingSummarize  = document.getElementById('loading-summarize');
const outputSummarize   = document.getElementById('output-summarize');
const outputTitleSum    = document.getElementById('outputTitle-summarize');
const outputContentSum  = document.getElementById('outputContent-summarize');
const copyBtnSum        = document.getElementById('copyBtn-summarize');
const exportBtnSum      = document.getElementById('exportBtn-summarize');

function renderSummary(text) {
    const lines = text.split('\n');
    let html = '<div class="summary-content">';
    let tableLines = [];

    function flushTable() {
        if (!tableLines.length) return;
        const rows = tableLines.filter(l => !l.match(/^\|[-| :]+\|$/));
        if (rows.length < 1) { tableLines = []; return; }
        const headers = rows[0].split('|').filter((_, i, a) => i > 0 && i < a.length - 1).map(h => h.trim());
        html += '<table class="summary-table"><thead><tr>' +
            headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
        rows.slice(1).forEach(row => {
            const cells = row.split('|').filter((_, i, a) => i > 0 && i < a.length - 1).map(c => c.trim());
            html += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
        });
        html += '</tbody></table>';
        tableLines = [];
    }

    lines.forEach(line => {
        if (line.trim().startsWith('|')) {
            tableLines.push(line.trim());
        } else {
            flushTable();
            const bold = line.match(/^\*\*(.+?)\*\*$/);
            if (bold)        html += `<div class="summary-heading">${bold[1]}</div>`;
            else if (line.trim()) html += `<div class="summary-para">${line}</div>`;
        }
    });
    flushTable();
    html += '</div>';
    return html;
}

if (summarizeBtn) {
    summarizeBtn.addEventListener('click', async () => {
        const notes = document.getElementById('notes');
        const text  = notes ? notes.value.trim() : '';
        if (!uploadedFiles.length && !text) {
            return alert('Please upload a file or paste your notes first.');
        }

        // Reset UI
        summarizeBtn.disabled = true;
        loadingSummarize.classList.remove('hidden');
        outputSummarize.classList.add('hidden');
        outputContentSum.innerHTML = '';

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));
        if (text) fd.append('text', text);

        try {
            const res = await fetch('/summarize/stream', { method: 'POST', body: fd });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Server error');
            }

            loadingSummarize.classList.add('hidden');
            outputSummarize.classList.remove('hidden');
            outputTitleSum.textContent = '📝 Summary';
            outputContentSum.innerHTML = '<span id="streamCursor"></span>';

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '', fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();
                for (const part of parts) {
                    if (!part.startsWith('data: ')) continue;
                    const data = JSON.parse(part.slice(6));
                    if (data.error) throw new Error(data.error);
                    if (data.chunk) {
                        fullText += data.chunk;
                        outputContentSum.innerHTML = renderSummary(fullText) +
                            (data.done ? '' : '<span id="streamCursor"></span>');
                    }
                    if (data.done) {
                        if (data.cached) outputTitleSum.innerHTML += ' <span class="cache-badge">⚡ Cached</span>';
                        outputContentSum.innerHTML = renderSummary(fullText);
                        copyBtnSum.classList.remove('hidden');
                        exportBtnSum.classList.remove('hidden');
                    }
                }
            }
        } catch (streamErr) {
            try {
                const res2 = await fetch('/summarize', { method: 'POST', body: fd });
                const data2 = await res2.json();
                if (data2.error) throw new Error(data2.error);
                loadingSummarize.classList.add('hidden');
                outputSummarize.classList.remove('hidden');
                outputTitleSum.innerHTML = '📝 Summary' + (data2.cached ? ' <span class="cache-badge">⚡ Cached</span>' : '');
                outputContentSum.innerHTML = renderSummary(data2.summary);
                copyBtnSum.classList.remove('hidden');
                exportBtnSum.classList.remove('hidden');
            } catch (e) {
                loadingSummarize.classList.add('hidden');
                outputSummarize.classList.remove('hidden');
                outputContentSum.innerHTML = `<div class="error">❌ ${e.message}</div>`;
            }
        } finally {
            summarizeBtn.disabled = false;
        }
    });
}

if (copyBtnSum) {
    copyBtnSum.addEventListener('click', () => {
        navigator.clipboard.writeText(outputContentSum.innerText);
        copyBtnSum.textContent = '✅ Copied!';
        setTimeout(() => copyBtnSum.textContent = '📋 Copy', 2000);
    });
}

if (exportBtnSum) {
    exportBtnSum.addEventListener('click', () => window.open('/export/summary', '_blank'));
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ── Quiz ──
const quizBtn           = document.getElementById('quizBtn');
const loadingQuiz       = document.getElementById('loading-quiz');
const outputQuiz        = document.getElementById('output-quiz');
const outputTitleQuiz   = document.getElementById('outputTitle-quiz');
const outputContentQuiz = document.getElementById('outputContent-quiz');
const exportBtnQuiz     = document.getElementById('exportBtn-quiz');

let currentQuiz    = null;
let userAnswers    = {};
let quizSubmitted  = false;
let quizTimerInterval = null;
let quizElapsed    = 0;

// Difficulty selector
document.querySelectorAll('.diff-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    });
});

function getSelectedDifficulty() {
    const active = document.querySelector('.diff-btn.active');
    return active ? active.dataset.level : 'medium';
}

function renderQuiz(data) {
    const { quiz, difficulty } = data;
    const isHard = difficulty === 'hard';
    userAnswers   = {};
    quizSubmitted = false;

    const questions = quiz.map((q, i) => ({ ...q, index: i }));
    currentQuiz = { questions, difficulty, topic: data.topic || 'General' };

    // start timer
    quizElapsed = 0;
    clearInterval(quizTimerInterval);
    quizTimerInterval = setInterval(() => {
        quizElapsed++;
        const el = document.getElementById('quizTimer');
        if (el) el.textContent = formatTime(quizElapsed);
    }, 1000);

    const total = questions.length;
    let html = `
        <div class="quiz-timer">⏱️ Time: <span id="quizTimer">0:00</span></div>
        <div class="quiz-progress-label">
            <span>Question Progress</span><span id="progressLabel">0 / ${total} answered</span>
        </div>
        <div class="quiz-progress"><div class="quiz-progress-fill" id="progressFill" style="width:0%"></div></div>`;

    questions.forEach((q, i) => {
        if (isHard) {
            html += `
            <div class="quiz-question hard-mode" id="q-${i}">
                <h3>Q${i + 1}. ${q.question}</h3>
                <div class="hard-input-group">
                    <input class="hard-answer-input" id="hard-input-${i}" placeholder="Type your answer..." />
                    <button class="btn-check" data-i="${i}">Check</button>
                </div>
                <div class="quiz-feedback" id="feedback-${i}"></div>
            </div>`;
        } else {
            const opts = q.options.map((opt, j) => `
                <li class="quiz-option" data-i="${i}" data-j="${j}">${opt}</li>`).join('');
            html += `
            <div class="quiz-question" id="q-${i}">
                <h3>Q${i + 1}. ${q.question}</h3>
                <ul class="quiz-options">${opts}</ul>
                <div class="quiz-feedback" id="feedback-${i}"></div>
            </div>`;
        }
    });

    html += `<button id="submitQuizBtn" class="btn btn-primary" style="margin-top:16px" disabled>Submit Quiz</button>`;
    outputContentQuiz.innerHTML = html;


    // MCQ option click
    outputContentQuiz.querySelectorAll('.quiz-option').forEach(opt => {
        opt.addEventListener('click', () => {
            if (quizSubmitted) return;
            const i = +opt.dataset.i;
            // deselect siblings
            outputContentQuiz.querySelectorAll(`.quiz-option[data-i="${i}"]`)
                .forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            userAnswers[i] = opt.textContent.trim();
            updateProgress(total);
        });
    });

    // Hard mode check buttons
    outputContentQuiz.querySelectorAll('.btn-check').forEach(btn => {
        btn.addEventListener('click', () => {
            const i   = +btn.dataset.i;
            const inp = document.getElementById(`hard-input-${i}`);
            if (!inp.value.trim()) return;
            userAnswers[i] = inp.value.trim();
            inp.disabled   = true;
            btn.disabled   = true;
            const correct  = currentQuiz.questions[i].answer;
            const isRight  = inp.value.trim().toLowerCase() === correct.toLowerCase();
            const fb       = document.getElementById(`feedback-${i}`);
            fb.innerHTML   = isRight
                ? `<span class="feedback-correct">✅ Correct!</span>`
                : `<span class="feedback-incorrect">❌ Incorrect. Answer: <strong>${correct}</strong></span>`;
            updateProgress(total);
        });
    });

    // Submit button
    const submitBtn = document.getElementById('submitQuizBtn');
    submitBtn.addEventListener('click', () => submitQuiz(questions));
}

function updateProgress(total) {
    const answered = Object.keys(userAnswers).length;
    const pct      = Math.round(answered / total * 100);
    const fill     = document.getElementById('progressFill');
    const label    = document.getElementById('progressLabel');
    if (fill)  fill.style.width  = pct + '%';
    if (label) label.textContent = `${answered} / ${total} answered`;
    const submitBtn = document.getElementById('submitQuizBtn');
    if (submitBtn) submitBtn.disabled = answered < total;
}

function formatTime(secs) {
    return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
}

function submitQuiz(questions) {
    quizSubmitted = true;
    clearInterval(quizTimerInterval);
    const timeTaken = quizElapsed;
    const isHard    = currentQuiz.difficulty === 'hard';
    let score       = 0;

    questions.forEach(q => {
        const given   = (userAnswers[q.index] || '').trim();
        const correct = q.answer.trim();
        const isRight = isHard
            ? given.toLowerCase() === correct.toLowerCase()
            : given === correct;
        if (isRight) score++;

        if (!isHard) {
            outputContentQuiz.querySelectorAll(`.quiz-option[data-i="${q.index}"]`).forEach(opt => {
                if (opt.textContent.trim() === correct) opt.classList.add('correct');
                else if (opt.classList.contains('selected')) opt.classList.add('incorrect');
            });
            const fb = document.getElementById(`feedback-${q.index}`);
            if (fb) fb.innerHTML = isRight
                ? `<span class="feedback-correct">✅ Correct!</span>`
                : `<span class="feedback-incorrect">❌ Incorrect. Answer: <strong>${correct}</strong></span>`;
        }
    });

    const pct      = Math.round(score / questions.length * 100);
    const colorCls = pct >= 80 ? 'score-green' : pct >= 50 ? 'score-yellow' : 'score-red';
    const msg      = pct >= 80 ? '🎉 Excellent work!' : pct >= 50 ? '💪 Keep it up!' : '📚 Review your notes.';

    document.getElementById('submitQuizBtn').remove();

    // ── Score card ──
    outputContentQuiz.insertAdjacentHTML('beforeend', `
        <div class="quiz-score">
            <div class="score-circle ${colorCls}">${pct}%</div>
            <div class="score-label">${score} / ${questions.length} correct</div>
            <div class="score-recommendation">${msg} &nbsp;⏱️ ${formatTime(timeTaken)}</div>
            <button class="btn-retry" id="retryQuizBtn">🔄 Try Again</button>
            <button class="btn-review" id="reviewSheetBtn" style="margin-left:10px">📋 Review Sheet</button>
        </div>`);

    document.getElementById('retryQuizBtn').addEventListener('click', () => {
        outputQuiz.classList.add('hidden');
        userAnswers = {}; quizSubmitted = false; currentQuiz = null;
    });

    document.getElementById('reviewSheetBtn').addEventListener('click', () => renderReviewSheet(questions));

    // ── Record progress & wrong answers ──
    fetch('/progress/record', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: currentQuiz.topic, score, total: questions.length, difficulty: currentQuiz.difficulty })
    }).catch(() => {});

    questions.forEach(q => {
        const given = (userAnswers[q.index] || '').trim();
        if (given.toLowerCase() !== q.answer.trim().toLowerCase()) {
            fetch('/progress/record-wrong', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: q.question, correct_answer: q.answer, topic: currentQuiz.topic })
            }).catch(() => {});
        }
    });

    if (exportBtnQuiz) exportBtnQuiz.classList.remove('hidden');
}

function renderReviewSheet(questions) {
    const isHard = currentQuiz.difficulty === 'hard';
    let html = `<div class="review-sheet"><h3>📋 Review Sheet</h3>`;

    questions.forEach(q => {
        const given   = (userAnswers[q.index] || '').trim();
        const correct = q.answer.trim();
        const isRight = isHard
            ? given.toLowerCase() === correct.toLowerCase()
            : given === correct;
        const badge   = isRight
            ? `<span class="review-badge correct">✅ Correct</span>`
            : `<span class="review-badge wrong">❌ Wrong</span>`;

        html += `<div class="review-question" id="review-q-${q.index}">
            <div class="review-qnum">Q${q.index + 1} ${badge}</div>
            <div class="review-qtext">${q.question}</div>`;

        if (isHard) {
            html += `<div class="review-hard">
                <strong>Your answer:</strong> ${given || '<em>No answer</em>'}<br>
                <strong>Correct answer:</strong> ${correct}
            </div>`;
        } else {
            html += q.options.map(opt => {
                let cls = 'review-option';
                if (opt.trim() === correct)       cls += ' review-opt-correct';
                else if (opt.trim() === given)    cls += ' review-opt-wrong';
                return `<div class="${cls}">${opt}</div>`;
            }).join('');
        }

        html += `<div class="quiz-explanation hidden" id="exp-${q.index}"></div>
                 <button class="btn-explain" data-i="${q.index}" data-wrong="${!isRight}">${isRight ? '💡 Why correct?' : '💡 Explain mistake'}</button>
            </div>`;
    });

    html += `</div>`;

    // Remove old review sheet if present, then append
    const old = outputContentQuiz.querySelector('.review-sheet');
    if (old) old.remove();
    outputContentQuiz.insertAdjacentHTML('beforeend', html);

    // Explain buttons
    outputContentQuiz.querySelectorAll('.btn-explain').forEach(btn => {
        btn.addEventListener('click', async () => {
            const i       = +btn.dataset.i;
            const isWrong = btn.dataset.wrong === 'true';
            const box     = document.getElementById(`exp-${i}`);
            btn.disabled  = true;
            btn.textContent = '⏳ Loading...';
            try {
                const q = currentQuiz.questions[i];
                const userAns = isWrong ? (userAnswers[i] || '') : q.answer;
                const res = await fetch('/quiz/explain', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ questions: [q], user_answers: { [i]: userAns } })
                });
                const data = await res.json();
                const exp  = (data.explanations || [])[0];
                box.textContent = exp ? exp.explanation : 'No explanation available.';
                box.classList.remove('hidden');
                btn.textContent = isWrong ? '💡 Explain mistake' : '💡 Why correct?';
            } catch {
                box.textContent = 'Failed to load explanation.';
                box.classList.remove('hidden');
                btn.textContent = isWrong ? '💡 Explain mistake' : '💡 Why correct?';
            }
        });
    });
}

if (quizBtn) {
    quizBtn.addEventListener('click', async () => {
        const notes = document.getElementById('notes');
        const text  = notes ? notes.value.trim() : '';
        if (!uploadedFiles.length && !text) return alert('Please upload a file or paste your notes first.');

        quizBtn.disabled = true;
        loadingQuiz.classList.remove('hidden');
        outputQuiz.classList.add('hidden');

        if (topicDetectionPromise) await topicDetectionPromise;

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));
        if (text) fd.append('text', text);
        fd.append('difficulty', getSelectedDifficulty());
        const detectedTopic = topicBadge ? topicBadge.textContent.replace('🏷️ ', '').trim() : '';
        if (detectedTopic) fd.append('topic', detectedTopic);

        try {
            const res  = await fetch('/quiz', { method: 'POST', body: fd });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            loadingQuiz.classList.add('hidden');
            outputQuiz.classList.remove('hidden');
            outputTitleQuiz.textContent = `❓ Quiz — ${getSelectedDifficulty().toUpperCase()}`;
            renderQuiz(data);
            if (exportBtnQuiz) exportBtnQuiz.classList.add('hidden');
        } catch (e) {
            loadingQuiz.classList.add('hidden');
            outputQuiz.classList.remove('hidden');
            outputContentQuiz.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally {
            quizBtn.disabled = false;
        }
    });
}

if (exportBtnQuiz) {
    exportBtnQuiz.addEventListener('click', () => window.open('/export/quiz', '_blank'));
}

// ── Roadmap ──
const roadmapBtn           = document.getElementById('roadmapBtn');
const loadingRoadmap       = document.getElementById('loading-roadmap');
const outputRoadmap        = document.getElementById('output-roadmap');
const outputTitleRoadmap   = document.getElementById('outputTitle-roadmap');
const outputContentRoadmap = document.getElementById('outputContent-roadmap');
const copyBtnRoadmap       = document.getElementById('copyBtn-roadmap');
const exportBtnRoadmap     = document.getElementById('exportBtn-roadmap');

function renderRoadmap(text) {
    return text.split('\n')
        .filter(l => l.trim())
        .map(line => `<div class="roadmap-day">${line}</div>`)
        .join('');
}

if (roadmapBtn) {
    roadmapBtn.addEventListener('click', async () => {
        const notes = document.getElementById('notes');
        const text  = notes ? notes.value.trim() : '';
        if (!uploadedFiles.length && !text) return alert('Please upload a file or paste your notes first.');

        roadmapBtn.disabled = true;
        loadingRoadmap.classList.remove('hidden');
        outputRoadmap.classList.add('hidden');

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));
        if (text) fd.append('text', text);
        const days = document.getElementById('daysInput');
        fd.append('days', days ? days.value : 7);

        try {
            const res  = await fetch('/roadmap', { method: 'POST', body: fd });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            loadingRoadmap.classList.add('hidden');
            outputRoadmap.classList.remove('hidden');
            outputTitleRoadmap.innerHTML = `🗺️ ${days ? days.value : 7}-Day Roadmap` +
                (data.cached ? ' <span class="cache-badge">⚡ Cached</span>' : '');
            outputContentRoadmap.innerHTML = renderRoadmap(data.roadmap);
            copyBtnRoadmap.classList.remove('hidden');
            exportBtnRoadmap.classList.remove('hidden');
        } catch (e) {
            loadingRoadmap.classList.add('hidden');
            outputRoadmap.classList.remove('hidden');
            outputContentRoadmap.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally {
            roadmapBtn.disabled = false;
        }
    });
}

if (copyBtnRoadmap) {
    copyBtnRoadmap.addEventListener('click', () => {
        navigator.clipboard.writeText(outputContentRoadmap.innerText);
        copyBtnRoadmap.textContent = '✅ Copied!';
        setTimeout(() => copyBtnRoadmap.textContent = '📋 Copy', 2000);
    });
}

if (exportBtnRoadmap) {
    exportBtnRoadmap.addEventListener('click', () => window.open('/export/roadmap', '_blank'));
}

// ── Flashcards ──
const flashcardBtn           = document.getElementById('flashcardBtn');
const loadingFlashcards      = document.getElementById('loading-flashcards');
const outputFlashcards       = document.getElementById('output-flashcards');
const outputTitleFlashcards  = document.getElementById('outputTitle-flashcards');
const outputContentFlashcards = document.getElementById('outputContent-flashcards');
const exportBtnFlashcards    = document.getElementById('exportBtn-flashcards');

function renderFlashcards(cards) {
    const html = `<div class="flashcards-grid">${
        cards.map((c, i) => `
            <div class="flashcard" id="fc-${i}">
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <div class="card-num">Card ${i + 1} of ${cards.length}</div>
                        <p>${c.front}</p>
                        <div class="flip-hint">Click to flip</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="card-num">Answer</div>
                        <p>${c.back}</p>
                        <div class="flip-hint">Click to flip back</div>
                    </div>
                </div>
            </div>`).join('')
    }</div>`;
    outputContentFlashcards.innerHTML = html;

    outputContentFlashcards.querySelectorAll('.flashcard').forEach(card => {
        card.addEventListener('click', () => card.classList.toggle('flipped'));
    });
}

if (flashcardBtn) {
    flashcardBtn.addEventListener('click', async () => {
        const notes = document.getElementById('notes');
        const text  = notes ? notes.value.trim() : '';
        if (!uploadedFiles.length && !text) return alert('Please upload a file or paste your notes first.');

        flashcardBtn.disabled = true;
        loadingFlashcards.classList.remove('hidden');
        outputFlashcards.classList.add('hidden');

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));
        if (text) fd.append('text', text);

        try {
            const res  = await fetch('/flashcards', { method: 'POST', body: fd });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            loadingFlashcards.classList.add('hidden');
            outputFlashcards.classList.remove('hidden');
            outputTitleFlashcards.innerHTML = `🃏 Flashcards (${data.flashcards.length})` +
                (data.cached ? ' <span class="cache-badge">⚡ Cached</span>' : '');
            renderFlashcards(data.flashcards);
            if (exportBtnFlashcards) exportBtnFlashcards.classList.remove('hidden');
        } catch (e) {
            loadingFlashcards.classList.add('hidden');
            outputFlashcards.classList.remove('hidden');
            outputContentFlashcards.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally {
            flashcardBtn.disabled = false;
        }
    });
}

if (exportBtnFlashcards) {
    exportBtnFlashcards.addEventListener('click', () => window.open('/export/flashcards', '_blank'));
}

// ── Compare ──
const compareBtn           = document.getElementById('compareBtn');
const loadingCompare       = document.getElementById('loading-compare');
const outputCompare        = document.getElementById('output-compare');
const outputTitleCompare   = document.getElementById('outputTitle-compare');
const outputContentCompare = document.getElementById('outputContent-compare');
const copyBtnCompare       = document.getElementById('copyBtn-compare');

function renderComparison(text) {
    return renderSummary(text);
}

if (compareBtn) {
    compareBtn.addEventListener('click', async () => {
        if (uploadedFiles.length < 2)
            return alert('Please upload exactly 2 documents to compare.');
        if (uploadedFiles.length > 2)
            return alert('Please upload exactly 2 documents. Remove extra files first.');

        compareBtn.disabled = true;
        loadingCompare.classList.remove('hidden');
        outputCompare.classList.add('hidden');

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));

        try {
            const res  = await fetch('/compare', { method: 'POST', body: fd });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            loadingCompare.classList.add('hidden');
            outputCompare.classList.remove('hidden');
            const labels = data.labels || uploadedFiles.map(f => f.name);
            outputTitleCompare.innerHTML =
                `🔀 ${labels[0]} vs ${labels[1]}` +
                (data.cached ? ' <span class="cache-badge">⚡ Cached</span>' : '');
            outputContentCompare.innerHTML = renderComparison(data.comparison);
            copyBtnCompare.classList.remove('hidden');
        } catch (e) {
            loadingCompare.classList.add('hidden');
            outputCompare.classList.remove('hidden');
            outputContentCompare.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally {
            compareBtn.disabled = false;
        }
    });
}

if (copyBtnCompare) {
    copyBtnCompare.addEventListener('click', () => {
        navigator.clipboard.writeText(outputContentCompare.innerText);
        copyBtnCompare.textContent = '✅ Copied!';
        setTimeout(() => copyBtnCompare.textContent = '📋 Copy', 2000);
    });
}

// ── Progress Dashboard ──
let scoreChartInstance = null;

async function loadProgress() {
    const panel = document.getElementById('panel-progress');
    if (!panel) return;

    const [histRes, weakRes] = await Promise.all([
        fetch('/progress').then(r => r.json()),
        fetch('/progress/weak-areas').then(r => r.json())
    ]);

    const history = histRes;
    const empty   = document.getElementById('progressEmpty');
    const dash    = document.getElementById('progressDashboard');

    if (!history.length) {
        empty.classList.remove('hidden');
        dash.classList.add('hidden');
        return;
    }

    empty.classList.add('hidden');
    dash.classList.remove('hidden');

    // ── Stat cards ──
    const avg  = Math.round(history.reduce((s, r) => s + r.pct, 0) / history.length);
    const best = Math.max(...history.map(r => r.pct));
    const topics = new Set(history.map(r => r.topic)).size;
    document.getElementById('statTotal').textContent  = history.length;
    document.getElementById('statAvg').textContent    = avg + '%';
    document.getElementById('statBest').textContent   = best + '%';
    document.getElementById('statTopics').textContent = topics;

    // ── Chart.js score history ──
    const canvas = document.getElementById('scoreChart');
    if (canvas && typeof Chart !== 'undefined') {
        if (scoreChartInstance) scoreChartInstance.destroy();
        const isDark = document.body.classList.contains('dark');
        const gridColor  = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
        const labelColor = isDark ? '#aaa' : '#666';
        scoreChartInstance = new Chart(canvas, {
            type: 'line',
            data: {
                labels: history.map((r, i) => `#${i + 1} ${r.topic.slice(0, 12)}`),
                datasets: [{
                    label: 'Score %',
                    data: history.map(r => r.pct),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102,126,234,0.12)',
                    borderWidth: 2,
                    pointBackgroundColor: history.map(r =>
                        r.pct >= 80 ? '#28a745' : r.pct >= 50 ? '#ffc107' : '#dc3545'),
                    pointRadius: 5,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 0, max: 100, ticks: { color: labelColor }, grid: { color: gridColor } },
                    x: { ticks: { color: labelColor, maxRotation: 30 }, grid: { color: gridColor } }
                }
            }
        });
    }

    // ── Weak areas ──
    const weakEl = document.getElementById('weakAreasContent');
    if (weakEl) {
        if (!weakRes.length) {
            weakEl.innerHTML = '<p style="color:#aaa;font-size:14px">No weak areas yet. Keep taking quizzes!</p>';
        } else {
            const maxCount = Math.max(...weakRes.map(w => w.wrong_count));
            weakEl.innerHTML = weakRes.map(w => `
                <div class="weak-area-row">
                    <div class="weak-area-info">
                        <span class="weak-area-q">${w.question}</span>
                        <span class="weak-area-meta">📚 ${w.topic}</span>
                        <span class="weak-area-ans">✔ ${w.correct_answer}</span>
                        <span class="weak-area-meta">❌ ${w.wrong_count}x wrong</span>
                    </div>
                    <div class="weak-area-bar-track">
                        <div class="weak-area-bar-fill" style="width:${Math.round(w.wrong_count / maxCount * 100)}%"></div>
                    </div>
                </div>`).join('');
        }
    }

    // ── History table ──
    const tableEl = document.getElementById('historyTable');
    if (tableEl) {
        const rows = [...history].reverse().map(r => {
            const cls = r.pct >= 80 ? 'green' : r.pct >= 50 ? 'yellow' : 'red';
            return `<tr>
                <td><div class="history-topic">${r.topic}</div></td>
                <td>
                    <div class="history-score-bar">
                        <div class="score-bar-track"><div class="score-bar-fill ${cls}" style="width:${r.pct}%"></div></div>
                        <span class="score-pct ${cls}">${r.pct}%</span>
                    </div>
                </td>
                <td><span class="diff-badge ${r.difficulty}">${r.difficulty}</span></td>
                <td><span class="history-date">${r.date}</span></td>
            </tr>`;
        }).join('');
        tableEl.innerHTML = `
            <table class="history-table">
                <thead><tr>
                    <th>Topic</th><th>Score</th><th>Difficulty</th><th>Date</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    }
}

// Load progress when switching to progress tab
tabBtns.forEach(btn => {
    if (btn.dataset.tab === 'progress') btn.addEventListener('click', loadProgress);
});

// Load immediately if progress tab is the active/saved tab
if (localStorage.getItem('activeTab') === 'progress') loadProgress();

// Clear progress button
const clearProgressBtn = document.getElementById('clearProgressBtn');
if (clearProgressBtn) {
    clearProgressBtn.addEventListener('click', async () => {
        if (!confirm('Clear all quiz history and weak areas?')) return;
        await fetch('/progress/clear', { method: 'POST' });
        if (scoreChartInstance) { scoreChartInstance.destroy(); scoreChartInstance = null; }
        loadProgress();
    });
}

// ── Chat Drawer ──
const fabChatBtn  = document.getElementById('fabChatBtn');
const chatDrawer  = document.getElementById('chatDrawer');
const closeChatBtn = document.getElementById('closeChatBtn');
const chatHistory = document.getElementById('chatHistory');
const chatInput   = document.getElementById('chatInput');
const chatBtn     = document.getElementById('chatBtn');

if (fabChatBtn)   fabChatBtn.addEventListener('click',   () => chatDrawer.classList.toggle('hidden'));
if (closeChatBtn) closeChatBtn.addEventListener('click', () => chatDrawer.classList.add('hidden'));

document.addEventListener('click', e => {
    if (!chatDrawer || chatDrawer.classList.contains('hidden')) return;
    if (!chatDrawer.contains(e.target) && e.target !== fabChatBtn)
        chatDrawer.classList.add('hidden');
});

function formatChatResponse(text) {
    // Decode HTML entities
    text = text.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    // Code blocks
    text = text.replace(/```(\w*)\n?([\/\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code>${code.trim()}</code></pre>`);
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Line breaks
    text = text.replace(/\n/g, '<br>');
    return text;
}

function appendChatBubble(role, text) {
    const div = document.createElement('div');
    div.className = `chat-answer-bubble ${role}`;
    div.innerHTML = role === 'ai' ? `<strong>🤖 AI:</strong><br>${formatChatResponse(text)}` : text;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return div;
}

async function sendChat() {
    const question = chatInput ? chatInput.value.trim() : '';
    if (!question) return;
    if (!uploadedFiles.length && !document.getElementById('notes')?.value.trim())
        return alert('Upload notes or paste text before chatting.');

    chatInput.value = '';
    chatBtn.disabled = true;
    appendChatBubble('user', question);

    const aiBubble = appendChatBubble('ai', '<span id="streamCursor"></span>');

    const fd = new FormData();
    uploadedFiles.forEach(f => fd.append('file', f));
    const notes = document.getElementById('notes');
    if (notes && notes.value.trim()) fd.append('text', notes.value.trim());
    fd.append('question', question);

    try {
        const res = await fetch('/chat/stream', { method: 'POST', body: fd });
        if (!res.ok) throw new Error((await res.json()).error || 'Server error');

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop();
            for (const part of parts) {
                if (!part.startsWith('data: ')) continue;
                const data = JSON.parse(part.slice(6));
                if (data.error) throw new Error(data.error);
                if (data.chunk) {
                    fullText += data.chunk;
                    aiBubble.innerHTML = `<strong>🤖 AI:</strong><br>${formatChatResponse(fullText)}<span id="streamCursor"></span>`;
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
                if (data.done) aiBubble.innerHTML = `<strong>🤖 AI:</strong><br>${formatChatResponse(fullText)}`;
            }
        }
    } catch (streamErr) {
        try {
            const fd2 = new FormData();
            uploadedFiles.forEach(f => fd2.append('file', f));
            const notes2 = document.getElementById('notes');
            if (notes2 && notes2.value.trim()) fd2.append('text', notes2.value.trim());
            fd2.append('question', question);
            const res2 = await fetch('/chat', { method: 'POST', body: fd2 });
            const data2 = await res2.json();
            if (data2.error) throw new Error(data2.error);
            aiBubble.innerHTML = `<strong>🤖 AI:</strong><br>${formatChatResponse(data2.answer)}`;
        } catch (e) {
            aiBubble.innerHTML = `<strong>🤖 AI:</strong><br><span style="color:#dc3545">❌ ${e.message}</span>`;
        }
    } finally {
        chatBtn.disabled = false;
        chatInput.focus();
    }
}

if (chatBtn)   chatBtn.addEventListener('click', sendChat);
if (chatInput) chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } });

function renderFileTags() {
    if (!fileTagsContainer) return;
    if (!uploadedFiles.length) { fileTagsContainer.classList.add('hidden'); return; }
    fileTagsContainer.classList.remove('hidden');
    fileTagsContainer.innerHTML = uploadedFiles.map((f, i) => {
        const name = decodeURIComponent(f.name);
        const { icon, cls } = getFileIcon(name);
        const size = formatSize(f.size);
        return `<div class="file-tag">
            <div class="file-tag-icon ${cls}">${icon}</div>
            <div class="file-tag-info">
                <span class="file-tag-name" title="${name}">${name}</span>
                <span class="file-tag-size">${size}</span>
            </div>
            <button class="file-tag-remove" data-i="${i}" title="Remove">&times;</button>
        </div>`;
    }).join('');
    fileTagsContainer.querySelectorAll('.file-tag-remove').forEach(btn =>
        btn.addEventListener('click', () => {
            uploadedFiles.splice(+btn.dataset.i, 1);
            renderFileTags();
        })
    );
}

// ── Agentic Study Session (Two-Phase Human-in-the-Loop) ───────────────────

// ── Agentic Study Session (Three-Phase Human-in-the-Loop) ─────────────────

const sessionBtn               = document.getElementById('sessionBtn');
const loadingP1                = document.getElementById('loading-session-p1');
const stepLabelP1              = document.getElementById('sessionStepLabel-p1');
const stepTrackerP1            = document.getElementById('sessionStepTracker-p1');
const phase1Result             = document.getElementById('session-phase1-result');
const sessionTopicHero         = document.getElementById('session-topic-hero');
const sessionSummaryBody       = document.getElementById('session-summary-body');
const sessionDiagQuizBody      = document.getElementById('session-diag-quiz-body');
const sessionSubmitQuizBtn     = document.getElementById('sessionSubmitQuizBtn');
const loadingP2                = document.getElementById('loading-session-p2');
const stepLabelP2              = document.getElementById('sessionStepLabel-p2');
const stepTrackerP2            = document.getElementById('sessionStepTracker-p2');
const phase2aResult            = document.getElementById('session-phase2a-result');
const sessionScoreBanner       = document.getElementById('session-score-banner');
const sessionFlashcardsSection = document.getElementById('session-flashcards-section');
const sessionFlashcardsBody    = document.getElementById('session-flashcards-body');
const sessionTargetedSection   = document.getElementById('session-targeted-quiz-section');
const sessionTargetedBody      = document.getElementById('session-targeted-quiz-body');
const sessionSubmitTargetedBtn = document.getElementById('sessionSubmitTargetedBtn');
const sessionSkipRemediation   = document.getElementById('session-skip-remediation');
const sessionBuildRoadmapBtn   = document.getElementById('sessionBuildRoadmapBtn');
const loadingP2b               = document.getElementById('loading-session-p2b');
const stepLabelP2b             = document.getElementById('sessionStepLabel-p2b');
const stepTrackerP2b           = document.getElementById('sessionStepTracker-p2b');
const outputSession            = document.getElementById('output-session');
const outputTitleSession       = document.getElementById('outputTitle-session');
const outputContentSession     = document.getElementById('outputContent-session');

const P1_STEPS = [
    { key: 'detect_topic',    label: '🔍 Detect Topic' },
    { key: 'summarize',       label: '📝 Summarize' },
    { key: 'diagnostic_quiz', label: '❓ Build Quiz' },
];
const P2A_STEPS = [
    { key: 'evaluate_quiz',       label: '📊 Evaluate' },
    { key: 'generate_flashcards', label: '🃏 Flashcards' },
    { key: 'targeted_quiz',       label: '🎯 Targeted Quiz' },
];
const P2B_STEPS = [
    { key: 'evaluate_targeted_quiz', label: '📊 Score Targeted' },
    { key: 'build_roadmap',          label: '🗺️ Roadmap' },
    { key: 'compile_report',         label: '📋 Report' },
];

function renderTracker(el, steps, activeKey) {
    if (!el) return;
    el.innerHTML = steps.map((s, i) => {
        const cls = s.key === activeKey ? 'step-dot active' : 'step-dot';
        const dot = `<div class="${cls}" title="${s.label}"><span>${s.label}</span></div>`;
        return i < steps.length - 1 ? dot + '<div class="step-line"></div>' : dot;
    }).join('');
}

let sessionAnswers         = {};
let sessionTargetedAnswers = {};
let sessionDiagQuizData    = null;
let sessionTargetedData    = null;

// ── PHASE 1 ──────────────────────────────────────────────────────────────────

if (sessionBtn) {
    sessionBtn.addEventListener('click', async () => {
        const notes = document.getElementById('notes');
        const text  = notes ? notes.value.trim() : '';
        if (!uploadedFiles.length && !text) return alert('Please upload a file or paste your notes first.');
        const goal = document.getElementById('sessionGoal') ? document.getElementById('sessionGoal').value.trim() : '';

        sessionBtn.disabled = true;
        document.getElementById('session-phase1-config').style.opacity = '0.5';
        loadingP1.classList.remove('hidden');
        phase1Result.classList.add('hidden');
        phase2aResult.classList.add('hidden');
        outputSession.classList.add('hidden');
        sessionAnswers = {}; sessionTargetedAnswers = {};
        renderTracker(stepTrackerP1, P1_STEPS, 'detect_topic');

        const fd = new FormData();
        uploadedFiles.forEach(f => fd.append('file', f));
        if (text) fd.append('text', text);
        fd.append('goal', goal);

        try {
            const res = await fetch('/study-session/phase1', { method: 'POST', body: fd });
            if (!res.ok) throw new Error((await res.json()).error || 'Server error');
            const reader = res.body.getReader(), decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n'); buffer = parts.pop();
                for (const part of parts) {
                    if (!part.startsWith('data: ')) continue;
                    const data = JSON.parse(part.slice(6));
                    if (data.error) throw new Error(data.error);
                    if (data.step) { if (stepLabelP1) stepLabelP1.textContent = data.label; renderTracker(stepTrackerP1, P1_STEPS, data.step); }
                    if (data.done && data.phase === 1) {
                        loadingP1.classList.add('hidden');
                        document.getElementById('session-phase1-config').style.opacity = '1';
                        renderPhase1Result(data);
                    }
                }
            }
        } catch (e) {
            loadingP1.classList.add('hidden');
            document.getElementById('session-phase1-config').style.opacity = '1';
            phase1Result.classList.remove('hidden');
            sessionSummaryBody.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally { sessionBtn.disabled = false; }
    });
}

function renderPhase1Result(data) {
    if (sessionTopicHero) {
        sessionTopicHero.innerHTML = `
            <div class="session-hero">
                <div class="session-hero-emoji">${data.emoji || '📚'}</div>
                <div>
                    <div class="session-hero-topic">${data.topic}${data.subtopic ? ' — ' + data.subtopic : ''}</div>
                    <div style="color:#28a745;font-size:13px;margin-top:4px">✅ Phase 1 complete — answer the quiz below</div>
                </div>
            </div>`;
    }
    if (sessionSummaryBody) sessionSummaryBody.innerHTML = renderSummary(data.summary || '');
    sessionDiagQuizData = data.diagnostic_quiz;
    sessionAnswers = {};
    renderInteractiveQuiz(data.diagnostic_quiz, sessionDiagQuizBody, sessionAnswers, sessionSubmitQuizBtn, data.diagnostic_quiz?.quiz?.length || 5);
    phase1Result.classList.remove('hidden');
    phase1Result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Generic interactive quiz renderer ────────────────────────────────────────

function renderInteractiveQuiz(quizData, container, answersObj, submitBtn, total) {
    if (!container || !quizData || !quizData.quiz) return;
    const questions = quizData.quiz;
    const isHard    = quizData.difficulty === 'hard';
    let html = '';
    questions.forEach((q, i) => {
        if (isHard) {
            html += `<div class="quiz-question hard-mode" id="iq-${container.id}-${i}">
                <h3>Q${i+1}. ${q.question}</h3>
                <div class="hard-input-group">
                    <input class="hard-answer-input" id="iq-inp-${container.id}-${i}" placeholder="Type your answer (1-3 words)..." />
                    <button class="btn-check" data-i="${i}" data-cid="${container.id}">Check</button>
                </div>
                <div class="quiz-feedback" id="iq-fb-${container.id}-${i}"></div>
            </div>`;
        } else {
            const opts = q.options.map((opt, j) =>
                `<li class="quiz-option" data-i="${i}" data-opt="${opt}" data-cid="${container.id}">${opt}</li>`
            ).join('');
            html += `<div class="quiz-question" id="iq-${container.id}-${i}">
                <h3>Q${i+1}. ${q.question}</h3>
                <ul class="quiz-options">${opts}</ul>
            </div>`;
        }
    });
    container.innerHTML = html;

    container.querySelectorAll('.quiz-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const i = +opt.dataset.i;
            container.querySelectorAll(`.quiz-option[data-i="${i}"]`).forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            answersObj[String(i)] = opt.dataset.opt;
            updateSubmitBtn(submitBtn, Object.keys(answersObj).length, total);
        });
    });

    container.querySelectorAll('.btn-check').forEach(btn => {
        btn.addEventListener('click', () => {
            const i   = +btn.dataset.i;
            const inp = document.getElementById(`iq-inp-${container.id}-${i}`);
            if (!inp.value.trim()) return;
            answersObj[String(i)] = inp.value.trim();
            inp.disabled = btn.disabled = true;
            document.getElementById(`iq-fb-${container.id}-${i}`).innerHTML =
                `<span style="color:#667eea;font-weight:600">✍️ Answer recorded</span>`;
            updateSubmitBtn(submitBtn, Object.keys(answersObj).length, total);
        });
    });
}

function updateSubmitBtn(btn, answered, total) {
    if (!btn) return;
    btn.disabled = answered < total;
    btn.textContent = answered < total
        ? `🚀 Submit (${answered}/${total} answered)`
        : '🚀 Submit Answers';
}

// ── PHASE 2a ─────────────────────────────────────────────────────────────────

if (sessionSubmitQuizBtn) {
    sessionSubmitQuizBtn.addEventListener('click', async () => {
        sessionSubmitQuizBtn.disabled = true;
        loadingP2.classList.remove('hidden');
        phase2aResult.classList.add('hidden');
        renderTracker(stepTrackerP2, P2A_STEPS, 'evaluate_quiz');

        try {
            const res = await fetch('/study-session/phase2a', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_answers: sessionAnswers }),
            });
            if (!res.ok) throw new Error((await res.json()).error || 'Server error');
            const reader = res.body.getReader(), decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n'); buffer = parts.pop();
                for (const part of parts) {
                    if (!part.startsWith('data: ')) continue;
                    const data = JSON.parse(part.slice(6));
                    if (data.error) throw new Error(data.error);
                    if (data.step) {
                        if (stepLabelP2) stepLabelP2.textContent = data.label;
                        renderTracker(stepTrackerP2, P2A_STEPS, data.step);
                        if (data.step === 'evaluate_quiz' && data.score_pct !== undefined) {
                            if (stepLabelP2) stepLabelP2.textContent =
                                `📊 Score: ${data.score_pct}% — ${data.score_pct < 60 ? 'Generating remediation...' : 'Great score!'}`;
                        }
                    }
                    if (data.done && data.phase === '2a') {
                        loadingP2.classList.add('hidden');
                        renderPhase2aResult(data);
                    }
                }
            }
        } catch (e) {
            loadingP2.classList.add('hidden');
            phase2aResult.classList.remove('hidden');
            sessionScoreBanner.innerHTML = `<div class="error">❌ ${e.message}</div>`;
        } finally { sessionSubmitQuizBtn.disabled = false; }
    });
}

function renderPhase2aResult(data) {
    const score      = data.score_pct;
    const scoreColor = score >= 80 ? '#28a745' : score >= 60 ? '#ffc107' : '#dc3545';
    const scoreMsg   = score >= 80 ? '🎉 Excellent! Roadmap will focus on advanced topics.'
                     : score >= 60 ? '💪 Good base. Roadmap will cover your gaps.'
                     : '📚 Weak areas detected — study the flashcards, then answer the targeted quiz.';

    // Score banner
    sessionScoreBanner.innerHTML = `
        <div class="session-score-card" style="margin-bottom:16px">
            <div class="session-score-circle" style="border-color:${scoreColor};color:${scoreColor}">${score}%</div>
            <div class="session-score-info">
                <strong>Diagnostic Score</strong>
                <p>${scoreMsg}</p>
                ${data.weak_topics && data.weak_topics.length ? `<div class="session-weak-list"><strong>Weak areas:</strong> ${data.weak_topics.map(t => `<span class="weak-tag">${t.slice(0,60)}</span>`).join('')}</div>` : ''}
            </div>
        </div>`;

    if (data.needs_remediation) {
        // Show flashcards
        if (data.flashcards && data.flashcards.flashcards && data.flashcards.flashcards.length) {
            sessionFlashcardsBody.innerHTML = `<div class="flashcards-grid">${
                data.flashcards.flashcards.map((c, i) => `
                    <div class="flashcard" id="sfc-${i}">
                        <div class="flashcard-inner">
                            <div class="flashcard-front"><div class="card-num">Card ${i+1}</div><p>${c.front}</p><div class="flip-hint">Click to flip</div></div>
                            <div class="flashcard-back"><div class="card-num">Answer</div><p>${c.back}</p><div class="flip-hint">Click to flip back</div></div>
                        </div>
                    </div>`).join('')
            }</div>`;
            sessionFlashcardsBody.querySelectorAll('.flashcard').forEach(card =>
                card.addEventListener('click', () => card.classList.toggle('flipped'))
            );
            sessionFlashcardsSection.classList.remove('hidden');
        }

        // Show interactive targeted quiz
        sessionTargetedData    = data.targeted_quiz;
        sessionTargetedAnswers = {};
        const tTotal = data.targeted_quiz?.quiz?.length || 5;
        renderInteractiveQuiz(data.targeted_quiz, sessionTargetedBody, sessionTargetedAnswers, sessionSubmitTargetedBtn, tTotal);
        sessionTargetedSection.classList.remove('hidden');
        sessionSkipRemediation.classList.add('hidden');
    } else {
        // Score >= 60%, skip remediation
        sessionFlashcardsSection.classList.add('hidden');
        sessionTargetedSection.classList.add('hidden');
        sessionSkipRemediation.classList.remove('hidden');
    }

    phase2aResult.classList.remove('hidden');
    phase2aResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── PHASE 2b — triggered by targeted quiz submit OR skip button ───────────────

async function runPhase2b(targetedAnswers) {
    loadingP2b.classList.remove('hidden');
    outputSession.classList.add('hidden');
    renderTracker(stepTrackerP2b, P2B_STEPS, 'evaluate_targeted_quiz');

    try {
        const res = await fetch('/study-session/phase2b', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ targeted_quiz_answers: targetedAnswers || {} }),
        });
        if (!res.ok) throw new Error((await res.json()).error || 'Server error');
        const reader = res.body.getReader(), decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n'); buffer = parts.pop();
            for (const part of parts) {
                if (!part.startsWith('data: ')) continue;
                const data = JSON.parse(part.slice(6));
                if (data.error) throw new Error(data.error);
                if (data.step) {
                    if (stepLabelP2b) stepLabelP2b.textContent = data.label;
                    renderTracker(stepTrackerP2b, P2B_STEPS, data.step);
                }
                if (data.done && data.phase === '2b') {
                    loadingP2b.classList.add('hidden');
                    outputSession.classList.remove('hidden');
                    outputTitleSession.innerHTML = `🤖 Study Session Report — ${data.report.topic || 'Complete'}`;
                    renderSessionReport(data.report);
                    outputSession.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        }
    } catch (e) {
        loadingP2b.classList.add('hidden');
        outputSession.classList.remove('hidden');
        outputContentSession.innerHTML = `<div class="error">❌ ${e.message}</div>`;
    }
}

if (sessionSubmitTargetedBtn) {
    sessionSubmitTargetedBtn.addEventListener('click', async () => {
        sessionSubmitTargetedBtn.disabled = true;
        await runPhase2b(sessionTargetedAnswers);
    });
}

if (sessionBuildRoadmapBtn) {
    sessionBuildRoadmapBtn.addEventListener('click', async () => {
        sessionBuildRoadmapBtn.disabled = true;
        await runPhase2b({});
    });
}

// ── Final report renderer ─────────────────────────────────────────────────────

function renderSessionReport(report) {
    const score          = report.score_pct;
    const targetedScore  = report.targeted_score_pct;
    const scoreColor     = score >= 80 ? '#28a745' : score >= 60 ? '#ffc107' : '#dc3545';
    const tScoreColor    = targetedScore >= 80 ? '#28a745' : targetedScore >= 60 ? '#ffc107' : '#dc3545';

    const diagQs = (report.diagnostic_quiz && report.diagnostic_quiz.quiz) ? report.diagnostic_quiz.quiz : [];
    const userAns = report.user_answers || sessionAnswers;

    const diagAnswersHtml = diagQs.map((q, i) => {
        const given = (userAns[String(i)] || '').trim();
        const ok    = given.toLowerCase() === q.answer.trim().toLowerCase();
        return `<div class="session-quiz-item" style="border-left-color:${ok ? '#28a745' : '#dc3545'}">
            <strong>Q${i+1}.</strong> ${q.question}
            <div style="margin-top:6px;font-size:12px">
                <span style="color:${ok ? '#28a745' : '#dc3545'}">${ok ? '✅' : '❌'} Your answer: ${given || 'No answer'}</span>
                ${!ok ? `<span style="color:#28a745;margin-left:12px">✅ Correct: ${q.answer}</span>` : ''}
            </div>
        </div>`;
    }).join('');

    let targetedResultHtml = '';
    if (report.needs_remediation && report.targeted_quiz && report.targeted_quiz.quiz) {
        const tQs  = report.targeted_quiz.quiz;
        const tAns = report.targeted_quiz_answers || sessionTargetedAnswers;
        const tRows = tQs.map((q, i) => {
            const given = (tAns[String(i)] || '').trim();
            const ok    = given.toLowerCase() === q.answer.trim().toLowerCase();
            return `<div class="session-quiz-item" style="border-left-color:${ok ? '#28a745' : '#dc3545'}">
                <strong>Q${i+1}.</strong> ${q.question}
                <div style="margin-top:6px;font-size:12px">
                    <span style="color:${ok ? '#28a745' : '#dc3545'}">${ok ? '✅' : '❌'} Your answer: ${given || 'No answer'}</span>
                    ${!ok ? `<span style="color:#28a745;margin-left:12px">✅ Correct: ${q.answer}</span>` : ''}
                </div>
            </div>`;
        }).join('');

        targetedResultHtml = `
        <div class="session-section">
            <div class="session-section-title">🎯 Targeted Quiz Results</div>
            <div class="session-score-card" style="margin-bottom:12px">
                <div class="session-score-circle" style="border-color:${tScoreColor};color:${tScoreColor}">${targetedScore}%</div>
                <div class="session-score-info">
                    <strong>Targeted Quiz Score</strong>
                    <p>${targetedScore >= 80 ? '🎉 Great improvement!' : targetedScore >= 60 ? '💪 Getting better!' : '📚 Keep reviewing these topics.'}</p>
                </div>
            </div>
            <div class="session-quiz-list">${tRows}</div>
        </div>`;
    }

    const logHtml = (report.steps_log || []).map(s => {
        const details = Object.entries(s).filter(([k]) => k !== 'step')
            .map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(' | ');
        return `<div class="session-log-item"><span class="log-step">${s.step}</span><span class="log-detail">${details}</span></div>`;
    }).join('');

    outputContentSession.innerHTML = `
    <div class="session-report">
        <div class="session-score-card">
            <div class="session-score-circle" style="border-color:${scoreColor};color:${scoreColor}">${score}%</div>
            <div class="session-score-info">
                <strong>Diagnostic Score</strong>
                <p>${score >= 80 ? '🎉 Excellent! Roadmap focuses on advanced topics.'
                   : score >= 60 ? '💪 Good base. Roadmap covers your gaps.'
                   : '📚 Weak areas addressed through flashcards & targeted quiz.'}</p>
            </div>
        </div>

        <div class="session-section">
            <div class="session-section-title">❓ Diagnostic Quiz — Your Answers</div>
            <div class="session-quiz-list">${diagAnswersHtml}</div>
        </div>

        ${targetedResultHtml}

        <div class="session-section">
            <div class="session-section-title">🗺️ Personalized Study Roadmap</div>
            <div class="session-roadmap">${renderRoadmap(report.roadmap)}</div>
        </div>

        <div class="session-section session-log-section">
            <div class="session-section-title">⚙️ Agent Execution Log</div>
            <div class="session-log">${logHtml}</div>
        </div>
    </div>`;
}
