# Nanobanana — CLI for Google's Nano Banana image models

Python CLI that generates images through Google's Nano Banana models — **Nano Banana 2.1** (default), **Nano Banana Pro** and **Nano Banana 2 Lite**. Built to be driven by a human **and** by an AI agent: `--json` I/O, parseable errors, per-image cost reporting, and retry logic that distinguishes transient failures from hard ones.

## Setup

```bash
./setup.sh                    # finds Python 3.11+, creates .venv, installs the package
./run.sh <command> [flags]    # activates .venv and runs the CLI from any directory
```

`GEMINI_API_KEY` lives in `.env` (gitignored, template in `.env.example`). Image generation is a paid feature — the key's project needs billing enabled.

## Code structure

| File | Responsibility |
|---|---|
| `nanobanana/config.py` | **Model registry (`MODELS`)**, defaults, enums, validators, **pricing + `cost_from_usage()`**, **retry classification** |
| `nanobanana/generator.py` | The API call, retry/backoff with jitter, real cost from usage metadata, format-specific saving |
| `nanobanana/batch.py` | Job file parse/validate, sequential runner, cost totals |
| `nanobanana/cli.py` | Typer commands (`generate`, `batch`, `validate`, `describe`), human + `--json` output |
| `nanobanana/utils.py` | Filename sanitising (diacritics → ASCII) and timestamped naming |

## Commands

**Full flag reference + worked examples: [README.md](README.md).**

- `generate "PROMPT"` — one image. `-m` model (`2.1`/`pro`/`lite`), `-t` thinking, `-a` ratio, `-r` resolution, `-f` format, `-o` dir, `-n` name, `-ref` reference, `--json`
- `batch <job.json>` — many images sequentially. `-o` dir, `-d` delay, `--json`
- `validate <job.json>` — offline structural check, **no API calls, no cost**
- `describe <image>` — analyse an image into a reusable prompt. `--detailed` for a fuller version

## Models

`config.MODELS` maps a CLI alias to a `ModelSpec` (API ID, ratios, resolutions, thinking levels, token prices). `DEFAULT_MODEL = "2.1"`.

| Alias | Model ID | Ratios | Resolutions | Thinking |
|---|---|---|---|---|
| `2.1` | `gemini-nano-banana-2.1` (GA 2026-10-06) | 10 standard + `1:4` `4:1` `1:8` `8:1` | 1K 2K 4K | `minimal`/`medium`/`high`, default `medium` |
| `pro` | `gemini-3-pro-image` | 10 standard | 1K 2K 4K | not configurable |
| `lite` | `gemini-3.1-flash-lite-image` | 10 standard | 1K | `minimal`/`high` |

`DESCRIBE_MODEL_NAME = "gemini-3.8-flash"` (vision model behind `describe`).

All verified live against `models.list()` + a real call on 2026-10-11. **Model IDs are the single most common way this tool breaks** — `gemini-3-pro-image-preview` retired 2026-06-25, `gemini-2.0-flash` shut down 2026-06-01, `gemini-3.5-flash` deprecated 2026-10-08, `gemini-3.1-flash-image` (Nano Banana 2) deprecated 2026-10-06 in favour of 2.1. If generation starts failing with 404, check the IDs first.

The 2.1 docs show the new **Interactions API** (`client.interactions.create`, `response_format`); this CLI keeps `generate_content` + `ImageConfig` + `ThinkingConfig(thinking_level=…)`, which works for 2.1 (verified).

## Pricing (built into the code)

All image models bill **per token**. Each `ModelSpec` carries the list per-image price (`price_per_image_usd`, used by `estimate_cost()` for up-front estimates) and token rates (used by `cost_from_usage()` for the receipt). `cost_usd` in results comes from the API's `usage_metadata` — prompt + image + text/thinking tokens — so it is exact, and on 2.1 it's **20–36 % above list** because of thinking tokens (2K list $0.0504, measured $0.060–0.068). Falls back to the list price if usage is missing.

