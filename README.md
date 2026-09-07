# Nanobanana

CLI na generování obrázků modelem **Gemini 3 Pro Image** od Googlu (Nano Banana Pro). Jeden obrázek nebo celá dávka, vizuální reference, analýza obrázku. Navržené tak, aby to zvládl řídit člověk i AI agent typu Claude Code.

Součástí je **[skill pro Claude Code](skill/INSTALL.md)**, takže tvůj agent zná ceny, formáty, pravidla promptování a to, co model umí a co ne.

```bash
./run.sh generate "A weathered fisherman mending nets on a wooden dock at golden hour, warm rim light catching the salt spray, documentary photography" -a 16:9 -r 2K
```

- **Ceny za obrázek zabudované uvnitř.** Každé spuštění ti řekne, kolik stálo.
- **Strojově čitelný `--json`** na stdout, výstup pro člověka na stderr.
- **Opakuje jen to, co má smysl opakovat:** rate limity a chyby serveru, s exponenciálním backoffem a jitterem. Špatný prompt spadne hned, místo aby třikrát pálil kvótu.
- **Dávkové úlohy z JSON souboru**, k tomu offline `validate` jako dry run zdarma.

> [!TIP]
> **Appka je zdarma a je tvoje.** Naklonuj si ji, používej ji, přestav si ji po svém.
>
> Nevíš, jak ji rozjet? Nebo chceš AI v marketingu používat systematicky: řídit z jednoho místa všechny kanály, automatizovat rutinu, postavit si vlastní znalostní bázi a vibe codovat si nástroje na míru své firmě? To učím v kurzu **[AI First](https://aifirst.cz)**. Tahle appka je v něm vysvětlená i s tím, jak si postavit vlastní.

---

## Obsah

- [Instalace](#instalace)
- [Příkazy](#příkazy)
- [Parametry](#parametry)
- [Ceny](#ceny)
- [Formát souboru s dávkou](#formát-souboru-s-dávkou)
- [Výstup v JSON](#výstup-v-json)
- [Referenční obrázky](#referenční-obrázky)
- [Jak psát prompty](#jak-psát-prompty)
- [Rate limity a spolehlivost](#rate-limity-a-spolehlivost)
- [Skill pro Claude Code](#skill-pro-claude-code)
- [Vývoj](#vývoj)
- [Když něco nefunguje](#když-něco-nefunguje)

---

## Instalace

**Co potřebuješ:** Python 3.11+ a API klíč ke Gemini.

```bash
git clone https://github.com/faborsky/nanobanana-app.git
cd nanobanana-app
./setup.sh
```

`setup.sh` najde vhodný Python (3.11+), vytvoří `.venv` a nainstaluje balíček.

Pak přidej svůj API klíč:

```bash
cp .env.example .env
# otevři .env a vlož do něj klíč
```

```
GEMINI_API_KEY=your-api-key-here
```

Klíč získáš na **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**. Generování obrázků je **placená funkce**, takže projekt v Google Cloudu, ke kterému klíč patří, musí mít zapnuté fakturování.

> `.env` je v gitignore. Klíč nikdy necommituj a nikdy ho nelep do kódu.

Ověř si instalaci, aniž bys cokoli utratil:

```bash
./run.sh --version
./run.sh validate jobs/example.json
```

---

## Příkazy

`run.sh` aktivuje virtualenv a všechno předá CLI, takže funguje z jakékoli složky.

| Příkaz | Co dělá | Stojí peníze |
|---|---|---|
| `generate` | Vygeneruje jeden obrázek z promptu | ano |
| `batch` | Vygeneruje víc obrázků podle JSON souboru s úlohami | ano |
| `validate` | Zkontroluje soubor s úlohami, offline | ne |
| `describe` | Rozebere existující obrázek a vrátí prompt | ano (levně) |

### generate

```bash
./run.sh generate "PROMPT" [options]
```

| Flag | Výchozí | Popis |
|---|---|---|
| `-a`, `--aspect` | `1:1` | Poměr stran |
| `-r`, `--resolution` | `1K` | `1K`, `2K`, `4K` |
| `-f`, `--format` | `webp` | `webp`, `png`, `jpeg` |
| `-o`, `--output` | `./output` | Výstupní složka (vytvoří se, když neexistuje) |
| `-n`, `--name` | odvozeno z promptu | Vlastní název souboru, bez přípony |
| `-ref`, `--reference` | žádná | Referenční obrázek pro styl nebo obsah |
| `--json` | vypnuto | Strojově čitelný výsledek na stdout |

```bash
# Široký hero obrázek v 2K jako PNG
./run.sh generate "A minimal glossy magazine cover, the title \"NANO BANANA\" in large bold sans-serif at the top, clean editorial layout, soft studio lighting" -a 16:9 -r 2K -f png

# Pojmenovaný výstup do konkrétní složky
./run.sh generate "Serene Japanese garden at dawn, cherry blossoms falling, koi pond reflection" -n japanese_garden -o ./images

# Ultraširoká tapeta ve 4K
./run.sh generate "Vast cosmic nebula with swirling purple and blue gases" -a 21:9 -r 4K
```

Soubory se jmenují `<base>_<ratio>_<resolution>_<timestamp>.<ext>`, třeba `japanese_garden_16x9_2K_20260725_104636.webp`. Časové razítko znamená, že si opakovaná spuštění navzájem nikdy nepřepíšou výsledky.

### batch

```bash
./run.sh batch jobs/example.json [-o ./images] [-d 1.0] [--json]
```

| Flag | Výchozí | Popis |
|---|---|---|
| `-o`, `--output` | `./output` | Výstupní složka pro všechny obrázky |
| `-d`, `--delay` | `1.0` | Sekundy mezi requesty |
| `--json` | vypnuto | Strojově čitelné shrnutí na stdout |

Úlohy běží po sobě, s ukazatelem průběhu, chyby jednotlivých úloh hlásí hned jak nastanou a na konci vypíše **celkovou cenu**. `Ctrl+C` dodělá rozdělaný obrázek a čistě skončí, místo aby to spadlo uprostřed zápisu.

Soubor s úlohami se kontroluje před prvním voláním API, takže tě překlep nic nestojí.

### validate

```bash
./run.sh validate jobs/example.json
```

Zkontroluje strukturu, povolené hodnoty a to, že každá `reference_path` existuje. **Žádné volání API, žádné náklady.** Pouštěj to před každou větší dávkou.

### describe

```bash
./run.sh describe image.jpg              # krátký popis, do 100 slov
./run.sh describe image.jpg --detailed   # podrobný popis rovnou použitelný jako prompt
```

Rozebere existující obrázek modelem `gemini-3.5-flash` a vrátí text, který můžeš poslat zpátky do `generate`. `--detailed` pokryje motiv, kompozici, styl, paletu, světlo, náladu i pozadí. Hodí se, když chceš zopakovat vzhled, který se ti líbí.

---

## Parametry

**Poměry stran:** `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

**Rozlišení:** `1K`, `2K`, `4K`

**Výstupní formáty:** `webp` (výchozí, kvalita 90), `png` (bezztrátový), `jpeg` (kvalita 95)

**Formáty referenčních obrázků:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

Na web a UI ber `webp` + `1K`, na tisk a tapety `png` + `2K`/`4K`. Poměr stran nastavuj přes `-a`, nikdy ho nepiš do textu promptu.

---

## Ceny

Účtuje se **za obrázek**, ne za tokeny. Zdroj: [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (ověřeno 25. 7. 2026).

| Rozlišení | Cena za obrázek |
|---|---|
| 1K | **$0.134** |
| 2K | **$0.134** |
| 4K | **$0.24** |

**1K a 2K stojí úplně stejně.** Když platíš tak jako tak, chtěj rovnou 2K. Dražší je jenom 4K.

Každý úspěšný `generate` vypíše svoji cenu, `batch` vypíše součet. Neúspěšné generování se neúčtuje a nepočítá se. Dávka 20 obrázků ve 2K vyjde zhruba na **$2.68**.

`describe` se účtuje po tokenech na `gemini-3.5-flash` ($1.50 za 1M vstupních, $9.00 za 1M výstupních), takže jde o zlomky centu za obrázek.

> Asynchronní **Batch API** od Googlu je zhruba o 50&nbsp;% levnější, ale je to jiný endpoint s frontou a odloženým doručením. Příkaz `batch` je tady sekvenční smyčka nad standardním endpointem, takže platí běžné ceny.

---

## Formát souboru s dávkou

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

`defaults` je nepovinný a platí pro každou úlohu. Každá úloha **musí** mít `prompt`. Klíče `output_name`, `aspect_ratio`, `resolution`, `format` a `reference_path` jsou volitelné a přebijí výchozí hodnoty.

Funkční příklad najdeš v [`jobs/example.json`](jobs/example.json).

---

## Výstup v JSON

`--json` pošle strojově zpracovatelný výsledek na **stdout** a všechen výstup pro člověka přesune na **stderr**, takže to můžeš bezpečně poslat rourou dál.

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

Batch vrací součty a k tomu pole s jednotlivými obrázky:

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

Když něco selže, dostaneš `{"success": false, "error": "..."}` a nenulový návratový kód.

---

## Referenční obrázky

Přilož k promptu obrázek a naveď tím model na styl nebo obsah:

```bash
./run.sh generate "Reimagine this scene at night, neon reflections on wet asphalt" -ref photo.jpg -a 16:9
```

V dávkových úlohách použij `"reference_path": "references/photo.jpg"`.

Když z reference edituješ, řekni **co se má změnit a co má zůstat stejné**. To je největší rozdíl mezi generováním a editací:

> Replace the background with a seamless deep navy studio backdrop. Keep the product, its label, and the lighting exactly the same.

Tohle CLI posílá **jednu** referenci na úlohu. Samotný model jich zvládne víc (Nano Banana Pro bere až 6 objektů a 5 postav), takže na skládání z několika referencí volej API napřímo.

---

## Jak psát prompty

Vychází z [promptovacího průvodce k Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana) od Googlu a z [dokumentace ke generování obrázků](https://ai.google.dev/gemini-api/docs/image-generation).

**Model nad promptem přemýšlí, takže mu popiš scénu místo výčtu klíčových slov.** Souvislý odstavec skoro vždycky porazí hromadu tagů oddělených čárkami.

### Vzorec

```
[Subject] + [Action] + [Location/context] + [Composition] + [Style]
```

> A striking fashion model wearing a tailored brown dress **[subject]**, posing with a confident, statuesque stance **[action]**, against a seamless deep cherry red studio backdrop **[context]**, medium-full shot, centre-framed **[composition]**, fashion editorial style shot on medium-format analog film with pronounced grain **[style]**.

### Co dělat a co ne

| Dělej | Nedělej |
|---|---|
| Piš celé věty, které popisují scénu | Sypat výčty klíčových slov (`cat, 8K, cinematic, detailed`) |
| **Formuluj kladně:** „prázdná ulice“ | Spoléhat na zápory: „žádná auta, žádní lidé“ |
| Řiď kameru: „záběr z podhledu“, „makro“, „f/1.8“ | Nechávat kompozici a světlo náhodě |
| Pojmenuj materiály: „tmavě modrý tvíd“, „zdobené ryté stříbro“ | Říct jen „bunda“, „brnění“ |
| Přesný text dej do uvozovek a pojmenuj font | Doufat, že text vyjde sám od sebe |
| Iteruj krátkými úpravami po jedné změně | Cpát všechny nápady do jednoho obřího promptu |
| Použij jednu stylovou větu napříč celou sérií | Měnit formulace a divit se, že série nedrží pohromadu |
| Řekni účel: „hero banner na landing page fintechu“ | Předpokládat, že model účel odvodí sám |

**Nejdůležitější poučení:** popisuj, co *chceš*, ne co nechceš. „Čisté jednolité pozadí“ funguje, zatímco „bez nepořádku, bez textu, bez log“ ti často vyrobí přesně to, co jsi vyloučil.

### Text v obrázcích

Tyhle modely umí vysázet čitelný stylizovaný text: loga, plakáty, infografiky, jídelní lístky.

1. Přesná slova dej do **uvozovek**.
2. Popiš typografii: *„těžkým hranatým fontem Impact“*, *„tenkým minimalistickým bezpatkovým písmem“*.
3. Řekni, kam patří: *„přes horní třetinu“*.

> A high-end glossy commercial beauty shot of a minimalist nude-coloured moisturiser jar on a warm studio background. Render the word „GLOW“ in a flowing elegant brush script above the product, and „10% OFF“ in a heavy blocky font beneath it.

### Konzistence napříč sérií

Používej v každém promptu série stejnou stylovou větu, stejný slovník pro světlo a stejný poměr stran. Když potřebuješ držet i motiv, pošli do každé úlohy tutéž referenci.

### Známé slabiny

- Hustý nebo hodně malý text může pořád vyjít nedokonale, takže drž layout jednoduchý a iteruj.
- Znalosti modelu končí v lednu 2025.
- Přemýšlecí tokeny se účtují, i když je nikdy neuvidíš (jsou už započítané v ceně za obrázek výš).

---

## Rate limity a spolehlivost

Limity závisí na tvém fakturačním tieru a vidíš je v [dashboardu rate limitů v AI Studiu](https://aistudio.google.com/rate-limit). Obrázkové modely se navíc měří v **IPM** (images per minute), ne jenom v requestech a tokenech.

Jak se chová tohle CLI:

- **429 (rate limit) a 5xx** → zkusí to znovu, nejvýš třikrát, s exponenciálním backoffem **a jitterem**, strop je 60&nbsp;s. Jitter má smysl ve chvíli, kdy běží víc dávek naráz. Bez něj by opakovaly všechny ve stejnou chvíli a narazily na tutéž zeď.
- **400 / 401 / 403 / 404** → selže hned. Neplatný prompt nebo špatný klíč dopadne pokaždé stejně, opakovat ho jenom pálí kvótu.
- **Prompty zachycené bezpečnostním filtrem** → hlásí se jako `Content filtered` a neopakují se.
- **Batch** čeká mezi obrázky `--delay` sekund (výchozí 1&nbsp;s). Když narážíš na limity IPM, zvyš to.

---

## Skill pro Claude Code

Ve složce [`skill/`](skill/) je skill pro Claude Code, který tvého agenta naučí tenhle nástroj: příkazy, ceny, pravidla promptování a to, co model umí a co ne. Návod na instalaci: **[skill/INSTALL.md](skill/INSTALL.md)**.

```bash
mkdir -p ~/.claude/skills
cp -R skill/nanobanana ~/.claude/skills/nanobanana
# pak ve skillu nahraď <NANOBANANA_APP_DIR> cestou k tomuhle repu
```

Potom si v Claude Code řekni o obrázek a agent tohle CLI obslouží za tebe.

---

## Vývoj

```bash
source .venv/bin/activate
python -m pytest tests/ -q     # offline testy, žádné volání API
ruff check nanobanana/         # lint
```

Rozložení kódu:

| Soubor | Za co odpovídá |
|---|---|
| `nanobanana/config.py` | Modely, výchozí hodnoty, enumy, validátory, ceny, rozhodování o opakování |
| `nanobanana/generator.py` | Volání Gemini API, opakování a backoff, uložení ve zvoleném formátu |
| `nanobanana/batch.py` | Parsování a validace souboru s úlohami, sekvenční průběh dávky |
| `nanobanana/cli.py` | Příkazy Typeru, výstup pro člověka i `--json` |
| `nanobanana/utils.py` | Čištění a skládání názvů souborů |

Architektonické poznámky, které potřebuje AI agent, najdeš v **[CLAUDE.md](CLAUDE.md)**, a to, jak se Gemini API na obrázky reálně chová, v **[docs/api-notes.md](docs/api-notes.md)**.

---

## Když něco nefunguje

**`Missing API key`**: `.env` neexistuje nebo v něm chybí `GEMINI_API_KEY`. Zkopíruj `.env.example` na `.env` a vlož do něj klíč.

**`404` / model nenalezen**: projekt, ke kterému klíč patří, nemusí mít přístup ke generování obrázků, nebo bylo ID modelu vyřazeno. Porovnej aktuální ID v `nanobanana/config.py` se [seznamem modelů](https://ai.google.dev/gemini-api/docs/models).

**`429 RESOURCE_EXHAUSTED`**: narazil jsi na rate limit nebo na strop útraty. CLI to zkusí znovu s backoffem. Když to trvá dál, zvyš `--delay` nebo si zkontroluj svůj tier v AI Studiu.

**`Content filtered`**: prompt spustil bezpečnostní filtr. Přeformuluj ho, opakovat stejná slova nepomůže.

**`Virtual environment not found`**: spusť `./setup.sh`.

**Starý Python**: potřebuje 3.11+. `setup.sh` vypíše, jaké interpretery našel.

---

## Licence

MIT, viz [LICENSE](LICENSE).
