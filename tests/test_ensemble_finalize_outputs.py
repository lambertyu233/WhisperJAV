"""Tests for ensemble output finalization: rename the merged subtitle, drop the rest.

`finalize_outputs` is the only place that deletes files sitting in the user's
own video folder, so most of what follows is about what it must *not* do.
"""

from pathlib import Path

from whisperjav.utils.subtitle_outputs import (
    finalize_outputs,
    final_srt_name,
    merged_srt_working_name,
    pass_srt_name,
)


def _write(path: Path, text: str = "1\n00:00:01,000 --> 00:00:02,000\nhello\n") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


class TestNaming:
    """The naming rules, which three call sites now share."""

    def test_pass_name(self):
        assert pass_srt_name("video", "ja", 1) == "video.ja.pass1.srt"
        assert pass_srt_name("video", "ja", 2) == "video.ja.pass2.srt"

    def test_merged_working_name(self):
        assert merged_srt_working_name("video", "ja") == "video.ja.merged.whisperjav.srt"

    def test_final_name_keeps_language_code(self):
        # The language code is what stops a ja and an en rendering of the same
        # video from overwriting each other.
        assert final_srt_name("video", "ja") == "video.ja.srt"
        assert final_srt_name("video", "en") == "video.en.srt"

    def test_names_preserve_dotted_stems(self):
        # 'MIAA-432.20sec_piano' must not be truncated at its inner dot.
        assert final_srt_name("MIAA-432.20sec_piano", "ja") == "MIAA-432.20sec_piano.ja.srt"


class TestHappyPath:
    def test_renames_merged_and_removes_passes(self, tmp_path):
        content = "1\n00:00:01,000 --> 00:00:02,000\nhello\n"
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"), content)
        _write(tmp_path / pass_srt_name("video", "ja", 1))
        _write(tmp_path / pass_srt_name("video", "ja", 2))

        result = finalize_outputs(merged, "video", "ja")

        assert result.renamed is True
        assert result.final_path == tmp_path / "video.ja.srt"
        assert result.final_path.read_text(encoding="utf-8") == content
        assert not (tmp_path / pass_srt_name("video", "ja", 1)).exists()
        assert not (tmp_path / pass_srt_name("video", "ja", 2)).exists()
        assert not (tmp_path / merged_srt_working_name("video", "ja")).exists()

    def test_records_what_it_removed(self, tmp_path):
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"))
        _write(tmp_path / pass_srt_name("video", "ja", 1))
        _write(tmp_path / pass_srt_name("video", "ja", 2))

        result = finalize_outputs(merged, "video", "ja")

        assert sorted(result.removed_intermediates) == ["video.ja.pass1.srt", "video.ja.pass2.srt"]

    def test_leaves_unrelated_subtitles_alone(self, tmp_path):
        """The output directory is the user's video folder, not ours."""
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"))
        theirs = _write(tmp_path / "video.en.srt", "someone else's subtitles")
        other = _write(tmp_path / "completely.different.srt")

        finalize_outputs(merged, "video", "ja")

        assert theirs.read_text(encoding="utf-8") == "someone else's subtitles"
        assert other.exists()


class TestDegradedPaths:
    """When a pass fails there is nothing to merge, so a pass SRT *is* the answer.

    This is the case where a naive cleanup deletes the only subtitle the run
    produced.
    """

    def test_pass1_as_final_output_is_renamed_not_deleted(self, tmp_path):
        pass1 = _write(tmp_path / pass_srt_name("video", "ja", 1), "the real subtitles")
        _write(tmp_path / pass_srt_name("video", "ja", 2))

        result = finalize_outputs(pass1, "video", "ja")

        assert result.final_path == tmp_path / "video.ja.srt"
        assert result.final_path.read_text(encoding="utf-8") == "the real subtitles"
        assert not (tmp_path / pass_srt_name("video", "ja", 2)).exists()

    def test_pass2_as_final_output_is_renamed_not_deleted(self, tmp_path):
        pass2 = _write(tmp_path / pass_srt_name("video", "ja", 2), "pass 2 only")

        result = finalize_outputs(pass2, "video", "ja")

        assert result.final_path.read_text(encoding="utf-8") == "pass 2 only"


