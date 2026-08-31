*This project has been created as part of the 42 curriculum by kpanfero.*

# RAG against the machine

A Retrieval-Augmented Generation system that answers questions about the
**vLLM** codebase. It ingests the repository, builds a BM25 index over
intelligently chunked code and documentation, retrieves the most relevant spans
for a question, optionally fuses a dense (semantic) ranking and re-ranks with a
cross-encoder, and generates a grounded answer with `Qwen/Qwen3-0.6B`.

## Description

**Goal.** Given a question such as *"What HTTP endpoint dynamically loads a LoRA
adapter?"*, locate the exact source spans in the vLLM repository that answer it
and produce a faithful, source-grounded answer.

The system is graded on **retrieval recall@k**. The pipeline has five stages:
ingestion, indexing, retrieval (with optional dense fusion + reranking),
generation, and evaluation.

## Instructions

### Install (layered — install only what you need)

```bash
uv venv
uv sync                      # CORE: BM25 retrieval, search, evaluate (required)
uv sync --extra semantic     # BONUS: dense retrieval via model2vec (light, ~30MB, no torch)
uv sync --extra rerank       # BONUS: cross-encoder reranking via fastembed (ONNX, no torch)
uv sync --extra semantic --extra rerank #BONUS: Both
uv sync --extra dev          # flake8 / mypy / pytest
```

> **Do NOT run `uv sync --extra generation` on a quota-limited machine unless
> you redirect the cache.** That extra pulls full **PyTorch (~5GB of CUDA
> libraries)** and will fill a small home quota with `No space left on device`.
> It is only needed for the `answer` / `answer_dataset` commands (LLM answer
> generation), **not** for retrieval/recall. If you do need it, point the caches
> at a large volume first:
> ```bash
> export UV_CACHE_DIR=/sgoinfre/<login>/uv-cache
> export HF_HOME=/sgoinfre/<login>/hf-cache
> uv cache clean
> uv sync --extra generation
> ```

### Prepare the data

Place the extracted repository so that `data/raw/vllm-0.10.1/` contains `vllm/`,
`docs/`, etc., and the datasets under `data/datasets/AnsweredQuestions/`. Ground
-truth source paths are relative to the working directory (e.g.
`data/raw/vllm-0.10.1/docs/...`), so the repository must live at exactly
`data/raw/vllm-0.10.1`. Large data, indices and model weights are not committed
(see `.gitignore`); the evaluator regenerates them.

### Run

```bash
# 1. Build the knowledge base (BM25; add --semantic to also build dense vectors)
uv run python -m student index --max_chunk_size 800 --semantic

# 2. Search a single query
uv run python -m student search "How to configure the OpenAI server?" --k 10

# 3a. CODE dataset — plain BM25 is enough (passes the 50% bar)
uv run python -m student search_dataset \
    --dataset_path data/datasets/AnsweredQuestions/dataset_code_public.json \
    --k 10 --save_directory data/output/search_results

# 3b. DOCS dataset — dense fusion + cross-encoder reranking (to clear the 80% bar)
uv run python -m student search_dataset \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --rerank --save_directory data/output/search_results

# 4. Evaluate retrieval against ground truth
uv run python -m student evaluate \
    data/output/search_results/dataset_docs_public.json \
    data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --max_context_length 2000 --threshold 0.05

# 5. Answer generation (requires the 'generation' extra — see install note)
uv run python -m student answer "How to configure the OpenAI server?" --k 10
```

`make install`, `make run`, `make lint`, `make lint-strict`, `make test` and
`make clean` are provided.

## System architecture

```
question
   │
   ▼
Retriever ── BM25 ─────────────┐
            (+ TF-IDF) ────────┤── Reciprocal Rank Fusion ──► candidates
            (+ dense, model2vec)┘                                 │
                                                                  ▼
                                            Cross-encoder reranker (fastembed/ONNX)
                                                                  │
                                                                  ▼
                                                    top-k MinimalSource spans
                                                          │            │
                                                          ▼            ▼
                                          AnswerGenerator (Qwen3)   Evaluation (recall@k)
```

| Component | Module | Responsibility |
|-----------|--------|----------------|
| Ingestion | `ingest.py` | Walk the repo, dispatch per file type, emit `Chunk`s with provenance |
| Chunking | `chunking.py` | AST chunking for Python, heading sections for Markdown, sliding window for text |
| Indexing | `indexing.py` | Code-aware tokeniser + BM25 build / save / load |
| Retrieval | `retrieval.py` | Load indices once, rank and fuse candidates |
| Dense (bonus) | `embeddings.py` | model2vec static embeddings (no torch) |
| Fusion (bonus) | `fusion.py` | Weighted Reciprocal Rank Fusion |
| Rerank (extra) | `rerank.py` | ONNX cross-encoder reranking (no torch) |
| Expansion (extra) | `expansion.py` | Domain-synonym query expansion |
| Cache (bonus) | `cache.py` | Disk-backed query cache |
| Generation | `generation.py` | `Qwen/Qwen3-0.6B` answer generation |
| Evaluation | `evaluation.py` | recall@k via interval IoU (mirrors the grader) |
| Models | `models.py` | Pydantic schemas matching the grader |
| CLI | `__main__.py` | `python-fire` command surface |

## Chunking strategy

Retrieval can only return spans it has indexed, so chunking caps achievable
recall. Three strategies record the exact half-open character span `[first, last)`
each chunk occupies; no chunk exceeds `--max_chunk_size` (hard cap 2000).

