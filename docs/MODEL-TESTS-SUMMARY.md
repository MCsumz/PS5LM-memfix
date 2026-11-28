# Model tests: summary

Short version of [MODEL-TESTS.md](MODEL-TESTS.md). PS5LM v0.11.0-memfix8 on a PS5 Fat and a PS5 Pro
(same build), Open WebUI 0.13.3 with the Coding Sandbox VM and the Security Investigation Tools.
21 and 22 November 2026: 11 models, 12 runs.

| Model | Console | Vision | Context, cache | Prompt / gen tok/s | Chat reread after an agent turn? | Agent work in Open WebUI |
|---|---|---|---|---|---|---|
| Qwen 3.8 27B UD-Q2_K_XL | Pro | without | 32k, q4_0 | 153 / 28.4 | no (own switch) | **pass** |
| Qwen 3.8 27B UD-IQ2_XXS | Pro | without | 64k, q8_0 | 66 / 20.1 | no (own switch) | **pass** |
| Qwen 3.6 27B UD-IQ2_XXS | Pro | without | 64k, q4_0 | 78.3 / 23.1 | no (own switch) | **pass** |
| Bonsai 2 27B Q2_0 | Fat | without | 64k, q8_0 | 109 / 16.4 | no (own switch) | **pass** |
| Gemma 4 12B it IQ4_NL | Fat | with | 32k, q4_0 | 124.5 / 19.9 | no (own switch) | **pass** |
| Ornith 1.5 9B Q4_K_M | Pro | without | 64k, q8_0 | 305 / 42.4 | no (own switch) | **pass** |
| Granite 4.2 8B Q4_K_M | Pro | without | 64k, q4_0 | 200 / 22.9 | no (own switch) | **pass**, slow |
| Gemma 4 E4B it Q4_0 | Pro | with | 64k, q8_0 | 526 / 73 | no (own switch) | partial |
| Nemotron Nano 9B v2 Q4_K_M | Fat | without | 64k, q4_0 | 323 / 34.7 | no (consistent template) | partial |
| MiniCPM5 2B Q4_K_M | Fat | without | 64k, q8_0 | 481 / 116 | no (consistent template) | partial |
| MiniCPM-V 4.7 1B Q4_K_M | Pro | with | 64k, q8_0 | 5,200 / 237 | **yes, if the client sends thinking back** (not with Open WebUI) | fail |
| Qwen 3.5 0.8B Q4_K_M | Fat | without | 64k, q8_0 | 3,516 / 206 | no (`patches/0012`) | fail |
| Qwen 3.8 27B UD-Q2_K_XL | Fat | wrong one paired | does not fit in the app's plan | | | not run |
| Qwen 3.8 27B UD-Q2_K_XL | Pro | with its own | does not fit in the app's plan | | | not run |

- **The Qwen3.5 fix holds; nothing needed changing for Open WebUI.** No model reread its chat after
  an agent turn there (follow-ups read 116 to 208 new tokens). Without keeping earlier thinking,
  Qwen 3.8 and Qwen 3.6 reread the whole turn: 10,258 to 10,371 tokens.
- **One fix candidate: MiniCPM-V 4.7 1B.** Its template drops earlier thinking with no switch, as
  Qwen 3.5's did before `0012`: a client that sends thinking back keeps only 8.7 % of the prompt.
- **Issue #84:** MiniCPM5 and Nemotron do not reread their chat on PS5LM.
- **Partial / fail:** Gemma 4 E4B reached first for a broken Mac tool; Nemotron and MiniCPM5
  skipped or misused the security tools; MiniCPM-V 1B and Qwen 3.5 0.8B could not do the agent
  steps (questions to the user, Mac commands, tool loops).
- **Memory stayed level** on every run; tightest: Qwen 3.6 27B, 0.48 GiB free.
- **Found for upstream:** stale download checksums for files changed on Hugging Face (Qwen 3.8 27B,
  Gemma 4 E4B's vision module); vision modules paired by name only, so Qwen 3.x models get the
  Qwen 3.5 9B's; Bonsai 2 and Qwen 3.8 reject reasoning effort "high"; MiniCPM-V 4.7's template
  (above).