class TestNothingToFinalize:
    def test_no_final_output_touches_nothing(self, tmp_path):
        _write(tmp_path / pass_srt_name("video", "ja", 1))

        result = finalize_outputs(None, "video", "ja")

        assert result.final_path is None
        assert result.skipped_reason == "no_final_output"
        assert (tmp_path / pass_srt_name("video", "ja", 1)).exists()

    def test_missing_final_file_touches_nothing(self, tmp_path):
        """A recorded path that isn't on disk means the run broke earlier."""
        _write(tmp_path / pass_srt_name("video", "ja", 1))

        result = finalize_outputs(tmp_path / "video.ja.merged.whisperjav.srt", "video", "ja")

        assert result.final_path is None
        assert result.skipped_reason == "final_output_missing"
        assert (tmp_path / pass_srt_name("video", "ja", 1)).exists()
        assert not (tmp_path / "video.ja.srt").exists()

    def test_already_final_name_is_left_in_place(self, tmp_path):
        final = _write(tmp_path / final_srt_name("video", "ja"))
        _write(tmp_path / pass_srt_name("video", "ja", 1))

        result = finalize_outputs(final, "video", "ja")

        assert result.renamed is False
        assert result.final_path == final
        assert final.exists()


class TestRetentionAndOverwrite:
    def test_keep_intermediates_preserves_passes(self, tmp_path):
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"))
        pass1 = _write(tmp_path / pass_srt_name("video", "ja", 1))
        pass2 = _write(tmp_path / pass_srt_name("video", "ja", 2))

        result = finalize_outputs(merged, "video", "ja", remove_intermediates=False)

        assert result.removed_intermediates == []
        assert pass1.exists() and pass2.exists()
        assert result.final_path == tmp_path / "video.ja.srt"

    def test_existing_subtitle_is_overwritten(self, tmp_path):
        """A re-run replaces the previous subtitle, as the single-pass modes do."""
        _write(tmp_path / final_srt_name("video", "ja"), "stale")
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"), "fresh")

        result = finalize_outputs(merged, "video", "ja")

        assert result.final_path.read_text(encoding="utf-8") == "fresh"

    def test_pass_count_is_configurable(self, tmp_path):
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"))
        _write(tmp_path / pass_srt_name("video", "ja", 1))
        pass3 = _write(tmp_path / pass_srt_name("video", "ja", 3))

        result = finalize_outputs(merged, "video", "ja", pass_count=2)

        assert not (tmp_path / pass_srt_name("video", "ja", 1)).exists()
        assert pass3.exists(), "pass 3 is outside the declared pass count"

    def test_rename_failure_keeps_the_merged_file(self, tmp_path, monkeypatch):
        """A subtitle left under the working name beats no subtitle at all."""
        merged = _write(tmp_path / merged_srt_working_name("video", "ja"))

        def boom(*_args, **_kwargs):
            raise OSError("disk says no")

        monkeypatch.setattr("os.replace", boom)

        result = finalize_outputs(merged, "video", "ja")

        assert result.renamed is False
        assert result.final_path == merged
        assert merged.exists()
        assert result.skipped_reason == "rename_failed"


class TestDeletionSafety:
    """Guard the property that keeps this from eating a user's files.

    The intermediates live in the user's video folder among their own
    subtitles, so anything that *finds* candidates by scanning the directory
    instead of computing the one exact name is a future incident.
    """

    def test_no_directory_scanning(self):
        source = (
            Path(__file__).resolve().parents[1] / "whisperjav" / "utils" / "subtitle_outputs.py"
        ).read_text(encoding="utf-8")

        for forbidden in ("glob(", "rglob(", "iterdir(", "os.listdir", "os.scandir", "walk("):
            assert forbidden not in source, (
                f"subtitle_outputs.py must not use {forbidden}: it deletes files in the "
                f"user's own folder, so candidates must be computed, not discovered"
            )