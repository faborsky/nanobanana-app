# Nanobanana — CLI for Gemini 3 Pro Image

Python CLI that generates images through Google's **Gemini 3 Pro Image** (Nano Banana Pro). Built to be driven by a human **and** by an AI agent: `--json` I/O, parseable errors, per-image cost reporting, and retry logic that distinguishes transient failures from hard ones.

## Setup

```bash
./setup.sh                    # finds Python 3.11+, creates .venv, installs the package
./run.sh <command> [flags]    # activates .venv and runs the CLI from any directory
```

`GEMINI_API_KEY` lives in `.env` (gitignored, template in `.env.example`). Image generation is a paid feature — the key's project needs billing enabled.

## Code structure

| File | Responsibility |
|---|---|
| `nanobanana/config.py` | Model IDs, defaults, enums, validators, **pricing**, **retry classification** |
| `nanobanana/generator.py` | The API call, retry/backoff with jitter, format-specific saving |
| `nanobanana/batch.py` | Job file parse/validate, sequential runner, cost totals |
| `nanobanana/cli.py` | Typer commands (`generate`, `batch`, `validate`, `describe`), human + `--json` output |
| `nanobanana/utils.py` | Filename sanitising (diacritics → ASCII) and timestamped naming |

## Commands

**Full flag reference + worked examples: [README.md](README.md).**

- `generate "PROMPT"` — one image. `-a` ratio, `-r` resolution, `-f` format, `-o` dir, `-n` name, `-ref` reference, `--json`
- `batch <job.json>` — many images sequentially. `-o` dir, `-d` delay, `--json`
- `validate <job.json>` — offline structural check, **no API calls, no cost**
- `describe <image>` — analyse an image into a reusable prompt. `--detailed` for a fuller version

## Models

```python
MODEL_NAME = "gemini-3-pro-image"        # image generation (GA, not -preview)
DESCRIBE_MODEL_NAME = "gemini-3.5-flash" # vision model behind `describe`
```

Both verified live against `models.list()` on 2026-07-25. **Model IDs are the single most common way this tool breaks** — `gemini-3-pro-image-preview` was retired 2026-06-25 and `gemini-2.0-flash` was shut down 2026-06-01. If generation starts failing with 404, check the IDs first.

## Pricing (built into the code)

`PRICE_PER_IMAGE_USD` in `config.py`: **1K and 2K both $0.134**, 4K $0.24. Billed per image, not per token, so `estimate_cost()` is exact for successful generations. Every `generate` reports its cost; `batch` reports the total. Failures aren't billed and aren't counted.

Because 1K and 2K cost the same, **prefer 2K whenever quality matters** — there is no reason to pay the same for less.

## ⚠️ Critical for automation (read before scripting)

- **`--json` writes only the result to stdout; all prose goes to stderr.** Parse stdout, never mix the two. On failure you get `{"success": false, "error": …}` and a non-zero exit code.
- **Retry classification lives in `is_retryable_error()`.** 429 + 5xx and network timeouts retry with exponential backoff **plus jitter** (capped 60 s). 400/401/403/404 fail immediately — retrying an invalid argument or a bad key wastes quota and time. Safety-filtered prompts return `Content filtered` and are never retried.
- **Run `validate` before any large batch.** It's free and offline; a typo in a 50-image job file otherwise costs real money before it fails.
- **Image models are metered in IPM (images per minute)**, not just RPM/TPM. If a batch hits 429 repeatedly, raise `--delay` rather than adding parallelism.
- **The Gemini SDK's `part.as_image()` is NOT a `PIL.Image`.** It's a wrapper whose `.save(path)` only takes a file path and derives the format from the extension. To use PIL features (quality params, mode conversion), save to a temp PNG first, then reopen with `PIL.Image.open()` — `generator.py` already does this.
- **One reference image per job.** The model itself accepts up to 6 objects + 5 characters; this CLI passes a single `-ref` / `reference_path`.
- **`DEFAULT_OUTPUT_DIR` is `./output`.** Agents should pass `-o` explicitly rather than relying on the default.

## Prompting rules that change output quality

Full guide with examples in [README.md](README.md#prompting-guide); the two that matter most:

1. **Narrative scene, not keyword list.** The model reasons over the prompt; `[Subject] + [Action] + [Context] + [Composition] + [Style]` beats comma-separated tags.
2. **Positive framing.** "A plain seamless background" works; "no clutter, no text, no logos" often produces exactly what you excluded.

Aspect ratio and resolution belong in the `-a`/`-r` flags, never in the prompt text.

## Testing

```bash
python -m pytest tests/ -q   # offline: validators, pricing, retry classification, filenames, job parsing
ruff check nanobanana/
```

Tests never touch the API. One test asserts the published price table, so if Google changes prices the suite fails loudly instead of silently misreporting cost.

## Release checklist

Bump `__version__` in `nanobanana/__init__.py` and `version` in `pyproject.toml` → update README (pricing/commands if changed), this file, `CHANGELOG.md` (new `## [x.y.z] — YYYY-MM-DD` entry) and the bundled skill in `skill/nanobanana/` → run `pytest` + `ruff` → commit → tag `vX.Y.Z` → **GitHub Release from the tag** (`gh release create vX.Y.Z --latest`). A pushed tag alone doesn't appear on /releases.

## Documentation map

- **[README.md](README.md)** — full command reference, pricing, prompting guide, troubleshooting.
- **[docs/api-notes.md](docs/api-notes.md)** — how the Gemini image API actually behaves: model lifecycle, rate limits, response shape, gotchas found in live testing.
- **[CHANGELOG.md](CHANGELOG.md)** — version history.
- **`skill/nanobanana/`** — the bundled Claude Code skill (`/nanobanana`): pricing, formats, prompting rules, capabilities. `skill/INSTALL.md` is the Czech install guide for course participants.
