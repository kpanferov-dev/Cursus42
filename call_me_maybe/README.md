*This project has been created as part of the 42 curriculum by kpanfero

# call me maybe

> Introduction to function calling in LLMs through **constrained decoding**.

---

## Description

`call_me_maybe` turns natural-language requests into structured
function calls by running a small open-source LLM (Qwen3-0.6B by
default) under **constrained decoding**. The model does not produce
JSON freely; it picks a function name from a fixed list and fills
typed parameters, while a deterministic state machine guarantees
that every emitted token keeps the output on a valid JSON path.

Given an input like

```
"What is the sum of 40 and 2?"
```

the program does **not** answer `42`. It emits

```json
{ "prompt": "...", "name": "fn_add_numbers", "parameters": {"a": 40.0, "b": 2.0} }
```

100% of the time, because the structure is enforced at the logit
level rather than hoped for at the prompt level.

---

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) for dependency management
- The `llm_sdk/` package (provided by 42) placed at the repository
  root, replacing the placeholder there.

### Install

```bash
uv sync
```

(equivalent: `make install`).

### Run with default paths

```bash
make run
```

This reads `data/input/functions_definition.json` and
`data/input/function_calling_tests.json`, runs the LLM under
constrained decoding, and writes
`data/output/function_calling_results.json`.

### Run with custom paths

