# Ensemble Mode

Ensemble mode runs two different ASR pipelines on the same video and merges their output for higher accuracy. This is WhisperJAV's most powerful transcription mode.

---

## How It Works

```
Video → Pass 1 (Pipeline A) → SRT₁ ─┐
                                      ├→ Merge → Final SRT
Video → Pass 2 (Pipeline B) → SRT₂ ─┘
```

Each pipeline has different strengths. For example:

- **Whisper** (Balanced): excellent timing, good text
- **Qwen3-ASR**: excellent text quality, different timing approach

Merging combines the best of both.

---

## Setting Up Ensemble

1. Go to the **Ensemble** tab (Tab 3)
2. **Pass 1** is always active and **Pass 2 is checked by default** — both come pre-set to the ChronosJAV recipe (see *Default Configuration* below), so the defaults work out of the box
3. To run a single pass only: uncheck the **Pass 2** checkbox
4. Optionally adjust pipeline, sensitivity, and options for each pass
5. Choose a **Merge Strategy** (Smart Merge by default)
6. Click **Start**

### Default Configuration (ChronosJAV Recipe)

The out-of-the-box two-pass setup, taken from the [ChronosJAV pipeline](chronosjav.md) page ("As part of ensemble mode") — on the CLI, `whisperjav video.mp4 --ensemble` uses the same one:

| Pass | Pipeline | Sensitivity | Scene | Enhancer | Segmenter | Model |
|------|----------|-------------|-------|----------|-----------|-------|
| 1 | Anime-Whisper (ChronosJAV) | Balanced | Semantic | None | TEN | litagin/anime-whisper |
| 2 | Qwen3-ASR | Balanced | Semantic | None | TEN | Qwen/Qwen3-ASR-1.7B |

The default merge strategy is **Smart Merge**. For maximum quality, swap Pass 1 to **Fidelity** (large-v2 + FireRedVAD); for speed, swap it to **Balanced**; or turn Pass 2 off with `--pass2-pipeline none`.

> **CLI note:** `--pass1-pipeline qwen` cannot say which ChronosJAV generator it means — anime-whisper and Qwen3-ASR are one pipeline with two generators. Pass 1 defaults to anime-whisper; for Qwen3-ASR on pass 1, pass `--pass1-qwen-params '{"generator_backend": "qwen3"}'`.

### Pass Configuration

Each pass has identical controls:

| Control | Description |
|---------|-------------|
| **Pipeline** | ASR backend (Balanced, Fast, Faster, Qwen3-ASR, ChronosJAV, etc.) |
| **Sensitivity** | Detection threshold (Aggressive, Balanced, Conservative) |
| **Scene Detector** | How to split audio into scenes (Auditok, Silero, Semantic, None) |
| **Speech Enhancer** | Audio preprocessing (None, FFmpeg DSP, ClearVoice, BS-RoFormer) |
| **Speech Segmenter** | Voice activity detection within scenes (Silero, TEN, None) |
| **Model** | Which model to use (pipeline-dependent) |

Click **Customize** on any pass for fine-grained parameter control.

---

## Merge Strategies

| Strategy | Best For |
|----------|----------|
| **Pass 1 Primary** | When Pass 1 is your trusted baseline — fills gaps from Pass 2 |
| **Smart Merge** | General use — selects the best subtitle from each pass using quality heuristics |
| **Full Merge** | Maximum coverage — combines all subtitles, resolves overlaps |
| **Longest** | Picks the longer (more detailed) subtitle when passes overlap |
| **Pass 2 Primary** | When Pass 2 is your trusted baseline |
| **Overlap 30%** | Conservative merge — requires 30% time overlap before merging |

!!! tip "Default Combo"
    **Anime-Whisper** (Pass 1) + **Qwen3-ASR** (Pass 2) + **Smart Merge** is the out-of-the-box default — the pairing the ChronosJAV pipeline page recommends. Swap Pass 1 to **Fidelity** for maximum quality, or to **Balanced** when you want speed.

---

## BYOP: XXL Faster Whisper (v1.8.9+)

Select **XXL Faster Whisper** as the Pass 2 pipeline to use [PurfView's Faster Whisper XXL](https://github.com/Purfview/whisper-standalone-win) as an external subprocess. This is "Bring Your Own Pipeline" — you supply the executable.

### Setup

1. Download Faster Whisper XXL from the link above
2. In the Ensemble tab, select **XXL Faster Whisper** for Pass 2
3. Click **Browse** to point to your `faster-whisper-xxl.exe`
4. Add any extra args (e.g., `--verbose True --standard_asia`)

WhisperJAV sends only 4 required args (input, output dir, model, language). Everything else is controlled by your Extra Args field.

### CLI

```bash
whisperjav video.mp4 --pass2-pipeline xxl --xxl-exe /path/to/faster-whisper-xxl.exe
```

---

## Serial vs Parallel Batch Mode

When processing multiple files in ensemble mode:

| Mode | Behavior |
|------|----------|
| **Parallel** (default) | All Pass 1 jobs run first, then all Pass 2, then all merges |
| **Serial** | Each file completes fully (Pass 1 → Pass 2 → Merge) before the next starts |

**Serial mode** is useful when you want to see results as they finish. Enable it with the **Serial** checkbox in the GUI or `--ensemble-serial` in CLI.

---

## Presets

Save your ensemble configuration for reuse:

1. Configure your passes, merge strategy, and parameters
2. Click **Save Preset**
3. Give it a name (e.g., "High Quality JAV", "Quick Anime")
4. Load presets later from the preset dropdown

Presets save all pass configurations, merge strategy, and custom parameters. They persist across sessions.

---

## Inline Translation

Check **"AI-translate"** after the merge strategy to automatically translate the merged output. Select your provider and model inline, or click the settings button for full configuration.
