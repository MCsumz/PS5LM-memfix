# Model tests

The same short test for every model, so models can be compared and the Qwen3.5 template fix
(`patches/0012`, upstream #88) can be judged per chat template. Consoles: PS5 Fat (`<ps5-fat>`)
and PS5 Pro (`<ps5-pro>`), both PS5LM v0.11.0-memfix8, the same `eboot.bin`; client: Open WebUI
0.13.3 on a Mac, with the Coding Sandbox VM and the Security Investigation Tools. Tested 21 and 22
November 2026: 11 models in 12 runs, 5 on the Fat and 7 on the Pro, 3 of them with a vision module.

## Summary

- **The Qwen3.5 fix holds, and no other model needed it with Open WebUI.** For every model the
  prompt after an agent turn continues the previous one for a client that sends no thinking back
  (98.8 to 100 %), and the follow-up read only what was new (116 to 208 tokens after a 10k-token
  turn). Qwen 3.5 gets this from `patches/0012`; Bonsai 2, Qwen 3.8, Qwen 3.6, Ornith 1.5 and
  Granite 4.2 from their templates' own `preserve_thinking`, which llama.cpp turns on by default;
  Gemma 4 keeps thinking on tool calls only; MiniCPM5 and Nemotron render a turn the same wherever
  it is.
- **One template behaves like Qwen 3.5 before the fix: MiniCPM-V 4.7 1B.** It drops earlier
  thinking and has no switch, so for a client that sends the thinking back only 8.7 % of an agent
  turn's prompt is kept and the turn is read again on every new message. With Open WebUI (no
  thinking sent back) it keeps 100 %. It is the one candidate for the same change as `0012`.
- **Keeping thinking matters.** With `preserve_reasoning` off, the same follow-up read the whole
  turn again: 10,371 tokens (Qwen 3.8 Q2_K_XL), 10,335 (Qwen 3.8 IQ2_XXS), 10,258 (Qwen 3.6).
- **Issue #84 (MiniCPM5, Nemotron reprocessing): not caused by PS5LM.** Both keep their prefix; the
  cause must be on the client side or another request taking the one slot.
- **Agent work in Open WebUI** (VM, security tools, LAN tools):
  - pass: Qwen 3.8 27B (both quants, Pro), Qwen 3.6 27B (Pro), Bonsai 2 27B (Fat), Gemma 4 12B
    (Fat, with vision), Ornith 1.5 9B (Pro), Granite 4.2 8B (Pro, slow);
  - partial: Gemma 4 E4B (Pro, with vision), Nemotron Nano 9B v2, MiniCPM5 2B (Fat);
  - fail: MiniCPM-V 4.7 1B (Pro, with vision), Qwen 3.5 0.8B (Fat).

  Gemma 4 (both), Qwen 3.8, Qwen 3.6 and Ornith started the security tools on their own; the others
  only checked their status until told.
- **Empty visible replies** were the models' own: Qwen 3.5 0.8B (3 of 6) and Ornith (1 of 6) gave
  them with a prompt that was the same either way. Gemma 4 12B and Qwen 3.6 also ran into the test's
  token limit while thinking; those are counted apart as cut off.
- **A stray `</think>`** showed in the visible text of MiniCPM-V 4.7 1B and, once, Qwen 3.6 27B,
  after a tool call. Not looked into.
- **Speed** (prompt / generation, tok/s):

  | Fat | | Pro | |
  |---|---|---|---|
  | Qwen 3.5 0.8B | 3,516 / 206 | MiniCPM-V 4.7 1B | 5,200 / 237 |
  | MiniCPM5 2B | 481 / 116 | Gemma 4 E4B | 526 / 73 |
  | Nemotron Nano 9B v2 | 323 / 34.7 | Ornith 1.5 9B | 305 / 42.4 |
  | Gemma 4 12B | 124.5 / 19.9 | Granite 4.2 8B | 200 / 22.9 |
  | Bonsai 2 27B | 109 / 16.4 | Qwen 3.8 27B Q2_K_XL | 153 / 28.4 |
  | | | Qwen 3.6 27B IQ2_XXS | 78.3 / 23.1 |
  | | | Qwen 3.8 27B IQ2_XXS | 66 / 20.1 |

  The IQ2_XXS quants are smaller but slower than Q2_K_XL on this GPU.
