## Results (model x task)

| tag | model | task | result | iterations | input tok | output tok | time (s) |
|---|---|---|---|---|---|---|---|
| baseline | gemini:gemini-3-flash-preview | pydata__xarray-4629 | FAIL | 0 | 0 | 0 | 190 |
| baseline | gemini:gemini-3-flash-preview | sympy__sympy-13480 | FAIL | 0 | 0 | 0 | 191 |
| baseline | gemini:gemini-3-flash-preview | sympy__sympy-14711 | FAIL | 21 | 116556 | 5707 | 473 |
| baseline | gemini:gemini-3.1-flash-lite | pydata__xarray-4629 | PASS | 9 | 38233 | 787 | 24 |
| baseline | gemini:gemini-3.1-flash-lite | sympy__sympy-13480 | PASS | 5 | 17550 | 3954 | 82 |
| baseline | gemini:gemini-3.1-flash-lite | sympy__sympy-14711 | PASS | 22 | 109916 | 6188 | 92 |
| baseline | groq:openai/gpt-oss-120b | pydata__xarray-4629 | PASS | 13 | 43138 | 2840 | 255 |
| baseline | groq:openai/gpt-oss-120b | sympy__sympy-13480 | PASS | 7 | 18581 | 678 | 59 |
| baseline | groq:openai/gpt-oss-120b | sympy__sympy-14711 | FAIL | 14 | 39509 | 10000 | 292 |
| baseline | groq:qwen/qwen3.8-27b | pydata__xarray-4629 | PASS | 13 | 44647 | 551 | 324 |
| baseline | groq:qwen/qwen3.8-27b | sympy__sympy-13480 | PASS | 6 | 19733 | 376 | 111 |
| baseline | groq:qwen/qwen3.8-27b | sympy__sympy-14711 | PASS | 8 | 27602 | 578 | 178 |
| baseline | openrouter:poolside/laguna-s-2.1:free | pydata__xarray-4629 | FAIL | 0 | 0 | 0 | 189 |
| baseline | openrouter:poolside/laguna-s-2.1:free | sympy__sympy-13480 | FAIL | 12 | 46118 | 4497 | 450 |
| baseline | openrouter:poolside/laguna-s-2.1:free | sympy__sympy-14711 | PASS | 27 | 160151 | 10000 | 638 |
| maxiter10 | groq:qwen/qwen3.8-27b | pydata__xarray-4629 | FAIL | 9 | 25284 | 289 | 285 |
| maxiter10 | groq:qwen/qwen3.8-27b | sympy__sympy-13480 | PASS | 6 | 19501 | 418 | 134 |
| maxiter10 | groq:qwen/qwen3.8-27b | sympy__sympy-14711 | PASS | 10 | 35924 | 894 | 250 |

## Provider reliability

| model | runs | solved | avg latency / request (ms) | retries | runs aborted by LLM errors |
|---|---|---|---|---|---|
| gemini:gemini-3-flash-preview | 3 | 0/3 | 4754 | 11 | 3 |
| gemini:gemini-3.1-flash-lite | 3 | 3/3 | 4622 | 0 | 0 |
| groq:openai/gpt-oss-120b | 3 | 2/3 | 1620 | 28 | 0 |
| groq:qwen/qwen3.8-27b | 6 | 5/6 | 551 | 42 | 1 |
| openrouter:poolside/laguna-s-2.1:free | 3 | 1/3 | 9758 | 46 | 2 |

## Intermediary metrics

| tag | model | task | first step touching a patched file | failures first decrease | tests first pass | iterations after first pass |
|---|---|---|---|---|---|---|
| baseline | gemini:gemini-3-flash-preview | pydata__xarray-4629 | - | - | - | - |
| baseline | gemini:gemini-3-flash-preview | sympy__sympy-13480 | - | - | - | - |
| baseline | gemini:gemini-3-flash-preview | sympy__sympy-14711 | - | - | - | - |
| baseline | gemini:gemini-3.1-flash-lite | pydata__xarray-4629 | 2 | - | 8 | 1 |
| baseline | gemini:gemini-3.1-flash-lite | sympy__sympy-13480 | 1 | - | - | - |
| baseline | gemini:gemini-3.1-flash-lite | sympy__sympy-14711 | 4 | - | 21 | 1 |
| baseline | groq:openai/gpt-oss-120b | pydata__xarray-4629 | 7 | - | 12 | 1 |
| baseline | groq:openai/gpt-oss-120b | sympy__sympy-13480 | 2 | - | 6 | 1 |
| baseline | groq:openai/gpt-oss-120b | sympy__sympy-14711 | - | - | - | - |
| baseline | groq:qwen/qwen3.8-27b | pydata__xarray-4629 | 1 | - | 12 | 1 |
| baseline | groq:qwen/qwen3.8-27b | sympy__sympy-13480 | 1 | - | 5 | 1 |
| baseline | groq:qwen/qwen3.8-27b | sympy__sympy-14711 | 1 | - | 7 | 1 |
| baseline | openrouter:poolside/laguna-s-2.1:free | pydata__xarray-4629 | - | - | - | - |
| baseline | openrouter:poolside/laguna-s-2.1:free | sympy__sympy-13480 | - | - | - | - |
| baseline | openrouter:poolside/laguna-s-2.1:free | sympy__sympy-14711 | 1 | - | - | - |
| maxiter10 | groq:qwen/qwen3.8-27b | pydata__xarray-4629 | - | - | - | - |
| maxiter10 | groq:qwen/qwen3.8-27b | sympy__sympy-13480 | 1 | - | 5 | 1 |
| maxiter10 | groq:qwen/qwen3.8-27b | sympy__sympy-14711 | 1 | - | - | - |
