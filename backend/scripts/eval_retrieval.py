"""Measures RAG retrieval quality against a small labeled eval set, per
ENGINEERING_STANDARDS.md §3: "Retrieval quality is measured, not assumed."

Each eval case pairs a hand-written paraphrase of a real seeded bug
(data/rag_eval_set.json) with the source it should retrieve — paraphrased
rather than copied verbatim, so this measures genuine semantic retrieval,
not exact-text lookup.

Usage:
    python -m scripts.eval_retrieval [--top-k 5]
"""
import argparse
import json
import logging
from pathlib import Path

import app.env  # noqa: F401 — loads .env as a side effect
from app.retrieval import retrieve_similar_fixes
from llm_core.embeddings import get_default_embedder

logging.basicConfig(level=logging.WARNING)  # quiet HTTP request logs during eval

EVAL_SET_PATH = Path(__file__).resolve().parents[2] / "data" / "rag_eval_set.json"


def rank_of_expected(results: list, expected_source: str) -> "int | None":
    for i, r in enumerate(results, start=1):
        if r["source"] == expected_source:
            return i
    return None


def run_eval(top_k: int) -> None:
    eval_cases = json.loads(EVAL_SET_PATH.read_text())
    embedder = get_default_embedder()

    ranks = []
    print(f"{'rank':>5}  {'expected_source':<45} query")
    print("-" * 100)
    for case in eval_cases:
        query_embedding = embedder.embed(case["query"])
        results = retrieve_similar_fixes(query_embedding, top_k=top_k)
        rank = rank_of_expected(results, case["expected_source"])
        ranks.append(rank)
        print(f"{str(rank):>5}  {case['expected_source']:<45} {case['query'][:60]}")

    n = len(ranks)
    hits_at_1 = sum(1 for r in ranks if r == 1) / n
    hits_at_3 = sum(1 for r in ranks if r is not None and r <= 3) / n
    hits_at_k = sum(1 for r in ranks if r is not None) / n
    mrr = sum((1 / r) if r else 0 for r in ranks) / n

    print("-" * 100)
    print(f"n={n} eval cases, top_k={top_k}")
    print(f"Hits@1:  {hits_at_1:.0%}")
    print(f"Hits@3:  {hits_at_3:.0%}")
    print(f"Hits@{top_k}:  {hits_at_k:.0%}")
    print(f"MRR:     {mrr:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    run_eval(args.top_k)