- **Python code** is parsed with `ast` and split along top-level definitions;
  each function/class is its own chunk and module preamble is grouped
  separately. Keeping definitions separate keeps the IoU high against small
  ground-truth spans.
- **Markdown** is split into heading sections (`#`..`######`), so each chunk is a
  coherent, keyword-dense unit aligned with how documentation is annotated.
- **Plain text** uses an overlapping sliding window that prefers blank-line
  boundaries.

The default `--max_chunk_size` is **800** with 200 overlap: smaller chunks raise
both ranking precision and IoU on the passage-sized documentation targets.

## Retrieval method

The mandatory core is **BM25** (via `bm25s`) with a **code-aware tokeniser** that
lowercases, splits on non-alphanumerics, and additionally breaks `snake_case`
and `camelCase` into sub-tokens while keeping the whole identifier (so a query
for `limits` matches `get_supported_mm_limits`).

On top of BM25 the system can (bonus) fuse a **dense semantic ranking**
(model2vec static embeddings, cosine similarity) via **Reciprocal Rank Fusion**,
and finally **re-rank** the fused candidate pool with an **ONNX cross-encoder**
(`ms-marco-MiniLM`). Both dense and rerank backends are torch-free.

## Performance analysis

Retrieval is scored with **recall@k**; a retrieved source counts as a hit when,
on the same file, the Intersection-over-Union of its character interval with a
ground-truth interval exceeds **0.05**. A question's recall is
`found / number_of_true_sources`, averaged over questions. The bundled
`evaluate` command reproduces the grading moulinette's arithmetic exactly.

Measured on the public datasets (Recall@5):

| Configuration | Code | Docs |
|---------------|------|------|
| BM25 only | **0.71** (pass) | 0.67 |
| BM25 + dense (model2vec) | — | ~0.75 |
| BM25 + dense + cross-encoder rerank | — | ~0.77+ |

Code clears its 50% bar with plain BM25. Documentation is vocabulary-driven
(questions paraphrase the docs), so lexical methods plateau around 0.67;
**adding dense retrieval lifts Recall@5 to ~0.75, and cross-encoder reranking
raises Recall@1 from 0.48 to 0.64** and pushes Recall@5 toward the 80% bar.
Indexing stays well under the 5-minute budget (~20s); plain BM25 retrieval is
sub-millisecond per query. (Reranking trades throughput for recall and is an
opt-in flag, so the no-rerank path still meets the warm-throughput budget.)

## Design decisions

- **BM25 first.** The subject recommends starting simple; lexical matching is
  strong for code and trivially meets timing budgets.
- **Dense via model2vec, not transformers.** Static embeddings give semantic
  recall with pure NumPy inference and a ~30MB model — no torch, so it fits a
  quota-limited cluster where full PyTorch does not.
- **Cross-encoder rerank via ONNX (fastembed).** Recall@10 exceeded Recall@5,
  i.e. an ordering problem; a cross-encoder fixes ordering. ONNX keeps it
  torch-free.
- **Schemas mirror the grader** (note the `question` field) so output always
  validates.
- **Lazy heavy imports.** torch/transformers (generation) and ONNX/model are
  imported only on the paths that use them.

## Challenges faced

- **Source path alignment.** Ground-truth `file_path` values include the
  `data/raw/vllm-0.10.1/` prefix; storing repo-relative paths gave 0 recall
  until the prefix was matched. (Always re-`index` after a code change.)
- **IoU vs chunk size.** Over-large chunks dropped small targets below the 0.05
  IoU threshold; structural/section chunking fixed it.
- **Disk-constrained cluster.** Full PyTorch (~5GB CUDA) overflowed the home
  quota; model2vec and ONNX reranking provided torch-free equivalents, and
  caches can be redirected to a large volume when torch is genuinely needed.
- **Lexical tricks backfired.** TF-IDF fusion and query expansion *reduced* docs
  recall (still lexical); the real gap was paraphrase, fixed by dense retrieval.

## Example usage

```text
$ uv run python -m student search_dataset \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --semantic --rerank --save_directory data/output/search_results
Searching: 100%|██████████| 100/100 [00:11<00:00,  8.7q/s]
Saved student_search_results to data/output/search_results/dataset_docs_public.json

$ uv run python -m student evaluate \
    data/output/search_results/dataset_docs_public.json \
    data/datasets/AnsweredQuestions/dataset_docs_public.json --threshold 0.80
Recall@1: 0.64   Recall@3: 0.73   Recall@5: 0.77   Recall@10: 0.81
```

## Resources

- vLLM documentation — https://docs.vllm.ai
- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009)
- `bm25s` — https://github.com/xhluca/bm25s
- model2vec (static embeddings) — https://github.com/MinishLab/model2vec
- fastembed (ONNX embeddings/rerankers) — https://github.com/qdrant/fastembed
- Qwen3 model card — https://huggingface.co/Qwen/Qwen3-0.6B
- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020)

**Use of AI.** AI assistance was used to (1) reverse-engineer the grader's exact
IoU/recall arithmetic and schema so the local `evaluate` matches it, (2) draft
boilerplate (docstrings, CLI scaffolding) and this README, and (3) diagnose
retrieval edge cases (path prefix, chunk size, fusion/rerank tuning). All logic
was read, tested against the real moulinette, and is owned by the author.
