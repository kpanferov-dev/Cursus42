*This project has been created as part of the 42 curriculum by &lt;your_login&gt;.*

# call me maybe

## Description

**call me maybe** turns natural-language prompts into structured function
calls. Given a request like *"What is the sum of 40 and 2?"* and a set of
function definitions, it does **not** answer `42`; it emits the call to
make:

```json
{"prompt": "What is the sum of 40 and 2?",
 "name": "fn_add_numbers",
 "parameters": {"a": 40.0, "b": 2.0}}
```

The hard part is reliability. A small model (Qwen3-0.6B) left to free-form
generation produces valid JSON only some of the time. This project uses
**constrained decoding**: at every generation step the set of tokens that
would break the required JSON structure or the function schema is masked
out (their logits set to negative infinity), so the model can only ever
continue along a valid path. The result is **100% valid, schema-compliant
JSON by construction** — even though the model still decides *which*
function to call and *what* arguments to extract.

The project is written in **Python 3.10+**, is fully type-annotated
(passes `mypy --strict`), is **flake8**-clean, validates all structured
data with **pydantic**, and implements every algorithm by hand (no
`outlines`, `transformers`, `dspy`, etc.).

> **Important — the LLM SDK.** The real `llm_sdk` package and the Qwen
> model are provided by the subject, not by this repository. To let the
> project run and be tested out of the box, a **mock** `llm_sdk/` is
> included that implements the exact public interface but returns
> deterministic pseudo-random logits. **Replace `llm_sdk/` with the real
> provided package** (copy it next to `src/`) and run `uv sync` for real
> model accuracy. Constrained decoding guarantees valid output with either
> one; only the *choice quality* depends on the real model.

## Instructions

```bash
# install dependencies into a uv-managed environment
make install            # == uv sync

# run on the default files (data/input/*.json -> data/output/...)
make run                # == uv run python -m src ...

# or run directly with explicit paths
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json

# quality gates and tests
make lint               # flake8 . + mypy . (subject flag set)
make lint-strict        # flake8 . + mypy . --strict
make test               # uv run pytest
make debug              # run under pdb
make clean              # remove caches
```

The program reads from `data/input/` and writes to `data/output/` by
default; all three paths are overridable with the flags above. A
`--model` flag selects the model identifier (default `Qwen/Qwen3-0.6B`).

## Algorithm explanation (constrained decoding)

The output object is described as a tiny **program** of two instruction
kinds (see `src/grammar.py`):

* **Literal** — fixed text that must appear verbatim: the braces, the
  `"name"` / `"parameters"` keys, quotes and separators.
* **Slot** — a model-driven value, restricted by a **matcher** to a
  function name, a number, an integer, a string, or a boolean.

A `SchemaGuide` walks this program **one character at a time** and can
answer two questions: *which characters may come next?* and *does this
candidate token keep us valid?* Decoding then works like this, per step:

1. Ask the SDK for the next-token logits given the tokens so far
   (`get_logits_from_input_ids`).
2. Using the vocabulary file (`get_path_to_vocab_file`), test candidate
   tokens: a token is **allowed** only if appending its decoded text keeps
   the guide on a valid path. All other tokens are effectively
   `-inf`.
3. Pick the highest-logit **allowed** token. The model chooses; the guide
   constrains.
4. Append the token and advance the guide; stop when the program is
   complete.

Decoding happens in **two stages**: first a guide that accepts only one of
the known function names (so the *function is selected by the model*),
then a guide built from that function's parameter schema (so each argument
is generated with its correct type). Because literals are fixed and every
value is type-constrained, the captured slot text converts directly into
typed Python values — no fragile post-hoc JSON parsing required.

Handling the real tokenizer's **byte-level BPE** is essential: vocabulary
tokens are stored in a byte-to-unicode alphabet (the classic GPT-2 table),
so `src/vocab.py` maps them back to real text before matching, and groups
tokens by first character so each step only tests a small relevant subset.

## Design decisions

* **The guide is the source of truth.** Validity never depends on the
  model or on prompt wording — it is enforced structurally. The prompt
  only nudges *accuracy*.
