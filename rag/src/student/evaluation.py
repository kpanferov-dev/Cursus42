"""Retrieval evaluation: recall@k via interval IoU.

This reproduces the grading *moulinette* exactly so a passing self-evaluation
guarantees a passing grade. A retrieved source counts as a hit for a
ground-truth source when, on the same file, their character intervals have an
Intersection-over-Union strictly greater than ``minimal_iou_threshold`` (0.05).
A question's recall is ``found / number_of_true_sources``; the dataset score is
the mean across questions that carry ground-truth sources.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from . import config
from .models import (
    MinimalSource,
    RagDataset,
    StudentSearchResults,
)


def compare_sources(s1: MinimalSource, s2: MinimalSource) -> float:
    """Return the IoU of two sources' character intervals (0 if different file)."""
    if s1.file_path != s2.file_path:
        return 0.0
    s1_len = s1.last_character_index - s1.first_character_index
    s2_len = s2.last_character_index - s2.first_character_index
    intersection = max(
        0,
        min(s1.last_character_index, s2.last_character_index)
        - max(s1.first_character_index, s2.first_character_index),
    )
    union = s1_len + s2_len - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def recall_for_one_question(
    pred_sources: Sequence[MinimalSource],
    true_sources: Sequence[MinimalSource],
    minimal_iou_threshold: float = config.DEFAULT_IOU_THRESHOLD,
) -> float:
    """Compute recall for a single question.

    Returns 1.0 when there are no ground-truth sources, 0.0 when nothing was
    retrieved, otherwise the (threshold-filtered) overlap count divided by the
    number of ground-truth sources.
    """
    if not true_sources:
        return 1.0
    if not pred_sources:
        return 0.0
    found: Dict[int, float] = {i: 0.0 for i in range(len(true_sources))}
    for i, true_source in enumerate(true_sources):
        for pred_source in pred_sources:
            if compare_sources(true_source, pred_source) > minimal_iou_threshold:
                found[i] += 1.0
    return sum(found.values()) / len(true_sources)


def evaluate_dataset(
    student: StudentSearchResults,
    dataset: RagDataset,
    minimal_iou_threshold: float = config.DEFAULT_IOU_THRESHOLD,
    k_values: Sequence[int] = config.DEFAULT_K_VALUES,
) -> Dict[str, float]:
    """Compute average recall@k over a dataset.

    Predicted sources are matched to questions by ``question_id``; questions
    without ground-truth sources are ignored.
    """
    true_by_id: Dict[str, List[MinimalSource]] = {}
    for question in dataset.rag_questions:
        sources = getattr(question, "sources", None)
        if sources is not None:
            true_by_id[question.question_id] = list(sources)

    pred_by_id: Dict[str, List[MinimalSource]] = {qid: [] for qid in true_by_id}
    for result in student.search_results:
        if result.question_id in pred_by_id:
            pred_by_id[result.question_id] = list(result.retrieved_sources)

    per_k: Dict[str, List[float]] = {f"recall@{k}": [] for k in k_values}
    for qid, true_sources in true_by_id.items():
        pred_sources = pred_by_id[qid]
        for k in k_values:
            recall = recall_for_one_question(
                pred_sources[:k], true_sources, minimal_iou_threshold
            )
            per_k[f"recall@{k}"].append(recall)

    averaged: Dict[str, float] = {}
    for k in k_values:
        scores = per_k[f"recall@{k}"]
        averaged[f"recall@{k}"] = sum(scores) / len(scores) if scores else 0.0
    return averaged


def validate_student_data(
    student: StudentSearchResults,
    max_context_length: int,
    k: int,
) -> bool:
    """Check the structural constraints the grader enforces.

    A submission is invalid if the declared ``k`` exceeds the requested ``k``,
    if any question returns more than ``k`` sources, or if any source span is
    longer than ``max_context_length`` characters.
    """
    is_valid = True
    if student.k > k:
        is_valid = False
        print(f"Student data has more than {k} sources")
    for result in student.search_results:
        if len(result.retrieved_sources) > k:
            is_valid = False
            print(f"Search result {result.question_id} has more than {k} sources")
            continue
        for source in result.retrieved_sources:
            length = source.last_character_index - source.first_character_index
            if length > max_context_length:
                is_valid = False
                print(
                    f"Source {source.file_path}"
                    f"[{source.first_character_index}:"
                    f"{source.last_character_index}] has a length of {length} "
                    f"which is more than the limit of {max_context_length} "
                    f"characters"
                )
    print(f"Student data is valid: {is_valid}")
    return is_valid
