"""Grounded retrieval over a bundled markdown corpus, using only the stdlib.

Why hand-rolled BM25 instead of Azure AI Search?

* The demo stays free and self-contained -- no search resource to provision,
  no index to keep in sync, no extra RBAC to explain.
* Retrieval is deterministic, so evaluation runs are reproducible.
* The tool contract (`search_documentation` / `fetch_document`) is identical to
  what you would expose over a real vector index, so swapping in Azure AI Search
  later is a change to this module only -- `main.py` does not move.

Documents are split into chunks on markdown headings, which keeps each chunk
semantically coherent and gives every chunk a natural citation label.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# BM25 tuning. k1 controls term-frequency saturation, b controls how strongly
# chunk length normalises the score. These are the standard defaults.
BM25_K1 = 1.5
BM25_B = 0.75

TOKEN_RE = re.compile(r"[a-z0-9]+")

# A hit must match at least this many *distinct* query terms. Without it, one
# incidental rare word is enough to score a chunk: "who won the world cup"
# matches the dispute doc purely on "won", and the agent then cites a document
# that cannot answer the question. Requiring real overlap is what makes an
# out-of-scope question return nothing so the agent can decline honestly.
MIN_TERM_COVERAGE = 2

# Very common words carry no signal and would otherwise let a long chunk win on
# filler alone.
STOPWORDS = frozenset(
    """a an and are as at be by can do does for from has have how i if in is it its
    of on or our so than that the their then there these this to was what when where
    which who why will with you your""".split()
)


def _stem(token: str) -> str:
    """Crude suffix stripper so 'refunded'/'refunds' both match 'refund'.

    Deliberately not a full Porter stemmer: the corpus is small, and a handful
    of plural/participle rules removes the bulk of the mismatches without
    pulling in a dependency or surprising anyone reading this file.
    """
    for suffix, min_stem in (("ing", 4), ("ed", 4), ("es", 3), ("s", 3)):
        if token.endswith(suffix) and len(token) - len(suffix) >= min_stem:
            if suffix == "s" and token.endswith("ss"):
                return token
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    return [
        _stem(token)
        for token in TOKEN_RE.findall(text.lower())
        if token not in STOPWORDS
    ]


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    section: str
    text: str
    tokens: list[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    @property
    def citation(self) -> str:
        return f"{self.doc_id}#{self.section}"


def _split_into_chunks(doc_id: str, raw: str) -> list[Chunk]:
    """Split a markdown document into one chunk per section heading."""
    lines = raw.splitlines()
    doc_title = doc_id
    for line in lines:
        if line.startswith("# "):
            doc_title = line[2:].strip()
            break

    chunks: list[Chunk] = []
    section = "overview"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            chunks.append(Chunk(doc_id=doc_id, doc_title=doc_title, section=section, text=body))

    for line in lines:
        heading = re.match(r"^(#{2,3})\s+(.*)$", line)
        if heading:
            flush()
            buffer = []
            section = heading.group(2).strip()
        else:
            buffer.append(line)
    flush()

    for chunk in chunks:
        # The section heading is part of the searchable text -- a question often
        # echoes the heading wording more than the body wording.
        chunk.tokens = tokenize(f"{chunk.doc_title} {chunk.section} {chunk.text}")
        chunk.counts = Counter(chunk.tokens)

    return chunks


@lru_cache(maxsize=1)
def _index() -> tuple[list[Chunk], dict[str, int], float]:
    """Build the in-memory index once per process.

    Returns the chunk list, the document frequency per term, and the mean chunk
    length used for BM25 length normalisation.
    """
    chunks: list[Chunk] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        chunks.extend(_split_into_chunks(path.stem, path.read_text(encoding="utf-8")))

    doc_freq: Counter = Counter()
    for chunk in chunks:
        doc_freq.update(set(chunk.tokens))

    avg_len = (sum(len(chunk.tokens) for chunk in chunks) / len(chunks)) if chunks else 0.0
    return chunks, dict(doc_freq), avg_len


def _bm25(
    query_tokens: list[str],
    chunk: Chunk,
    doc_freq: dict[str, int],
    n_docs: int,
    avg_len: float,
) -> tuple[float, int]:
    """Score a chunk, returning ``(score, distinct_query_terms_matched)``."""
    score = 0.0
    matched = 0
    chunk_len = len(chunk.tokens) or 1
    for term in set(query_tokens):
        tf = chunk.counts.get(term, 0)
        if not tf:
            continue
        matched += 1
        df = doc_freq.get(term, 0)
        idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
        denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * chunk_len / (avg_len or 1))
        score += idf * (tf * (BM25_K1 + 1)) / denom
    return score, matched


def search(query: str, top_k: int = 3) -> list[dict]:
    """Return the top-k most relevant chunks for a query.

    Chunks that score zero are dropped rather than padded, so an off-topic
    question returns an empty list and the agent can honestly say it does not
    know instead of citing an irrelevant document.
    """
    chunks, doc_freq, avg_len = _index()
    if not chunks:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # A one- or two-word query cannot be expected to overlap on two terms.
    required_coverage = min(MIN_TERM_COVERAGE, len(set(query_tokens)))

    n_docs = len(chunks)
    scored = []
    for chunk in chunks:
        score, matched = _bm25(query_tokens, chunk, doc_freq, n_docs, avg_len)
        if score > 0 and matched >= required_coverage:
            scored.append((score, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    top_k = max(1, min(top_k, 10))
    return [
        {
            "citation": chunk.citation,
            "doc_id": chunk.doc_id,
            "doc_title": chunk.doc_title,
            "section": chunk.section,
            "relevance": round(score, 3),
            "content": chunk.text,
        }
        for score, chunk in scored[:top_k]
    ]


def get_document(doc_id: str) -> dict:
    """Return a whole document by id, for when a chunk is not enough context."""
    safe_id = Path(doc_id).stem  # defensive: never let a doc_id escape the corpus
    path = KNOWLEDGE_DIR / f"{safe_id}.md"
    if not path.is_file():
        return {"found": False, "requested": doc_id, "available": list_documents()}
    return {"found": True, "doc_id": safe_id, "content": path.read_text(encoding="utf-8")}


def list_documents() -> list[str]:
    return sorted(path.stem for path in KNOWLEDGE_DIR.glob("*.md"))
