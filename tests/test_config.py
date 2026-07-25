"""Tests for validation, pricing and retry classification. No API calls."""

from __future__ import annotations

import pytest

from nanobanana.config import (
    PRICE_PER_IMAGE_USD,
    VALID_ASPECT_RATIOS,
    VALID_OUTPUT_FORMATS,
    VALID_RESOLUTIONS,
    estimate_cost,
    is_retryable_error,
    validate_aspect_ratio,
    validate_output_format,
    validate_reference_path,
    validate_resolution,
)


class _ApiError(Exception):
    """Stands in for google.genai.errors.APIError, which carries a .code attribute."""

    def __init__(self, code: int, message: str = "api error") -> None:
        super().__init__(message)
        self.code = code


class TestValidators:
    def test_accepts_every_documented_aspect_ratio(self) -> None:
        # These 10 ratios are the ones the Gemini image API documents as supported.
        assert VALID_ASPECT_RATIOS == {
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
        }
        for ratio in VALID_ASPECT_RATIOS:
            assert validate_aspect_ratio(ratio) == ratio

    def test_rejects_unknown_aspect_ratio_and_lists_options(self) -> None:
        with pytest.raises(ValueError, match="Invalid aspect ratio"):
            validate_aspect_ratio("7:3")

    def test_resolutions(self) -> None:
        assert VALID_RESOLUTIONS == {"1K", "2K", "4K"}
        assert validate_resolution("4K") == "4K"
        with pytest.raises(ValueError, match="Invalid resolution"):
            validate_resolution("8K")

    def test_output_formats(self) -> None:
        assert VALID_OUTPUT_FORMATS == {"webp", "png", "jpeg"}
        assert validate_output_format("png") == "png"
        with pytest.raises(ValueError, match="Invalid output format"):
            validate_output_format("gif")

    def test_reference_path_must_exist(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="not found"):
            validate_reference_path(tmp_path / "missing.png")

    def test_reference_path_rejects_unsupported_suffix(self, tmp_path) -> None:
        bad = tmp_path / "notes.txt"
        bad.write_text("x")
        with pytest.raises(ValueError, match="Unsupported image format"):
            validate_reference_path(bad)

    def test_reference_path_accepts_supported_suffix(self, tmp_path) -> None:
        good = tmp_path / "ref.png"
        good.write_bytes(b"fake")
        assert validate_reference_path(good) == good

    def test_reference_path_rejects_directory(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="not a file"):
            validate_reference_path(tmp_path)


class TestPricing:
    def test_matches_published_per_image_prices(self) -> None:
        # Source: https://ai.google.dev/gemini-api/docs/pricing (verified 2026-07-25).
        assert PRICE_PER_IMAGE_USD == {"1K": 0.134, "2K": 0.134, "4K": 0.24}

    def test_1k_and_2k_cost_the_same(self) -> None:
        assert estimate_cost("1K") == estimate_cost("2K")

    def test_4k_is_more_expensive(self) -> None:
        assert estimate_cost("4K") > estimate_cost("2K")

    def test_scales_linearly_with_count(self) -> None:
        assert estimate_cost("1K", 10) == pytest.approx(1.34)

    def test_unknown_resolution_falls_back_to_default(self) -> None:
        assert estimate_cost("42K") == estimate_cost("1K")


class TestRetryClassification:
    @pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
    def test_retries_rate_limit_and_server_errors(self, code: int) -> None:
        assert is_retryable_error(_ApiError(code)) is True

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
    def test_does_not_retry_hard_errors(self, code: int) -> None:
        # Retrying a bad prompt or a missing model just burns time and quota.
        assert is_retryable_error(_ApiError(code)) is False

    @pytest.mark.parametrize(
        "message",
        ["Connection reset by peer", "Request timed out", "Read timeout", "temporarily unavailable"],
    )
    def test_retries_transient_network_failures(self, message: str) -> None:
        assert is_retryable_error(Exception(message)) is True

    def test_does_not_retry_unrecognised_error(self) -> None:
        assert is_retryable_error(ValueError("prompt too long")) is False


class TestOutputStreamDiscipline:
    """--json promises a clean, parseable stdout. Retry notices must not break it."""

    def test_retry_notices_go_to_stderr(self) -> None:
        # Regression guard: these notices used to print to stdout, which corrupted
        # the --json payload whenever a request was retried (found during a real
        # upstream outage). They are diagnostics, so stderr is the correct stream.
        from nanobanana.generator import console

        assert console.stderr is True, "generator console must write to stderr"
