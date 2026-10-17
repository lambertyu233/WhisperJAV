"""Regression tests for EnsembleOrchestrator language handling."""

from pathlib import Path

from whisperjav.ensemble.orchestrator import EnsembleOrchestrator


def _build_orchestrator(tmp_path, keep_temp_files=True, keep_intermediates=False):
    output = tmp_path / "out"
    temp = tmp_path / "tmp"
    return EnsembleOrchestrator(
        output_dir=str(output),
        temp_dir=str(temp),
        keep_temp_files=keep_temp_files,
        keep_intermediates=keep_intermediates,
        subs_language="native",
    )


def test_process_batch_handles_none_overrides(tmp_path, monkeypatch):
    orchestrator = _build_orchestrator(tmp_path)

    media_info = {
        "basename": "sample",
        "path": str(tmp_path / "sample.wav"),
    }

    # Create mock SRT files on disk — orchestrator verifies existence defensively
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    pass1_file = out_dir / "sample.ja.pass1.srt"
    pass2_file = out_dir / "sample.ja.pass2.srt"
    pass1_file.write_text("1\n00:00:00,000 --> 00:00:01,000\npass1\n", encoding="utf-8")
    pass2_file.write_text("1\n00:00:00,000 --> 00:00:01,000\npass2\n", encoding="utf-8")

    pass1_result = {
        "status": "completed",
        "srt_path": str(pass1_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }
    pass2_result = {
        "status": "completed",
        "srt_path": str(pass2_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }

    def fake_run_pass(*args, **kwargs):
        if kwargs["pass_number"] == 1:
            return {"sample": pass1_result}
        return {"sample": pass2_result}

    monkeypatch.setattr(orchestrator, "_run_pass_in_subprocess", fake_run_pass)

    def fake_merge(*args, **kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.write_text("1\n00:00:00,000 --> 00:00:01,000\ntext\n", encoding="utf-8")
        return {"merged_count": 1}

    monkeypatch.setattr(orchestrator.merge_engine, "merge", fake_merge)

    results = orchestrator.process_batch(
        media_files=[media_info],
        pass1_config={"pipeline": "balanced", "overrides": None},
        pass2_config={"pipeline": "balanced", "overrides": None},
        merge_strategy="pass1_primary",
    )

    # The merge's working filename is not the delivered one: the orchestrator
    # renames it to <name>.<lang>.srt before handing the path back, because main
    # translates and converts to VTT from this very field.
    assert results[0]["summary"]["final_output"].endswith("sample.ja.srt")
    final_path = Path(results[0]["summary"]["final_output"])
    assert final_path.exists()
    assert final_path.read_text(encoding="utf-8").endswith("text\n")
    assert not (out_dir / "sample.ja.merged.whisperjav.srt").exists()

    # keep_temp_files=True means "leave the artifacts for inspection", which
    # extends to the per-pass SRTs next to the video.
    assert (out_dir / "sample.ja.pass1.srt").exists()
    assert (out_dir / "sample.ja.pass2.srt").exists()


def test_process_batch_removes_intermediates_by_default(tmp_path, monkeypatch):
    """Default run: the user gets one subtitle and nothing else."""
    orchestrator = _build_orchestrator(tmp_path, keep_temp_files=False)

    media_info = {
        "basename": "sample",
        "path": str(tmp_path / "sample.wav"),
    }

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    pass1_file = out_dir / "sample.ja.pass1.srt"
    pass2_file = out_dir / "sample.ja.pass2.srt"
    pass1_file.write_text("pass1", encoding="utf-8")
    pass2_file.write_text("pass2", encoding="utf-8")

    pass1_result = {
        "status": "completed",
        "srt_path": str(pass1_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }
    pass2_result = {
        "status": "completed",
        "srt_path": str(pass2_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }

    def fake_run_pass(*args, **kwargs):
        if kwargs["pass_number"] == 1:
            return {"sample": pass1_result}
        return {"sample": pass2_result}

    monkeypatch.setattr(orchestrator, "_run_pass_in_subprocess", fake_run_pass)

    def fake_merge(*args, **kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.write_text("merged", encoding="utf-8")
        return {"merged_count": 1}

    monkeypatch.setattr(orchestrator.merge_engine, "merge", fake_merge)

    results = orchestrator.process_batch(
        media_files=[media_info],
        pass1_config={"pipeline": "balanced", "overrides": None},
        pass2_config={"pipeline": "balanced", "overrides": None},
        merge_strategy="pass1_primary",
    )

    final_path = Path(results[0]["summary"]["final_output"])
    assert final_path == out_dir / "sample.ja.srt"
    assert final_path.read_text(encoding="utf-8") == "merged"
    assert not pass1_file.exists()
    assert not pass2_file.exists()
    assert not (out_dir / "sample.ja.merged.whisperjav.srt").exists()
    assert sorted(p.name for p in out_dir.iterdir()) == ["sample.ja.srt"]


def test_keep_intermediates_flag_preserves_pass_srts(tmp_path, monkeypatch):
    orchestrator = _build_orchestrator(
        tmp_path, keep_temp_files=False, keep_intermediates=True
    )

    media_info = {
        "basename": "sample",
        "path": str(tmp_path / "sample.wav"),
    }

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    pass1_file = out_dir / "sample.ja.pass1.srt"
    pass2_file = out_dir / "sample.ja.pass2.srt"
    pass1_file.write_text("pass1", encoding="utf-8")
    pass2_file.write_text("pass2", encoding="utf-8")

    pass1_result = {
        "status": "completed",
        "srt_path": str(pass1_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }
    pass2_result = {
        "status": "completed",
        "srt_path": str(pass2_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }

    def fake_run_pass(*args, **kwargs):
        if kwargs["pass_number"] == 1:
            return {"sample": pass1_result}
        return {"sample": pass2_result}

    monkeypatch.setattr(orchestrator, "_run_pass_in_subprocess", fake_run_pass)

    def fake_merge(*args, **kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.write_text("merged", encoding="utf-8")
        return {"merged_count": 1}

    monkeypatch.setattr(orchestrator.merge_engine, "merge", fake_merge)

    orchestrator.process_batch(
        media_files=[media_info],
        pass1_config={"pipeline": "balanced", "overrides": None},
        pass2_config={"pipeline": "balanced", "overrides": None},
        merge_strategy="pass1_primary",
    )

    assert pass1_file.exists() and pass2_file.exists()
    assert (out_dir / "sample.ja.srt").exists()


def test_process_batch_reports_merge_failure_and_summary(tmp_path, monkeypatch):
    orchestrator = _build_orchestrator(tmp_path)

    media_info = {
        "basename": "sample",
        "path": str(tmp_path / "sample.wav"),
    }

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    pass1_file = out_dir / "sample.ja.pass1.srt"
    pass2_file = out_dir / "sample.ja.pass2.srt"
    pass1_file.write_text("pass1", encoding="utf-8")
    pass2_file.write_text("pass2", encoding="utf-8")

    pass1_result = {
        "status": "completed",
        "srt_path": str(pass1_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }
    pass2_result = {
        "status": "completed",
        "srt_path": str(pass2_file),
        "subtitles": 1,
        "processing_time": 1.0,
    }

    def fake_run_pass(*args, **kwargs):
        if kwargs["pass_number"] == 1:
            return {"sample": pass1_result}
        return {"sample": pass2_result}

    monkeypatch.setattr(orchestrator, "_run_pass_in_subprocess", fake_run_pass)

    def failing_merge(*args, **kwargs):  # pragma: no cover - direct failure path
        raise RuntimeError("merge boom")

    monkeypatch.setattr(orchestrator.merge_engine, "merge", failing_merge)

    results = orchestrator.process_batch(
        media_files=[media_info],
        pass1_config={"pipeline": "balanced", "overrides": None},
        pass2_config={"pipeline": "balanced", "overrides": None},
        merge_strategy="pass1_primary",
    )

    # Merge failed → the pass 1 SRT is the delivered subtitle, so it must be
    # renamed to the delivered name rather than treated as an intermediate and
    # deleted. This is the path where a careless cleanup eats the only output.
    assert results[0]["summary"]["final_output"].endswith("sample.ja.srt")
    final_path = Path(results[0]["summary"]["final_output"])
    assert final_path.read_text(encoding="utf-8") == "pass1"
    assert not pass1_file.exists()
    merged_path = out_dir / "sample.ja.merged.whisperjav.srt"
    assert not merged_path.exists()

    # Summary JSON is written to temp_dir, not output_dir
    temp_dir = tmp_path / "tmp"
    summaries = list(temp_dir.glob("ensemble_summary_*.json"))
    assert summaries, "JSON summary file should be created"