- **Memory stayed level** in every run (pool free within 0.4 GiB of the value when ready); the
  tightest was Qwen 3.6 27B at 64k with a q4_0 cache, 0.48 GiB free after the test.
- **Found for upstream:**
  1. Suggested downloads whose file changed on Hugging Face fail their checksum: `suggested.hpp`
     pins each file's size and sha256 but the app downloads `resolve/main`. Qwen 3.8 27B: unsloth
     replaced the file on 11 November (9,948,666,784 bytes, pinned 9,828,981,664). Gemma 4 E4B's
     vision module is now 559,874,848 bytes, pinned 559,874,816. Pinning the revision in the URL
     would keep the pinned file downloadable.
  2. Vision modules are paired by name only (`find_mmproj`): `Qwen3.5-9B.mmproj` is paired with
     Qwen 3.8 27B and Qwen 3.5 0.8B, whose width does not match, and makes Qwen 3.8 not fit on the
     Fat. Checking `projection_dim` against `embedding_length` would avoid it.
  3. Bonsai 2 and Qwen 3.8 templates reject `reasoning_effort` "high" (they take xhigh, medium,
     low); a client sending "high" fails every request.
  4. MiniCPM-V 4.7 1B's template rereads agent turns for clients that send thinking back (above).
- **Qwen 3.8 27B** (11 November file) fits text only: 32k with a q4_0 cache (Q2_K_XL) or 64k with
  a q8_0 cache (IQ2_XXS) on the Pro. The Fat has the same 12 GiB pool and build, so both should fit
  there too once the wrong projector is not paired (not tried). With its own vision module the
  app's plan does not fit it, even on the Pro (screen on, the planner choosing the context). It can
  run outside that plan: in [cobanov/PS5LM#75](https://github.com/cobanov/PS5LM/issues/75) it serves full-size photos with the F16 projector at a 2k context
  set by hand, screen off, with heap and warm-up fixes.

## Method

1. **Load** the model from the library. `app.log` gives the plan (context, cache), the load time
   and `memory when ready`.
2. **Direct** (`scripts/ps5lm-modeltest.py <console>`, about 5 to 10 minutes for a 27B):
   - *template*: renders a turn and the next user message with `/apply-template` and reports whether
     earlier thinking is kept, whether a turn without thinking gets an empty thinking block, and how
     much of an agent turn's last prompt is a prefix of the next message's prompt, for a client that
     sends the thinking back and for one that does not (Open WebUI without a provider). Below 100 %,
     the rest of the turn is read again on every new message.
   - *live*: one agent turn with a `read_file` tool, sent as Open WebUI sends it, then the same
     follow-up three times, then three times more with `preserve_reasoning` off: tokens processed,
     whether the visible reply is empty (the model answering only inside its thinking), and whether
     it was cut off by the 4,000-token limit.
   - *speed*: prompt and generation speed for a fixed 1,500-word prompt (3,276 tokens with Qwen's
     tokenizer, up to 3,599 with others) and 256 generated (issue #6).

   Results: `build/model-tests/<model>.json` (Fat) and `build/model-tests/pro/<model>.json` (Pro).
3. **Open WebUI**: a profile `PS5LM/<model>` copied from `PS5LM/Qwen3.5-9B` (same tools, system
   prompt, 64k context, compaction at 48k, native tool calls; images off). The Pro has its own
   connection (`http://<ps5-pro>:8081/v1`, same settings as the Fat's). One chat with the Coding
   Sandbox selected: a script created and run in the VM, the security tools' status, a LAN check and
   a LAN page read; then follow-ups: start the security tools and run `network.audit_service`, stop
   them, and a plain question. Each step's tokens come from `/metrics`.

Pass: the plan fits, the prefix is kept (or the model's own switch keeps it), no empty visible
replies, follow-ups read only what is new, tools are used correctly, memory stays level.

Read the answers from the stored chat (`/api/v1/chats/<id>`), not from the page: the page can lag
behind the end of a reply, and read early it shows a cut-off answer. `recall_memories` and
`list_available_skills` appear in every reply because Open WebUI's memory and skills features call
them; they do not count as the model using tools.

Open WebUI's approval prompts (Mac commands, LAN pages, stopping the security tools) expire after
a short time, and an expired prompt counts as a denial. Where that happened it is noted; the models
either asked again or said so.

## Results

| Model | Console | Vision | Plan | Load | Prompt / gen tok/s | Template | Empty replies | Open WebUI |
|---|---|---|---|---|---|---|---|---|
| Bonsai 2 27B Q2_0 | Fat | without | 64k, q8_0, 10.5 of 11.6 GiB | 103 s | 109 / 16.4 | own switch; prefix 100 % both clients; empty blocks rendered | 0 of 3 | pass |
| Qwen 3.5 0.8B Q4_K_M | Fat | without (a wrong one was planned, see Qwen 3.8) | 64k, q8_0, 3.1 of 11.6 GiB | 36 s | 3,516 / 206 | patches/0012; prefix 100 % / 99.2 %; no empty blocks | 3 of 6 (model's own) | fail: tool loops |
| MiniCPM5 2B Q4_K_M | Fat | without | 64k, q8_0, 3.7 of 11.6 GiB | 47 s | 481 / 116 | consistent by itself; prefix 100 % both clients; empty blocks rendered | 0 of 6 | partial: first turn passes, then fails |
| Nemotron Nano 9B v2 Q4_K_M | Fat | without | 64k, q4_0, 11.0 of 11.6 GiB planned | 72 s | 323 / 34.7 | strips thinking always; prefix 98.9 % both clients | 0 of 6 | partial: avoids the security tools |
| Gemma 4 12B it IQ4_NL | Fat | **with** (`mmproj-gemma-4-12B-it-f16`) | 32k, q4_0, images: 10.0 of 11.6 GiB | 83 s | 124.5 / 19.9 | own switch (tool calls only); prefix 98.9 % both clients; no empty blocks | 0 of 6 (3 cut off by the test's limit while thinking) | pass |
| Qwen 3.8 27B UD-Q2_K_XL (11 Nov file) | Fat | wrongly paired with the 9B's | does not fit in the app's plan | | | own switch (as Bonsai) | | not run |
| Qwen 3.8 27B UD-Q2_K_XL (11 Nov file) | **Pro** | without | 32k, q4_0, 11.0 of 11.6 GiB | 109 s | 153 / 28.4 | own switch; prefix 100 % both clients; empty blocks rendered | 0 of 6 | pass |
| Qwen 3.8 27B UD-Q2_K_XL (11 Nov file) | **Pro** | **with** its own (`mmproj-F16`, 0.93 GB) | does not fit in the app's plan | | | | | not run |
| Qwen 3.8 27B UD-IQ2_XXS | **Pro** | without | 64k, q8_0, 10.1 of 11.6 GiB | 81 s | 66 / 20.1 | own switch; prefix 100 % both clients; empty blocks rendered | 0 of 6 | pass |
| Qwen 3.6 27B UD-IQ2_XXS | **Pro** | without | 64k, q4_0, 11.2 of 11.6 GiB | 103 s | 78.3 / 23.1 | own switch; prefix 100 % both clients; empty blocks rendered | 0 of 6 (2 cut off by the test's limit while thinking) | pass |
| Ornith 1.5 9B Q4_K_M | **Pro** | without | 64k, q8_0, 7.5 of 11.6 GiB | 63 s | 305 / 42.4 | own switch; prefix 100 % both clients; empty blocks rendered | 1 of 6 (model's own) | pass |
| Granite 4.2 8B Q4_K_M | **Pro** | without | 64k, q4_0, 8.8 of 11.6 GiB | 59 s | 200 / 22.9 | own switch; prefix 100 % / 99.6 %; empty blocks rendered | 0 of 6 | pass, slow |
| Gemma 4 E4B it Q4_0 | **Pro** | **with** (`mmproj-gemma-4-E4B-it-Q8_0`) | 64k, q8_0, images: 7.7 of 11.6 GiB | 75 s | 526 / 73 | tool calls only, as the 12B; prefix 98.9 % / 98.8 %; no empty blocks | 0 of 6 | partial: wrong tool first |
| MiniCPM-V 4.7 1B Q4_K_M | **Pro** | **with** (`mmproj-MiniCPM-V-4_7-1B-f16`) | 64k, q8_0, images: 3.7 of 11.6 GiB | 21 s | 5,200 / 237 | **drops earlier thinking, no switch; prefix 8.7 % if thinking is sent back**, 100 % if not; empty blocks rendered | 0 of 6 | fail |

"Both clients": one that sends the thinking back and one that does not (Open WebUI). Where two
values are given, they are in that order.

### Bonsai 2 27B (Q2_0, PrismML; Qwen 3.8 27B in ternary weights) · Fat · without vision

First run on a console (`suggested.hpp`: "Not yet run on the console").

- Memory: 1.46 GiB free when ready, 1.01 GiB after the tests; CPU heap 0.68 to 0.90 GiB.
- Template: honours `preserve_thinking` itself (no patch needed). It renders an empty thinking
  block for an earlier turn without thinking, the condition that made Qwen3.5 leave its replies
  empty on memfix6; Bonsai's replies stayed visible (0 of 3 direct, 0 of 4 in Open WebUI).
- Direct: the follow-up after a 10k-token agent turn processed 159 tokens.
- Open WebUI: the agent turn (VM script, LAN check, `/health`) was correct. The first follow-up
  processed 134 tokens, started the security tools, ran `network.audit_service` on port 8081,
  identified llama.cpp from the `Server` header, explained Nmap's port-number guess, and stopped the
  tools. Later follow-ups processed 1.4k to 1.5k tokens of about 22k.
- **Profile setting:** Bonsai's template accepts `reasoning_effort` xhigh (its default), medium or
  low; Open WebUI's `high`, copied from the Qwen3.5 profile, failed every request with a Jinja
  exception. The profile uses xhigh. Qwen 3.8 27B's template has the same check.
- Thinking is long: 1k to 2k tokens per answer, about 2 minutes at 16 tok/s.

### Qwen 3.5 0.8B (Q4_K_M, unsloth) · Fat · without vision

- Memory: 8.02 GiB free when ready, 7.84 GiB after; load 36 s; no vision module was loaded
  although the plan line says "images".
- Template: the same as Qwen 3.5 9B; `patches/0012` applies. The follow-up after a 10k-token agent
  turn processed 123 tokens.
- Empty visible replies: 2 of 3, then 1 of 3 on a rerun, 0 of 3 with `preserve_reasoning` off. The
  off runs read 4 tokens each: with a client that sends no thinking back the prompt is the same
  either way, so the empty replies are the model's own, not the patch's.
- Open WebUI: fail. It created `check.py`, then asked twice to stop the Coding Sandbox (denied)
  while saying it would start it, made about 20 tool calls, never reached the security tools or the
  LAN reader, and wrote no summary. A plain follow-up ("without using any tools") looped again
  through 13 commands and an ask-user prompt; it was cancelled. Too small for agent work; fine for
  short plain answers at 206 tok/s.

### MiniCPM5 2B (Q4_K_M, openbmb; one of the models in issue #84) · Fat · without vision

- Memory: 8.55 GiB free when ready, 8.47 GiB after; load 47 s.
- Template: renders an assistant turn the same wherever it is (with its thinking, or an empty
  block), so the prompt stays a prefix for both kinds of client without a patch. The follow-up after
  the direct agent turn processed 126 tokens; in Open WebUI a follow-up processed 1.5k of 59k.
  **For #84: PS5LM does not make MiniCPM5 read its chat again.** Reprocessing the reporter sees must
  come from elsewhere (a client that changes earlier text, or another request taking the one slot).
- Open WebUI: the agent turn passed in one round of parallel calls with a correct summary. The
  security-tools follow-up failed: 14,474 tokens of thinking over 7 minutes, the controller started
  twice, no scan, no stop, no visible answer (the controller was switched off by hand afterwards). A
  plain "without tools" question used `read_file` and `run_command` anyway; its answer was correct.

### Nemotron Nano 9B v2 (Q4_K_M, bartowski; one of the models in issue #84) · Fat · without vision

- Memory: the plan counts 11.0 of 11.6 GiB with a q4_0 cache, but 4.88 GiB were free when ready
  and 4.57 GiB after: a hybrid Mamba model keeps far less per token than the planner assumes.
  Load 72 s (server start to ready).
- Template: drops the thinking from every assistant turn, so only the turn's last message differs
  (98.9 % kept for both kinds of client). The follow-up after the direct agent turn (3 tool calls)
  processed 187 tokens; in Open WebUI a plain follow-up processed 1.4k of 18k. **For #84: PS5LM does
  not make Nemotron read its chat again either.**
- Open WebUI: the VM step was correct; it then stopped because the security tools were off and
  said, wrongly, that the LAN reader needed them. Asked to start them, it started the controller but
  checked the port with the Mac's LAN diagnostics instead of the scan, read `/health`, and did not
  stop the tools (switched off by hand afterwards). Its visible answers were correct, and a plain
  follow-up used no tools.

### Gemma 4 12B (it, IQ4_NL) · Fat · with vision (`mmproj-gemma-4-12B-it-f16.gguf`)

- Plan: 32k context with a q4_0 cache, images, video and audio; 2.65 GiB free when ready, 2.46 GiB
  after; load 83 s. The Open WebUI profile was aligned with the Qwen3.5-9B one for this test (it had
  compaction at 5,000, no tools and another system prompt); the old settings are saved in
  `build/model-tests/gemma-profile-backup.json`.
- Template: Gemma's own `preserve_thinking` keeps thinking only on tool-call messages; a turn renders
  the same before and after the next message except its last reply (98.9 % kept). No empty blocks.
  The follow-up after the direct agent turn (3 tool calls) processed 119 tokens.
- It thinks long: 3 of 6 direct follow-ups reached the test's 1,500-token limit while thinking
  (about 6,000 characters) and so had no visible text; the test now raises the limit to 4,000 and
  records replies cut off by it separately. Open WebUI's profile allows 13,312 tokens.
- Open WebUI: pass. It started the security tools without being told and ran
  `network.check_tcp_services` in the agent turn, then `network.audit_service` on request
  (llama.cpp identified) and stopped them. It repeated Nmap's port-number guess ("blackice-icecap")
  once as the service. Follow-ups processed 1.3k to 2.5k tokens.

### Qwen 3.8 27B UD-Q2_K_XL (unsloth, 11 November file)

**Fat: not run.** The app pairs a vision module with a model by the longest common start of their
names (at least five letters, `find_mmproj` in `ps5/app/model_plan.cpp`), so
`Qwen3.8-27B-UD-Q2_K_XL.gguf` gets `Qwen3.5-9B.mmproj-Q8_0.gguf` ("qwen3"). That projector cannot
work with it (it outputs 4,096 values; Qwen 3.8 27B is 5,120 wide), and counting it makes the plan
"needs 11.6 GiB with a 4k context". Qwen 3.5 0.8B is paired the same way ("images" in its plan) and
ran without images. A check that the projector's `clip.vision.projection_dim` equals the model's
`embedding_length` would avoid both.

**Pro, without vision: pass.**

- Plan: 32k context with a q4_0 cache, 11.0 of 11.6 GiB; 1.19 GiB free when ready, 0.86 GiB
  after; load 109 s.
- Speed: 153 / 28.4 tok/s, nearly twice Bonsai 2 27B on the Fat (109 / 16.4) for a model of the
  same size.
- Template: its own switch, earlier thinking kept, empty blocks rendered, prefix 100 % for both
  kinds of client. The follow-up after the direct agent turn (3 tool calls) processed 208 tokens;
  **with `preserve_reasoning` off the same follow-up processed 10,371 tokens**, the whole turn again.
  0 empty replies of 6.
- Open WebUI: the agent turn ran the VM script, started the security tools itself, ran
  `network.audit_service`, read its report and `/health`, and summed up correctly (16.7k tokens
  processed, 132k from cache). The follow-up named llama.cpp from the `Server` header, said no
  version is exposed, and stopped the tools; a plain follow-up answered without tools. Follow-ups
  processed 1.4k to 1.6k tokens.

**Pro, with its own vision module: does not fit in the app's plan** (screen on, the planner choosing
the context; [cobanov/PS5LM#75](https://github.com/cobanov/PS5LM/issues/75) runs it by hand at 2k with the screen off). unsloth's `mmproj-F16.gguf` (0.93 GB,
`projection_dim` 5,120, renamed `Qwen3.8-27B.mmproj-F16.gguf` to be paired).

### Qwen 3.8 27B UD-IQ2_XXS (unsloth) · Pro · without vision

- Plan: 64k context with a q8_0 cache, 10.1 of 11.6 GiB: the smaller quant buys twice the context
  and the better cache. 1.86 GiB free when ready, 1.49 GiB after Open WebUI; load 81 s.
- Speed: 66 / 20.1 tok/s, slower than the Q2_K_XL (153 / 28.4): IQ quants decode more slowly.
- Template: the same as the Q2_K_XL. Follow-up 172 tokens; with `preserve_reasoning` off 10,335.
  0 empty replies of 6.
- Open WebUI (`reasoning_effort` xhigh, as Bonsai): pass. VM script, started the security tools
  itself, `network.audit_service` found llama.cpp. Its two `/health` approvals expired before they
  were answered; it said so and used the audit as evidence. Asked to retry, it read
  `{"status":"ok"}`. Agent turn 16.8k processed (162k from cache, 6.2k generated); follow-ups 1.8k
  and 1.3k.

### Qwen 3.6 27B UD-IQ2_XXS (unsloth) · Pro · without vision

- Plan: 64k context with a q4_0 cache, 11.2 of 11.6 GiB, the fullest plan of the tests. 0.83 GiB
  free when ready, 0.48 GiB after; load 103 s.
- Speed: 78.3 / 23.1 tok/s.
- Template: its own switch, prefix 100 % for both kinds of client. Follow-up 149 tokens; with
  `preserve_reasoning` off 10,258. No empty replies; 2 of 6 follow-ups ran into the 4,000-token
  limit while still thinking.
- Open WebUI: pass. The agent turn ran the VM script, started the security tools itself, did the
  LAN check, read `/health` and summed up correctly (15.6k processed, 86k from cache). The audit
  follow-up identified llama.cpp and stopped the tools (2.9k processed, 395 generated); a stray
  `</think>` showed in its visible text after the tool call. The plain follow-up answered correctly
  without tools (1.3k processed).

### Ornith 1.5 9B (Q4_K_M) · Pro · without vision

- Plan: 64k context with a q8_0 cache, 7.5 of 11.6 GiB; 4.73 GiB free when ready, 4.59 GiB after;
  load 63 s.
- Speed: 305 / 42.4 tok/s.
- Template: Qwen 3.5 architecture with its own switch; prefix 100 % for both kinds of client.
  Follow-up 169 tokens. 1 of 6 replies empty, on a prompt that was the same as the visible ones
  (4 tokens read): the model's own.
- Open WebUI: pass, the strongest of the small models. In the agent turn it started the security
  tools itself, ran a scan and read the report, read `/health`, and called Nmap's
  "blackice-icecap" a port-number guess rather than the service. The audit follow-up named
  llama.cpp from the `Server` header and stopped the tools. Agent turn 17.9k processed;
  follow-ups 3.2k and 1.4k. (The first attempt failed before the model ran: the Coding Sandbox VM
  was off.)

### Granite 4.2 8B (Q4_K_M) · Pro · without vision

- Plan: 64k context with a q4_0 cache, 8.8 of 11.6 GiB; 3.48 GiB free when ready and after;
  load 59 s; the smallest CPU heap of the tests (0.14 to 0.18 GiB).
- Speed: 200 / 22.9 tok/s: slow generation for its size.
- Template: its own switch; prefix 100 % / 99.6 %. Follow-up 189 tokens. 0 empty replies of 6.
- Open WebUI: pass, but slow. The agent turn (VM script, security tools' status only, LAN check,
  `/health`, summary) was correct. The audit follow-up took about 8 minutes and 7.5k generated
  tokens; two approval prompts expired before they were answered and it asked again; it named
  llama.cpp, said no version is exposed, and stopped the tools. The plain follow-up was correct.

### Gemma 4 E4B (it, Q4_0) · Pro · with vision (`mmproj-gemma-4-E4B-it-Q8_0.gguf`)

- Plan: 64k context with a q8_0 cache, images, video and audio, 7.7 of 11.6 GiB; 3.43 GiB free
  when ready, 3.31 GiB after; load 75 s.
- Speed: 526 / 73 tok/s.
- Template: as the 12B, thinking kept on tool-call messages only; prefix 98.9 % / 98.8 %. Follow-up
  116 tokens. 0 empty replies of 6.
- Open WebUI: partial. It first tried to write `check.py` with the Mac project-files tool, which
  failed (that tool's configured folder no longer exists on the Mac; nothing was written), then ran
  it in the sandbox. It started the security tools itself, checked the port with the Mac's LAN
  diagnostics, read `/health` and summed up correctly. The audit follow-up identified llama.cpp and
  stopped the tools; the plain follow-up was correct.

### MiniCPM-V 4.7 1B (Q4_K_M, openbmb) · Pro · with vision (`mmproj-MiniCPM-V-4_7-1B-f16.gguf`)

- Plan: 64k context with a q8_0 cache, images and video, 3.7 of 11.6 GiB; 6.80 GiB free when ready,
  6.64 GiB after; load 21 s.
- Speed: 5,200 / 237 tok/s, the fastest of the tests.
- **Template: the one that behaves like Qwen 3.5 before `0012`.** The model is built on the Qwen 3.5
  architecture (`qwen35` in its plan) but ships its own template, which drops thinking from every
  earlier assistant turn and has no `preserve_thinking` switch. For a client that sends the thinking
  back, an agent turn's last prompt carries the thinking on its tool call, and the next message's
  prompt drops it: only 24 of 276 tokens (8.7 %) stay a prefix, so the whole agent turn is read
  again on every new message. For a client that sends no thinking back (Open WebUI) it keeps 100 %,
  and the direct follow-ups read 32 and 4 tokens. The same change as `patches/0012` would fix it
  for the other clients.
- Open WebUI: fail. In the agent turn it asked to run `sw_vers` on the Mac (denied), then asked five
  times through ask-user whether it was in the sandbox, and did no step. After a nudge it ran five
  more Mac commands (refused by that tool), asked again, did a LAN check and read `/health`, asked
  for a LAN check of a host named "ps5lm-modeltest" (denied), leaked `</think>` into the visible
  text, and wrote a contradictory summary; the script was never run. Too small for agent work.

## Found while preparing

- **Qwen 3.8 27B's file changed.** unsloth replaced `Qwen3.8-27B-UD-Q2_K_XL.gguf` on 11 November
  (UD3.1): 9,948,666,784 bytes instead of 9,828,981,664. PS5LM's Suggested entry pins the old
  file's sha256 but downloads `resolve/main`, so a download from the app now fails its checksum.
  The old file is still at revision `43f522df59109a037f64f1e29ab1eff5c00e8e1e`. The "needs 11.6 GiB
  with a 4k context" on the Fat came from the wrongly paired projector, not from the new file: on
  the Pro, without a projector, it fits at 32k.
- Templates of the models in issue #84 (MiniCPM5 2B, Nemotron Nano 9B v2) render a turn the same
  before and after the next user message; reprocessing there has another cause.

## Test setup notes (not PS5LM)

- The Mac project-files tool in Open WebUI is configured for a folder that was renamed, so every
  write through it fails (seen with Gemma 4 E4B).
- The Coding Sandbox VM and the Security Investigation Tools have to be running; the tools switch
  themselves off after 15 minutes idle, and the sandbox was found off twice during the tests.
- Open WebUI's approval prompts expire after a short time and count as denied (Granite 4.2,
  Qwen 3.8 IQ2_XXS).
- The Gemma 4 12B profile was changed for the test; its old settings are in
  `build/model-tests/gemma-profile-backup.json`.
