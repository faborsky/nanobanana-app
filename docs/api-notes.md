# Gemini Image API — how it actually behaves

Field notes on the Gemini image generation API as used by this CLI. Verified against the live API and the official docs on **2026-07-25**, model section refreshed **2026-10-11** (Nano Banana 2.1). This is the file to read when something breaks and the error message isn't enough.

## Model lifecycle — the most common cause of breakage

Google retires image model IDs on a real schedule, and a retired ID fails with a plain `404`. Two IDs this project used previously are already gone:

| Model ID | Status |
|---|---|
| `gemini-nano-banana-2.1` | **current**, default (`-m 2.1`), GA 2026-10-06 |
| `gemini-3-pro-image` | **current**, `-m pro` |
| `gemini-3.1-flash-lite-image` | **current**, `-m lite` |
| `gemini-3.8-flash` | **current**, used by `describe` |
| `gemini-3.1-flash-image` | deprecated 2026-10-06 (Nano Banana 2), replacement 2.1, no shutdown date yet |
| `gemini-3.5-flash` | deprecated 2026-10-08, auto-routed to 3.6 — previously used by `describe` |
| `gemini-3-pro-image-preview` | retired 2026-06-25 — the pre-GA ID |
| `gemini-2.0-flash` | shut down 2026-06-01 — previously used by `describe` |

All current IDs live in `MODELS` / `DESCRIBE_MODEL_NAME` in `nanobanana/config.py`. To check what your key can actually reach:

```python
from google import genai
client = genai.Client(api_key="...")
print(sorted(m.name.replace("models/", "") for m in client.models.list()))
```

Note that `models.list()` may still show an ID that no longer serves generation requests — presence in the list is not proof it works. A one-image `1K` test is the real check.

Other image models visible on the API, for reference: `gemini-2.5-flash-image` (shutdown 2027-03-15) and `nano-banana-pro-preview` (alias of the retired Pro preview). Imagen is shut down.

## Request shape

Generation goes through the standard `generate_content` endpoint with an `image_config`, not a dedicated image endpoint:

```python
client.models.generate_content(
    model="gemini-3-pro-image",
    contents=[prompt],                      # + optional PIL image for a reference
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="16:9",            # 10 standard ratios; 2.1 adds 1:4 4:1 1:8 8:1
            image_size="2K",                # "1K" | "2K" | "4K" — uppercase K required
        ),
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),  # 2.1 / Lite only
    ),
)
```

Google's 2.1 docs now show the **Interactions API** (`client.interactions.create(model=…, input=…, response_format={"type": "image", "aspect_ratio": …, "image_size": …}, generation_config={"thinking_level": …})`). `generate_content` still works for 2.1 — verified 2026-10-11 — so the CLI stays on it.

**Real output sizes differ slightly from the docs table:** 2.1 at `8:1` / 2K came back 5856×704 (docs say 6144×768); at `4:1` / 1K 2064×512.

**Usage metadata is the bill.** `response.usage_metadata` gives `prompt_token_count`, `candidates_token_count` (image + text) with a per-modality breakdown in `candidates_tokens_details`, and `thoughts_token_count`. A 1K 2.1 image is 1120 image tokens + a few hundred text tokens, so the real cost is a bit above the list price. The pricing page footnote says a 4K 2.1 image is 3780 tokens while the resolution table says 2520 — trust the measured `cost_usd`.

Aspect ratio and resolution are **config fields, not prompt text**. Writing "16:9" into the prompt does nothing useful and can leak into the image as literal text.

## Response shape and the `as_image()` trap

The response comes back as parts; a part is either text or an image:

```python
for part in response.parts:
    if part.text is not None:
        text_response = part.text          # model commentary, often None
    elif (image := part.as_image()) is not None:
        saved_image = image
```

**`part.as_image()` does NOT return a `PIL.Image.Image`.** It returns an SDK wrapper whose `.save(path)` accepts only a file path and infers the format from the extension. It has no `quality` parameter, no mode conversion, no format argument.

To save as WebP with quality control, or to convert RGBA → RGB for JPEG, you have to round-trip through disk:

```python
with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
    saved_image.save(tmp.name)              # SDK wrapper
    with Image.open(tmp.name) as pil_image: # now a real PIL image
        pil_image.save(output_path, "WEBP", quality=90)
```

`generator.py` does exactly this. It looks redundant; it isn't.

A response can also contain **no image at all** — typically when the prompt was refused. The text part then usually explains why, which is why `ImageGenerationError` includes it in the message.

## Errors and retry classification

The SDK raises `google.genai.errors.APIError` subclasses: `ClientError` (4xx) and `ServerError` (5xx). Both carry `.code` (int), `.status` and `.message`. `is_retryable_error()` in `config.py` keys off `.code`:

| Code | Meaning | Retried? |
|---|---|---|
| 429 | `RESOURCE_EXHAUSTED` — rate limit or spend cap | **yes** |
| 500, 502, 503, 504 | transient server-side failure | **yes** |
| 400 | `INVALID_ARGUMENT` — bad ratio, malformed request | no |
| 401 / 403 | bad or unauthorised API key | no |
| 404 | model ID not found (usually retired) | no |
| — | network timeouts, connection resets (no `.code`) | **yes**, matched on message |

Retrying a 400 or 404 is pure waste: the same request fails identically every time. That was the behaviour before v1.0.0 — every failure got three attempts, so a typo'd model ID took three round-trips to report.

