"""Answer generation with a local LLM.

The retrieved chunks are assembled into a context block and passed to
``Qwen/Qwen3-0.6B`` with an instruction to answer *only* from that context and
to cite the files used. Heavy dependencies (``torch``, ``transformers``) are
imported lazily so indexing, search and evaluation work even when they are not
installed.
"""

from __future__ import annotations

from typing import List, Optional

from . import config
from .models import RankedChunk

_SYSTEM_PROMPT = (
    "You are a precise technical assistant answering questions about the vLLM "
    "codebase. Use ONLY the provided context. If the answer is not in the "
    "context, say so. Be self-contained, factual, and cite the source files "
    "you used. Do not invent APIs or behaviour."
)


def build_context(
    ranked: List[RankedChunk],
    char_budget: int = config.DEFAULT_CONTEXT_CHAR_BUDGET,
) -> str:
    """Concatenate top chunks into a labelled context block within a budget."""
    blocks: List[str] = []
    used = 0
    for item in ranked:
        chunk = item.chunk
        header = (
            f"[Source: {chunk.file_path} "
            f"({chunk.first_character_index}:{chunk.last_character_index})]"
        )
        body = chunk.text
        remaining = char_budget - used
        if remaining <= len(header):
            break
        if len(header) + 1 + len(body) > remaining:
            body = body[: remaining - len(header) - 1]
        block = f"{header}\n{body}"
        blocks.append(block)
        used += len(block) + 2
        if used >= char_budget:
            break
    return "\n\n".join(blocks)


class AnswerGenerator:
    """Lazy wrapper around a Hugging Face causal LM for answer generation."""

    def __init__(
        self,
        model_name: str = config.DEFAULT_MODEL_NAME,
        max_new_tokens: int = config.DEFAULT_MAX_NEW_TOKENS,
    ) -> None:
        """Store configuration; the model is loaded on first use."""
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self._tokenizer: Optional[object] = None
        self._model: Optional[object] = None

    def _ensure_loaded(self) -> None:
        """Load the tokenizer and model once, on demand."""
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Answer generation requires 'transformers' and 'torch'. "
                "Install them with: uv add transformers torch"
            ) from exc
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype="auto",
            device_map="auto" if torch.cuda.is_available() else None,
        )

    def answer(self, question: str, ranked: List[RankedChunk]) -> str:
        """Generate an answer to ``question`` grounded in ``ranked`` chunks."""
        self._ensure_loaded()
        import torch

        context = build_context(ranked)
        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the context above and cite the source files."
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        tokenizer = self._tokenizer
        model = self._model
        assert tokenizer is not None and model is not None

        try:
            text = tokenizer.apply_chat_template(  # type: ignore[attr-defined]
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            text = tokenizer.apply_chat_template(  # type: ignore[attr-defined]
                messages, tokenize=False, add_generation_prompt=True
            )

        inputs = tokenizer(text, return_tensors="pt").to(model.device)  # type: ignore
        with torch.no_grad():
            generated = model.generate(  # type: ignore[attr-defined]
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        new_tokens = generated[0][inputs["input_ids"].shape[1]:]
        output = tokenizer.decode(  # type: ignore[attr-defined]
            new_tokens, skip_special_tokens=True
        )
        return str(output).strip()
