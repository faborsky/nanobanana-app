"""Configuration module for Nanobanana CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
# Multimodal model used by the `describe` command for image analysis.
# gemini-3.5-flash was deprecated on 2026-10-08 (auto-routed to 3.6);
# gemini-3.8-flash is the current Flash model, same price.
DESCRIBE_MODEL_NAME = "gemini-3.8-flash"

# Default values
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_RESOLUTION = "2K"
DEFAULT_OUTPUT_FORMAT = "webp"
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 2.0
DEFAULT_RETRY_MAX_DELAY = 60.0

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
    PORTRAIT_1_4 = "1:4"
    LANDSCAPE_4_1 = "4:1"
    PORTRAIT_1_8 = "1:8"
    LANDSCAPE_8_1 = "8:1"


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

# Aspect ratios every model supports; the panoramic ones are Nano Banana 2.1 only.
STANDARD_ASPECT_RATIOS: frozenset[str] = frozenset(
    {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
)
PANORAMIC_ASPECT_RATIOS: frozenset[str] = frozenset({"1:4", "4:1", "1:8", "8:1"})


@dataclass(frozen=True)
class ModelSpec:
    """
    One Nano Banana model: its API ID, capabilities and token prices.

    Prices are USD per 1M tokens, standard (non-batch) paid tier, from
    https://ai.google.dev/gemini-api/docs/pricing (verified 2026-10-11).
    All image models are billed per token; an output image is a fixed number
    of tokens per resolution, which is where the "per image" prices come from.
    """

    alias: str
    model_id: str
    label: str
    aspect_ratios: frozenset[str]
    resolutions: tuple[str, ...]
    # Published per-image output price — the up-front estimate.
    price_per_image_usd: dict[str, float]
    input_per_m: float
    text_output_per_m: float  # text and thinking tokens
    image_output_per_m: float
    thinking_levels: tuple[str, ...] = ()  # empty = not configurable via the API
    default_thinking: str | None = None


MODELS: dict[str, ModelSpec] = {
    # Nano Banana 2.1 — GA 2026-10-06. Google's "primary workhorse".
    "2.1": ModelSpec(
        alias="2.1",
        model_id="gemini-nano-banana-2.1",
        label="Nano Banana 2.1",
        aspect_ratios=STANDARD_ASPECT_RATIOS | PANORAMIC_ASPECT_RATIOS,
        resolutions=("1K", "2K", "4K"),
        price_per_image_usd={"1K": 0.0336, "2K": 0.0504, "4K": 0.113},
        input_per_m=1.50,
        text_output_per_m=7.50,
        image_output_per_m=30.00,
        thinking_levels=("minimal", "medium", "high"),
        default_thinking="medium",
    ),
    # Nano Banana Pro — premium model for the most complex tasks.
    # The old "gemini-3-pro-image-preview" was retired on 2026-06-25.
    "pro": ModelSpec(
        alias="pro",
        model_id="gemini-3-pro-image",
        label="Nano Banana Pro",
        aspect_ratios=STANDARD_ASPECT_RATIOS,
        resolutions=("1K", "2K", "4K"),
        price_per_image_usd={"1K": 0.134, "2K": 0.134, "4K": 0.24},
        input_per_m=2.00,
        text_output_per_m=12.00,
        image_output_per_m=120.00,
    ),
    # Nano Banana 2 Lite — cheapest and fastest, 1K only, no search grounding.
    "lite": ModelSpec(
        alias="lite",
        model_id="gemini-3.1-flash-lite-image",
        label="Nano Banana 2 Lite",
        aspect_ratios=STANDARD_ASPECT_RATIOS,
        resolutions=("1K",),
        price_per_image_usd={"1K": 0.0336},
        input_per_m=0.25,
        text_output_per_m=1.50,
        image_output_per_m=30.00,
        thinking_levels=("minimal", "high"),
        default_thinking="minimal",
    ),
}
DEFAULT_MODEL = "2.1"
VALID_MODELS: set[str] = set(MODELS)
VALID_THINKING_LEVELS: set[str] = {"minimal", "medium", "high"}


# Supported image formats for reference images
SUPPORTED_IMAGE_FORMATS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

# Type aliases
AspectRatioType = Literal[
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
    "1:4", "4:1", "1:8", "8:1",
]
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


def get_model(alias: str) -> ModelSpec:
    """
    Look up a model by its CLI alias ("2.1", "pro", "lite").

    Raises:
        ValueError: If the alias is unknown.
    """
    if alias not in MODELS:
        raise ValueError(f"Invalid model '{alias}'. Valid options: {', '.join(sorted(MODELS))}")
    return MODELS[alias]


def validate_for_model(
    model: ModelSpec, aspect_ratio: str, resolution: str, thinking: str | None = None
) -> None:
    """
    Check that a model supports the requested ratio, resolution and thinking level.

    Raises:
        ValueError: With a message naming the model and its valid options.
    """
    if aspect_ratio not in model.aspect_ratios:
        hint = " (panoramic ratios need -m 2.1)" if aspect_ratio in PANORAMIC_ASPECT_RATIOS else ""
        raise ValueError(f"{model.label} does not support aspect ratio '{aspect_ratio}'{hint}")
    if resolution not in model.resolutions:
        raise ValueError(
            f"{model.label} does not support resolution '{resolution}'. "
            f"Valid options: {', '.join(model.resolutions)}"
        )
    if thinking is not None and thinking not in model.thinking_levels:
        if not model.thinking_levels:
            raise ValueError(f"{model.label} does not support setting a thinking level")
        raise ValueError(
            f"{model.label} does not support thinking level '{thinking}'. "
            f"Valid options: {', '.join(model.thinking_levels)}"
        )


def estimate_cost(resolution: str, count: int = 1, model: str = DEFAULT_MODEL) -> float:
    """
    Up-front USD estimate from the published per-image price.

    Excludes input and thinking tokens — use `cost_from_usage()` for the
    actual bill of a finished call.

    Args:
        resolution: The resolution ("1K", "2K", "4K").
        count: Number of images.
        model: Model alias.

    Returns:
        Estimated cost in USD.
    """
    prices = get_model(model).price_per_image_usd
    return prices.get(resolution, max(prices.values())) * count


def cost_from_usage(
    model: ModelSpec,
    prompt_tokens: int,
    image_output_tokens: int,
    other_output_tokens: int,
) -> float:
    """
    Actual USD cost of one call from the API's usage metadata.

    `other_output_tokens` covers text and thinking tokens, which are billed at
    the (much cheaper) text output rate. Input images are counted in
    `prompt_tokens` and billed at the input rate.
    """
    return (
        prompt_tokens * model.input_per_m
        + image_output_tokens * model.image_output_per_m
        + other_output_tokens * model.text_output_per_m
    ) / 1_000_000


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
