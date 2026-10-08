import hashlib
import json
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'doc_cache')
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(doc_hash: str, feature: str, user_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{user_id}_{doc_hash}_{feature}.json")


def get_cached(doc_hash: str, feature: str, user_id: str = 'default'):
    path = _cache_path(doc_hash, feature, user_id)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def set_cached(doc_hash: str, feature: str, result, user_id: str = 'default'):
    try:
        path = _cache_path(doc_hash, feature, user_id)
        with open(path, 'w') as f:
            json.dump(result, f)
    except Exception:
        pass


def clear_cache(user_id: str = None):
    """Clear cache for a specific user, or all cache if user_id is None."""
    for fname in os.listdir(CACHE_DIR):
        if user_id is None or fname.startswith(f"{user_id}_"):
            try:
                os.remove(os.path.join(CACHE_DIR, fname))
            except Exception:
                pass
