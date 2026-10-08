import threading
import uuid
from datetime import datetime

# task_id -> { status, result, error, created_at }
_tasks = {}
_lock = threading.Lock()


def create_task() -> str:
    task_id = str(uuid.uuid4())
    with _lock:
        _tasks[task_id] = {
            'status': 'pending',
            'result': None,
            'error': None,
            'created_at': datetime.now().isoformat()
        }
    return task_id


def run_task(task_id: str, fn, *args, **kwargs):
    """Run fn(*args, **kwargs) in a background thread, storing result in task."""
    def worker():
        with _lock:
            _tasks[task_id]['status'] = 'running'
        try:
            result = fn(*args, **kwargs)
            with _lock:
                _tasks[task_id]['status'] = 'done'
                _tasks[task_id]['result'] = result
        except Exception as e:
            with _lock:
                _tasks[task_id]['status'] = 'error'
                _tasks[task_id]['error'] = str(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()


def get_task(task_id: str):
    with _lock:
        return dict(_tasks.get(task_id, {}))


def cleanup_old_tasks():
    """Remove tasks older than 1 hour to prevent memory leak."""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=1)
    with _lock:
        to_delete = [
            tid for tid, t in _tasks.items()
            if datetime.fromisoformat(t['created_at']) < cutoff
        ]
        for tid in to_delete:
            del _tasks[tid]
