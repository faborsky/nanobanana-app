# Nanobanana - Claude Code Instructions

## Project Overview

CLI application for image generation using Google Gemini 3 Pro Image model. Supports single and batch generation.

## Structure

```
nanobanana/
├── nanobanana/        # Python package
│   ├── cli.py         # Typer CLI commands
│   ├── generator.py   # Gemini API wrapper
│   ├── batch.py       # Batch processing logic
│   ├── config.py      # Config, validation, constants
│   └── utils.py       # Filename generation helpers
├── jobs/              # Batch job JSON files
└── output/            # Generated images
```

## Running

```bash
./run.sh generate "prompt" -a 16:9 -r 2K
./run.sh generate "prompt" -f png -r 4K            # Konkrétní formát a rozlišení
./run.sh generate "prompt" -ref reference.jpg      # S vizuální referencí
./run.sh batch jobs/myjob.json
./run.sh validate jobs/myjob.json
./run.sh describe image.jpg                        # Analýza obrázku
./run.sh describe image.jpg --detailed             # Detailní popis pro prompt
```

## Creating Batch Job Files

### JSON Format

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "2K",
    "format": "webp"
  },
  "jobs": [
    {
      "prompt": "Detailed description of the image",
      "output_name": "optional_filename",
      "aspect_ratio": "1:1",
      "resolution": "4K",
      "format": "png"
    }
  ]
}
```

### Rules

- `defaults` is optional - sets default values for all jobs
- Each job MUST have a `prompt`
- `output_name`, `aspect_ratio`, `resolution`, `format`, `reference_path` are optional (defaults will be used)
- Valid `aspect_ratio`: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
- Valid `resolution`: `1K`, `2K`, `4K`
- Valid `format`: `webp` (default), `png`, `jpeg`
- Valid image formats for references: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

### Example batch file for wallpapers

```json
{
  "defaults": {
    "aspect_ratio": "21:9",
    "resolution": "4K"
  },
  "jobs": [
    {
      "prompt": "Vast cosmic nebula with swirling purple and blue gases, stars scattered throughout, cinematic lighting, ultra detailed",
      "output_name": "nebula_wallpaper"
    },
    {
      "prompt": "Serene Japanese garden at dawn, cherry blossoms falling, koi pond reflection, soft morning light",
      "output_name": "japanese_garden"
    },
    {
      "prompt": "Futuristic cyberpunk cityscape at night, neon signs, rain-slicked streets, flying vehicles",
      "output_name": "cyberpunk_city"
    }
  ]
}
```

---

## Prompting Gemini 3 Pro Image

### Core Principles

Gemini 3 Pro Image reasons over the prompt ("Thinking"), so it responds best to
**descriptive narrative prompts, not keyword lists**. Describe the finished image
the way you'd describe a photo to a person.

1. **Write a scene, not a tag list** - full sentences describing subject, setting, and how it looks beat a comma-separated pile of keywords
2. **Be specific** - the more concrete the description, the better the result
3. **State the intent** when useful - e.g. "a hero banner for a fintech landing page" helps the model compose appropriately
4. **Set aspect ratio/resolution via flags** (`-a`, `-r`), not in the prompt text

### Effective Prompt Structure

Describe, in a sentence or two, this flow:

```
[Subject + what it's doing] in [environment], [composition & camera angle],
[lighting], [style/mood], [key material/detail].
```

### Good Prompt Examples

**Landscape:**
```
A majestic snow-capped mountain range at golden hour, warm sunlight reflecting
off the peaks, an alpine meadow full of wildflowers in the foreground, dramatic
clouds overhead, shot as a wide cinematic photorealistic composition.
```

**Portrait/Character:**
```
A portrait of an elderly fisherman with a weathered, deeply wrinkled face and
kind eyes, wearing a worn cable-knit sweater, lit by soft natural window light
from the side with a shallow depth of field, in a documentary photography style.
```

**Abstract:**
```
A fluid abstract composition with vibrant gradients flowing from deep purple
into electric blue and warm orange, organic shapes accented with metallic
highlights, in a contemporary digital art style.
```

**Product/Object:**
```
A minimalist product shot of a matte white ceramic coffee mug on a light gray
background, soft shadows and clean studio lighting, commercial photography with
a sharp, clean aesthetic.
```

### Text Inside the Image (strong capability)

Gemini 3 image models render legible, stylized text well — ideal for logos,
posters, infographics, menus, and marketing assets. Put the **exact text in
quotes** and describe its placement and look:

```
A minimal glossy magazine cover, the title "NANO BANANA" in large bold
sans-serif at the top, clean editorial layout, soft studio lighting.
```

### Useful Vocabulary

Weave these into the narrative — don't dump them as a bare list:

| Category | Terms |
|----------|-------|
| Camera/Quality | `shallow depth of field`, `wide angle`, `close-up`, `sharp focus`, `photorealistic` |
| Lighting | `golden hour`, `soft light`, `dramatic lighting`, `backlit`, `rim light`, `studio lighting` |
| Style | `cinematic`, `editorial`, `documentary`, `fine art`, `commercial`, `3D render`, `flat vector` |
| Composition | `rule of thirds`, `symmetrical`, `aerial view` |
| Mood | `moody`, `ethereal`, `vibrant`, `serene`, `dramatic` |

### What to Avoid

- Bare keyword lists with no scene ("cat, 8K, cinematic, detailed")
- Too short prompts ("a cat") - results will be generic
- Conflicting instructions ("realistic cartoon style")
- Too many subjects at once
- For exclusions, give a clear positive instruction ("plain seamless background, no text") rather than a vague negative — Gemini 3 respects explicit constraints, but describing what you DO want still works best

### Tips for Consistent Series

For batch jobs with the same style:
1. Reuse the same descriptive style sentence across every prompt
2. Keep the same lighting and camera language
3. Keep a consistent aspect ratio
4. For tight subject/style consistency, pass the same reference image (`reference_path`)

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "2K"
  },
  "jobs": [
    {
      "prompt": "Ocean waves breaking at sunset under a dramatic sky, warm golden tones, shot as a cinematic wide photograph.",
      "output_name": "ocean"
    },
    {
      "prompt": "Rolling desert dunes at sunset under a dramatic sky, warm golden tones, shot as a cinematic wide photograph.",
      "output_name": "desert"
    },
    {
      "prompt": "A still mountain lake at sunset under a dramatic sky, warm golden tones, shot as a cinematic wide photograph.",
      "output_name": "mountain"
    }
  ]
}
```

---

## Visual References

Nanobanana podporuje dva způsoby práce s vizuálními referencemi:

### 1. Přímá reference (multimodální vstup)

Obrázek lze poslat přímo do Gemini API jako součást promptu:

```bash
# Jednoduchý příkaz
./run.sh generate "create similar image in watercolor style" -ref photo.jpg

# S dalšími parametry
./run.sh generate "reimagine this scene at night" -ref sunset.png -a 16:9 -r 4K
```

**Batch job s referencí:**

```json
{
  "jobs": [
    {
      "prompt": "Transform this into anime style, vibrant colors",
      "reference_path": "references/photo1.jpg",
      "output_name": "anime_version"
    },
    {
      "prompt": "Create oil painting version of this landscape",
      "reference_path": "references/landscape.png",
      "aspect_ratio": "16:9"
    }
  ]
}
```

### 2. Claude Code asistence (doporučeno pro složité případy)

Pro maximální kontrolu nad výsledkem můžeš poslat obrázek přímo do Claude Code konverzace. Claude analyzuje obrázek a vytvoří detailní prompt.

**Workflow:**
1. Pošli obrázek do Claude Code (drag & drop nebo paste)
2. Požádej: "Vytvoř prompt pro nanobanana inspirovaný tímto obrázkem ve stylu X"
3. Claude vytvoří optimalizovaný prompt
4. Spusť generování s vytvořeným promptem

**Výhody tohoto přístupu:**
- Maximální kontrola nad interpretací reference
- Možnost iterovat a upravovat prompt před generováním
- Claude může kombinovat více referencí do jednoho promptu
- Lze specifikovat přesně které aspekty reference zachovat

### 3. Příkaz `describe`

Automatická analýza obrázku pro vytvoření promptu:

```bash
# Základní popis (stručný, pod 100 slov)
./run.sh describe image.jpg

# Detailní popis optimalizovaný pro generování
./run.sh describe image.jpg --detailed
```

Výstup `--detailed` obsahuje:
- Hlavní subjekt a kompozici
- Umělecký styl a techniku
- Barevnou paletu a osvětlení
- Náladu a atmosféru
- Detaily pozadí a prostředí

**Příklad použití:**

```bash
# Získej detailní popis
./run.sh describe reference.jpg --detailed
# Výstup: "A serene coastal scene at golden hour..."

# Použij jako základ pro generování
./run.sh generate "A serene coastal scene at golden hour, [tvé úpravy]" -r 4K
```

### Kdy použít který přístup

| Situace | Doporučený přístup |
|---------|-------------------|
| Rychlá stylová transformace | `--reference` parametr |
| Komplexní reference s úpravami | Claude Code asistence |
| Automatizovaný batch | `reference_path` v JSON |
| Extrakce popisu pro další použití | `describe` příkaz |
| Kombinace více referencí | Claude Code asistence |

---

## Development

### Adding a New CLI Command

1. Add a function with `@app.command()` decorator to `cli.py`
2. Use Typer annotations for parameters
3. Validate inputs using callbacks or functions from `config.py`

### Modifying Valid Values

Aspect ratios, resolutions, and output formats are defined in `config.py`:
- `AspectRatio` enum
- `Resolution` enum
- `OutputFormat` enum
- `VALID_ASPECT_RATIOS` set
- `VALID_RESOLUTIONS` set
- `VALID_OUTPUT_FORMATS` set
- `SUPPORTED_IMAGE_FORMATS` frozenset (for reference images)

### Important: Gemini SDK Image Object

`part.as_image()` from Gemini SDK does **NOT** return a standard `PIL.Image.Image`. It returns a SDK wrapper with its own `.save(path)` that only accepts a file path (format is derived from extension). To use PIL features (quality params, format conversion, mode conversion), first save to a temp file via the wrapper's `.save()`, then re-open with `PIL.Image.open()`.

### Testing

```bash
source .venv/bin/activate
./run.sh validate jobs/example.json  # Validation without API calls
./run.sh generate "test" -r 1K       # Quick test with small resolution
./run.sh generate "test" -f png      # Test with specific format
```
