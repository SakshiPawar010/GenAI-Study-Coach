import sys
import os
import json
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template, send_file, Response, stream_with_context, session
from urllib.parse import unquote
from flask_cors import CORS

from agents.summarizer_agent import SummarizerAgent
from agents.quiz_agent import QuizAgent
from agents.roadmap_agent import RoadmapAgent
from agents.flashcard_agent import FlashcardAgent
from agents.chat_agent import ChatAgent
from agents.comparison_agent import ComparisonAgent
from agents.topic_detector import TopicDetector
from agents.study_orchestrator import run_phase1, run_phase2a, run_phase2b
from service.document_processor import DocumentProcessor
from service.pdf_exporter import PDFExporter
from service.progress_store import record_quiz, get_history, clear_history, record_wrong_answer, get_weak_areas, init_db
from service.doc_cache import get_cached, set_cached, clear_cache
from service.task_queue import create_task, run_task, get_task, cleanup_old_tasks
from service.bedrock_client import BedrockClient

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'genai-study-coach-secret-2024')
CORS(app, supports_credentials=True)

# ── Singletons (stateless agents — safe to share) ──────────────────────────
summarizer      = SummarizerAgent()
quiz_agent      = QuizAgent()
roadmap_agent   = RoadmapAgent()
flashcard_agent = FlashcardAgent()
comparison_agent = ComparisonAgent()
topic_detector  = TopicDetector()
doc_processor   = DocumentProcessor()
pdf_exporter    = PDFExporter()

# ── Per-session state ───────────────────────────────────────────────────────
_sessions = {}

def get_session_id():
    if 'sid' not in session:
        session['sid'] = str(uuid.uuid4())
    return session['sid']

def get_session_data():
    sid = get_session_id()
    if sid not in _sessions:
        _sessions[sid] = {
            'chat_agent': ChatAgent(),
            'last_results': {}
        }
    return _sessions[sid]

# ── Init DB on startup ──────────────────────────────────────────────────────
init_db()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def extract_text(req):
    files = req.files.getlist('file')
    files = [f for f in files if f.filename]
    if files:
        texts, filenames, raw_list = [], [], []
        for file in files:
            file.seek(0, 2); size = file.tell(); file.seek(0)
            if size > MAX_FILE_SIZE:
                raise ValueError(f"File '{unquote(file.filename)}' too large ({size//(1024*1024)}MB). Max 10MB.")
            raw = file.read()
            file.seek(0)
            raw_list.append(raw)
            texts.append(doc_processor.process_file(file))
            filenames.append(unquote(file.filename))
        return '\n\n[DOCUMENT BREAK]\n\n'.join(texts), filenames, raw_list
    data = req.form if req.form else req.json
    text = data.get('text', '') if data else ''
    return text, [], [text.encode()]

def cache_key_for(raw_list):
    import hashlib
    h = hashlib.md5()
    for b in raw_list:
        h.update(b if isinstance(b, bytes) else b.encode())
    return h.hexdigest()

# ── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    get_session_id()
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        uid = get_session_id()
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        ck = cache_key_for(raw_list)
        cached = get_cached(ck, 'summary', uid)
        if cached:
            get_session_data()['last_results']['summary'] = cached['summary']
            return jsonify({**cached, 'cached': True})
        summary = summarizer.summarize(text, filenames)
        get_session_data()['last_results']['summary'] = summary
        result = {'summary': summary}
        set_cached(ck, 'summary', result, uid)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summarize/stream', methods=['POST'])
