# Console tests of upstream PS5LM

Console checks of [cobanov/PS5LM](https://github.com/cobanov/PS5LM) `main` and its open pull
requests, run with the same method as [MODEL-TESTS.md](MODEL-TESTS.md) (`scripts/ps5lm-modeltest.py`
and an Open WebUI agent chat). Consoles: PS5 Fat (`<ps5-fat>`) and PS5 Pro (`<ps5-pro>`).

## 27 November 2026: main 5e96235, #114 and #117

Two builds side by side, each installed over FTP:

- **A, on the Fat:** `main` 5e96235 + [#114](https://github.com/cobanov/PS5LM/pull/114) (projector
  by width) + [#117](https://github.com/cobanov/PS5LM/pull/117) (only KV layers count for hybrids).
  #117's `suggested.hpp` was left at `main`'s, since its Inkling entry has no `revision` yet.
- **B, on the Pro:** `main` 5e96235, unreleased, with llama.cpp d2bceda3d (#103), the title heap
  (#110), the media marker (#112) and the 256 MiB flexible pool (#95).

| Check | Before (0.11.0 + memfix8) | Now | |
|---|---|---|---|
| **#117** Nemotron Nano 9B v2 Q4_K_M plan (Fat) | 64k, q4_0, 11.0 of 11.6 GiB | 64k, **q8_0, 7.6 of 11.8 GiB**; 4.79 GiB free when ready (7.4 used) | ✅ |
| Nemotron speed, prompt / gen tok/s | 323 / 34.7 | 379.5 / 40.0 | |
| **#114** Qwen 3.8 27B UD-Q2_K_XL (Fat, 9B projector in the folder) | 9B projector paired: does not fit | no projector: 64k, q4_0, 11.4 of 11.8 GiB | ✅ |
| **#114** Qwen 3.5 0.8B | 9B projector, planned with images | no projector: 64k, q8_0, 1.7 GiB | ✅ |
| **#114** Qwen 3.5 9B | own projector | own projector: 64k, q8_0, 8.6 GiB | ✅ |
| **#88** Qwen 3.8 27B template on main (Pro) | prefix 100 %, follow-up 269 tokens | the same; 10,830 tokens with `preserve_reasoning` off | ✅ |
| Qwen 3.8 27B Q2_K_XL (Pro) | 32k, q4_0; 153 / 28.4 tok/s | **64k**, q4_0, 0.79 GiB free when ready; 154.4 / 28.6 tok/s | ✅ |
| **Keep-alive** without a PS5LM patch (Pro) | needed memfix's patch | Open WebUI agent turn with 6 tool calls and two follow-ups, no disconnect | ✅ |
| **#112** media marker (Pro) | a tool reading `/props` broke the chat | the model read `/props` itself; the next plain message was answered | ✅ |

**Found on main:**
- With the app's **File tools** setting on (the default), llama-server refuses to start: the new
  llama.cpp rejects server tools on a network address without an API key. Reported as
  [#122](https://github.com/cobanov/PS5LM/issues/122). Workaround: File tools off.
- The keep-alive fix comes with the llama.cpp move (ggml-org/llama.cpp#30492), so
  [#113](https://github.com/cobanov/PS5LM/pull/113) now only adds a test for it.
- #117 and #116 meet in `suggested.hpp`: the Inkling entry needs a `revision` before #117
  compiles on `main`.
