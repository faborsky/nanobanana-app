"""Tests for batch job parsing and validation. No API calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanobanana.batch import parse_job_file, validate_job_file


def write_job(tmp_path: Path, payload: object) -> Path:
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(payload), encoding="utf-8")
    return job_file


class TestValidateJobFile:
    def test_accepts_minimal_valid_file(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "a lake at dawn"}]})
        assert validate_job_file(job_file) == []

    def test_accepts_defaults_block(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"aspect_ratio": "16:9", "resolution": "2K", "format": "png"},
                "jobs": [{"prompt": "a lake"}, {"prompt": "a dune", "resolution": "4K"}],
            },
        )
        assert validate_job_file(job_file) == []

    def test_reports_invalid_json(self, tmp_path: Path) -> None:
        job_file = tmp_path / "bad.json"
        job_file.write_text("{not json", encoding="utf-8")
        errors = validate_job_file(job_file)
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_requires_jobs_array(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"defaults": {}})
        assert any("Missing required 'jobs'" in e for e in validate_job_file(job_file))

    def test_rejects_top_level_array(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, [{"prompt": "x"}])
        assert any("must be a JSON object" in e for e in validate_job_file(job_file))

    def test_requires_prompt_on_every_job(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "ok"}, {"output_name": "no_prompt"}]})
        errors = validate_job_file(job_file)
        assert any("Job 2" in e and "prompt" in e for e in errors)

    def test_rejects_empty_prompt(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "   "}]})
        assert any("cannot be empty" in e for e in validate_job_file(job_file))

    def test_rejects_invalid_enum_values(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {"jobs": [{"prompt": "x", "aspect_ratio": "7:3", "resolution": "8K", "format": "gif"}]},
        )
        errors = validate_job_file(job_file)
        assert any("aspect_ratio" in e for e in errors)
        assert any("resolution" in e for e in errors)
        assert any("format" in e for e in errors)

    def test_rejects_ratio_the_job_model_cannot_do(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"model": "pro"},
                "jobs": [{"prompt": "x", "aspect_ratio": "8:1"}, {"prompt": "y", "model": "nope"}],
            },
        )
        errors = validate_job_file(job_file)
        assert any("Job 1" in e and "panoramic" in e for e in errors)
        assert any("Job 2" in e and "invalid model" in e for e in errors)

    def test_accepts_panoramic_ratio_on_default_model(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "aspect_ratio": "8:1"}]})
        assert validate_job_file(job_file) == []

    def test_rejects_missing_reference_image(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path, {"jobs": [{"prompt": "x", "reference_path": "does/not/exist.png"}]}
        )
        assert any("reference image not found" in e for e in validate_job_file(job_file))

    def test_accepts_existing_reference_image(self, tmp_path: Path) -> None:
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"fake")
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_path": str(ref)}]})
        assert validate_job_file(job_file) == []

    def test_validation_never_touches_the_network(self, tmp_path: Path, monkeypatch) -> None:
        # Guard the promise that `validate` is a free, offline dry run.
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "a lake"}]})
        assert validate_job_file(job_file) == []


class TestParseJobFile:
    def test_jobs_inherit_defaults(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"aspect_ratio": "21:9", "resolution": "4K", "format": "png"},
                "jobs": [{"prompt": "a dune"}],
            },
        )
        config = parse_job_file(job_file)
        job = config.jobs[0]
        assert (job.aspect_ratio, job.resolution, job.output_format) == ("21:9", "4K", "png")

    def test_per_job_values_override_defaults(self, tmp_path: Path) -> None:
        job_file = write_job(
            tmp_path,
            {
                "defaults": {"aspect_ratio": "1:1", "resolution": "1K"},
                "jobs": [{"prompt": "a dune", "aspect_ratio": "16:9", "resolution": "4K"}],
            },
        )
        job = parse_job_file(job_file).jobs[0]
        assert (job.aspect_ratio, job.resolution) == ("16:9", "4K")

    def test_falls_back_to_library_defaults_without_defaults_block(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "a dune"}]})
        job = parse_job_file(job_file).jobs[0]
        assert (job.aspect_ratio, job.resolution, job.output_format) == ("1:1", "2K", "webp")

    def test_reference_path_becomes_a_path(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"prompt": "x", "reference_path": "a/b.png"}]})
        assert parse_job_file(job_file).jobs[0].reference_path == Path("a/b.png")

    def test_raises_on_missing_prompt(self, tmp_path: Path) -> None:
        job_file = write_job(tmp_path, {"jobs": [{"output_name": "x"}]})
        with pytest.raises(ValueError, match="missing required 'prompt'"):
            parse_job_file(job_file)
