"""Tests for filename generation helpers. No API calls."""

from __future__ import annotations

from pathlib import Path

from nanobanana.utils import (
    generate_filename,
    get_output_path,
    sanitize_filename,
    truncate_prompt,
)


class TestSanitizeFilename:
    def test_lowercases_and_underscores_spaces(self) -> None:
        assert sanitize_filename("Golden Hour Mountain") == "golden_hour_mountain"

    def test_strips_diacritics(self) -> None:
        # Czech prompts are common here; the filename must stay ASCII-safe.
        assert sanitize_filename("Příšerně žluťoučký kůň") == "priserne_zlutoucky_kun"

    def test_drops_punctuation(self) -> None:
        assert sanitize_filename("a cat, 8K! (cinematic)") == "a_cat_8k_cinematic"

    def test_truncates_to_max_length_without_trailing_underscore(self) -> None:
        result = sanitize_filename("word " * 40, max_length=20)
        assert len(result) <= 20
        assert not result.endswith("_")

    def test_falls_back_when_nothing_survives(self) -> None:
        assert sanitize_filename("!!!///") == "image"

    def test_empty_input_falls_back(self) -> None:
        assert sanitize_filename("") == "image"


class TestGenerateFilename:
    def test_embeds_ratio_and_resolution(self) -> None:
        name = generate_filename("a lake", "16:9", "2K")
        # Colons are illegal in filenames on some platforms, so 16:9 becomes 16x9.
        assert "_16x9_2K_" in name
        assert ":" not in name

    def test_uses_custom_name_over_prompt(self) -> None:
        name = generate_filename("some long prompt text", "1:1", "1K", custom_name="hero")
        assert name.startswith("hero_")
        assert "some_long" not in name

    def test_jpeg_maps_to_jpg_extension(self) -> None:
        assert generate_filename("x", "1:1", "1K", output_format="jpeg").endswith(".jpg")

    def test_webp_and_png_keep_their_extension(self) -> None:
        assert generate_filename("x", "1:1", "1K", output_format="webp").endswith(".webp")
        assert generate_filename("x", "1:1", "1K", output_format="png").endswith(".png")

    def test_timestamp_makes_repeated_prompts_unique(self) -> None:
        name = generate_filename("same prompt", "1:1", "1K")
        # Format: <base>_<ratio>_<res>_<YYYYmmdd>_<HHMMSS>.<ext>
        stem = name.rsplit(".", 1)[0]
        date_part, time_part = stem.split("_")[-2:]
        assert len(date_part) == 8 and date_part.isdigit()
        assert len(time_part) == 6 and time_part.isdigit()


class TestGetOutputPath:
    def test_joins_directory_and_filename(self) -> None:
        path = get_output_path(Path("/tmp/out"), "a lake", "1:1", "1K", custom_name="lake")
        assert path.parent == Path("/tmp/out")
        assert path.name.startswith("lake_1x1_1K_")


class TestTruncatePrompt:
    def test_leaves_short_prompt_untouched(self) -> None:
        assert truncate_prompt("short", 60) == "short"

    def test_adds_ellipsis_and_respects_limit(self) -> None:
        result = truncate_prompt("x" * 100, 20)
        assert len(result) == 20
        assert result.endswith("...")
