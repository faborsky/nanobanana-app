"""Configuration module for Nanobanana CLI."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
# Image generation model (Nano Banana Pro). GA / stable ID.
# The old "gemini-3-pro-image-preview" was retired on 2026-06-25.
MODEL_NAME = "gemini-3-pro-image"
# Multimodal model used by the `describe` command for image analysis.
# gemini-2.0-flash was shut down on 2026-06-01; gemini-3.5-flash is the
# current stable flash model with vision support.
DESCRIBE_MODEL_NAME = "gemini-3.5-flash"

# Default values
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_RESOLUTION = "1K"
DEFAULT_OUTPUT_FORMAT = "webp"
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 2.0
DEFAULT_RETRY_MAX_DELAY = 60.0

# Per-image price in USD, source: https://ai.google.dev/gemini-api/docs/pricing
# (verified 2026-07-25). 1K and 2K cost the same — only 4K is more expensive.
# These are standard-tier prices for direct API calls, which is what this CLI makes.
# Google's Batch API is ~50% cheaper but is a different, asynchronous endpoint;
# the `batch` command here is a sequential loop over the standard endpoint.
PRICE_PER_IMAGE_USD: dict[str, float] = {"1K": 0.134, "2K": 0.134, "4K": 0.24}

# HTTP status codes worth retrying: 429 = rate limit (RESOURCE_EXHAUSTED),
# 5xx = transient server-side failures. Everything else (400 invalid argument,
# 403 permission, 404 model not found) is a hard error — retrying only wastes time.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class AspectRatio(StrEnum):
    """Supported aspect ratios for image generation."""

    SQUARE = "1:1"
    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_3_2 = "3:2"
    PORTRAIT_3_4 = "3:4"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_4_5 = "4:5"
    LANDSCAPE_5_4 = "5:4"
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_16_9 = "16:9"
    ULTRAWIDE = "21:9"


class Resolution(StrEnum):
    """Supported resolutions for image generation."""

    RES_1K = "1K"
    RES_2K = "2K"
    RES_4K = "4K"


class OutputFormat(StrEnum):
    """Supported output image formats."""

    WEBP = "webp"
    PNG = "png"
    JPEG = "jpeg"


# Valid values for validation
VALID_ASPECT_RATIOS: set[str] = {ratio.value for ratio in AspectRatio}
VALID_RESOLUTIONS: set[str] = {res.value for res in Resolution}
VALID_OUTPUT_FORMATS: set[str] = {fmt.value for fmt in OutputFormat}

# Supported image formats for reference images
SUPPORTED_IMAGE_FORMATS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

# Type aliases
AspectRatioType = Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
ResolutionType = Literal["1K", "2K", "4K"]
OutputFormatType = Literal["webp", "png", "jpeg"]


class ConfigError(Exception):
    """Configuration-related errors."""

    pass


def get_api_key() -> str:
    """
    Get the Gemini API key from environment.

    Returns:
        The API key string.

    Raises:
        ConfigError: If the API key is not set.
    """
    api_key = os.environ.get(GEMINI_API_KEY_ENV)
    if not api_key:
        raise ConfigError(
            f"Missing API key. Set the {GEMINI_API_KEY_ENV} environment variable "
            f"or add it to a .env file."
        )
    return api_key


def validate_aspect_ratio(aspect_ratio: str) -> str:
    """
    Validate an aspect ratio string.

    Args:
        aspect_ratio: The aspect ratio to validate.

    Returns:
        The validated aspect ratio.

    Raises:
        ValueError: If the aspect ratio is invalid.
    """
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        valid_options = ", ".join(sorted(VALID_ASPECT_RATIOS))
        raise ValueError(
            f"Invalid aspect ratio '{aspect_ratio}'. Valid options: {valid_options}"
        )
    return aspect_ratio


def validate_resolution(resolution: str) -> str:
    """
    Validate a resolution string.

    Args:
        resolution: The resolution to validate.

    Returns:
        The validated resolution.

    Raises:
        ValueError: If the resolution is invalid.
    """
    if resolution not in VALID_RESOLUTIONS:
        valid_options = ", ".join(sorted(VALID_RESOLUTIONS))
        raise ValueError(f"Invalid resolution '{resolution}'. Valid options: {valid_options}")
    return resolution


def ensure_output_dir(output_dir: Path) -> Path:
    """
    Ensure the output directory exists.

    Args:
        output_dir: The output directory path.

    Returns:
        The output directory path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def validate_output_format(output_format: str) -> str:
    """
    Validate an output format string.

    Args:
        output_format: The output format to validate.

    Returns:
        The validated output format.

    Raises:
        ValueError: If the output format is invalid.
    """
    if output_format not in VALID_OUTPUT_FORMATS:
        valid_options = ", ".join(sorted(VALID_OUTPUT_FORMATS))
        raise ValueError(
            f"Invalid output format '{output_format}'. Valid options: {valid_options}"
        )
    return output_format


def estimate_cost(resolution: str, count: int = 1) -> float:
    """
    Estimate the USD cost of generating images at a given resolution.

    Nano Banana Pro is billed per image, not per token, so the estimate is exact
    for successful generations. Failed attempts are not billed and are excluded
    by the caller.

    Args:
        resolution: The resolution ("1K", "2K", "4K").
        count: Number of images.

    Returns:
        Estimated cost in USD.
    """
    return PRICE_PER_IMAGE_USD.get(resolution, PRICE_PER_IMAGE_USD[DEFAULT_RESOLUTION]) * count


def is_retryable_error(error: Exception) -> bool:
    """
    Decide whether a failed API call is worth retrying.

    Retries 429 (rate limit) and 5xx (transient server errors) plus network-level
    failures. Hard errors — invalid arguments, bad API key, missing model — are not
    retried, because the same request will fail identically every time.

    Args:
        error: The exception raised by the API call.

    Returns:
        True if the call should be retried.
    """
    code = getattr(error, "code", None)
    if isinstance(code, int):
        return code in RETRYABLE_STATUS_CODES

    # Network-level failures carry no status code but are usually transient.
    transient_markers = ("timeout", "timed out", "connection", "temporarily unavailable")
    message = str(error).lower()
    return any(marker in message for marker in transient_markers)


def validate_reference_path(reference_path: Path) -> Path:
    """
    Validate a reference image path.

    Args:
        reference_path: Path to the reference image.

    Returns:
        The validated path.

    Raises:
        ValueError: If the file doesn't exist or has unsupported format.
    """
    if not reference_path.exists():
        raise ValueError(f"Reference image not found: {reference_path}")

    if not reference_path.is_file():
        raise ValueError(f"Reference path is not a file: {reference_path}")

    suffix = reference_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        valid_formats = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        raise ValueError(
            f"Unsupported image format '{suffix}'. Supported formats: {valid_formats}"
        )

    return reference_path