```bash
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input  data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

### Other Make targets

| Target          | Purpose                                                         |
|-----------------|-----------------------------------------------------------------|
| `make install`  | `uv sync`                                                       |
| `make run`      | Run with default paths                                          |
| `make debug`    | Run under `pdb`                                                 |
| `make clean`    | Remove caches and the `data/output/` directory                  |
| `make lint`     | `flake8 .` + `mypy` with the mandatory flags                    |
| `make lint-strict` | `flake8 .` + `mypy --strict` (optional)                      |
| `make test`     | Run the `pytest` suite                                          |
| `make visualize`| Run with the token-by-token trace turned on (bonus)             |

---

## Algorithm explanation

The core idea: **the LLM never decides the JSON structure -- we do.**

We pre-build the target JSON as a sequence of three kinds of
*segments*:

| Segment    | What it represents                                            |
|------------|---------------------------------------------------------------|
| `Literal`  | A fixed string, e.g. `{"name": "` or `", "parameters": {`     |
| `Enum`     | One choice out of a finite list (e.g. the function name)      |
| `Value`    | A typed scalar (`number`, `integer`, `string`, `boolean`) or  |
|            | a nested `object` / `array` (bonus)                           |

At every generation step:

1. We ask the model for logits over the full vocabulary.
2. We ask the state machine which token ids would *keep* the current
   segment on a valid prefix. Tokens that span segment boundaries
   are allowed if every character is accepted in turn.
3. We mask every other token id to `-inf` in the logits.
4. We pick `argmax` over the survivors, append the token id to the
   context, and advance the state machine.

Once the model has finished emitting the function-name `Enum`, we
know exactly which function was selected, so the plan is **extended
dynamically** with the parameter pairs for that function:
`"a": <number>, "b": <number>}` etc. This makes the schema dependent
on a model decision while still being fully enforced.

### State-machine invariants

Two subtle properties make the machine robust:

1. **Tokens may span segment boundaries.** A token like `", "` may
   close one segment and start the next. We consume characters
   one at a time and roll the cursor forward as soon as the
   current segment is complete. See
   `ConstraintMachine._try_consume_char` in `src/constraints.py`.
2. **Enum choices are locked in late.** We only commit to a function
   name when no longer prefix is still reachable. This prevents
   prematurely committing to `fn_add` when `fn_add_numbers` is also
   a valid choice.

The state machine lives in `src/constraints.py`. The decoding loop
is in `src/generator.py`. Both depend only on `numpy` and the SDK's
public methods; no `transformers`, `outlines`, `dspy`, or private
SDK attributes are used.

### Why this works on a 0.6B model

Small models are unreliable at producing perfectly-shaped JSON from
prompting alone (~30% success rate, per the subject). By forcing
the *structure* via masking, the model only has to make local
decisions ("which function fits?" and "which number/string goes
here?"), which 0.6B parameters do well. Reliability of the
surrounding JSON is exactly 100% by construction.

---

## Design decisions

- **Pydantic everywhere.** Inputs and outputs are validated through
  Pydantic v2 models (`src/schemas.py`), so a malformed input file
  yields a clean error instead of a runtime crash.
- **Byte-level vocab decoding.** Qwen uses GPT-2-style byte<->unicode
  encoding (`Ġ` for space, `Ċ` for newline). `src/vocabulary.py`
  inverts that mapping so the constraint machine compares *real*
  strings, not surface forms.
- **Snapshot-and-restore matching.** `_token_matches` simulates
  consuming a candidate token against a deep-copied state, then
  restores. This is slightly more memory than a single-character
  matcher but correctly handles multi-character BPE tokens that
  cross segment boundaries.
- **Numpy-only masking.** Logits are converted to a numpy array, the
  mask is built once per step, and `argmax` runs on numpy. No
  `torch` imports in user code.
- **No private SDK attributes.** The project relies only on the
  three public methods named in the subject:
  `get_logits_from_input_ids`, `get_path_to_vocabulary_json`, and
  (for non-bonus paths) `encode`.
- **Late tail injection.** The parameter-body segments are appended
  to the plan only *after* the function-name enum has been locked
  in, so the schema can depend on which function the model picked.

---

## Performance analysis

- **Structural reliability: 100%.** By construction, the output is
  always a valid JSON object matching the requested schema.
- **Semantic accuracy:** depends on the model. With Qwen3-0.6B and
  the example prompts shipped in `data/input/`, function selection
  and argument extraction are correct on essentially every prompt.
  Failure modes are usually on ambiguous prompts (e.g. "calculate
  with 5"), not structural.
- **Speed:** dominated by the per-step forward pass of the model.
  Building the mask scans the vocabulary once per step (about
  150 000 token comparisons), which is negligible next to a
  transformer call. With the
  [`_AllowedCache`](src/generator.py) memoising allowed-id sets per
  segment state, sequential literal characters reuse the previous
  scan. All example prompts run end-to-end in well under five
  minutes on a CPU-only laptop.

---

## Challenges faced

1. **BPE byte decoding.** Without the byte-level inverse, half the
   vocabulary appeared to start with weird characters and never
   matched the JSON we wanted to produce. Implementing the inverse
   map (`vocabulary._byte_decoder`) was the largest single fix.
2. **Tokens spanning segment boundaries.** The token `", "` may end
   one segment and start the next. The state machine has to consume
   characters one at a time, possibly rolling over to the next
   segment mid-token. The `_try_consume_char` / `_token_matches`
   pair handles this.
3. **Premature enum lock-in.** Initially we committed to a function
   name as soon as `typed` matched any choice. But `fn_add` is a
   prefix of `fn_add_numbers`, so picking `fn_add` first would
   irreversibly cut off the longer choice. Fixed by requiring
   *no remaining choice extends `typed`* before locking in.
4. **Snapshot leakage.** `_token_matches` simulates token
   consumption by mutating segment state and restoring it
   afterwards. The first version forgot to restore the
   `chosen_function` field, which was set by `_lock_in_function`.
   This corrupted later allowed-token computations. Now the
   snapshot captures the full mutable state and `_restore` puts
   all of it back.
5. **Type coercion.** The schema declares `number`, but JSON has
   both ints and floats. After parsing, `_coerce_params` casts each
   value to the exact declared type so the output matches the
   schema regardless of how the model wrote the digits.

---

## Testing strategy

- **Unit tests** for the value DFAs (`number`, `integer`, `string`,
  `boolean`) — cover acceptance and rejection of edge cases
  (leading zeros, double dots, control characters).
- **Enum tests** verify lock-in timing: `fn_greet` commits after
  the word is fully typed, but `fn_add` does *not* commit when
  `fn_add_numbers` is still a valid choice.
- **End-to-end tests** with a stub model returning uniform logits —
  whatever the model "wants", the constraint mask alone must
  produce valid JSON that matches the schema.
- **Nested-object test** verifies bonus complex-argument support:
  a function with an `object` parameter (`{"name": ..., "age": ...}`)
  produces a properly nested JSON parameters body.
- **I/O tests** assert that every error path through the input
  loader raises a clean `InputError` and never a stack trace
  (missing file, malformed JSON, wrong top-level type, schema
  violation).
- **Tokenizer tests** for the bonus public BPE tokenizer:
  round-trip encoding/decoding, greedy longest-match preference,
  and error handling for unknown bytes.

Run the suite:

```bash
make test
```

All 30 tests pass; `mypy --strict` and `flake8` are also clean on
the `src/` package.

---

## Example usage

### Defaults

```bash
uv run python -m src
```

### Custom paths

```bash
uv run python -m src \
    --functions_definition my_functions.json \
    --input  my_prompts.json \
    --output my_results.json
```

### Visualization (bonus)

```bash
uv run python -m src --visualize
```

This prints a token-by-token trace showing, at every step, the
top-3 unmasked logits, which ones survived the constraint mask,
and which token was finally chosen. Useful for understanding why
the model never went off the rails.

### Different model (bonus)

```bash
uv run python -m src --model Qwen/Qwen3-1.7B
```

Any HuggingFace model id supported by `Small_LLM_Model` works; the
constraint machine is model-agnostic.

### Example output

For `"Greet shrek"`:

```json
{
  "prompt": "Greet shrek",
  "name": "fn_greet",
  "parameters": { "name": "shrek" }
}
```

---

## Bonus features

This section maps each bonus item from the subject (Chapter VII) to
the file that implements it. Every bonus is **working code**, not
just description.

| # | Bonus item                                              | Location                                          |
|---|---------------------------------------------------------|---------------------------------------------------|
| 1 | Support for multiple LLM models                         | `src/__main__.py` `--model` flag (model-agnostic) |
| 2 | Recoding the tokenizer (no SDK `encode`/`decode`)       | `src/tokenizer.py` — uses only the vocab JSON     |
| 3 | Advanced error recovery                                 | `generator._parse_rendered` + model-call try/except|
| 4 | Performance optimisations (caching)                     | `generator._AllowedCache` (per-state memoisation) |
| 5 | Comprehensive test suite                                | `tests/` — 30 tests                               |
| 6 | Visualization of the generation process                 | `src/visualizer.py` + `--visualize` flag          |
| 7 | Support for complex nested function arguments           | `schemas.ParamSpec.properties/items` + tests      |
| 8 | Public implementation of tokenizer `encode`/`decode`    | `src/tokenizer.py` — public API                   |
| 9 | Demonstration of how encoding integrates with decoding  | `generator.generate_call` uses both jointly       |

### Bonus 1 — Multiple models

The `--model` flag accepts any HuggingFace model id supported by
`Small_LLM_Model`. Nothing in the constraint machine is hard-coded
to Qwen3-0.6B; the vocabulary is loaded from
`get_path_to_vocabulary_json()` at runtime.

### Bonus 2 + 8 — Recoded tokenizer

`src/tokenizer.py` implements a byte-level BPE tokenizer using
**only** the SDK's `get_path_to_vocabulary_json()`. The SDK's own
`encode` / `decode` are never called. The algorithm:

1. Map each input byte to its byte-level surface character
   (`_byte_encoder`).
2. Walk the input left-to-right, picking the longest token whose
   surface prefixes the remaining input (greedy longest-match over
   a precomputed trie).

This produces token id sequences that round-trip cleanly through
the model. `decode` reverses the process: look up each id's stored
surface, run it through the byte<->unicode inverse, concatenate.

### Bonus 3 — Error recovery

- **JSON parse fallback.** If `json.loads(rendered)` ever fails
  (theoretically impossible under constrained decoding, but defence
  in depth), `_parse_rendered` tries again on the prefix up to the
  last `}}`. If that also fails, it returns a clean empty call.
- **Model-call resilience.** A wrapping `try/except` around
  `get_logits_from_input_ids` catches transient failures, logs
  them, and stops the loop cleanly with whatever has been produced
  so far.
- **Type-coercion fallback.** `_coerce_value` falls through to the
  raw value when type coercion fails (e.g. `int("3.5")`), instead
  of raising.

### Bonus 4 — Caching

`_AllowedCache` keys allowed-id sets by
`(cursor, segment_kind, segment_state)`. During the long stretch
of literal characters (`"name"`, `"parameters"`, etc.) the cache
hits every step but the first, saving an entire vocab scan.

### Bonus 5 — Tests

Five test modules in `tests/` cover value DFAs, enum lock-in, the
end-to-end machine (including the nested-object case), I/O error
handling, and the public tokenizer. Run with `make test`.

### Bonus 6 — Visualization

`--visualize` prints, for every generation step:

- the current segment kind (Literal / Enum / Value),
- how many tokens the mask allowed,
- the top-3 tokens by *raw* logit (what the model "wanted"),
- the top-3 tokens by *masked* logit (what it was allowed to do),
- the chosen token.

This makes the constrained-decoding mechanic *visible*: high-logit
"wrong" tokens are still visible in the raw column, but they
receive `-inf` in the masked column and never get picked.

### Bonus 7 — Nested arguments

`ParamSpec` carries optional `properties` (for `object` types) and
`items` (for `array` types). `_segments_for_value` recurses on
these, producing properly nested JSON. A test
(`test_nested_object_parameter`) verifies the round-trip.

### Bonus 9 — Encode/decode + constrained decoding integration

`generator.generate_call` uses the *public* tokenizer to encode
the prompt prefix, then drives constrained decoding token-by-token
against the model's logits. The flow is:

```
prompt (str)
   -> Tokenizer.encode (bonus)         -> ids[]
   -> Small_LLM_Model.get_logits...    -> logits
   -> ConstraintMachine.allowed_ids    -> mask
   -> argmax over masked logits        -> next_id
   -> ConstraintMachine.advance(...)
   ... (loop)
   -> machine.rendered()               -> json.loads -> FunctionCall
