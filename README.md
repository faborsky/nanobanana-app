# Nanobanana

CLI for AI image generation using Google's **Gemini 3 Pro Image** model (Nano Banana Pro). Single images or batches, visual references, image analysis — designed to be driven both by a human and by an AI agent like Claude Code.

Ships with a **[Claude Code skill](skill/INSTALL.md)** so your agent knows the pricing, the formats, the prompting rules, and what the model can and cannot do.

```bash
./run.sh generate "A weathered fisherman mending nets on a wooden dock at golden hour, warm rim light catching the salt spray, documentary photography" -a 16:9 -r 2K
```

- **Per-image pricing built in** — every run reports what it cost.
- **Machine-readable `--json`** on stdout, human output on stderr.
- **Retries only what's worth retrying** — rate limits and server errors, with exponential backoff and jitter. A bad prompt fails immediately instead of burning quota three times.
- **Batch jobs from a JSON file**, with a free offline `validate` dry run.

---

## Contents

- [Setup](#setup)
- [Commands](#commands)
- [Parameters](#parameters)
- [Pricing](#pricing)
- [Batch job format](#batch-job-format)
- [JSON output](#json-output)
- [Reference images](#reference-images)
- [Prompting guide](#prompting-guide)
- [Rate limits and reliability](#rate-limits-and-reliability)
- [Claude Code skill](#claude-code-skill)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Setup

**Requirements:** Python 3.11+ and a Gemini API key.

```bash
git clone https://github.com/faborsky/nanobanana-app.git
cd nanobanana-app
./setup.sh
```

`setup.sh` finds a suitable Python (3.11+), creates `.venv`, and installs the package.

Then add your API key:

```bash
cp .env.example .env
# open .env and paste your key
```

```
GEMINI_API_KEY=your-api-key-here
```

Get a key at **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**. Image generation is a **paid feature** — the key needs billing enabled on its Google Cloud project.

> `.env` is gitignored. Never commit your key, and never paste it into code.

Verify the install without spending anything:

```bash
./run.sh --version
./run.sh validate jobs/example.json
```

---

## Commands

`run.sh` activates the virtualenv and forwards everything to the CLI, so it works from any directory.

| Command | What it does | Costs money |
|---|---|---|
| `generate` | Generate one image from a prompt | yes |
| `batch` | Generate many images from a JSON job file | yes |
| `validate` | Check a job file for errors, offline | no |
| `describe` | Analyse an existing image and get a prompt back | yes (cheap) |

### generate

```bash
./run.sh generate "PROMPT" [options]
```

| Flag | Default | Description |
|---|---|---|
| `-a`, `--aspect` | `1:1` | Aspect ratio |
| `-r`, `--resolution` | `1K` | `1K`, `2K`, `4K` |
| `-f`, `--format` | `webp` | `webp`, `png`, `jpeg` |
| `-o`, `--output` | `./output` | Output directory (created if missing) |
| `-n`, `--name` | derived from prompt | Custom filename, no extension |
| `-ref`, `--reference` | — | Reference image for style/content |
| `--json` | off | Machine-readable result on stdout |

```bash
# Wide 2K hero image as PNG
./run.sh generate "A minimal glossy magazine cover, the title \"NANO BANANA\" in large bold sans-serif at the top, clean editorial layout, soft studio lighting" -a 16:9 -r 2K -f png

# Named output into a specific folder
./run.sh generate "Serene Japanese garden at dawn, cherry blossoms falling, koi pond reflection" -n japanese_garden -o ./images

# 4K ultrawide wallpaper
./run.sh generate "Vast cosmic nebula with swirling purple and blue gases" -a 21:9 -r 4K
```

Filenames are `<base>_<ratio>_<resolution>_<timestamp>.<ext>`, e.g. `japanese_garden_16x9_2K_20260725_104636.webp`. The timestamp means repeated runs never overwrite each other.

### batch

```bash
./run.sh batch jobs/example.json [-o ./images] [-d 1.0] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output` | `./output` | Output directory for all images |
| `-d`, `--delay` | `1.0` | Seconds between requests |
| `--json` | off | Machine-readable summary on stdout |

Runs jobs sequentially with a progress bar, reports per-job failures as they happen, and prints the **total cost** at the end. `Ctrl+C` finishes the current image and stops cleanly rather than dying mid-write.

The job file is validated before the first API call, so a typo costs nothing.

### validate

```bash
./run.sh validate jobs/example.json
```

Checks structure, enum values and that every `reference_path` exists. **No API calls, no cost.** Run it before any large batch.

### describe

```bash
./run.sh describe image.jpg              # short description, under 100 words
./run.sh describe image.jpg --detailed   # full prompt-ready description
```

Analyses an existing image with `gemini-3.5-flash` and returns text you can feed back into `generate`. `--detailed` covers subject, composition, style, palette, lighting, mood and background — useful for recreating a look you like.

---

## Parameters

**Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

**Resolutions:** `1K`, `2K`, `4K`

**Output formats:** `webp` (default, quality 90), `png` (lossless), `jpeg` (quality 95)

**Reference image formats:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

Pick `webp` + `1K` for web and UI work; `png` + `2K`/`4K` for print and wallpapers. Set the ratio with `-a` — never write it into the prompt text.

---

## Pricing

Billed **per image**, not per token. Source: [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (verified 2026-07-25).

| Resolution | Price per image |
|---|---|
| 1K | **$0.134** |
| 2K | **$0.134** |
| 4K | **$0.24** |

**1K and 2K cost exactly the same** — if you're paying either way, ask for 2K. Only 4K costs more.

Every successful `generate` prints its cost; `batch` prints the total. Failed generations aren't billed and aren't counted. A 20-image 2K batch is about **$2.68**.

`describe` is billed as tokens on `gemini-3.5-flash` ($1.50 per 1M input, $9.00 per 1M output) — fractions of a cent per image.

> Google's asynchronous **Batch API** is roughly 50 % cheaper, but it's a different endpoint with a queued delivery model. The `batch` command here is a sequential loop over the standard endpoint, so standard prices apply.

---

## Batch job format

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "2K",
    "format": "webp"
  },
  "jobs": [
    {
      "prompt": "Majestic snow-capped mountain range at golden hour, alpine meadow with wildflowers in the foreground, dramatic clouds, wide cinematic photorealistic composition",
      "output_name": "mountain_golden_hour"
    },
    {
      "prompt": "Tropical beach with crystal clear turquoise water, palm trees swaying, aerial drone perspective, vibrant travel photography",
      "output_name": "tropical_beach",
      "aspect_ratio": "21:9",
      "resolution": "4K"
    },
    {
      "prompt": "Transform this into a watercolour painting, soft washes, visible paper texture",
      "reference_path": "references/photo.jpg"
    }
  ]
}
```

`defaults` is optional and applies to every job. Each job **must** have `prompt`; `output_name`, `aspect_ratio`, `resolution`, `format` and `reference_path` are optional and override the defaults.

A working example lives in [`jobs/example.json`](jobs/example.json).

---

## JSON output

`--json` puts a parseable result on **stdout** and moves all human-readable output to **stderr**, so you can pipe it safely.

```bash
./run.sh generate "a lake at dawn" --json | jq -r '.output_path'
```

```json
{
  "success": true,
  "output_path": "/path/to/output/a_lake_at_dawn_1x1_1K_20260725_104636.webp",
  "aspect_ratio": "1:1",
  "resolution": "1K",
  "format": "webp",
  "cost_usd": 0.134,
  "attempts": 1,
  "model": "gemini-3-pro-image",
  "text_response": null
}
```

Batch returns totals plus a per-image array:

```json
{
  "success": true,
  "total": 3,
  "successful": 3,
  "failed": 0,
  "interrupted": false,
  "cost_usd": 0.508,
  "images": [{ "prompt": "...", "output_path": "...", "success": true, "error": null }]
}
```

On failure you get `{"success": false, "error": "..."}` and a non-zero exit code.

---

## Reference images

Pass an image alongside the prompt to guide style or content:

```bash
./run.sh generate "Reimagine this scene at night, neon reflections on wet asphalt" -ref photo.jpg -a 16:9
```

In batch jobs use `"reference_path": "references/photo.jpg"`.

When editing from a reference, say **what changes and what stays the same** — that's the single biggest difference between generating and editing:

> "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label, and the lighting exactly the same."

This CLI sends **one** reference image per job. The underlying model accepts more (Nano Banana Pro takes up to 6 objects and 5 characters), so if you need multi-reference compositing, call the API directly.

---

## Prompting guide

Based on Google's [Nano Banana prompting guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana) and the [image generation docs](https://ai.google.dev/gemini-api/docs/image-generation).

**The model reasons over your prompt, so describe a scene — don't list keywords.** A narrative paragraph beats a pile of comma-separated tags almost every time.

### Formula

```
[Subject] + [Action] + [Location/context] + [Composition] + [Style]
```

> "A striking fashion model wearing a tailored brown dress **[subject]**, posing with a confident, statuesque stance **[action]**, against a seamless deep cherry red studio backdrop **[context]**, medium-full shot, centre-framed **[composition]**, fashion editorial style shot on medium-format analog film with pronounced grain **[style]**."

### DO and DON'T

| DO | DON'T |
|---|---|
| Write full sentences describing a scene | Dump keyword lists (`cat, 8K, cinematic, detailed`) |
| **Frame positively** — "an empty street" | Rely on negatives — "no cars, no people" |
| Direct the camera — "low-angle shot", "macro", "f/1.8" | Leave framing and lighting to chance |
| Name materials — "navy blue tweed", "ornate etched silver" | Say "a jacket", "armor" |
| Put exact copy in quotes and name the font | Hope the text comes out right on its own |
| Iterate with small single-change follow-ups | Cram every idea into one giant prompt |
| Reuse one style sentence across a series | Vary the wording and wonder why the set doesn't match |
| State the purpose — "a hero banner for a fintech landing page" | Assume the model infers the use case |

**The one lesson that matters most:** describe what you *want*, not what you don't. "A plain seamless background" works; "no clutter, no text, no logos" often produces exactly what you excluded.

### Text inside images

These models render legible, stylized text well — logos, posters, infographics, menus.

1. Put the exact words in **quotes**.
2. Describe the typography: *"in a heavy, blocky Impact font"*, *"thin minimalist sans-serif"*.
3. Say where it goes: *"across the top third"*.

> "A high-end glossy commercial beauty shot of a minimalist nude-coloured moisturiser jar on a warm studio background. Render the word \"GLOW\" in a flowing elegant brush script above the product, and \"10% OFF\" in a heavy blocky font beneath it."

### Consistency across a series

Reuse the same style sentence, the same lighting language and the same aspect ratio in every prompt of the set. For tighter subject consistency, pass the same reference image to every job.

### Known weaknesses

- Dense or very small text can still come out imperfect — keep layouts simple and iterate.
- The model's knowledge cuts off in January 2025.
- Thinking tokens are billed even though you never see them (already included in the per-image price above).

---

## Rate limits and reliability

Limits depend on your billing tier and are visible in the [AI Studio rate limit dashboard](https://aistudio.google.com/rate-limit). Image models are additionally metered in **IPM** (images per minute), not just requests and tokens.

How this CLI behaves:

- **429 (rate limit) and 5xx** → retried up to 3 times with exponential backoff **plus jitter**, capped at 60 s. Jitter matters when several batches run at once — without it they all retry in lockstep and hit the same wall together.
- **400 / 401 / 403 / 404** → failed immediately. An invalid prompt or a bad key fails the same way every time; retrying just wastes your quota.
- **Safety-filtered prompts** → reported as `Content filtered`, not retried.
- **Batch** waits `--delay` seconds between images (1 s default). Raise it if you hit IPM limits.

---

## Claude Code skill

[`skill/`](skill/) contains a Claude Code skill that teaches your agent this tool: the commands, the pricing, the prompting rules, and what the model can and cannot do. Install instructions (in Czech): **[skill/INSTALL.md](skill/INSTALL.md)**.

```bash
mkdir -p ~/.claude/skills
cp -R skill/nanobanana ~/.claude/skills/nanobanana
# then replace <NANOBANANA_APP_DIR> in the skill with the path to this repo
```

After that, ask Claude Code for an image and it drives this CLI for you.

---

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -q     # offline tests, no API calls
ruff check nanobanana/         # lint
```

Code layout:

| File | Responsibility |
|---|---|
| `nanobanana/config.py` | Models, defaults, enums, validators, pricing, retry classification |
| `nanobanana/generator.py` | Gemini API call, retry/backoff, saving in the requested format |
| `nanobanana/batch.py` | Job file parsing/validation, sequential batch runner |
| `nanobanana/cli.py` | Typer commands, human and `--json` output |
| `nanobanana/utils.py` | Filename sanitising and generation |

See **[CLAUDE.md](CLAUDE.md)** for the architecture notes an AI agent needs, and **[docs/api-notes.md](docs/api-notes.md)** for how the Gemini image API actually behaves.

---

## Troubleshooting

**`Missing API key`** — `.env` doesn't exist or has no `GEMINI_API_KEY`. Copy `.env.example` to `.env` and paste your key.

**`404` / model not found** — your key's project may not have access to image generation, or the model ID has been retired. Check the current ID in `nanobanana/config.py` against [the model list](https://ai.google.dev/gemini-api/docs/models).

**`429 RESOURCE_EXHAUSTED`** — you hit a rate limit or spend cap. The CLI retries with backoff; if it persists, raise `--delay` or check your tier in AI Studio.

**`Content filtered`** — the prompt tripped a safety filter. Rephrase; retrying the same words won't help.

**`Virtual environment not found`** — run `./setup.sh`.

**Python too old** — needs 3.11+. `setup.sh` reports which interpreters it found.

---

## License

MIT — see [LICENSE](LICENSE).
