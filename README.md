# Nanobanana

CLI aplikace pro dávkové generování obrázků pomocí **Google Gemini 3 Pro Image** modelu.

## Požadavky

- Python 3.12+
- Google Gemini API klíč ([získat zde](https://aistudio.google.com/app/apikey))

## Instalace

```bash
# Spustit setup skript
./setup.sh

# Přidat API klíč do .env souboru
nano .env
```

## Použití

### Generování jednoho obrázku

```bash
./run.sh generate "sunset over ocean" --aspect 16:9 --resolution 2K
```

**Parametry:**

| Parametr | Zkratka | Default | Popis |
|----------|---------|---------|-------|
| `prompt` | - | (povinný) | Text prompt pro generování |
| `--aspect` | `-a` | `1:1` | Poměr stran |
| `--resolution` | `-r` | `1K` | Rozlišení (1K/2K/4K) |
| `--output` | `-o` | `./output` | Výstupní adresář |
| `--name` | `-n` | auto | Vlastní název souboru |
| `--reference` | `-ref` | - | Referenční obrázek pro styl/obsah |

**Podporované hodnoty:**

- **Aspect ratio**: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
- **Resolution**: `1K` (1024px), `2K` (2048px), `4K` (4096px)
- **Image formats** (pro reference): `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

### Batch processing

```bash
# Spustit batch job
./run.sh batch jobs/example.json

# S vlastním delay mezi requesty
./run.sh batch jobs/example.json --delay 2.0

# Validovat batch soubor
./run.sh validate jobs/example.json
```

### Formát batch souboru

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "2K"
  },
  "jobs": [
    {
      "prompt": "A serene mountain landscape at golden hour",
      "output_name": "mountain_golden"
    },
    {
      "prompt": "Tropical beach with crystal clear water",
      "aspect_ratio": "21:9"
    },
    {
      "prompt": "Northern lights over forest",
      "resolution": "4K"
    },
    {
      "prompt": "Transform this into watercolor style",
      "reference_path": "references/photo.jpg"
    }
  ]
}
```

### Vizuální reference

Generování s referenčním obrázkem pro styl nebo obsah:

```bash
# Přímá reference
./run.sh generate "create similar scene in anime style" -ref photo.jpg

# S dalšími parametry
./run.sh generate "reimagine at sunset" -ref landscape.png -a 16:9 -r 4K
```

### Analýza obrázku (describe)

Analyzuje obrázek a vytvoří textový popis vhodný jako prompt:

```bash
# Základní popis
./run.sh describe image.jpg

# Detailní popis optimalizovaný pro generování
./run.sh describe image.jpg --detailed
```

**Tip:** Výstup `describe --detailed` lze přímo použít jako základ pro generování nových obrázků.

## Příklady

```bash
# Jednoduchý obrázek
./run.sh generate "red apple on white background"

# Landscape wallpaper ve 4K
./run.sh generate "epic mountain vista" -a 21:9 -r 4K

# Portrait pro mobil
./run.sh generate "abstract art" -a 9:16 -r 2K -n my_wallpaper

# Batch s vlastním output adresářem
./run.sh batch jobs/example.json -o ./my_images

# Generování s referenčním obrázkem
./run.sh generate "podobný styl, ale v noci" -ref sunset.jpg -a 16:9

# Analýza obrázku pro tvorbu promptu
./run.sh describe photo.jpg --detailed
```

## Struktura projektu

```
nanobanana/
├── nanobanana/
│   ├── cli.py          # CLI příkazy
│   ├── generator.py    # Gemini API wrapper
│   ├── batch.py        # Batch processing
│   ├── config.py       # Konfigurace
│   └── utils.py        # Pomocné funkce
├── jobs/
│   └── example.json    # Ukázkový batch
├── output/             # Výstupní adresář
├── setup.sh            # Instalační skript
├── run.sh              # Spouštěcí skript
└── .env                # API klíč (neverzovat!)
```

## Licence

MIT
