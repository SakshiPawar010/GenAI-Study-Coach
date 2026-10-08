import json
import hashlib
import os
import pickle
import numpy as np
import faiss
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_SESSION_TOKEN, USE_IAM_ROLE

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'vector_store')


class VectorStore:
    def __init__(self):
        if USE_IAM_ROLE:
            self.embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        else:
            self.embedding_client = boto3.client(
                "bedrock-runtime",
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
        self.embedding_model = "amazon.titan-embed-text-v1"
        self.index = None
        self.chunks = []
        self._embed_cache = {}
        self._current_doc_hash = None
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    def _doc_hash(self, chunks):
        """Stable hash of the document chunks list."""
        combined = '||'.join(chunks)
        return hashlib.md5(combined.encode()).hexdigest()

    def _index_path(self, doc_hash):
        return os.path.join(VECTOR_STORE_DIR, f"{doc_hash}.faiss")

    def _meta_path(self, doc_hash):
        return os.path.join(VECTOR_STORE_DIR, f"{doc_hash}.pkl")

    def _load_from_disk(self, doc_hash):
        """Try to load a previously saved index. Returns True if successful."""
        idx_path = self._index_path(doc_hash)
        meta_path = self._meta_path(doc_hash)
        if os.path.exists(idx_path) and os.path.exists(meta_path):
            try:
                self.index = faiss.read_index(idx_path)
                with open(meta_path, 'rb') as f:
                    meta = pickle.load(f)
                self.chunks = meta['chunks']
                self._embed_cache.update(meta.get('embed_cache', {}))
                self._current_doc_hash = doc_hash
                return True
            except Exception:
                pass
        return False

    def _save_to_disk(self, doc_hash):
        """Persist the current index and metadata to disk."""
        try:
            faiss.write_index(self.index, self._index_path(doc_hash))
            with open(self._meta_path(doc_hash), 'wb') as f:
                pickle.dump({'chunks': self.chunks, 'embed_cache': self._embed_cache}, f)
        except Exception:
            pass  # non-fatal — app still works without persistence

    def _embed(self, text):
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._embed_cache:
            return self._embed_cache[text_hash]
        body = json.dumps({"inputText": text[:8000]})
        response = self.embedding_client.invoke_model(
            modelId=self.embedding_model, body=body,
            contentType="application/json", accept="application/json"
        )
        vector = np.array(json.loads(response["body"].read())["embedding"], dtype=np.float32)
        self._embed_cache[text_hash] = vector
        return vector

    def build_index(self, chunks):
        """Build FAISS index — loads from disk if same doc was indexed before."""
        doc_hash = self._doc_hash(chunks)

        # Cache hit — load from disk instantly
        if self._load_from_disk(doc_hash):
            return

        self.chunks = chunks
        self._current_doc_hash = doc_hash

        embeddings = [None] * len(chunks)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._embed, chunk): i for i, chunk in enumerate(chunks)}
            for future in as_completed(futures):
                embeddings[futures[future]] = future.result()

        embeddings = np.array(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Persist to disk for future use
        self._save_to_disk(doc_hash)

    def search(self, query, top_k=3):
        if self.index is None or not self.chunks:
            return []
        query_vector = self._embed(query).reshape(1, -1)
        distances, indices = self.index.search(query_vector, min(top_k, len(self.chunks)))
        return [self.chunks[i] for i in indices[0] if i < len(self.chunks)]

    def clear(self):
        self.index = None
        self.chunks = []
        self._current_doc_hash = None
