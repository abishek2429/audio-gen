"""Integration tests for the CLI pipeline."""
import os
import json
import pytest

from src.cli import run_pipeline


def test_cli_pipeline_end_to_end(tmp_path):
    """Verify that run_pipeline produces a complete, compliant audio pack with all deliverables."""
    out_dir = str(tmp_path / "poc_output")
    res = run_pipeline(
        prompt="calm corporate acoustic background",
        duration_s=8.0,
        output_dir=out_dir,
        tempo_bpm=100,
        key="C major",
        seed=42,
        provider_name="mock",
    )

    assert os.path.exists(os.path.join(out_dir, "request.json"))
    assert os.path.exists(os.path.join(out_dir, "raw_generation.wav"))
    assert os.path.exists(os.path.join(out_dir, "mix.wav"))
    assert os.path.exists(os.path.join(out_dir, "stems"))
    assert os.path.exists(os.path.join(out_dir, "music_manifest.json"))
    assert os.path.exists(os.path.join(out_dir, "validation_report.json"))
    assert os.path.exists(os.path.join(out_dir, "run.log"))

    # Verify validation report passes
    val_report = res["validation_report"]
    assert val_report["overall_passed"] is True
    assert val_report["gates"]["exact_duration"]["passed"] is True
    assert val_report["gates"]["stem_reconstruction"]["passed"] is True
    assert val_report["gates"]["stem_reconstruction"]["details"]["sdr_db"] > 60.0

    # Verify manifest
    manifest = res["manifest"]
    assert manifest["actual_duration_s"] == pytest.approx(8.0, abs=0.05)
    assert len(manifest["stems"]) >= 3
    assert manifest["cost_usd"] == 0.0