```

Nothing here uses the SDK's `encode` or `decode`; the bonus public
tokenizer is the only encode path.

---

## Resources

- HuggingFace tokenizers documentation (byte-level BPE):
  <https://huggingface.co/docs/tokenizers>
- Willard & Louf, *Efficient Guided Generation for Large Language
  Models*, 2023 — the canonical reference on finite-state-machine
  constrained decoding.
- Qwen3 model card: <https://huggingface.co/Qwen/Qwen3-0.6B>
- GPT-2 byte-level BPE explanation:
  <https://huggingface.co/learn/nlp-course/chapter6/5>

### AI usage

AI assistance (Claude) was used to brainstorm the segment-based
plan representation and to draft initial docstrings. Every line of
code was read, edited, and re-tested by the author. The constraint
machine, the byte-level vocabulary decoder, the type-coercion
logic, and the error-handling boundaries were rewritten from the
AI's first draft after manual testing showed edge cases that the
draft missed — notably:

- multi-character tokens crossing segment boundaries,
- the GPT-2-style `Ġ` prefix in vocabulary entries,
- premature lock-in of enum prefixes when a longer choice was
  still reachable,
- snapshot/restore not covering all mutable state.

The bonus tokenizer, visualizer, and nested-argument support were
designed and reviewed by hand.
