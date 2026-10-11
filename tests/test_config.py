"""Tests for validation, pricing and retry classification. No API calls."""

from __future__ import annotations

import pytest

from nanobanana.config import (
    MODELS,
    VALID_ASPECT_RATIOS,
    VALID_OUTPUT_FORMATS,
    VALID_RESOLUTIONS,
    cost_from_usage,
    estimate_cost,
    get_model,
    is_retryable_error,
    validate_aspect_ratio,
    validate_for_model,
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
        # 10 standard ratios + 4 panoramic ones added with Nano Banana 2.1.
        assert VALID_ASPECT_RATIOS == {
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
            "1:4", "4:1", "1:8", "8:1",
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


class TestModels:
    def test_model_ids(self) -> None:
        assert MODELS["2.1"].model_id == "gemini-nano-banana-2.1"
        assert MODELS["pro"].model_id == "gemini-3-pro-image"
        assert MODELS["lite"].model_id == "gemini-3.1-flash-lite-image"

    def test_panoramic_ratios_are_2_1_only(self) -> None:
        validate_for_model(get_model("2.1"), "8:1", "2K")
        with pytest.raises(ValueError, match="panoramic"):
            validate_for_model(get_model("pro"), "8:1", "2K")

    def test_lite_is_1k_only(self) -> None:
        validate_for_model(get_model("lite"), "1:1", "1K")
        with pytest.raises(ValueError, match="resolution"):
            validate_for_model(get_model("lite"), "1:1", "2K")

    def test_thinking_levels(self) -> None:
        validate_for_model(get_model("2.1"), "1:1", "2K", "high")
        with pytest.raises(ValueError, match="thinking"):
            validate_for_model(get_model("pro"), "1:1", "2K", "high")
        with pytest.raises(ValueError, match="thinking level 'medium'"):
            validate_for_model(get_model("lite"), "1:1", "1K", "medium")

    def test_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="Invalid model"):
            get_model("flash")


class TestPricing:
    def test_matches_published_per_image_prices(self) -> None:
        # Source: https://ai.google.dev/gemini-api/docs/pricing (verified 2026-10-11).
        assert MODELS["2.1"].price_per_image_usd == {"1K": 0.0336, "2K": 0.0504, "4K": 0.113}
        assert MODELS["pro"].price_per_image_usd == {"1K": 0.134, "2K": 0.134, "4K": 0.24}
        assert MODELS["lite"].price_per_image_usd == {"1K": 0.0336}

    def test_pro_1k_and_2k_cost_the_same(self) -> None:
        assert estimate_cost("1K", model="pro") == estimate_cost("2K", model="pro")

    def test_2_1_is_cheaper_than_pro_at_every_resolution(self) -> None:
        for res in ("1K", "2K", "4K"):
            assert estimate_cost(res, model="2.1") < estimate_cost(res, model="pro")

    def test_scales_linearly_with_count(self) -> None:
        assert estimate_cost("2K", 10, model="pro") == pytest.approx(1.34)

    def test_unknown_resolution_falls_back_to_most_expensive(self) -> None:
        assert estimate_cost("42K", model="2.1") == estimate_cost("4K", model="2.1")

    def test_usage_cost_matches_published_image_price(self) -> None:
        # 1K image = 1120 output tokens at $30/1M = $0.0336 (pricing page footnote).
        cost = cost_from_usage(MODELS["2.1"], 0, 1120, 0)
        assert cost == pytest.approx(0.0336)

    def test_usage_cost_includes_prompt_and_text_tokens(self) -> None:
        base = cost_from_usage(MODELS["2.1"], 0, 1120, 0)
        assert cost_from_usage(MODELS["2.1"], 100, 1120, 300) > base


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
