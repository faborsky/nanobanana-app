"""Core image generation module using Gemini API."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from google import genai
from google.genai import types
from rich.console import Console

from nanobanana.config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_RETRY_MAX_DELAY,
    MODEL_NAME,
    estimate_cost,
    get_api_key,
    is_retryable_error,
    validate_aspect_ratio,
    validate_output_format,
    validate_reference_path,
    validate_resolution,
)
from nanobanana.utils import get_output_path

if TYPE_CHECKING:
    from PIL import Image as PILImage

from PIL import Image

console = Console()


@dataclass
class GenerationResult:
    """Result of an image generation attempt."""

    success: bool
    output_path: Path | None = None
    error_message: str | None = None
    text_response: str | None = None
    cost_usd: float = 0.0
    attempts: int = 0


class ImageGenerationError(Exception):
    """Error during image generation."""

    pass


class ImageGenerator:
    """
    Wrapper for Gemini image generation API.

    Handles API communication, retry logic, and image saving.
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    ) -> None:
        """
        Initialize the image generator.

        Args:
            max_retries: Maximum number of retry attempts for failed requests.
            retry_base_delay: Base delay in seconds for exponential backoff.

        Raises:
            ConfigError: If the API key is not configured.
        """
        self._api_key = get_api_key()
        self._client = genai.Client(api_key=self._api_key)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    def generate(
        self,
        prompt: str,
        aspect_ratio: str,
        resolution: str,
        output_dir: Path,
        custom_name: str | None = None,
        reference_path: Path | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> GenerationResult:
        """
        Generate an image from a text prompt with optional reference image.

        Args:
            prompt: The text prompt describing the image to generate.
            aspect_ratio: The aspect ratio (e.g., "16:9").
            resolution: The resolution (e.g., "2K").
            output_dir: Directory to save the generated image.
            custom_name: Optional custom filename (without extension).
            reference_path: Optional path to a reference image.
            output_format: Output image format (webp, png, jpeg).

        Returns:
            GenerationResult with success status and output path or error.
        """
        # Validate parameters
        try:
            validate_aspect_ratio(aspect_ratio)
            validate_resolution(resolution)
            validate_output_format(output_format)
            if reference_path:
                validate_reference_path(reference_path)
        except ValueError as e:
            return GenerationResult(success=False, error_message=str(e))

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load reference image if provided
        reference_image: Image.Image | None = None
        if reference_path:
            reference_image = self._load_reference_image(reference_path)

        # Attempt generation with retries
        last_error: str | None = None
        for attempt in range(self._max_retries):
            try:
                result = self._generate_with_api(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                    output_dir=output_dir,
                    custom_name=custom_name,
                    reference_image=reference_image,
                    output_format=output_format,
                )
                result.cost_usd = estimate_cost(resolution)
                result.attempts = attempt + 1
                return result

            except Exception as e:
                last_error = str(e)

                # Content filtering is a verdict on the prompt — retrying is pointless.
                if "blocked" in last_error.lower() or "safety" in last_error.lower():
                    return GenerationResult(
                        success=False,
                        error_message=f"Content filtered: {last_error}",
                        attempts=attempt + 1,
                    )

                # Hard errors (invalid argument, bad key, unknown model) fail identically
                # on every attempt — surface them immediately instead of burning retries.
                if not is_retryable_error(e):
                    return GenerationResult(
                        success=False,
                        error_message=last_error,
                        attempts=attempt + 1,
                    )

                if attempt < self._max_retries - 1:
                    delay = self._backoff_delay(attempt)
                    console.print(
                        f"[yellow]Attempt {attempt + 1} failed ({last_error[:80]}), "
                        f"retrying in {delay:.1f}s...[/yellow]"
                    )
                    time.sleep(delay)

        return GenerationResult(
            success=False,
            error_message=f"Failed after {self._max_retries} attempts: {last_error}",
            attempts=self._max_retries,
        )

    def _backoff_delay(self, attempt: int) -> float:
        """
        Exponential backoff with jitter, capped at DEFAULT_RETRY_MAX_DELAY.

        Jitter keeps concurrent batch runs from retrying in lockstep and hitting the
        same rate limit again together — the strategy both Google and OpenAI recommend.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Delay in seconds.
        """
        delay = min(self._retry_base_delay * (2**attempt), DEFAULT_RETRY_MAX_DELAY)
        return delay * (0.5 + random.random() * 0.5)

    def _load_reference_image(self, reference_path: Path) -> Image.Image:
        """
        Load a reference image from disk.

        Args:
            reference_path: Path to the reference image.

        Returns:
            PIL Image object.

        Raises:
            ImageGenerationError: If the image cannot be loaded.
        """
        try:
            return Image.open(reference_path)
        except Exception as e:
            raise ImageGenerationError(f"Failed to load reference image: {e}") from e

    def _generate_with_api(
        self,
        prompt: str,
        aspect_ratio: str,
        resolution: str,
        output_dir: Path,
        custom_name: str | None,
        reference_image: Image.Image | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> GenerationResult:
        """
        Make the actual API call to generate an image.

        Args:
            prompt: The generation prompt.
            aspect_ratio: The aspect ratio.
            resolution: The resolution.
            output_dir: Output directory.
            custom_name: Optional custom name.
            reference_image: Optional reference image for multimodal input.

        Returns:
            GenerationResult with the outcome.

        Raises:
            ImageGenerationError: If the API call fails.
        """
        # Build contents: text prompt + optional reference image
        contents: list[str | Image.Image] = [prompt]
        if reference_image:
            contents.append(reference_image)

        response = self._client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                )
            ),
        )

        # Process response parts
        text_response: str | None = None
        saved_image: PILImage | None = None
        output_path: Path | None = None

        for part in response.parts:
            if part.text is not None:
                text_response = part.text
            elif (image := part.as_image()) is not None:
                saved_image = image

        if saved_image is None:
            raise ImageGenerationError(
                f"No image in response. Text response: {text_response or 'None'}"
            )

        # Save the image in the requested format
        output_path = get_output_path(
            output_dir=output_dir,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            custom_name=custom_name,
            output_format=output_format,
        )

        # Gemini SDK's as_image() returns a wrapper with .save(path) only,
        # not a standard PIL Image. Convert via temp PNG first, then re-open
        # as PIL for format-specific saving with quality params.
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            saved_image.save(tmp.name)
            with Image.open(tmp.name) as pil_image:
                if output_format == "png":
                    pil_image.save(output_path, "PNG")
                elif output_format == "webp":
                    pil_image.save(output_path, "WEBP", quality=90)
                elif output_format == "jpeg":
                    rgb_image = pil_image.convert("RGB") if pil_image.mode == "RGBA" else pil_image
                    rgb_image.save(output_path, "JPEG", quality=95)

        return GenerationResult(
            success=True,
            output_path=output_path,
            text_response=text_response,
        )
