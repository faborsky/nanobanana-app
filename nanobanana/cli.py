"""CLI entry point for Nanobanana."""

from __future__ import annotations

import json as jsonlib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from nanobanana import __version__
from nanobanana.config import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_RESOLUTION,
    MODELS,
    SUPPORTED_IMAGE_FORMATS,
    VALID_ASPECT_RATIOS,
    VALID_MODELS,
    VALID_OUTPUT_FORMATS,
    VALID_RESOLUTIONS,
    VALID_THINKING_LEVELS,
    ConfigError,
)
from nanobanana.generator import ImageGenerator

app = typer.Typer(
    name="nanobanana",
    help="CLI for image generation using Google's Nano Banana models (2.1, Pro, Lite).",
    add_completion=False,
)
console = Console()

# Human-readable output goes to stderr so that --json keeps stdout clean and parseable.
err_console = Console(stderr=True)


def emit_json(payload: dict[str, object]) -> None:
    """Print a machine-readable result to stdout."""
    print(jsonlib.dumps(payload, ensure_ascii=False, indent=2))


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        default = MODELS[DEFAULT_MODEL].model_id
        console.print(f"nanobanana {__version__} (default model: {default})")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """CLI for image generation using Google's Nano Banana models (2.1, Pro, Lite)."""


def validate_aspect_ratio_callback(value: str) -> str:
    """Validate aspect ratio CLI argument."""
    if value not in VALID_ASPECT_RATIOS:
        valid_options = ", ".join(sorted(VALID_ASPECT_RATIOS))
        raise typer.BadParameter(f"Invalid aspect ratio. Valid options: {valid_options}")
    return value


def validate_resolution_callback(value: str) -> str:
    """Validate resolution CLI argument."""
    if value not in VALID_RESOLUTIONS:
        valid_options = ", ".join(sorted(VALID_RESOLUTIONS))
        raise typer.BadParameter(f"Invalid resolution. Valid options: {valid_options}")
    return value


def validate_model_callback(value: str) -> str:
    """Validate model alias CLI argument."""
    if value not in VALID_MODELS:
        raise typer.BadParameter(f"Invalid model. Valid options: {', '.join(sorted(VALID_MODELS))}")
    return value


def validate_thinking_callback(value: str | None) -> str | None:
    """Validate thinking level CLI argument."""
    if value is not None and value not in VALID_THINKING_LEVELS:
        valid_options = ", ".join(sorted(VALID_THINKING_LEVELS))
        raise typer.BadParameter(f"Invalid thinking level. Valid options: {valid_options}")
    return value


def validate_format_callback(value: str) -> str:
    """Validate output format CLI argument."""
    if value not in VALID_OUTPUT_FORMATS:
        valid_options = ", ".join(sorted(VALID_OUTPUT_FORMATS))
        raise typer.BadParameter(f"Invalid output format. Valid options: {valid_options}")
    return value


def validate_reference_callback(value: Path | None) -> Path | None:
    """Validate reference image CLI argument."""
    if value is None:
        return None

    if not value.exists():
        raise typer.BadParameter(f"Reference image not found: {value}")

    if not value.is_file():
        raise typer.BadParameter(f"Reference path is not a file: {value}")

    suffix = value.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        valid_formats = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        raise typer.BadParameter(f"Unsupported image format. Valid formats: {valid_formats}")

    return value


@app.command()
def generate(
    prompt: Annotated[str, typer.Argument(help="Text prompt for image generation")],
    aspect: Annotated[
        str,
        typer.Option(
            "--aspect",
            "-a",
            help="Aspect ratio (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9; "
            "2.1 only: 1:4, 4:1, 1:8, 8:1)",
            callback=validate_aspect_ratio_callback,
        ),
    ] = DEFAULT_ASPECT_RATIO,
    resolution: Annotated[
        str,
        typer.Option(
            "--resolution",
            "-r",
            help="Resolution (1K, 2K, 4K)",
            callback=validate_resolution_callback,
        ),
    ] = DEFAULT_RESOLUTION,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory",
        ),
    ] = DEFAULT_OUTPUT_DIR,
    name: Annotated[
        str | None,
        typer.Option(
            "--name",
            "-n",
            help="Custom filename (without extension)",
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format (webp, png, jpeg)",
            callback=validate_format_callback,
        ),
    ] = DEFAULT_OUTPUT_FORMAT,
    reference: Annotated[
        Path | None,
        typer.Option(
            "--reference",
            "-ref",
            help="Reference image for style/content guidance",
            callback=validate_reference_callback,
        ),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="Model: 2.1 (Nano Banana 2.1), pro (Nano Banana Pro), lite (Nano Banana 2 Lite)",
            callback=validate_model_callback,
        ),
    ] = DEFAULT_MODEL,
    thinking: Annotated[
        str | None,
        typer.Option(
            "--thinking",
            "-t",
            help="Thinking level (2.1: minimal/medium/high, default medium; lite: minimal/high)",
            callback=validate_thinking_callback,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit a machine-readable JSON result on stdout",
        ),
    ] = False,
) -> None:
    """Generate a single image from a text prompt with optional reference image."""
    out = err_console if json_output else console

    try:
        generator = ImageGenerator()
    except ConfigError as e:
        if json_output:
            emit_json({"error": str(e)})
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    out.print("[blue]Generating image...[/blue]")
    out.print(f"  Model: {MODELS[model].label}" + (f" (thinking: {thinking})" if thinking else ""))
    out.print(f"  Prompt: {prompt}")
    out.print(f"  Aspect ratio: {aspect}")
    out.print(f"  Resolution: {resolution}")
    out.print(f"  Format: {format.upper()}")
    if reference:
        out.print(f"  Reference: {reference}")

    result = generator.generate(
        prompt=prompt,
        aspect_ratio=aspect,
        resolution=resolution,
        output_dir=output,
        custom_name=name,
        reference_path=reference,
        output_format=format,
        model=model,
        thinking=thinking,
    )

    if result.success:
        if json_output:
            emit_json(
                {
                    "success": True,
                    "output_path": str(result.output_path),
                    "aspect_ratio": aspect,
                    "resolution": resolution,
                    "format": format,
                    "cost_usd": round(result.cost_usd, 4),
                    "attempts": result.attempts,
                    "seconds": round(result.seconds, 1),
                    "model": result.model_id,
                    "thinking": thinking,
                    "text_response": result.text_response,
                }
            )
        else:
            console.print(f"[green]Image saved to: {result.output_path}[/green]")
            console.print(f"[dim]Cost: ${result.cost_usd:.4f} · {result.seconds:.1f}s[/dim]")
            if result.text_response:
                console.print(f"[dim]Model response: {result.text_response}[/dim]")
    else:
        if json_output:
            emit_json({"success": False, "error": result.error_message})
        else:
            console.print(f"[red]Generation failed: {result.error_message}[/red]")
        raise typer.Exit(code=1)