List prices, 2K: 2.1 $0.0504 · Pro $0.134 · Lite (1K) $0.0336. See [docs/benchmark-2026-10.md](docs/benchmark-2026-10.md) for measured costs.

## ⚠️ Critical for automation (read before scripting)

- **`--json` writes only the result to stdout; all prose goes to stderr.** Parse stdout, never mix the two. On failure you get `{"success": false, "error": …}` and a non-zero exit code.
- **Retry classification lives in `is_retryable_error()`.** 429 + 5xx and network timeouts retry with exponential backoff **plus jitter** (capped 60 s). 400/401/403/404 fail immediately — retrying an invalid argument or a bad key wastes quota and time. Safety-filtered prompts return `Content filtered` and are never retried.
- **Run `validate` before any large batch.** It's free and offline; a typo in a 50-image job file otherwise costs real money before it fails.
- **Image models are metered in IPM (images per minute)**, not just RPM/TPM. If a batch hits 429 repeatedly, raise `--delay` rather than adding parallelism.
- **The Gemini SDK's `part.as_image()` is NOT a `PIL.Image`.** It's a wrapper whose `.save(path)` only takes a file path and derives the format from the extension. To use PIL features (quality params, mode conversion), save to a temp PNG first, then reopen with `PIL.Image.open()` — `generator.py` already does this.
- **One reference image per job.** The models accept more (2.1: 10 objects + 4 characters; Pro: 6 objects + 5 characters + 3 style refs); this CLI passes a single `-ref` / `reference_path`.
- **Model × parameter compatibility is validated before any call** (`validate_for_model()`): 8:1 on Pro, 2K on Lite or `-t` on Pro fail immediately and free, also in `validate`.
- **Interim thought images** come back as parts with `part.thought = True`; the generator skips them and saves only the final render.
- **`DEFAULT_OUTPUT_DIR` is `./output`.** Agents should pass `-o` explicitly rather than relying on the default.

## Prompting rules that change output quality

Full guide with examples in [README.md](README.md#prompting-guide); the two that matter most:

1. **Narrative scene, not keyword list.** The model reasons over the prompt; `[Subject] + [Action] + [Context] + [Composition] + [Style]` beats comma-separated tags.
2. **Positive framing.** "A plain seamless background" works; "no clutter, no text, no logos" often produces exactly what you excluded.

Aspect ratio and resolution belong in the `-a`/`-r` flags, never in the prompt text.

## Testing

```bash
python -m pytest tests/ -q   # offline: validators, model registry, pricing, retry classification, filenames, job parsing
ruff check nanobanana/
```

Tests never touch the API. One test asserts the published price tables of all models, so if Google changes prices the suite fails loudly instead of silently misreporting cost.

## Release checklist

Bump `__version__` in `nanobanana/__init__.py` and `version` in `pyproject.toml` → update README (pricing/commands if changed), this file, `CHANGELOG.md` (new `## [x.y.z] — YYYY-MM-DD` entry) and the bundled skill in `skill/nanobanana/` → run `pytest` + `ruff` → commit → tag `vX.Y.Z` → **GitHub Release from the tag** (`gh release create vX.Y.Z --latest`). A pushed tag alone doesn't appear on /releases.

## Documentation map

- **[README.md](README.md)** — full command reference, pricing, prompting guide, troubleshooting.
- **[docs/benchmark-2026-10.md](docs/benchmark-2026-10.md)** — Nano Banana 2.1 vs Pro vs NB2: panorama 8:1 and Czech text, measured cost and latency.
- **[docs/api-notes.md](docs/api-notes.md)** — how the Gemini image API actually behaves: model lifecycle, rate limits, response shape, gotchas found in live testing.
- **[CHANGELOG.md](CHANGELOG.md)** — version history.
- **`skill/nanobanana/`** — the bundled Claude Code skill (`/nanobanana`): pricing, formats, prompting rules, capabilities. `skill/INSTALL.md` is the Czech install guide for course participants.
