# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-10-11

### Added

- **Model choice: `-m` / `--model` with `2.1`, `pro`, `lite`** (and `"model"` in
  batch defaults or per job). Each model has a spec in `config.MODELS`: API ID,
  supported ratios, resolutions, thinking levels and token prices.
  - `2.1` → `gemini-nano-banana-2.1` (Nano Banana 2.1, GA 2026-10-06) — **new default**
  - `pro` → `gemini-3-pro-image` (Nano Banana Pro) — the previous default
  - `lite` → `gemini-3.1-flash-lite-image` (Nano Banana 2 Lite, 1K only)
- **Panoramic aspect ratios `1:4`, `4:1`, `1:8`, `8:1`** (Nano Banana 2.1 only).
- **`-t` / `--thinking`** — `minimal` / `medium` / `high` on 2.1 (default
  `medium`), `minimal` / `high` on Lite. Pro has no configurable thinking.
- **Real cost from usage metadata.** `cost_usd` is now computed from the tokens
  the API actually billed (prompt + image + text/thinking), not from the
  per-image list price. Falls back to the list price if usage is missing.
- `--json` adds `seconds` and `thinking`; batch JSON adds per-image `model`,
  `cost_usd`, `seconds`.
- `validate` checks that each job's ratio / resolution / thinking level is
  supported by the model that job resolves to.

### Changed

- **Default model is Nano Banana 2.1** (was Nano Banana Pro). At 2K it costs
  $0.0504 vs $0.134 — see README for when Pro is still worth it.
- **Default resolution is 2K** (was 1K).
- `describe` uses `gemini-3.8-flash` — `gemini-3.5-flash` was deprecated on
  2026-10-08 and is auto-routed to 3.6.
- Interim "thought" images in the response are skipped explicitly; only the
  final render is saved.

## [1.0.1] — 2026-07-25

### Fixed

- **`--json` no longer emits invalid JSON when a request is retried.** Retry
  notices from `generator.py` were printed to stdout, so any retried call
  interleaved human text with the JSON payload and broke parsing. They now go to
  stderr, where diagnostics belong — stdout stays a clean, parseable result.

  Found while an OpenAI-wide outage made every call retry, which is exactly the
  condition that triggers it. A regression test asserts the generator console
  writes to stderr.

## [1.0.0] — 2026-07-25

First production release. The tool becomes safe to hand to someone else: correct model IDs, honest cost reporting, retry logic that doesn't waste quota, a documented API surface, and a bundled Claude Code skill.

### Added

- **Cost reporting.** `PRICE_PER_IMAGE_USD` and `estimate_cost()` in `config.py`, sourced from the official pricing page. `generate` prints the cost of each image; `batch` prints the total. Failed generations aren't billed and aren't counted.
- **`--json` output** for `generate` and `batch`. The result goes to stdout as JSON; all human-readable output moves to stderr, so output can be piped safely. Errors come back as `{"success": false, "error": …}` with a non-zero exit code.
- **`--version` / `-V`**, reporting the version and the active model ID.
- **Retry classification** (`is_retryable_error()`): 429 and 5xx plus network timeouts are retried; 400/401/403/404 fail immediately.
- **Jitter on backoff** — `min(base * 2**attempt, 60) * uniform(0.5, 1.0)`, as recommended by both Google and OpenAI, so parallel runs don't retry in lockstep after a shared rate limit.
- **Test suite** (`tests/`): offline coverage of validators, pricing, retry classification, filename generation and batch job parsing. No API calls. One test asserts the published price table so a price change fails the suite instead of silently misreporting cost.
- **`docs/api-notes.md`** — model lifecycle, response shape, the `as_image()` trap, error codes, IPM rate limiting, pricing including the Batch API comparison, and the known gaps in this CLI.
- **Bundled Claude Code skill** in `skill/` — `skill/nanobanana/SKILL.md` plus a Czech install guide (`skill/INSTALL.md`), so an agent driving this tool knows the pricing, formats, prompting rules and capabilities.
- **Prompting guide** in README, based on Google's official Nano Banana guide: the `[Subject] + [Action] + [Context] + [Composition] + [Style]` formula, a DO/DON'T table, text-in-image rules and consistency tips.
- **`jobs/example.json`** — a working three-job batch file.
- **LICENSE** (MIT).

### Changed

- **`describe` now uses `gemini-3.5-flash`.** The previous `gemini-2.0-flash` was shut down on 2026-06-01, which had broken the command outright.
- **Generation uses the GA model ID `gemini-3-pro-image`.** The previous `gemini-3-pro-image-preview` was retired on 2026-06-25.
- `setup.sh` accepts any Python 3.11+ interpreter instead of requiring exactly `python3.12`, and reports which one it selected.
- Enums moved from `(str, Enum)` to `StrEnum`.
- README rewritten as a full reference (setup, commands, pricing, JSON, prompting, rate limits, troubleshooting); CLAUDE.md rewritten as a lean signpost with a documentation map.
- Author metadata in `pyproject.toml` corrected; package classified as Production/Stable.

### Fixed

- **Retries no longer burn quota on unretryable failures.** Previously every error got three attempts, so a retired model ID or an invalid argument took three round-trips to surface.
- Removed a dead `import io` in `generator.py` and an unused `import sys` in `batch.py`.
- Batch progress output honours the injected console, so `--json` keeps stdout clean even while the progress bar renders.
- `.gitignore` now covers `.claude/settings.local.json` and `output/*.webp`.

### Security

- `.env` is gitignored and has never been committed; `.env.example` carries no real key. Verified against the full git history.