def summarize_stream():
    try:
        uid = get_session_id()
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400

        ck = cache_key_for(raw_list)
        cached = get_cached(ck, 'summary', uid)
        if cached:
            def replay():
                chunk_size = 80
                summary = cached['summary']
                for i in range(0, len(summary), chunk_size):
                    yield f"data: {json.dumps({'chunk': summary[i:i+chunk_size]})}\n\n"
                get_session_data()['last_results']['summary'] = summary
                yield f"data: {json.dumps({'done': True, 'cached': True})}\n\n"
            return Response(stream_with_context(replay()), mimetype='text/event-stream',
                            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

        sd = get_session_data()

        def generate():
            try:
                full = []
                for chunk in summarizer.summarize_stream(text, filenames):
                    full.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                summary = ''.join(full)
                sd['last_results']['summary'] = summary
                set_cached(ck, 'summary', {'summary': summary}, uid)
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quiz', methods=['POST'])
def quiz():
    try:
        difficulty = request.form.get('difficulty', 'medium') if request.form else (request.json or {}).get('difficulty', 'medium')
        topic      = request.form.get('topic', 'General')     if request.form else (request.json or {}).get('topic', 'General')
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        quiz_data = quiz_agent.generate_quiz(text, difficulty)
        quiz_data['topic'] = topic
        get_session_data()['last_results']['quiz'] = quiz_data
        return jsonify(quiz_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/roadmap', methods=['POST'])
def roadmap():
    try:
        uid = get_session_id()
        days = request.form.get('days', 7) if request.form else (request.json or {}).get('days', 7)
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        ck = cache_key_for(raw_list) + f'_days{days}'
        cached = get_cached(ck, 'roadmap', uid)
        if cached:
            get_session_data()['last_results']['roadmap'] = cached['roadmap']
            return jsonify({**cached, 'cached': True})
        roadmap_text = roadmap_agent.create_roadmap(text, days)
        get_session_data()['last_results']['roadmap'] = roadmap_text
        result = {'roadmap': roadmap_text}
        set_cached(ck, 'roadmap', result, uid)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flashcards', methods=['POST'])
def flashcards():
    try:
        uid = get_session_id()
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        ck = cache_key_for(raw_list)
        cached = get_cached(ck, 'flashcards', uid)
        if cached:
            get_session_data()['last_results']['flashcards'] = cached
            return jsonify({**cached, 'cached': True})
        flashcard_data = flashcard_agent.generate_flashcards(text)
        get_session_data()['last_results']['flashcards'] = flashcard_data
        set_cached(ck, 'flashcards', flashcard_data, uid)
        return jsonify(flashcard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if request.is_json:
            data = request.json
            question, text = data.get('question', ''), data.get('text', '')
            raw_list = [text.encode()]
        else:
            question = request.form.get('question', '')
            text, _, raw_list = extract_text(request)
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        agent = get_session_data()['chat_agent']
        if not text and not agent.context:
            return jsonify({'error': 'No notes provided'}), 400
        answer = agent.ask(question, text if text else None)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    try:
        if request.is_json:
            data = request.json
            question, text = data.get('question', ''), data.get('text', '')
        else:
            question = request.form.get('question', '')
            text, _, _ = extract_text(request)
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        agent = get_session_data()['chat_agent']
        if not text and not agent.context:
            return jsonify({'error': 'No notes provided'}), 400

        def generate():
            try:
                for chunk in agent.ask_stream(question, text if text else None):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Background Task endpoints ───────────────────────────────────────────────

@app.route('/summarize/async', methods=['POST'])
def summarize_async():
    try:
        uid = get_session_id()
        text, filenames, raw_list = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        ck = cache_key_for(raw_list)
        cached = get_cached(ck, 'summary', uid)
        if cached:
            get_session_data()['last_results']['summary'] = cached['summary']
            return jsonify({**cached, 'cached': True, 'task_id': None})
        sd = get_session_data()
        task_id = create_task()

        def do_summarize():
            result = summarizer.summarize(text, filenames)
            sd['last_results']['summary'] = result
            set_cached(ck, 'summary', {'summary': result}, uid)
            return {'summary': result}

        run_task(task_id, do_summarize)
        return jsonify({'task_id': task_id, 'status': 'pending'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/task/<task_id>', methods=['GET'])
def poll_task(task_id):
    cleanup_old_tasks()
    task = get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)

# ── Compare ─────────────────────────────────────────────────────────────────

@app.route('/compare', methods=['POST'])
def compare():
    try:
        uid = get_session_id()
        files = request.files.getlist('file')
        files = [f for f in files if f.filename]
        if len(files) < 2:
            return jsonify({'error': 'Please upload exactly 2 documents to compare.'}), 400
        texts, labels, raw_list = [], [], []
        for f in files[:2]:
            f.seek(0, 2); size = f.tell(); f.seek(0)
            if size > MAX_FILE_SIZE:
                return jsonify({'error': f"File '{unquote(f.filename)}' too large."}), 400
            raw = f.read(); f.seek(0)
            raw_list.append(raw)
            texts.append(doc_processor.process_file(f))
            labels.append(unquote(f.filename))
        ck = cache_key_for(raw_list)
        cached = get_cached(ck, 'compare', uid)
        if cached:
            return jsonify({**cached, 'cached': True})
        result = comparison_agent.compare(texts[0], texts[1], labels[0], labels[1])
        data = {'comparison': result, 'labels': labels}
        set_cached(ck, 'compare', data, uid)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Topic Detection ──────────────────────────────────────────────────────────

@app.route('/detect-topic', methods=['POST'])
def detect_topic():
    try:
        text, filenames, _ = extract_text(request)
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        filename = filenames[0] if filenames else None
        result = topic_detector.detect(text, filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Quiz Explain ─────────────────────────────────────────────────────────────

@app.route('/quiz/explain', methods=['POST'])
def quiz_explain():
    try:
        d = request.json
        questions = d.get('questions', [])
        user_answers = d.get('user_answers', {})
        # Detect if this is a "why correct" request (user_answer == correct answer)
        is_correct_explain = all(
            user_answers.get(str(q['index']), user_answers.get(str(i), '')) == q['answer']
            for i, q in enumerate(questions)
        )
        explanations = quiz_agent.explain_wrong_answers(questions, user_answers, explain_correct=is_correct_explain)
        return jsonify({'explanations': explanations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quiz/explain-all', methods=['POST'])
def quiz_explain_all():
    try:
        d = request.json
        questions = d.get('questions', [])
        user_answers = d.get('user_answers', {})
        items = '\n\n'.join([
            f"Q{q['index']+1}: {q['question']}\nCorrect Answer: {q['answer']}\nUser answered: {user_answers.get(str(q['index']), 'No answer')}"
            for q in questions
        ])
        prompt = f"""For each question below, write 1-2 sentences explaining WHY the correct answer is right.
For questions the user got wrong, also explain why their answer is incorrect.

{items}

Return ONLY valid JSON:
{{"explanations": [
  {{"index": 0, "explanation": "..."}}
]}}"""
        client = BedrockClient()
        response = client.invoke(prompt, max_tokens=1500, temperature=0.3)
        try:
            data = json.loads(response)
        except Exception:
            start = response.find('{'); end = response.rfind('}') + 1
            data = json.loads(response[start:end])
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Progress ─────────────────────────────────────────────────────────────────

@app.route('/progress/record', methods=['POST'])
def progress_record():
    try:
        uid = get_session_id()
        d = request.json
        record_quiz(uid, d.get('topic', 'General'), d['score'], d['total'], d.get('difficulty', 'medium'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/progress', methods=['GET'])
def progress_get():
    return jsonify(get_history(get_session_id()))

@app.route('/progress/clear', methods=['POST'])
def progress_clear():
    uid = get_session_id()
    clear_history(uid)
    clear_cache(uid)
    return jsonify({'ok': True})

@app.route('/progress/weak-areas', methods=['GET'])
def weak_areas():
    return jsonify(get_weak_areas(get_session_id()))

@app.route('/progress/record-wrong', methods=['POST'])
def record_wrong():
    try:
        uid = get_session_id()
        d = request.json
        record_wrong_answer(uid, d['question'], d['correct_answer'], d.get('topic', 'General'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Cache management ─────────────────────────────────────────────────────────

@app.route('/cache/clear', methods=['POST'])
def cache_clear():
    clear_cache(get_session_id())
    return jsonify({'ok': True})

@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    from service.doc_cache import CACHE_DIR
    from service.vector_store import VECTOR_STORE_DIR
    doc_files = len([f for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))])
    vec_files = len([f for f in os.listdir(VECTOR_STORE_DIR) if f.endswith('.faiss')])
    return jsonify({'doc_cache_entries': doc_files, 'vector_indexes': vec_files})

# ── PDF Export ───────────────────────────────────────────────────────────────

@app.route('/export/summary', methods=['GET'])
def export_summary():
    try:
        summary = get_session_data()['last_results'].get('summary', '')
        if not summary:
            return jsonify({'error': 'No summary to export. Generate a summary first.'}), 400
        buffer = pdf_exporter.export_summary(summary)
        return send_file(buffer, as_attachment=True, download_name='summary.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/quiz', methods=['GET'])
def export_quiz():
    try:
        quiz_data = get_session_data()['last_results'].get('quiz', {})
        if not quiz_data:
            return jsonify({'error': 'No quiz to export. Generate a quiz first.'}), 400
        buffer = pdf_exporter.export_quiz(quiz_data)
        return send_file(buffer, as_attachment=True, download_name='quiz.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/roadmap', methods=['GET'])
def export_roadmap():
    try:
        roadmap = get_session_data()['last_results'].get('roadmap', '')
        if not roadmap:
            return jsonify({'error': 'No roadmap to export. Generate a roadmap first.'}), 400
        buffer = pdf_exporter.export_roadmap(roadmap)
        return send_file(buffer, as_attachment=True, download_name='roadmap.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/flashcards', methods=['GET'])
def export_flashcards():
    try:
        flashcard_data = get_session_data()['last_results'].get('flashcards', {})
        if not flashcard_data:
            return jsonify({'error': 'No flashcards to export. Generate flashcards first.'}), 400
        buffer = pdf_exporter.export_flashcards(flashcard_data)
        return send_file(buffer, as_attachment=True, download_name='flashcards.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Agentic Study Session (Three-Phase Human-in-the-Loop) ──────────────────────────

PHASE1_LABELS = {
    'detect_topic':    '🔍 Detecting topic...',
    'summarize':       '📝 Summarizing notes...',
    'diagnostic_quiz': '❓ Generating diagnostic quiz...',
}
PHASE2A_LABELS = {
    'evaluate_quiz':       '📊 Evaluating your answers...',
    'generate_flashcards': '🃏 Creating targeted flashcards...',
    'targeted_quiz':       '🎯 Building targeted quiz...',
}
PHASE2B_LABELS = {
    'evaluate_targeted_quiz': '📊 Evaluating targeted quiz...',
    'build_roadmap':          '🗺️ Building personalized roadmap...',
    'compile_report':         '📋 Compiling your study session...',
}


@app.route('/study-session/phase1', methods=['POST'])
def study_session_phase1():
    try:
        import queue, threading
        data = request.form or request.json or {}
        goal = data.get('goal', '')
        text, _, _ = extract_text(request)
        if not text:
            return jsonify({'error': 'No text or file provided'}), 400
        event_queue, result_holder = queue.Queue(), {}

        def on_step(node_name, node_state):
            event = {'step': node_name, 'label': PHASE1_LABELS.get(node_name, node_name)}
            if node_name == 'detect_topic':
                event.update({'topic': node_state.get('topic',''), 'subtopic': node_state.get('subtopic',''), 'emoji': node_state.get('emoji','')})
            elif node_name == 'summarize':
                event['summary'] = node_state.get('summary', '')
            elif node_name == 'diagnostic_quiz':
                event['diagnostic_quiz'] = node_state.get('diagnostic_quiz', {})
            event_queue.put(event)

        def run_in_thread():
            try:
                result_holder['state'] = run_phase1(text, goal=goal, progress_cb=on_step)
            except Exception as e:
                result_holder['error'] = str(e)
            finally:
                event_queue.put(None)

        threading.Thread(target=run_in_thread, daemon=True).start()

        def stream_events():
            while True:
                event = event_queue.get()
                if event is None:
                    if 'error' in result_holder:
                        yield f"data: {json.dumps({'error': result_holder['error']})}\n\n"
                    else:
                        get_session_data()['phase1_state'] = result_holder['state']
                        s = result_holder['state']
                        yield f"data: {json.dumps({'done': True, 'phase': 1, 'topic': s.get('topic',''), 'subtopic': s.get('subtopic',''), 'emoji': s.get('emoji',''), 'summary': s.get('summary',''), 'diagnostic_quiz': s.get('diagnostic_quiz',{})})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"

        return Response(stream_with_context(stream_events()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/study-session/phase2a', methods=['POST'])
def study_session_phase2a():
    """Evaluate diagnostic answers. If weak: generate flashcards + targeted quiz and PAUSE."""
    try:
        import queue, threading
        sd = get_session_data()
        phase1_state = sd.get('phase1_state')
        if not phase1_state:
            return jsonify({'error': 'Phase 1 not completed.'}), 400
        data = request.json or {}
        user_answers = data.get('user_answers', {})
        if not user_answers:
            return jsonify({'error': 'No answers provided.'}), 400
        event_queue, result_holder = queue.Queue(), {}

        def on_step(node_name, node_state):
            event = {'step': node_name, 'label': PHASE2A_LABELS.get(node_name, node_name)}
            if node_name == 'evaluate_quiz':
                event.update({'score_pct': node_state.get('score_pct', 0), 'weak_topics': node_state.get('weak_topics', [])})
            elif node_name == 'targeted_quiz':
                event['targeted_quiz'] = node_state.get('targeted_quiz', {})
            event_queue.put(event)

        def run_in_thread():
            try:
                result_holder['state'] = run_phase2a(phase1_state, user_answers, progress_cb=on_step)
            except Exception as e:
                result_holder['error'] = str(e)
            finally:
                event_queue.put(None)

        threading.Thread(target=run_in_thread, daemon=True).start()

        def stream_events():
            while True:
                event = event_queue.get()
                if event is None:
                    if 'error' in result_holder:
                        yield f"data: {json.dumps({'error': result_holder['error']})}\n\n"
                    else:
                        s = result_holder['state']
                        get_session_data()['phase2a_state'] = s
                        needs_remediation = s.get('score_pct', 100) < 60
                        yield f"data: {json.dumps({'done': True, 'phase': '2a', 'score_pct': s.get('score_pct', 0), 'weak_topics': s.get('weak_topics', []), 'needs_remediation': needs_remediation, 'flashcards': s.get('flashcards', {}), 'targeted_quiz': s.get('targeted_quiz', {})})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"

        return Response(stream_with_context(stream_events()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/study-session/phase2b', methods=['POST'])
def study_session_phase2b():
    """Build roadmap and compile final report using targeted quiz answers."""
    try:
        import queue, threading
        sd = get_session_data()
        phase2a_state = sd.get('phase2a_state')
        if not phase2a_state:
            return jsonify({'error': 'Phase 2a not completed.'}), 400
        data = request.json or {}
        targeted_answers = data.get('targeted_quiz_answers', {})
        event_queue, result_holder = queue.Queue(), {}

        def on_step(node_name, node_state):
            event = {'step': node_name, 'label': PHASE2B_LABELS.get(node_name, node_name)}
            if node_name == 'evaluate_targeted_quiz':
                event['targeted_score_pct'] = node_state.get('targeted_score_pct', 0)
            event_queue.put(event)

        def run_in_thread():
            try:
                result_holder['report'] = run_phase2b(phase2a_state, targeted_answers, progress_cb=on_step)
            except Exception as e:
                result_holder['error'] = str(e)
            finally:
                event_queue.put(None)

        threading.Thread(target=run_in_thread, daemon=True).start()

        def stream_events():
            while True:
                event = event_queue.get()
                if event is None:
                    if 'error' in result_holder:
                        yield f"data: {json.dumps({'error': result_holder['error']})}\n\n"
                    else:
                        yield f"data: {json.dumps({'done': True, 'phase': '2b', 'report': result_holder['report']})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"

        return Response(stream_with_context(stream_events()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
