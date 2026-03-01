"""
Vector-indexed Knowledge Base for FeaGPT.
Implements semantic search using sentence-transformers (Eq. 1 in paper).
Threshold sigma > 0.85 triggers knowledge-augmented mode.
"""
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Knowledge base with vector-indexed semantic search."""

    def __init__(self, config):
        self.config = config
        self.embedding_model = None
        self.materials = {}
        self.geometry_patterns = {}
        self.solver_configs = {}
        self._embeddings_cache = {}
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            logger.info(f"Loaded embedding model: {self.config.embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using keyword fallback")
        self._load_data()
        self._build_index()
        self._initialized = True

    def _load_data(self):
        for attr, path_attr in [("materials", "materials_path"), ("geometry_patterns", "geometry_patterns_path"), ("solver_configs", "solver_configs_path")]:
            path = Path(getattr(self.config, path_attr, ""))
            if path.exists():
                with open(path) as f:
                    setattr(self, attr, json.load(f))
                logger.info(f"Loaded {len(getattr(self, attr))} {attr}")

    def _build_index(self):
        if not self.embedding_model:
            return
        texts, keys = [], []
        for name, data in self.materials.items():
            texts.append(f"{name} {data.get('description', '')} {' '.join(data.get('keywords', []))}")
            keys.append(("material", name))
        for name, data in self.geometry_patterns.items():
            texts.append(f"{name} {data.get('description', '')} {' '.join(data.get('keywords', []))}")
            keys.append(("geometry", name))
        for name, data in self.solver_configs.items():
            texts.append(f"{name} {data.get('description', '')} {' '.join(data.get('keywords', []))}")
            keys.append(("solver", name))
        if texts:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            self._embeddings_cache = {"texts": texts, "keys": keys, "embeddings": embeddings}

    def search(self, query: str, category: Optional[str] = None, top_k: int = 5) -> List[Tuple]:
        """Semantic search. Returns [(category, name, score, data), ...]"""
        if not self.embedding_model or not self._embeddings_cache:
            return self._keyword_search(query, category, top_k)
        q_emb = self.embedding_model.encode([query], show_progress_bar=False)[0]
        db_emb = self._embeddings_cache["embeddings"]
        sims = np.dot(db_emb, q_emb) / (np.linalg.norm(db_emb, axis=1) * np.linalg.norm(q_emb) + 1e-10)
        keys = self._embeddings_cache["keys"]
        if category:
            mask = np.array([k[0] == category for k in keys])
            sims = np.where(mask, sims, -1)
        top_idx = np.argsort(sims)[::-1][:top_k]
        results = []
        for idx in top_idx:
            cat, name = keys[idx]
            score = float(sims[idx])
            if score < 0:
                continue
            results.append((cat, name, score, self._get_entry(cat, name)))
        return results

    def get_similarity_score(self, query: str, category: str = None) -> float:
        results = self.search(query, category=category, top_k=1)
        return results[0][2] if results else 0.0

    def _get_entry(self, category: str, name: str) -> Dict:
        db = {"material": self.materials, "geometry": self.geometry_patterns, "solver": self.solver_configs}
        return db.get(category, {}).get(name, {})

    def _keyword_search(self, query: str, category: Optional[str], top_k: int) -> List[Tuple]:
        words = set(query.lower().split())
        results = []
        sources = []
        if not category or category == "material":
            sources.append(("material", self.materials))
        if not category or category == "geometry":
            sources.append(("geometry", self.geometry_patterns))
        if not category or category == "solver":
            sources.append(("solver", self.solver_configs))
        for cat, db in sources:
            for name, data in db.items():
                kw = set(w.lower() for w in [name] + data.get("keywords", []))
                overlap = len(words & kw)
                if overlap > 0:
                    results.append((cat, name, overlap / max(len(words), len(kw)), data))
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]

    def add_entry(self, category: str, name: str, data: Dict):
        db = {"material": self.materials, "geometry": self.geometry_patterns, "solver": self.solver_configs}
        if category in db:
            db[category][name] = data
            if self.embedding_model:
                self._build_index()

    def save(self):
        for path_attr, data_attr in [("materials_path", "materials"), ("geometry_patterns_path", "geometry_patterns"), ("solver_configs_path", "solver_configs")]:
            path = Path(getattr(self.config, path_attr, ""))
            if path.parent.exists():
                with open(path, "w") as f:
                    json.dump(getattr(self, data_attr), f, indent=2)