* **Character-level matching over candidate tokens** cleanly handles BPE
  merges (a token spanning a value and a separator is fine if the whole
  surface stays valid).
* **Two-stage decoding** keeps the parameter grammar dependent on the
  chosen function, which is only known after stage one.
* **pydantic** validates every function definition, prompt and result, so
  malformed schemas fail fast with clear messages.
* **A value-length cap** forces a slot to close cleanly if a (hypothetical)
  model never emits a terminator, guaranteeing termination.
* **A graceful fallback** yields a schema-valid default call if a single
  prompt cannot be decoded, so the output file is always complete.

## Performance analysis

* **Validity:** 100% by construction — proven by tests that feed
  unrelated (random) logits and still get valid, typed JSON.
* **Accuracy:** function and argument *correctness* depends on the real
  model; with the included mock it is intentionally random. The structure
  is always correct. (I could not benchmark real accuracy here because the
  official `llm_sdk`/Qwen weights were not available in my build
  environment — see the note above.)
* **Speed:** per step the decoder only tests tokens whose first character
  is currently allowed (the vocabulary is indexed by first character), and
  uses NumPy for the masked arg-max. For numbers/booleans/names only a few
  buckets are scanned; strings are short and bounded by the value cap. All
  example prompts process in well under the 5-minute budget.
* **Memory:** the vocabulary surfaces and the first-character index are
  built once and reused; paths are not recomputed per token beyond the
  small guide state.

## Challenges faced

* **Byte-level BPE.** Token strings are not raw text; getting the
  `bytes_to_unicode` inversion right (and skipping special tokens such as
  `<|im_end|>`) was necessary for correct masking.
* **Token/grammar misalignment.** Model tokens rarely line up with JSON
  tokens. Validating each candidate token *character by character* against
  the guide solved this without assuming any tokenisation.
* **Knowing when a value ends.** Numbers and strings have no fixed length;
  the "transition-out" rule (a value may end when it is complete and the
  next required literal character appears) plus a hard length cap make
  termination both natural and guaranteed.
* **Schema-dependent structure.** Parameters depend on the chosen
  function, which motivated the two-stage decode.

## Testing strategy

`tests/` (run with `uv run pytest`) covers:

* **Matchers and the guide** (`test_grammar.py`): numeric/integer/string/
  boolean prefix rules, name selection, and round-tripping a full
  parameters object back into captured values, including special
  characters.
* **Decoder and pipeline** (`test_pipeline.py`): with the mock SDK's
  *random* logits, every produced record is asserted to be valid JSON with
  exactly the right keys and the exact declared types — across numbers,
  integers, strings, booleans, an empty prompt, and a parameterless
  function. Error handling (missing file, invalid JSON, unknown type) is
  tested too.

The core guarantee — *validity independent of the model* — is exactly what
these tests demonstrate.

## Example usage

```bash
$ uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
wrote 7 function call(s) to data/output/function_calling_results.json
```

`data/output/function_calling_results.json` then contains one object per
prompt, each with exactly `prompt`, `name`, and `parameters`.

## Resources

* OpenAI/Qwen byte-level BPE and the `bytes_to_unicode` mapping (GPT-2
  tokenizer source; HuggingFace tokenizers documentation).
* Background on constrained / structured generation and finite-state
  guidance over a vocabulary (e.g. the ideas behind `outlines`, used here
  only as conceptual reference — the implementation is original and
  hand-written).
* `pydantic` v2 documentation; `mypy` and PEP 257 (docstrings); PEP 8 /
  `flake8`.

### How AI was used

An AI assistant was used as a design and drafting aid: to discuss the
overall architecture (guide / vocabulary / decoder / pipeline split), to
work through the byte-level-BPE and token-vs-grammar alignment problems, to
draft module code, docstrings and tests, and to build the mock SDK used
for local verification. Every design choice was reviewed and tested; in
particular the "validity under random logits" test suite was used to
confirm the constraint engine actually enforces the schema. In line with
the subject's AI guidance, this code is meant to be read, understood, and
defended line-by-line by the author before evaluation — and reworked where
that deepens understanding.
