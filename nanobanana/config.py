"""Configuration module for Nanobanana CLI."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
MODEL_NAME = "gemini-3-pro-image-preview"

# Default values
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_RESOLUTION = "1K"
DEFAULT_OUTPUT_FORMAT = "webp"
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 2.0


class AspectRatio(str, Enum):
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


class Resolution(str, Enum):
    """Supported resolutions for image generation."""

    RES_1K = "1K"
    RES_2K = "2K"
    RES_4K = "4K"


class OutputFormat(str, Enum):
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
