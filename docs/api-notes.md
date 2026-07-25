# Gemini Image API — how it actually behaves

Field notes on the Gemini image generation API as used by this CLI. Verified against the live API and the official docs on **2026-07-25**. This is the file to read when something breaks and the error message isn't enough.

## Model lifecycle — the most common cause of breakage

Google retires image model IDs on a real schedule, and a retired ID fails with a plain `404`. Two IDs this project used previously are already gone:

| Model ID | Status |
|---|---|
| `gemini-3-pro-image` | **current**, used for generation |
| `gemini-3.5-flash` | **current**, used by `describe` |
| `gemini-3-pro-image-preview` | retired 2026-06-25 — the pre-GA ID |
| `gemini-2.0-flash` | shut down 2026-06-01 — previously used by `describe` |

Both current IDs are defined at the top of `nanobanana/config.py`. To check what your key can actually reach:

```python
from google import genai
client = genai.Client(api_key="...")
print(sorted(m.name.replace("models/", "") for m in client.models.list()))
```

Note that `models.list()` may still show an ID that no longer serves generation requests — presence in the list is not proof it works. A one-image `1K` test is the real check.

Other image models visible on the API, for reference: `gemini-3.1-flash-image` (Nano Banana 2, cheaper/faster, adds 512px), `gemini-3.1-flash-lite-image`, `gemini-2.5-flash-image`, and the `imagen-4.0-*` family (a different API surface).

## Request shape

Generation goes through the standard `generate_content` endpoint with an `image_config`, not a dedicated image endpoint:

```python
client.models.generate_content(
    model="gemini-3-pro-image",
    contents=[prompt],                      # + optional PIL image for a reference
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="16:9",            # one of the 10 supported ratios
            image_size="2K",                # "1K" | "2K" | "4K"
        )
    ),
)
```

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

Per image, not per token ([source](https://ai.google.dev/gemini-api/docs/pricing)):

| Resolution | Standard | Batch API |
|---|---|---|
| 1K | $0.134 | $0.067 |
| 2K | $0.134 | $0.067 |
| 4K | $0.24 | $0.12 |

Input is $2.00/1M tokens (≈$0.0011 per image), image output is billed at $120.00/1M tokens — which is what the per-image figures above already resolve to.

Two things worth internalising:

1. **1K and 2K are the same price.** Asking for 1K saves nothing. Default to 2K when the output will be seen at any size.
2. **The "Batch API" column is a different endpoint.** It's Google's asynchronous, queued batch service — roughly half price with delayed delivery. The `batch` command in this CLI is a sequential loop over the *standard* endpoint, so it pays standard prices. Migrating to the real Batch API would be a genuine ~50 % saving for large non-urgent jobs, and is the single biggest cost optimisation left in this tool.

**Thinking tokens are billed** on Gemini 3 models even though the thought process isn't returned. For image generation this is already baked into the per-image price.

`describe` uses `gemini-3.5-flash` and is billed as ordinary tokens: $1.50/1M in, $9.00/1M out — a fraction of a cent per image.

## Capabilities and limits worth knowing

- **Aspect ratios:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`.
- **Resolutions:** 1K, 2K, 4K on Nano Banana Pro. The 512px (0.5K) option exists only on `gemini-3.1-flash-image`, not on the Pro model this CLI uses.
- **Reference images:** the Pro model accepts up to **6 object images + 5 character images** in one prompt. This CLI sends one. Multi-reference compositing means calling the API directly.
- **Context window:** 65,536 input tokens for Nano Banana Pro (131,072 for Nano Banana 2).
- **Text rendering** is a genuine strength — legible stylized text for posters, infographics, menus. Dense or very small text still degrades; keep layouts simple.
- **Knowledge cutoff:** January 2025.
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
- No 512px option (not supported by the Pro model anyway).
- Uses the standard endpoint, not the ~50 % cheaper asynchronous Batch API.
- `batch` is strictly sequential — no parallelism, by design, to stay clear of IPM limits.
- Cost is computed from the published price table, not from a billing API. If Google changes prices, `PRICE_PER_IMAGE_USD` needs updating; a test asserts the current table so the suite fails loudly rather than misreporting.
