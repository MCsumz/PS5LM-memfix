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

## 27 November 2026, afternoon: the title heap (#110) over a long chat, and as a fleet worker

`scripts/ps5lm-memtest.py`: about 1.5k tokens per turn up to 48.5k, the whole history sent again
every turn (as Open WebUI does), then 3 full reprocesses and their returns; `memory each` on, the
figures from the line after the trim. Posted on
[#110](https://github.com/cobanov/PS5LM/pull/110#issuecomment-7217615490).

| | PS5 Fat: Qwen3.5-9B Q4_K_M + Q8_0 mmproj, an image in every request, 64k q8_0 | PS5 Pro: Qwen 3.8 27B UD-Q2_K_XL, text only, 64k q4_0 |
|---|---|---|
| Build | main 5e96235 + #114 + #117 | main 5e96235 |
| Pool free: turn 1 → 48.5k → after the reprocesses | 3.74 → 3.48 → 3.43 GiB | 0.50 → 0.44 → 0.43 GiB |
| CPU heap in use: turn 1 → end | 647 → 682 MiB | 859 → 887 MiB |
| Largest free block at the end | 3,512 MiB | 442 MiB |
| Full 48k reprocess | 140 s | 419 s |

Every request was answered. On the Fat most of the 0.3 GiB the pool loses is outside the heap,
where `prealloc_x` grows with a quantized cache (memfix8's `0010`, not in memfix9).

**As a fleet worker** (the Fat with `PS5LM_WORKER_SCREEN=off`, a CPU llama-server on a Mac with all
layers of Qwen3.5-9B Q4_K_M on the worker, 64k q8_0; the same chat to 49k, then 3 reprocesses).
Posted on [#110](https://github.com/cobanov/PS5LM/pull/110#issuecomment-7220289341).

| | Turn 1 | Turn 42 (48k) | After 3 reprocesses |
|---|---|---|---|
| Pool free | 6.06 GiB | 5.86 GiB | 5.65 GiB |
| Worker heap mapped / in use | 52 / 40 MiB | 68 / 56 MiB | 78 / 56 MiB |
| Largest free block | 6,208 MiB | 6,000 MiB | 5,784 MiB |

A full 49k reprocess took 176 s over RPC. Worker mode in, out (`leave-worker`) and back to the
app went over FTP request files, with no one at the console.

## 27 November 2026, evening: MiniCPM-V 4.7 with #123

PS5 Pro, MiniCPM-V 4.7 1B Q4_K_M, `scripts/ps5lm-modeltest.py`: how much of an agent turn's prompt
the next message keeps. Posted on
[#123](https://github.com/cobanov/PS5LM/pull/123#issuecomment-7224335276).

| Client | main 5e96235 | main + #123 |
|---|---|---|
| sends the thinking back | 24 of 276 tokens (8.7 %) | 274 of 276 (99.3 %) |
| sends none (Open WebUI) | 269 of 269 (100 %) | 269 of 269 (100 %) |
