# AGENTS.md — WhisperJAV Team Charter

> Entry point for AI coding agents (Claude Code and any AGENTS.md-aware tool).
> This is the **operating model**. The detailed behavioral rules live in `CLAUDE.md`
> (call-chain verification, user-instruction supremacy, issue-handling discipline) and
> are **not superseded** — this file references them, it does not replace them.
>
> Verified 2026-10-18 in this workspace: `CLAUDE.md`, `memory/` and `.claude/agents/`
> are **not present here** (they live on the owner's machine). Rules stated in this file
> are self-sufficient; treat the missing ones as "unavailable", not as "unfollowed".

---

## 1. The operating model (read this first)

WhisperJAV is maintained by a **single orchestrator** (the main Claude Code session,
working with the owner) that dispatches **ephemeral, task-scoped subagents**. There are
**no standing per-module agents** — this is a deliberate, evidence-based choice (mid-2026
consensus: persistent module-owner fleets cost ~15× tokens, drift out of sync, and
underperform a strong orchestrator + good context for a solo-maintained mature codebase).

**Where expertise lives:** not in agents, but in **files** —
- per-area dossiers (`<dir>/AGENTS.md`, loaded only when that subtree is touched),
- the cross-area interface contracts (`docs/architecture/MODULE_CONTRACTS.md`),
- volatile "what I did / what's next" ledgers (`memory/`).

An agent does not *remember*; it **re-reads its dossier**. Dossiers therefore store
**decisions, rationale, contracts, and gotchas** — the things not recoverable from the
code — and **point to tests/code** for mechanics. Do not duplicate code into a dossier.

**Escalation rule (the coordination mechanism):** a task-scoped agent works **within its
area's scope**. If a task requires **changing a shared interface** documented in
`MODULE_CONTRACTS.md`, the agent **STOPS and escalates to the orchestrator** — it does not
unilaterally change a contract. The orchestrator coordinates the affected areas.

---

## 2. Build / test / run (verified commands)

**Dev environment is the project-root uv-managed `.venv`** (Python 3.12, uv; WhisperJAV
1.9.5 + torch cu128 pre-installed). This machine has **no conda** — the `WJ` conda env
recorded in earlier docs was the owner's setup and is equivalent in purpose. Activate the
uv venv first; run all commands inside it.

```powershell
cd E:\code\AI\WhisperJAV
.\.venv\Scripts\activate      # equivalently: uv run <cmd> (see the warning below)

# Full (re)install of the env — fresh machine / after dependency changes
uv sync --python 3.12 --extra all
#   or the project's own installer (auto-detects GPU and picks the PyTorch index):
uv run --no-project --python 3.12 python install.py   # flags: --dev / --minimal / --cpu-only

# Reinstall the package itself after code edits (leaves dependencies untouched)
uv pip install -e . --no-deps

# Tests
python scripts/run_tests.py                  # all, one file per process
python scripts/run_tests.py --fast           # all but the slow, model-loading files
python -m pytest tests/test_config_v4.py     # one file

# Lint / format  (ruff is NOT installed in .venv — run it through uvx, which fetches on demand)
uvx ruff check whisperjav/
uvx ruff format whisperjav/

# Inspect resolved config WITHOUT running ASR (the safe config probe)
python -m whisperjav.main --dump-params nul --mode balanced --sensitivity aggressive

# CLI-flag completeness gate (MANDATORY for any new main.py flag)
python -m whisperjav.main --help | grep <flag>
```

> Prefer the activated `.venv` over bare `uv run` in day-to-day work: exact syncing without
> extras can drop packages installed via the `all` extra. And use `--no-project` when running
> `install.py`, otherwise `uv run` pre-syncs dependencies before the installer does.

---

## 3. Architecture map → area dossiers

| Area | Lives in | Dossier | Status |
|------|----------|---------|--------|
| **ASR / engines** | `whisperjav/modules/*asr*.py`, `segment_filters.py` | `whisperjav/modules/AGENTS.md` | ✅ inducted |
| **Pipeline / orchestration** | `whisperjav/pipelines/`, `whisperjav/ensemble/pass_worker.py`, `main.py` | `whisperjav/pipelines/AGENTS.md` | ✅ inducted |
| **Config** | `whisperjav/config/` (Pydantic `components/`, `v4/`, `legacy.py`) | `whisperjav/config/AGENTS.md` | ✅ inducted |
| Audio front-end | `modules/scene_detection.py`, `modules/speech_segmentation/`, `audio_preprocessing.py`, `modules/speech_enhancement/` | _pending_ | ⬜ |
| Postprocessing / subtitle | `modules/subtitle_sanitizer.py`, `srt_postprocessing.py` | _pending_ | ⬜ |
| Translation | `whisperjav/translate/` | _pending_ | ⬜ |
| GUI | `whisperjav/webview_gui/` | _pending_ | ⬜ |
| Install / release | `whisperjav/installer/`, `installer/`, `build_release.py` | _pending_ | ⬜ |

The **interface contracts** between these areas: `docs/architecture/MODULE_CONTRACTS.md`.

---

## 4. Red-lines (summary — owner-side `CLAUDE.md` / `memory/` hold the long-form versions)

- **Primary sources only.** Read the actual file/log/comment. Never decide from a summary or memory.
- **NEVER do a heavy import to "verify".** Importing `pass_worker`/ASR/torch/transformers/faster-whisper **hangs for hours**. Use `py_compile` + Grep + `--help` + `--dump-params`.
- **Separate observed facts from inferences.** Label hypotheses as hypotheses.
- **Call-chain verification is mandatory** before declaring any GUI→CLI feature done.
- **No parallel heavy local processes** (multiple concurrent GPU/ASR runs freeze the machine). Parallel *reasoning* subagents are fine.
- **Do not push or commit without explicit owner authorization.**
- Active branch is **`local`** (verified 2026-10-18; created from `main`, both at `df6a486`).
  `main` is **1 commit ahead of `origin/main`** (unpushed) — pushing is the owner's call.
- `whisperjav/config/asr_config.json` is currently **unmodified**; if a local edit to it
  shows up again, treat it as intentional experiment state and do not commit it blindly.

---

## 5. Environment notes (this machine, 2026-10)

The workspace root is **`E:\code\AI\WhisperJAV`** (the project has moved twice:
`C:\bin\git\…` → `D:\Git\WhisperJav_V1_Minami_Edition` → here; do not assume older paths).

- **No conda on this machine.** The `WJ` conda env cited in older docs (and the `WJ2` /
  `WJ_TEST` / `HF` / `QWEN` envs) belong to the owner's setup — they are equivalent in
  purpose but **not present here**. The uv-managed **`.venv` at the repo root IS the dev
  env**; activate it before running any command (§2). Do not judge the environment by
  anything else.
- Installed stack: Python 3.12.13 (uv 0.11.25), WhisperJAV 1.9.5 (architecture v4.4),
  torch 2.11.0+cu128.
- Toolchain / hardware: FFmpeg 8.1.1 must be on PATH
  (`D:\program\ffmpeg-8.1.1-full_build-shared\bin`); NVIDIA RTX 5070 Ti, driver 591.86.
- **Models are not in the project directory** — they auto-download to user-level caches
  (`%USERPROFILE%\.cache\huggingface\hub`, `…\.cache\whisper`, `…\.cache\torch\hub`,
  `…\.cache\whisperjav\…`, `…\.cache\modelscope`). Relocating them: `项目介绍.md` §3.3/§3.4.
- Repo-local artifacts referenced in older notes (e.g. `install_log.txt`) reflect the last
  local install; re-check before drawing conclusions from them.

---

## 6. Subagent disciplines

Every subagent definition under `.claude/agents/` must include the shared discipline
snippet `.claude/agents/_disciplines.md` (neither `.claude/agents/` nor that snippet exists
in this workspace as of 2026-10-18 — create them here if you add local task agents).
Existing task agents on the owner side: `config-tracer`, `call-chain-verifier`, plus the
slash-command services `/whisperjav_forensic_analyst` and
`/whisperjav_issue_tracker_maintainer`.
