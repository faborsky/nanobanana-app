---
name: nanobanana
description: Generate images with Google's Gemini 3 Pro Image (Nano Banana Pro) — single images or batches, from a text prompt or a reference image. Knows the per-image pricing, the supported formats and resolutions, the official prompting rules, and what the model can and cannot do. Use when the user asks to create, generate or produce images, graphics, illustrations, covers, banners, wallpapers or any visual content, or to analyse an existing image into a reusable prompt.
argument-hint: <image description or task>
allowed-tools: Bash, Read, Write, Glob
---

# Nanobanana — image generation via Gemini 3 Pro Image

Drives the Nanobanana CLI at `<NANOBANANA_APP_DIR>`. Model: **`gemini-3-pro-image`** (Nano Banana Pro).

> If a command fails with "Missing API key", the user needs `GEMINI_API_KEY` in `<NANOBANANA_APP_DIR>/.env` (template in `.env.example`, key from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), billing must be enabled). Tell them — don't try to work around it.

## Before you generate

**Images cost real money — roughly $0.134 each.** So:

1. **Confirm the brief once** if anything material is unstated (subject, format, where it will be used). Don't ask twice.
2. **State the expected cost** before generating more than ~3 images. `10 images at 2K ≈ $1.34`.
3. **Never silently regenerate.** If the user dislikes a result, propose the prompt change and confirm before spending again.

## Workflow

### Output location

Save into `./generated_images/` in the user's **current project directory**:

- Images: `./generated_images/`
- Batch job files: `./generated_images/jobs/`

Create the directories before running anything.

### Single image

```bash
mkdir -p ./generated_images
<NANOBANANA_APP_DIR>/run.sh generate "<prompt>" \
  -a <aspect> -r <resolution> -f <format> -o ./generated_images --json
```

### Batch (2 or more images)

Always prefer a batch over repeated single calls — one progress bar, one total cost.

```bash
mkdir -p ./generated_images/jobs
# write the job file first, then:
<NANOBANANA_APP_DIR>/run.sh validate ./generated_images/jobs/<name>.json
<NANOBANANA_APP_DIR>/run.sh batch ./generated_images/jobs/<name>.json -o ./generated_images --json
```

**Always run `validate` first** — it's free, offline, and catches a typo that would otherwise fail mid-batch after several paid images.

### Run generation in the background

Generation is slow (tens of seconds per image). Use `run_in_background: true` on the Bash tool and collect the output with `TaskOutput` when it finishes.

### Use `--json`

`--json` puts the result on stdout and all prose on stderr, so you get a clean parseable payload: `output_path`, `cost_usd`, `attempts`, plus a per-image array for batches. Parse it instead of scraping the human output.

### After generating

1. Report which files were written and where.
2. Report the **actual cost** from the JSON (`cost_usd`), not an estimate.
3. Show the image to the user with the Read tool if they'll want to judge it.

## Defaults

| Parameter | Default | When to change it |
|---|---|---|
| Resolution | `2K` | `4K` only for print or large wallpapers; `1K` never (see below) |
| Aspect ratio | `1:1` | Match the destination: `16:9` covers/thumbnails, `9:16` stories, `21:9` ultrawide |
| Format | `webp` | `png` for transparency-free lossless or print, `jpeg` for photos where size matters |

**Default to `2K`, not `1K` — they cost exactly the same ($0.134).** Asking for 1K saves nothing and gives you less. Only go to 4K when the extra $0.106 buys something real.

## Pricing

