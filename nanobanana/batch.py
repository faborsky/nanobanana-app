"""Batch processing module for Nanobanana CLI."""

from __future__ import annotations

import json
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from nanobanana.config import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_RESOLUTION,
    SUPPORTED_IMAGE_FORMATS,
    VALID_ASPECT_RATIOS,
    VALID_OUTPUT_FORMATS,
    VALID_RESOLUTIONS,
)
from nanobanana.generator import GenerationResult, ImageGenerator
from nanobanana.utils import truncate_prompt

console = Console()


@dataclass
class JobConfig:
    """Configuration for a single generation job."""

    prompt: str
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    resolution: str = DEFAULT_RESOLUTION
    output_name: str | None = None
    reference_path: Path | None = None
    output_format: str = DEFAULT_OUTPUT_FORMAT


@dataclass
class BatchConfig:
    """Configuration for a batch of jobs."""

    jobs: list[JobConfig] = field(default_factory=list)
    default_aspect_ratio: str = DEFAULT_ASPECT_RATIO
    default_resolution: str = DEFAULT_RESOLUTION
    default_output_format: str = DEFAULT_OUTPUT_FORMAT


@dataclass
class BatchResult:
    """Result summary of a batch run."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    interrupted: bool = False
    results: list[tuple[JobConfig, GenerationResult]] = field(default_factory=list)


class BatchProcessor:
    """Handles batch processing of image generation jobs."""

    def __init__(
        self,
        generator: ImageGenerator,
        output_dir: Path,
        delay: float,
    ) -> None:
        """
        Initialize the batch processor.

        Args:
            generator: The image generator instance.
            output_dir: Directory for output images.
            delay: Delay between requests in seconds.
        """
        self._generator = generator
        self._output_dir = output_dir
        self._delay = delay
        self._interrupted = False

        # Set up signal handler for graceful interrupt
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: object) -> None:
        """Handle Ctrl+C interrupt."""
        self._interrupted = True
        console.print("\n[yellow]Interrupt received, finishing current job...[/yellow]")

    def process(self, batch_config: BatchConfig) -> BatchResult:
        """
        Process a batch of generation jobs.

        Args:
            batch_config: The batch configuration.

        Returns:
            BatchResult with summary of the run.
        """
        result = BatchResult(total=len(batch_config.jobs))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing jobs", total=len(batch_config.jobs))

            for i, job in enumerate(batch_config.jobs):
                if self._interrupted:
                    result.interrupted = True
                    console.print(
                        f"[yellow]Stopped at job {i + 1}/{len(batch_config.jobs)}[/yellow]"
                    )
                    break

                # Update progress description
                prompt_preview = truncate_prompt(job.prompt, 40)
                progress.update(task, description=f"[{i + 1}/{len(batch_config.jobs)}] {prompt_preview}")

                # Generate image
                gen_result = self._generator.generate(
                    prompt=job.prompt,
                    aspect_ratio=job.aspect_ratio,
                    resolution=job.resolution,
                    output_dir=self._output_dir,
                    custom_name=job.output_name,
                    reference_path=job.reference_path,
                    output_format=job.output_format,
                )

                result.results.append((job, gen_result))

                if gen_result.success:
                    result.successful += 1
                else:
                    result.failed += 1
                    console.print(
                        f"\n[red]Failed: {truncate_prompt(job.prompt, 30)} - {gen_result.error_message}[/red]"
                    )

                progress.advance(task)

                # Delay between requests (except for last one)
                if i < len(batch_config.jobs) - 1 and not self._interrupted:
                    time.sleep(self._delay)

        return result


def parse_job_file(job_file: Path) -> BatchConfig:
    """
    Parse a batch job JSON file.

    Args:
        job_file: Path to the JSON file.

    Returns:
        BatchConfig with parsed jobs.

    Raises:
        ValueError: If the file format is invalid.
    """
    with open(job_file, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Job file must be a JSON object")

    if "jobs" not in data:
        raise ValueError("Job file must contain a 'jobs' array")

    # Parse defaults
    defaults = data.get("defaults", {})
    default_aspect = defaults.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    default_resolution = defaults.get("resolution", DEFAULT_RESOLUTION)
    default_format = defaults.get("format", DEFAULT_OUTPUT_FORMAT)

    # Parse jobs
    jobs: list[JobConfig] = []
    for i, job_data in enumerate(data["jobs"]):
        if not isinstance(job_data, dict):
            raise ValueError(f"Job {i + 1} must be an object")

        if "prompt" not in job_data:
            raise ValueError(f"Job {i + 1} missing required 'prompt' field")

        # Parse reference_path if provided
        ref_path: Path | None = None
        if "reference_path" in job_data:
            ref_path = Path(job_data["reference_path"])

        jobs.append(
            JobConfig(
                prompt=job_data["prompt"],
                aspect_ratio=job_data.get("aspect_ratio", default_aspect),
                resolution=job_data.get("resolution", default_resolution),
                output_name=job_data.get("output_name"),
                reference_path=ref_path,
                output_format=job_data.get("format", default_format),
            )
        )

    return BatchConfig(
        jobs=jobs,
        default_aspect_ratio=default_aspect,
        default_resolution=default_resolution,
        default_output_format=default_format,
    )


def validate_job_file(job_file: Path) -> list[str]:
    """
    Validate a batch job JSON file.

    Args:
        job_file: Path to the JSON file.

    Returns:
        List of error messages (empty if valid).
    """
    errors: list[str] = []

    try:
        with open(job_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except OSError as e:
        return [f"Cannot read file: {e}"]

    if not isinstance(data, dict):
        return ["Job file must be a JSON object"]

    if "jobs" not in data:
        errors.append("Missing required 'jobs' array")
        return errors

    if not isinstance(data["jobs"], list):
        errors.append("'jobs' must be an array")
        return errors

    # Validate defaults
    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        errors.append("'defaults' must be an object")
    else:
        if "aspect_ratio" in defaults and defaults["aspect_ratio"] not in VALID_ASPECT_RATIOS:
            errors.append(f"Invalid default aspect_ratio: {defaults['aspect_ratio']}")
        if "resolution" in defaults and defaults["resolution"] not in VALID_RESOLUTIONS:
            errors.append(f"Invalid default resolution: {defaults['resolution']}")
        if "format" in defaults and defaults["format"] not in VALID_OUTPUT_FORMATS:
            errors.append(f"Invalid default format: {defaults['format']}")

    # Validate jobs
    for i, job in enumerate(data["jobs"]):
        job_num = i + 1

        if not isinstance(job, dict):
            errors.append(f"Job {job_num}: must be an object")
            continue

        if "prompt" not in job:
            errors.append(f"Job {job_num}: missing required 'prompt' field")
        elif not isinstance(job["prompt"], str):
            errors.append(f"Job {job_num}: 'prompt' must be a string")
        elif not job["prompt"].strip():
            errors.append(f"Job {job_num}: 'prompt' cannot be empty")

        if "aspect_ratio" in job and job["aspect_ratio"] not in VALID_ASPECT_RATIOS:
            errors.append(f"Job {job_num}: invalid aspect_ratio '{job['aspect_ratio']}'")

        if "resolution" in job and job["resolution"] not in VALID_RESOLUTIONS:
            errors.append(f"Job {job_num}: invalid resolution '{job['resolution']}'")

        if "format" in job and job["format"] not in VALID_OUTPUT_FORMATS:
            errors.append(f"Job {job_num}: invalid format '{job['format']}'")

        if "output_name" in job and not isinstance(job["output_name"], str):
            errors.append(f"Job {job_num}: 'output_name' must be a string")

        if "reference_path" in job:
            if not isinstance(job["reference_path"], str):
                errors.append(f"Job {job_num}: 'reference_path' must be a string")
            else:
                ref_path = Path(job["reference_path"])
                if not ref_path.exists():
                    errors.append(f"Job {job_num}: reference image not found: {ref_path}")
                elif not ref_path.is_file():
                    errors.append(f"Job {job_num}: reference path is not a file: {ref_path}")
                else:
                    suffix = ref_path.suffix.lower()
                    if suffix not in SUPPORTED_IMAGE_FORMATS:
                        valid_formats = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
                        errors.append(
                            f"Job {job_num}: unsupported reference format '{suffix}'. "
                            f"Valid: {valid_formats}"
                        )

    return errors


def run_batch(
    job_file: Path,
    generator: ImageGenerator,
    output_dir: Path,
    delay: float,
) -> bool:
    """
    Run a batch job from a file.

    Args:
        job_file: Path to the job file.
        generator: The image generator.
        output_dir: Output directory.
        delay: Delay between requests.

    Returns:
        True if all jobs succeeded, False otherwise.
    """
    # Validate first
    errors = validate_job_file(job_file)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        return False

    # Parse and process
    try:
        batch_config = parse_job_file(job_file)
    except ValueError as e:
        console.print(f"[red]Error parsing job file: {e}[/red]")
        return False

    if not batch_config.jobs:
        console.print("[yellow]No jobs to process[/yellow]")
        return True

    console.print(f"[blue]Processing {len(batch_config.jobs)} jobs...[/blue]")

    processor = BatchProcessor(
        generator=generator,
        output_dir=output_dir,
        delay=delay,
    )

    result = processor.process(batch_config)

    # Print summary
    console.print()
    if result.interrupted:
        console.print("[yellow]Batch interrupted[/yellow]")

    console.print(f"[green]Successful: {result.successful}[/green]")
    if result.failed > 0:
        console.print(f"[red]Failed: {result.failed}[/red]")

    return result.failed == 0 and not result.interrupted
