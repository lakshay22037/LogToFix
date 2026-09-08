"""Seeds fix_examples with real (bug -> fix) pairs from SWE-bench_Lite, per
DECISIONS.md: "Data sourcing strategy" and "Embedding model for RAG".

Usage:
    python -m scripts.seed_fix_examples [--count 25]
"""
import argparse
import logging
import sys

import requests

from llm_core.embeddings import EmbeddingError, get_default_embedder

import app.env  # noqa: F401 — loads .env as a side effect
from app.db import SessionLocal
from app.models import FixExample

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATASET = "princeton-nlp/SWE-bench_Lite"
ROWS_URL = "https://datasets-server.huggingface.co/rows"
MAX_PATCH_CHARS = 3000  # skip sprawling multi-file patches — keep examples digestible
PAGE_SIZE = 50


def fetch_candidate_rows(target_count: int) -> list:
    """Pages through SWE-bench_Lite, keeping small-enough patches, until
    target_count candidates are collected or the dataset is exhausted."""
    candidates = []
    offset = 0
    while len(candidates) < target_count:
        response = requests.get(
            ROWS_URL,
            params={"dataset": DATASET, "config": "default", "split": "test", "offset": offset, "length": PAGE_SIZE},
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json().get("rows", [])
        if not rows:
            break  # exhausted the dataset

        for entry in rows:
            row = entry["row"]
            if len(row["patch"]) <= MAX_PATCH_CHARS:
                candidates.append(row)
                if len(candidates) >= target_count:
                    break

        offset += PAGE_SIZE

    return candidates


def seed(count: int) -> None:
    embedder = get_default_embedder()
    session = SessionLocal()
    try:
        existing_sources = {
            row[0] for row in session.query(FixExample.source).all()
        }

        candidates = fetch_candidate_rows(count)
        logger.info("Fetched %d candidate examples from %s", len(candidates), DATASET)

        inserted = 0
        for row in candidates:
            source = f"swebench-lite:{row['instance_id']}"
            if source in existing_sources:
                continue

            try:
                embedding = embedder.embed(row["problem_statement"][:8000])
            except EmbeddingError:
                logger.exception("Failed to embed %s — skipping", source)
                continue

            session.add(FixExample(
                error_description=row["problem_statement"],
                fix_diff=row["patch"],
                source=source,
                embedding=embedding,
            ))
            inserted += 1

        session.commit()
        logger.info("Inserted %d new fix_examples (skipped %d already present)", inserted, len(candidates) - inserted)
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()

    try:
        seed(args.count)
    except requests.exceptions.RequestException:
        logger.exception("Failed to fetch dataset rows")
        sys.exit(1)