Billed **per image**, not per token. [Source](https://ai.google.dev/gemini-api/docs/pricing), verified 2026-07-25.

| Resolution | Price per image | 10 images |
|---|---|---|
| 1K | $0.134 | $1.34 |
| 2K | **$0.134** | $1.34 |
| 4K | $0.24 | $2.40 |

Failed generations are not billed. `describe` runs on `gemini-3.5-flash` and costs a fraction of a cent.

## What it can and cannot do

**Good at:**

- Photorealistic scenes, product shots, editorial and illustration styles.
- **Legible stylized text inside images** — posters, covers, infographics, menus, logos. This is a real strength of this model generation.
- Style transfer and edits from a reference image.
- Consistent series when you reuse one style sentence and one reference.

**Cannot / struggles:**

- **Dense or very small text** still degrades — keep text layouts simple and few words.
- **No transparent backgrounds.** If the user needs transparency, generate on a flat, uniform background and remove it afterwards in an image editor.
- **One reference image per job** through this CLI (the model itself accepts more; multi-reference compositing needs direct API calls).
- **No 512px option** on this model (only 1K/2K/4K).
- **Knowledge cutoff January 2025** — it doesn't know newer people, products or events.
- Exact brand logos, precise charts with real data, and specific real people's likenesses are unreliable and often blocked.
- Safety filters can refuse a prompt. That's a verdict, not a transient error — rephrase rather than retry.

## Parameters

**Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
**Resolutions:** `1K`, `2K`, `4K`
**Formats:** `webp` (default), `png`, `jpeg`
**Reference formats:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

Set the ratio with `-a`. **Never write the aspect ratio or resolution into the prompt text** — it does nothing and can appear in the image as literal text.

## Prompting guide

From Google's [official Nano Banana prompting guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana).

### The core principle

**The model reasons over the prompt before drawing, so write a scene in full sentences — not a list of keywords.** A narrative paragraph beats comma-separated tags almost every time.

### Formula

```
[Subject] + [Action] + [Location/context] + [Composition] + [Style]
```

> "A weathered fisherman mending nets **[subject + action]** on a wooden dock at golden hour **[context]**, shot slightly from below with a shallow depth of field **[composition]**, warm rim light catching the salt spray, documentary photography style **[style]**."

### DO and DON'T

| DO | DON'T |
|---|---|
| Write full sentences describing a scene | Dump keyword lists — `cat, 8K, cinematic, detailed` |
| **Frame positively** — "an empty street" | Use negatives — "no cars, no people" |
| Direct the camera — "low-angle", "macro", "f/1.8", "wide-angle" | Leave framing and lighting to chance |
| Name materials — "navy blue tweed", "matte ceramic" | Say "a jacket", "a mug" |
| Design the light — "three-point softbox", "chiaroscuro, harsh contrast" | Say "good lighting" |
| Put exact copy in quotes and name the font | Hope the text comes out right |
| State the purpose — "a hero banner for a fintech landing page" | Assume the model infers the use case |
| Change one thing per iteration | Rewrite everything and lose what worked |
| Reuse one style sentence across a series | Reword each prompt and wonder why the set doesn't match |

### The single most important lesson

**Describe what you want, not what you don't.** Negatives tend to summon exactly what they exclude — "no text, no clutter, no logos" often produces text, clutter and logos. Say "a plain seamless background" instead.

### Text inside images

1. Put the exact words in **quotes**.
2. Name the typography — *"in a heavy blocky font"*, *"a thin minimalist sans-serif"*.
3. Say where it sits — *"across the top third"*, *"beneath the product"*.

> "A minimal glossy magazine cover, the title \"NANO BANANA\" in large bold sans-serif across the top, clean editorial layout, soft studio lighting."

For Czech or other non-English text, write the prompt in English and specify the exact string in quotes plus the target language — the model renders diacritics reliably when the string is quoted verbatim.

### Editing vs generating

Generating is a blank canvas. **Editing is about what changes and what stays.** Always state both, and repeat the preserve-list on every iteration:

> "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label, and the lighting exactly the same."

### Consistency across a series

Reuse the same style sentence, the same lighting language and the same aspect ratio in every prompt of the set. Pass the same reference image with `-ref` for tighter subject consistency.

## Commands

```bash
# One image
<NANOBANANA_APP_DIR>/run.sh generate "<prompt>" -a 16:9 -r 2K -f webp -o ./generated_images --json

# With a reference image
<NANOBANANA_APP_DIR>/run.sh generate "<prompt>" -ref path/to/ref.jpg -o ./generated_images --json

# Batch
<NANOBANANA_APP_DIR>/run.sh validate ./generated_images/jobs/job.json
<NANOBANANA_APP_DIR>/run.sh batch ./generated_images/jobs/job.json -o ./generated_images --json

# Analyse an existing image into a prompt
<NANOBANANA_APP_DIR>/run.sh describe path/to/image.jpg --detailed
```

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
      "prompt": "Full narrative description of the image",
      "output_name": "optional_filename",
      "aspect_ratio": "1:1",
      "resolution": "4K",
      "format": "png",
      "reference_path": "path/to/reference.jpg"
    }
  ]
}
```

`defaults` is optional and applies to all jobs. Every job **must** have `prompt`; everything else is optional and overrides the defaults.

## Errors

| Error | Meaning | What to do |
|---|---|---|
| `Missing API key` | no `GEMINI_API_KEY` in `.env` | tell the user to add it — don't work around it |
| `Content filtered` | safety filter refused the prompt | rephrase; retrying identical wording won't help |
| `429 RESOURCE_EXHAUSTED` | rate limit (or spend cap) | the CLI already retries with backoff; for batches raise `-d` |
| `404` model not found | model ID retired | check the ID in `config.py` against the current model list |

Image models are metered in **images per minute (IPM)**, so a batch can hit 429 while well under the request limit. The fix is a longer `--delay`, never parallel calls.