@app.command()
def batch(
    job_file: Annotated[Path, typer.Argument(help="Path to the batch job JSON file")],
    delay: Annotated[
        float,
        typer.Option(
            "--delay",
            "-d",
            help="Delay between requests in seconds",
        ),
    ] = DEFAULT_DELAY_SECONDS,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory (overrides job file defaults)",
        ),
    ] = DEFAULT_OUTPUT_DIR,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit a machine-readable JSON summary on stdout",
        ),
    ] = False,
) -> None:
    """Run a batch job from a JSON file."""
    from nanobanana.batch import run_batch

    if not job_file.exists():
        if json_output:
            emit_json({"error": f"Job file not found: {job_file}"})
        else:
            console.print(f"[red]Job file not found: {job_file}[/red]")
        raise typer.Exit(code=1)

    try:
        generator = ImageGenerator()
    except ConfigError as e:
        if json_output:
            emit_json({"error": str(e)})
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    success = run_batch(
        job_file=job_file,
        generator=generator,
        output_dir=output,
        delay=delay,
        json_output=json_output,
    )

    if not success:
        raise typer.Exit(code=1)


@app.command()
def validate(
    job_file: Annotated[Path, typer.Argument(help="Path to the batch job JSON file")],
) -> None:
    """Validate a batch job JSON file."""
    from nanobanana.batch import validate_job_file

    if not job_file.exists():
        console.print(f"[red]Job file not found: {job_file}[/red]")
        raise typer.Exit(code=1)

    errors = validate_job_file(job_file)

    if errors:
        console.print("[red]Validation failed:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise typer.Exit(code=1)
    else:
        console.print("[green]Validation passed![/green]")


@app.command()
def describe(
    image_path: Annotated[
        Path,
        typer.Argument(help="Path to the image to describe"),
    ],
    detailed: Annotated[
        bool,
        typer.Option(
            "--detailed",
            "-d",
            help="Generate a more detailed description suitable for image generation prompts",
        ),
    ] = False,
) -> None:
    """Analyze an image and generate a text description suitable as a prompt."""
    from google import genai

    from nanobanana.config import DESCRIBE_MODEL_NAME, get_api_key

    if not image_path.exists():
        console.print(f"[red]Image not found: {image_path}[/red]")
        raise typer.Exit(code=1)

    suffix = image_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        valid_formats = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        console.print(f"[red]Unsupported format. Valid: {valid_formats}[/red]")
        raise typer.Exit(code=1)

    try:
        api_key = get_api_key()
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print(f"[blue]Analyzing image: {image_path}[/blue]")

    from PIL import Image

    try:
        image = Image.open(image_path)
    except Exception as e:
        console.print(f"[red]Failed to load image: {e}[/red]")
        raise typer.Exit(code=1) from e

    client = genai.Client(api_key=api_key)

    if detailed:
        prompt = (
            "Analyze this image in detail and create a comprehensive text description "
            "that could be used as a prompt for AI image generation. Include:\n"
            "- Main subject and composition\n"
            "- Art style, visual aesthetic, and technique\n"
            "- Color palette and lighting\n"
            "- Mood and atmosphere\n"
            "- Background and environment details\n"
            "- Any notable textures or patterns\n\n"
            "Format the description as a single, flowing paragraph suitable for "
            "use as an image generation prompt."
        )
    else:
        prompt = (
            "Describe this image concisely, focusing on the main subject, "
            "style, and visual characteristics. Keep it under 100 words."
        )

    try:
        response = client.models.generate_content(
            model=DESCRIBE_MODEL_NAME,
            contents=[prompt, image],
        )
        description = response.text
    except Exception as e:
        console.print(f"[red]Failed to analyze image: {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print()
    console.print("[green]Description:[/green]")
    console.print(description)


if __name__ == "__main__":
    app()
