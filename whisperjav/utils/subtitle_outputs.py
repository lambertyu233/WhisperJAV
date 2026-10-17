"""Naming and post-run cleanup for the subtitle files WhisperJAV writes.

Two independent concerns live here, both of them pure path arithmetic.

**Naming.** The name of a delivered ensemble subtitle used to be spelled out
independently in three places: the orchestrator (which writes it), `main`'s
``--skip-existing`` check (which decides whether a file needs re-running), and
the GUI's expected-output list (which it hands to the frontend). Nothing kept
them in step, so a change to any one of them silently desynchronised the other
two -- and a rename that missed ``--skip-existing`` would silently turn that
flag into a no-op. All of them now call the functions below.

**Ensemble finalization.** Ensemble runs each pass in its own subprocess, and
every pass writes its SRT straight into the *output* directory, not into the
temp directory. So one video leaves behind ``video.ja.pass1.srt``,
``video.ja.pass2.srt`` and a merged file; the user asked for one subtitle.
:func:`finalize_outputs` renames the merged file to the delivered name and
removes the per-pass ones.

Nothing in this module imports from the ASR stack, deliberately. Importing
anything under ``whisperjav.ensemble`` executes its ``__init__``, which imports
the orchestrator, which imports ``pass_worker``, which imports every pipeline
(transformers, faster-whisper, ...) at module level. Keeping finalization here
means it can be unit-tested without a multi-minute heavyweight import, which is
also why the GUI may import it safely.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from whisperjav.utils.logger import logger


def pass_srt_name(basename: str, language_code: str, pass_number: int) -> str:
    """Name of one pass's intermediate SRT: ``{basename}.{lang}.pass{N}.srt``.

    Lives in the output directory next to the video, because the merge step
    reads it from there.
    """
    return f"{basename}.{language_code}.pass{pass_number}.srt"


def merged_srt_working_name(basename: str, language_code: str) -> str:
    """Working name the merge step writes: ``{basename}.{lang}.merged.whisperjav.srt``.

    This name exists only between the merge and :func:`finalize_outputs`. It is
    deliberately a distinguishable marker, not the delivered name, so a run
    interrupted between those two steps leaves an obviously unfinished file
    behind instead of something that looks final.
    """
    return f"{basename}.{language_code}.merged.whisperjav.srt"


def final_srt_name(basename: str, language_code: str) -> str:
    """Delivered subtitle name: ``{basename}.{lang}.srt``.

    The language code stays because one folder routinely holds a ``ja`` and an
    ``en`` rendering of the same video, and they must not overwrite each other.
    """
    return f"{basename}.{language_code}.srt"


@dataclass
class FinalizeResult:
    """Outcome of finalizing one file's outputs."""

    # Path the caller should treat as the delivered subtitle. None when there
    # was nothing to finalize (failed pass, missing file).
    final_path: Optional[Path] = None
    renamed: bool = False
    removed_intermediates: List[str] = field(default_factory=list)
    # Machine-readable reason nothing was done; None on success.
    skipped_reason: Optional[str] = None


def finalize_outputs(
    final_output: Optional[Union[str, Path]],
    basename: str,
    language_code: str,
    *,
    remove_intermediates: bool = True,
    pass_count: int = 2,
) -> FinalizeResult:
    """Rename the merged subtitle to its delivered name and drop the per-pass SRTs.

    Call this once per file, after the merge (or after whatever degraded
    fallback produced the output). Best-effort throughout: any problem is logged
    and reported through the result, never raised, because losing the file's
    subtitles to a rename hiccup is strictly worse than leaving the merged
    filename in place.

    Two safety properties this function must keep, both of which exist because
    of the degraded paths in the orchestrator:

    * When pass 2 fails, the *pass 1* SRT **is** the delivered subtitle (there
      is nothing to merge it into). Renaming handles that correctly; deleting
      the pass files must never delete the file being delivered.
    * Intermediates are matched by exact name, never by scanning the directory
      for a pattern. These files sit in the user's own video folder, next to
      their other subtitles, and a glob would eventually eat one.

    Args:
        final_output: The path recorded as this file's final output. May be a
            pass SRT rather than a merged file; both are handled.
        basename: Media basename (the video's stem).
        language_code: Two-character subtitle language code.
        remove_intermediates: False to keep the per-pass SRTs (debugging).
        pass_count: Highest pass number to consider for removal.

    Returns:
        A :class:`FinalizeResult` holding the path the caller should record.
    """
    if not final_output:
        return FinalizeResult(skipped_reason='no_final_output')

    src = Path(final_output)
    if not src.is_file():
        logger.warning(
            "Cannot finalize outputs for %s: %s does not exist",
            basename,
            src,
        )
        return FinalizeResult(skipped_reason='final_output_missing')

    target = src.parent / final_srt_name(basename, language_code)
    final_path = src

    if target != src:
        try:
            # Same directory, so os.replace() is an atomic rename that also
            # overwrites a subtitle left by a previous run -- which is what the
            # single-pass pipelines do with their own output.
            os.replace(src, target)
            final_path = target
            logger.debug("Finalized %s -> %s", src.name, target.name)
        except OSError as rename_err:
            logger.warning(
                "Could not rename %s to %s (%s); keeping the merged filename",
                src,
                target,
                rename_err,
            )
            return FinalizeResult(
                final_path=src,
                skipped_reason='rename_failed',
            )

    removed: List[str] = []
    if remove_intermediates:
        final_resolved = _safe_resolve(final_path)
        for pass_number in range(1, pass_count + 1):
            candidate = src.parent / pass_srt_name(basename, language_code, pass_number)
            # The degraded path can make the delivered file *be* a pass file.
            if _safe_resolve(candidate) == final_resolved:
                continue
            if not candidate.exists():
                continue
            try:
                candidate.unlink()
                removed.append(candidate.name)
                logger.debug("Removed intermediate %s", candidate.name)
            except OSError as unlink_err:
                logger.warning("Could not remove intermediate %s: %s", candidate, unlink_err)

    return FinalizeResult(
        final_path=final_path,
        renamed=target != src,
        removed_intermediates=removed,
    )


def _safe_resolve(path: Path) -> Path:
    """Resolve for identity comparison, tolerating a path that no longer exists.

    ``Path.resolve()`` works on non-existent paths on current Python, but it can
    still raise on some Windows setups (a missing drive, a permission error on
    the parent). Identity is only used to avoid deleting the delivered file, so
    falling back to the literal path is safe.
    """
    try:
        return path.resolve()
    except OSError:
        return path