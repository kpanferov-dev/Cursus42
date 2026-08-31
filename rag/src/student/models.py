"""Pydantic data models for the RAG pipeline.

These models mirror the ones used by the evaluation *moulinette* exactly, so
that any JSON this project produces is accepted by the grader without changes.
Character indices follow a half-open convention: ``content[first:last]`` is the
exact text of the source, therefore ``last - first`` is its length in
characters.
"""

from __future__ import annotations

import uuid
from typing import List, Union

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """A pointer to a span of characters inside a single file."""

    file_path: str
    first_character_index: int
    last_character_index: int

    @property
    def length(self) -> int:
        """Return the number of characters covered by the span."""
        return self.last_character_index - self.first_character_index


class UnansweredQuestion(BaseModel):
    """A question without ground-truth answer or sources."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """A question annotated with ground-truth sources and a reference answer."""

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """A dataset of RAG questions (answered or not)."""

    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    """Sources retrieved for a single question.

    The field is named ``question`` to match the grading moulinette's
    schema exactly (its ``MinimalSearchResults`` uses ``question``).
    """

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Search results enriched with a generated answer."""

    answer: str


class StudentSearchResults(BaseModel):
    """Top-level container for the ``search_dataset`` output."""

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(StudentSearchResults):
    """Top-level container for the ``answer_dataset`` output."""

    search_results: List[MinimalAnswer]  # type: ignore[assignment]


class Chunk(BaseModel):
    """A unit of indexed text together with its provenance.

    A chunk is the atomic object the retriever ranks. ``text`` is what BM25
    scores; ``file_path`` plus the two indices let us emit a
    :class:`MinimalSource` the grader can compare against ground truth.
    """

    chunk_id: int
    file_path: str
    first_character_index: int
    last_character_index: int
    text: str
    kind: str = "text"  # "code" or "text"

    def to_source(self) -> MinimalSource:
        """Project the chunk onto a :class:`MinimalSource`."""
        return MinimalSource(
            file_path=self.file_path,
            first_character_index=self.first_character_index,
            last_character_index=self.last_character_index,
        )


class RankedChunk(BaseModel):
    """A chunk paired with the score assigned by the retriever."""

    chunk: Chunk
    score: float
