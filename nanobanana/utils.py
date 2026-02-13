"""Utility functions for Nanobanana CLI."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Sanitize text to be used as a filename.

    Args:
        text: The text to sanitize.
        max_length: Maximum length of the resulting string.

    Returns:
        A sanitized string safe for use in filenames.
    """
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase and replace spaces/special chars with underscores
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)

    # Remove leading/trailing underscores
    text = text.strip("_")

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rstrip("_")

    return text or "image"


def generate_filename(
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    custom_name: str | None = None,
    output_format: str = "webp",
) -> str:
    """
    Generate a filename for the output image.

    Args:
        prompt: The generation prompt.
        aspect_ratio: The aspect ratio (e.g., "16:9").
        resolution: The resolution (e.g., "2K").
        custom_name: Optional custom name to use instead of prompt-based name.
        output_format: Output image format used as file extension.

    Returns:
        A filename string (without directory path).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use custom name or derive from prompt
    if custom_name:
        base_name = sanitize_filename(custom_name)
    else:
        base_name = sanitize_filename(prompt)

    # Format aspect ratio for filename (e.g., "16:9" -> "16x9")
    ratio_str = aspect_ratio.replace(":", "x")

    # Map format to file extension
    ext = "jpg" if output_format == "jpeg" else output_format

    return f"{base_name}_{ratio_str}_{resolution}_{timestamp}.{ext}"


def get_output_path(
    output_dir: Path,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    custom_name: str | None = None,
    output_format: str = "webp",
) -> Path:
    """
    Get the full output path for an image.

    Args:
        output_dir: The output directory.
        prompt: The generation prompt.
        aspect_ratio: The aspect ratio.
        resolution: The resolution.
        custom_name: Optional custom name.
        output_format: Output image format.

    Returns:
        The full path for the output file.
    """
    filename = generate_filename(prompt, aspect_ratio, resolution, custom_name, output_format)
    return output_dir / filename


def truncate_prompt(prompt: str, max_length: int = 60) -> str:
    """
    Truncate a prompt for display purposes.

    Args:
        prompt: The prompt to truncate.
        max_length: Maximum length.

    Returns:
        Truncated prompt with ellipsis if needed.
    """
    if len(prompt) <= max_length:
        return prompt
    return prompt[: max_length - 3] + "..."
