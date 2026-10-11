---
name: nanobanana
description: Generate images with Google's Nano Banana models — Nano Banana 2.1 (default), Nano Banana Pro and Nano Banana 2 Lite — single images or batches, from a text prompt or a reference image. Knows which model to pick, the real per-image pricing, the supported formats and resolutions, the official prompting rules, and what the model can and cannot do. Use when the user asks to create, generate or produce images, graphics, illustrations, covers, banners, wallpapers or any visual content, or to analyse an existing image into a reusable prompt.
argument-hint: <image description or task>
allowed-tools: Bash, Read, Write, Glob
---

# Nanobanana — image generation via Google's Nano Banana models

Drives the Nanobanana CLI (v1.1.0+) at `<NANOBANANA_APP_DIR>`. Default model: **`gemini-nano-banana-2.1`** (Nano Banana 2.1).

## Which model (`-m`)

| `-m` | Model | Real cost at 2K | Use it for |
|---|---|---|---|
| `2.1` *(default)* | Nano Banana 2.1 — `gemini-nano-banana-2.1` | ~$0.06–0.07 | Almost everything: photos, illustrations, text-in-image, and the **only** model for panoramic `1:4` / `4:1` / `1:8` / `8:1` |
| `pro` | Nano Banana Pro — `gemini-3-pro-image` | ~$0.14 | The user asks for Pro, or 2.1 failed on a hard brief (heavy world knowledge, many style references, strict brand consistency) |
| `lite` | Nano Banana 2 Lite — `gemini-3.1-flash-lite-image` | $0.034 (1K only) | Bulk drafts where 1K is enough |

In a same-prompt test (2026-10-11) 2.1 matched Pro on Czech text-in-image at less than half the price, and rendered a clean 8:1 panorama where its predecessor showed tiling artifacts. Pro has no panoramic ratios.

**Thinking (`-t`, 2.1 and Lite):** 2.1 defaults to `medium`. `minimal` is faster and slightly cheaper. Avoid `high` unless asked — in testing it doubled the time and didn't improve the result.

> If a command fails with "Missing API key", the user needs `GEMINI_API_KEY` in `<NANOBANANA_APP_DIR>/.env` (template in `.env.example`, key from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), billing must be enabled). Tell them — don't try to work around it.

## Before you generate

**Images cost real money — ~$0.06 each on 2.1, ~$0.14 on Pro.** So:

1. **Confirm the brief once** if anything material is unstated (subject, format, where it will be used). Don't ask twice.
2. **State the expected cost** before generating more than ~3 images. `10 images at 2K on 2.1 ≈ $0.65`.
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
# optional: -m pro | -m lite, -t minimal|medium|high
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

`--json` puts the result on stdout and all prose on stderr, so you get a clean parseable payload: `output_path`, `cost_usd`, `model`, `seconds`, `attempts`, plus a per-image array for batches. Parse it instead of scraping the human output.

### After generating

1. Report which files were written and where.
2. Report the **actual cost** from the JSON (`cost_usd`), not an estimate.
3. Show the image to the user with the Read tool if they'll want to judge it.

## Defaults

| Parameter | Default | When to change it |
|---|---|---|
| Model | `2.1` | See *Which model* |
| Resolution | `2K` | `4K` only when the user asks for it |
| Aspect ratio | `1:1` | Match the destination: `16:9` covers/thumbnails, `9:16` stories, `21:9` ultrawide, `8:1` / `4:1` web headers and banners (2.1) |
| Format | `webp` | `png` for transparency-free lossless or print, `jpeg` for photos where size matters |

**Default to `2K`.** On Pro 1K and 2K cost the same; on 2.1 1K saves about a third but 2K is the sensible default. 4K roughly doubles the price — only when it buys something real.

## Pricing

All models are billed **per token**; an output image is a fixed token count per resolution. [Source](https://ai.google.dev/gemini-api/docs/pricing), verified 2026-10-11.

| Model | 1K | 2K | 4K |
|---|---|---|---|
| 2.1 (list) | $0.034 | $0.050 | $0.113 |
| Pro (list) | $0.134 | $0.134 | $0.24 |
| Lite (list) | $0.034 | — | — |

**The real bill is a bit higher** — thinking and text tokens are billed too. Measured at 2K: 2.1 $0.060–0.068, Pro ~$0.14. The CLI computes `cost_usd` from the token usage the API reports, so the JSON receipt is exact.

Failed generations are not billed. `describe` runs on `gemini-3.8-flash` and costs a fraction of a cent.

## What it can and cannot do

**Good at:**

- Photorealistic scenes, product shots, editorial and illustration styles.
- **Legible stylized text inside images** — posters, covers, infographics, menus, logos. This is a real strength of this model generation.
- Style transfer and edits from a reference image.
- Consistent series when you reuse one style sentence and one reference.

**Cannot / struggles:**

- **Dense or very small text** still degrades — keep text layouts simple and few words.
- **No transparent backgrounds.** If the user needs transparency, generate on a flat, uniform background and remove it afterwards in an image editor.
- **One reference image per job** through this CLI (2.1 accepts up to 10 objects + 4 characters, Pro 6 objects + 5 characters + 3 style refs; multi-reference compositing needs direct API calls).
- **No 512px option** (1K/2K/4K; Lite 1K only).
- **No recent world knowledge** — Google Search grounding exists on 2.1 but this CLI doesn't enable it.
- Exact brand logos, precise charts with real data, and specific real people's likenesses are unreliable and often blocked.
- Safety filters can refuse a prompt. That's a verdict, not a transient error — rephrase rather than retry.

## Parameters

**Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` — plus `1:4`, `4:1`, `1:8`, `8:1` on 2.1 only
**Resolutions:** `1K`, `2K`, `4K` (Lite: `1K`)
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

For Czech or other non-English text, write the prompt in English and specify the exact string in quotes plus the target language — the model renders diacritics reliably when the string is quoted verbatim. Watch the casing — models like to turn a title into ALL CAPS; say "in sentence case, exactly as written" if it matters.

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
      "model": "pro",
      "thinking": "minimal",
      "reference_path": "path/to/reference.jpg"
    }
  ]
}
```

`defaults` is optional and applies to all jobs. Every job **must** have `prompt`; everything else is optional and overrides the defaults (`model` and `thinking` work in `defaults` too). `validate` also checks each job against its model — e.g. `8:1` on Pro fails offline, for free.

## Errors

| Error | Meaning | What to do |
|---|---|---|
| `Missing API key` | no `GEMINI_API_KEY` in `.env` | tell the user to add it — don't work around it |
| `Content filtered` | safety filter refused the prompt | rephrase; retrying identical wording won't help |
| `429 RESOURCE_EXHAUSTED` | rate limit (or spend cap) | the CLI already retries with backoff; for batches raise `-d` |
| `does not support aspect ratio` / `resolution` / `thinking` | the chosen `-m` can't do it | switch to `-m 2.1` or a supported value — nothing was sent or billed |
| `404` model not found | model ID retired | check the ID in `config.py` against the current model list |

Image models are metered in **images per minute (IPM)**, so a batch can hit 429 while well under the request limit. The fix is a longer `--delay`, never parallel calls.