**Backoff is exponential with jitter**, capped at 60 s: `min(base * 2**attempt, 60) * uniform(0.5, 1.0)`. The jitter is not decorative — Google and OpenAI both recommend it, because without it parallel runs that hit the same rate limit retry in lockstep and collide again.

**Safety filtering** surfaces as an exception whose message contains "blocked" or "safety". It's a verdict on the prompt, so it's never retried — the CLI reports `Content filtered` and moves on.

## Rate limits

Documented limits are per billing tier and are **not published as fixed numbers** — see your live values in the [AI Studio rate limit dashboard](https://aistudio.google.com/rate-limit).

The detail that matters for image work: alongside RPM (requests/minute) and TPM (tokens/minute), image-capable models are metered in **IPM — images per minute**. A batch can be well under the request limit and still hit 429 on IPM. The fix is `--delay`, not parallelism.

Spend-based caps also return `429 RESOURCE_EXHAUSTED`, which looks identical to a rate limit but doesn't clear by waiting. If backoff never succeeds, check billing.

## Pricing

All image models are billed **per token**; an output image is a fixed token count per resolution, which is where the "per image" figures come from ([source](https://ai.google.dev/gemini-api/docs/pricing), verified 2026-10-11):

| Model | Input /1M | Text+thinking out /1M | Image out /1M | 1K | 2K | 4K | Batch API 2K |
|---|---|---|---|---|---|---|---|
| 2.1 | $1.50 | $7.50 | $30 | $0.0336 | $0.0504 | $0.113 | $0.0252 |
| Pro | $2.00 | $12.00 | $120 | $0.134 | $0.134 | $0.24 | $0.067 |
| Lite | $0.25 | $1.50 | $30 | $0.0336 | — | — | — |

Things worth internalising:

1. **The real bill is above the list price** because thinking and text tokens are billed too. Measured at 2K (see [benchmark-2026-10.md](benchmark-2026-10.md)): 2.1 $0.060–0.068 (+20–36 %), 2.1 `high` $0.079, Pro $0.139–0.145. The CLI computes `cost_usd` from `usage_metadata`, so it reports the real figure.
2. **On Pro 1K and 2K are the same price; on 2.1 they aren't** (1K is ~⅓ cheaper). 2K stays the default.
3. **The "Batch API" column is a different endpoint** — asynchronous, queued, half price. The `batch` command in this CLI is a sequential loop over the *standard* endpoint, so it pays standard prices. Migrating would be a genuine ~50 % saving for large non-urgent jobs.
4. **Search grounding** (2.1) costs $14 per 1,000 queries after 5,000 free per month. Not used by this CLI.

`describe` uses `gemini-3.8-flash`: $0.75/1M in, $3.75/1M out through 2026-12-31 ($1.50 / $7.50 from 2027) — a fraction of a cent per image.

## Capabilities and limits worth knowing

- **Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` on all models; **2.1 adds `1:4`, `4:1`, `1:8`, `8:1`** (Nano Banana 2 had them too, with visible tiling artifacts that 2.1 fixes).
- **Resolutions:** 1K, 2K, 4K on 2.1 and Pro; Lite 1K only. 512px existed only on the deprecated Nano Banana 2.
- **Thinking:** always on, can't be disabled. 2.1: `minimal` / `medium` / `high` (default `medium`); Lite: `minimal` / `high`; Pro: not configurable. Up to two interim "thought" images may be generated — not billed as images, and returned as `part.thought = True`.
- **Reference images:** 2.1 — up to 10 object + 4 character images; Pro — 6 objects + 5 characters + 3 style references; Lite — 14 objects. This CLI sends one.
- **Video input** (video-to-image) on 2.1 and Lite. Not exposed in this CLI.
- **Context window:** 65,536 input tokens for 2.1, 131,072 for Pro.
- **Text rendering** is a genuine strength on 2.1 and Pro — five Czech lines with diacritics came out flawless on both. Google lists Czech outside its best-supported languages, so still check every string.
- **SynthID watermark** on every generated image.
- **Reference image formats** accepted by this CLI: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`.

## Prompting behaviour

The model reasons over the prompt before drawing, so it responds to prose, not tags. Two rules carry most of the quality difference:

1. **Describe a scene in sentences.** Formula: `[Subject] + [Action] + [Location/context] + [Composition] + [Style]`.
2. **Frame positively.** "An empty street" reliably beats "no cars, no people" — negatives tend to summon what they exclude.

Editing from a reference is a different mode: state **what changes and what stays identical**, and repeat the preserve-list on every iteration.

Sources: [Ultimate prompting guide for Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana), [image generation docs](https://ai.google.dev/gemini-api/docs/image-generation).

## Known gaps in this CLI

Documented so nobody rediscovers them as bugs:

- Only one reference image per job (API allows more).
- No search grounding, no video input, no multi-turn editing (all supported by 2.1 via the API).
- Uses the standard endpoint, not the ~50 % cheaper asynchronous Batch API.
- `batch` is strictly sequential — no parallelism, by design, to stay clear of IPM limits.
- Cost is computed from `usage_metadata` × the token rates in `MODELS`, not from a billing API. If Google changes prices, the `ModelSpec` rates need updating; a test asserts the current tables so the suite fails loudly rather than misreporting.
