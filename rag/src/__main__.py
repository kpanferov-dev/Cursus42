"""Command-line interface (``python -m student <command>``).

Exposes the full pipeline through `python-fire`:

* ``index``           build and persist the knowledge base
* ``search``          retrieve sources for a single query
* ``search_dataset``  retrieve sources for every question in a dataset
* ``answer``          answer a single query with retrieved context
* ``answer_dataset``  attach generated answers to a search-results file
* ``evaluate``        score search results against a ground-truth dataset

Every command validates its inputs and reports errors clearly instead of
crashing on degenerate input.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import fire
from tqdm import tqdm

from . import config
from .evaluation import evaluate_dataset, validate_student_data
from .indexing import build_index, save_index
from .ingest import ingest_repository
from .models import (
    MinimalAnswer,
    MinimalSearchResults,
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)
from .retrieval import Retriever


def _load_dataset(dataset_path: str) -> RagDataset:
    """Load and validate a RAG dataset JSON file."""
    path = Path(dataset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    with path.open("r", encoding="utf-8") as handle:
        return RagDataset.model_validate(json.load(handle))


def _load_student_results(results_path: str) -> StudentSearchResults:
    """Load a previously produced search-results JSON file."""
    path = Path(results_path)
    if not path.is_file():
        raise FileNotFoundError(f"Search results not found: {results_path}")
    with path.open("r", encoding="utf-8") as handle:
        return StudentSearchResults.model_validate(json.load(handle))


class Student:
    """Container class exposing the RAG pipeline commands to Fire."""

    def index(
        self,
        repo_root: str = str(config.DEFAULT_REPO_ROOT),
        max_chunk_size: int = config.DEFAULT_MAX_CHUNK_SIZE,
        overlap: int = config.DEFAULT_CHUNK_OVERLAP,
        tfidf: bool = False,
        semantic: bool = False,
    ) -> bool:
        """Ingest a repository and build the BM25 index.

        Args:
            repo_root: Directory of the extracted repository to index.
            max_chunk_size: Maximum characters per chunk (capped at 2000).
            overlap: Characters shared between consecutive chunks.
            tfidf: Also build a TF-IDF index for hybrid retrieval (bonus).
            semantic: Also build dense embeddings for hybrid retrieval (bonus).
        """
        try:
            start = time.time()
            chunks = ingest_repository(Path(repo_root), max_chunk_size, overlap)
            if not chunks:
                print(f"No indexable files found under {repo_root}")
                return False
            retriever = build_index(chunks)
            meta = {
                "repo_root": str(repo_root),
                "max_chunk_size": min(max_chunk_size, config.HARD_MAX_CHUNK_SIZE),
                "overlap": overlap,
                "num_chunks": len(chunks),
                "tfidf": bool(tfidf),
                "semantic": bool(semantic),
            }
            save_index(retriever, chunks, meta=meta)
            if tfidf:
                from .tfidf import TfidfIndex
                TfidfIndex.build(chunks).save()
                print("Built TF-IDF index for hybrid retrieval.")
            if semantic:
                from .embeddings import SemanticIndex
                SemanticIndex.build(chunks).save()
                print("Built semantic embedding index for hybrid retrieval.")
            elapsed = time.time() - start
            print(
                f"Ingestion complete! {len(chunks)} chunks indexed in "
                f"{elapsed:.1f}s. Indices saved under {config.PROCESSED_DIR}/"
            )
            return True
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"Indexing failed: {exc}")
            return False

    def search(
        self,
        query: str = "",
        k: int = config.DEFAULT_K,
        tfidf: bool = False,
        semantic: bool = False,
        expand: bool = False,
        cache: bool = False,
    ) -> Optional[dict]:
        """Search the index for a single query and print the top sources.

        Args:
            query: The natural-language query.
            k: Number of results to return.
            tfidf: Fuse a TF-IDF ranking with BM25 (bonus: hybrid).
            semantic: Fuse a dense embedding ranking (bonus: semantic).
            expand: Expand the query with domain synonyms (bonus).
            cache: Cache and reuse results on disk (bonus).
        """
        if not query or not str(query).strip():
            print("Please provide a non-empty query.")
            return None
        try:
            retriever = Retriever(
                use_tfidf=tfidf, use_semantic=semantic,
                expand=expand, use_cache=cache,
            )
        except (FileNotFoundError, RuntimeError) as exc:
            print(str(exc))
            return None
        ranked = retriever.search(str(query), k=int(k))
        sources = [item.chunk.to_source().model_dump() for item in ranked]
        for rank, item in enumerate(ranked, start=1):
            chunk = item.chunk
            preview = chunk.text.strip().replace("\n", " ")[:100]
            print(
                f"{rank:>2}. [{item.score:6.2f}] {chunk.file_path}"
                f"[{chunk.first_character_index}:{chunk.last_character_index}] "
                f"{preview}"
            )
        return {"query": str(query), "k": int(k), "retrieved_sources": sources}

    def search_dataset(
        self,
        dataset_path: str,
        k: int = config.DEFAULT_K,
        save_directory: str = str(config.DATA_DIR / "output" / "search_results"),
        tfidf: bool = False,
        semantic: bool = False,
        expand: bool = False,
        cache: bool = False,
        rerank: bool = True,
    ) -> Optional[str]:
        """Retrieve sources for every question in a dataset.

        Args:
            dataset_path: Path to a dataset JSON (answered or unanswered).
            k: Number of sources to retrieve per question.
            save_directory: Directory in which to write the results file.
            tfidf: Fuse a TF-IDF ranking with BM25 (bonus: hybrid).
            semantic: Fuse a dense embedding ranking (bonus: semantic).
            expand: Expand each query with domain synonyms (bonus).
            cache: Cache and reuse results on disk (bonus).
            rerank: Re-order candidates with a cross-encoder (bonus).
        """
        try:
            dataset = _load_dataset(dataset_path)
            retriever = Retriever(
                use_tfidf=tfidf, use_semantic=semantic,
                expand=expand, use_cache=cache,
            )
            reranker = None
            if rerank:
                from .rerank import CrossEncoderReranker
                reranker = CrossEncoderReranker()
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"Search failed: {exc}")
            return None

        k = int(k)
        # When reranking, pull a deeper candidate pool then re-order it.
        fetch_k = max(k, config.RERANK_POOL) if reranker is not None else k
        results = []
        for question in tqdm(dataset.rag_questions, desc="Searching", unit="q"):
            ranked = retriever.search(question.question, k=fetch_k)
            if reranker is not None and ranked:
                order = reranker.order(
                    question.question, [item.chunk.text for item in ranked]
                )
                ranked = [ranked[i] for i in order]
            ranked = ranked[:k]
            results.append(
                MinimalSearchResults(
                    question_id=question.question_id,
                    question=question.question,
                    retrieved_sources=[item.chunk.to_source() for item in ranked],
                )
            )
        output = StudentSearchResults(search_results=results, k=k)

        save_dir = Path(save_directory)
        save_dir.mkdir(parents=True, exist_ok=True)
        out_path = save_dir / Path(dataset_path).name
        out_path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved student_search_results to {out_path}")
        return str(out_path)

    def answer(self, query: str = "", k: int = config.DEFAULT_K) -> Optional[str]:
        """Answer a single query using retrieved context.

        Args:
            query: The question to answer.
            k: Number of context sources to retrieve.
        """
        if not query or not str(query).strip():
            print("Please provide a non-empty query.")
            return None
        try:
            from .generation import AnswerGenerator

            retriever = Retriever()
            ranked = retriever.search(str(query), k=int(k))
            generator = AnswerGenerator()
            response = generator.answer(str(query), ranked)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"Answer failed: {exc}")
            return None
        print(response)
        return response

    def answer_dataset(
        self,
        student_search_results_path: str,
        save_directory: str = str(
            config.DATA_DIR / "output" / "search_results_and_answer"
        ),
    ) -> Optional[str]:
        """Generate an answer for each entry of a search-results file.

        Args:
            student_search_results_path: Path to a ``search_dataset`` output.
            save_directory: Directory in which to write the answered file.
        """
        try:
            from .generation import AnswerGenerator

            student = _load_student_results(student_search_results_path)
            retriever = Retriever()
            generator = AnswerGenerator()
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"Answer dataset failed: {exc}")
            return None

        print(
            f"Loaded {len(student.search_results)} questions from "
            f"{student_search_results_path}"
        )
        answered = []
        total = len(student.search_results)
        for done, result in enumerate(
            tqdm(student.search_results, desc="Answering", unit="q"), start=1
        ):
            ranked = retriever.search(result.question, k=student.k)
            response = generator.answer(result.question, ranked)
            answered.append(
                MinimalAnswer(
                    question_id=result.question_id,
                    question=result.question,
                    retrieved_sources=result.retrieved_sources,
                    answer=response,
                )
            )
            print(f"Processed {done} of {total} questions")
        output = StudentSearchResultsAndAnswer(
            search_results=answered, k=student.k
        )
        save_dir = Path(save_directory)
        save_dir.mkdir(parents=True, exist_ok=True)
        out_path = save_dir / Path(student_search_results_path).name
        out_path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved student_search_results_and_answer to {out_path}")
        return str(out_path)

    def evaluate(
        self,
        student_search_results_path: str,
        dataset_path: str,
        k: int = config.DEFAULT_K,
        max_context_length: int = config.HARD_MAX_CHUNK_SIZE,
        threshold: Optional[float] = None,
    ) -> Optional[dict]:
        """Evaluate search results against a ground-truth dataset.

        Args:
            student_search_results_path: Path to a ``search_dataset`` output.
            dataset_path: Path to the ground-truth (answered) dataset.
            k: Maximum number of sources considered per question.
            max_context_length: Maximum allowed length of a source span.
            threshold: If set, print PASS/FAIL on Recall@5 against this value.
        """
        try:
            student = _load_student_results(student_search_results_path)
            dataset = _load_dataset(dataset_path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Evaluation failed: {exc}")
            return None

        validate_student_data(student, int(max_context_length), int(k))
        num_with_sources = sum(
            1 for q in dataset.rag_questions if getattr(q, "sources", None)
        )
        print(f"Total number of questions: {len(dataset.rag_questions)}")
        print(f"Total number of questions with sources: {num_with_sources}")
        print(
            "Total number of questions with student sources: "
            f"{len(student.search_results)}"
        )

        scores = evaluate_dataset(student, dataset)
        print("\nEvaluation Results")
        print("=" * 40)
        print(f"Questions evaluated: {num_with_sources}")
        for key in ("recall@1", "recall@3", "recall@5", "recall@10"):
            if key in scores:
                print(f"{key.replace('recall', 'Recall')}: {scores[key]:.3f}")

        if threshold is not None:
            recall5 = scores.get("recall@5", 0.0)
            verdict = "PASS" if recall5 >= float(threshold) else "FAIL"
            print(f"\n{verdict} (Recall@5 = {recall5:.3f}, threshold = {threshold})")
        return scores


def main() -> None:
    """CLI entrypoint."""
    fire.Fire(Student)


if __name__ == "__main__":
    main()
