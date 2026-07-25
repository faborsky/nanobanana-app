# Instalace skillu `/nanobanana` do Claude Code

Tahle složka obsahuje **skill pro Claude Code**, který obaluje CLI aplikaci v tomhle repu a přidává know-how ke generování obrázků — ceny za kus, podporované formáty a rozlišení, oficiální pravidla promptování a hlavně co model umí a co ne. Po instalaci ho v Claude Code vyvoláš jako `/nanobanana`.

> Skill bez aplikace nefunguje — nejdřív zprovozni samotnou appku podle hlavního [`README.md`](../README.md) (`./setup.sh` + klíč v `.env`).

## Předpoklady

1. **Naklonovaný tenhle repozitář** a funkční appka (`./setup.sh` proběhl, `.env` má klíč).
2. Nainstalovaný **Claude Code**.

### Kde vzít API klíč

1. Otevři **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** a vygeneruj klíč.
2. Klíč vlož do `.env` v repu appky jako `GEMINI_API_KEY` (šablona je v `.env.example`).
3. **Generování obrázků je placená funkce** — projekt, ke kterému klíč patří, musí mít zapnuté fakturování. Bez toho ti volání spadne na chybu o oprávnění.

> Klíč je heslo k tvému účtu přes API — patří jen do `.env` (je v `.gitignore`), nikdy do kódu ani do gitu.

## Krok za krokem

Předpokládejme, že sis repo naklonoval do `~/dev/nanobanana-app` (uprav cesty podle sebe).

### 1) Zkopíruj skill do své Claude Code složky se skilly

```bash
mkdir -p ~/.claude/skills
cp -R ~/dev/nanobanana-app/skill/nanobanana ~/.claude/skills/nanobanana
```

### 2) Nastav skillu cestu k appce

Skill volá aplikaci přes placeholder `<NANOBANANA_APP_DIR>`. Nahraď ho **absolutní cestou** ke svému klonu repa. Jednorázově:

```bash
# macOS — uprav cestu za = na svoji
APP_DIR="$HOME/dev/nanobanana-app"
sed -i '' "s#<NANOBANANA_APP_DIR>#$APP_DIR#g" ~/.claude/skills/nanobanana/SKILL.md

# na Linuxu použij:
# sed -i "s#<NANOBANANA_APP_DIR>#$APP_DIR#g" ~/.claude/skills/nanobanana/SKILL.md
```

> Můžeš to udělat i ručně — otevři `~/.claude/skills/nanobanana/SKILL.md` a nahraď všechny výskyty `<NANOBANANA_APP_DIR>` cestou ke své appce.

### 3) Ověř

Otevři Claude Code a napiš:

```
/nanobanana
```

Skill by se měl nabídnout. Zkus třeba:

```
/nanobanana udělej mi cover na článek o vibe codingu, na šířku
```

Claude si doptá, co potřebuje vědět, řekne ti **kolik to bude stát**, a teprve pak generuje.

## Co skill umí

- **Jeden obrázek** z textového promptu — poměr stran, rozlišení, formát.
- **Dávku obrázků** z JSON souboru, včetně bezplatné kontroly (`validate`) předtím, než se cokoli zaplatí.
- **Práci s referenčním obrázkem** — stylová transformace, úprava existující scény.
- **Analýzu obrázku** (`describe`) — z existujícího obrázku vytáhne prompt, který můžeš použít dál.
- **Hlídá ceny** — zná cenu za kus, u větších dávek ti řekne cenu dopředu a po vygenerování nahlásí reálnou.
- **Zná pravidla promptování** — formuli `[Subject] + [Action] + [Context] + [Composition] + [Style]`, tabulku DO/DON'T a hlavní lekci: *popisuj, co chceš, ne co nechceš*.
- **Zná limity modelu** — že neumí průhledné pozadí, že drobný text se láme, že má knowledge cutoff v lednu 2025.

## Dvě věci, které ti ušetří peníze

1. **1K a 2K stojí úplně stejně** ($0,134 za kus). Skill proto defaultně bere **2K** — za stejné peníze dostaneš víc. 4K je dražší ($0,24), takže jen když ho reálně potřebuješ.
2. **U dávky vždycky nejdřív `validate`.** Je zdarma a offline. Bez něj ti chyba v desátém jobu spadne až po devíti zaplacených obrázcích.

## Doplň si skill o své vlastní know-how (doporučeno!)

Tenhle skill je **schválně univerzální** — umí nástroj a umí promptovat, ale nezná tvoji značku. Největší hodnotu z něj dostaneš, když si ho přizpůsobíš. Skill je jen složka markdown souborů, takže je to snadné:

1. **Přidej vlastní referenční dokument.** Do `~/.claude/skills/nanobanana/` si vytvoř např. `muj-styl.md` a sepiš:
   - tvoji barevnou paletu a vizuální styl (a klidně i konkrétní osvědčené prompty),
   - formáty, které reálně používáš (rozměry pro tvůj web, socky, newsletter),
   - kam se obrázky mají ukládat ve tvých projektech,
   - co ve vizuálech nikdy nechceš (klišé stock estetika, konkrétní barvy, motivy).

2. **Odkaž na něj ze `SKILL.md`.** Přidej řádek, ať ho Claude načítá:
   ```
   - `muj-styl.md` — moje vizuální pravidla (VŽDY přečíst před generováním)
   ```

3. **Klidně si uprav i defaulty.** Nelíbí se ti `webp`? Chceš jiný výchozí poměr stran? Je to tvůj soubor.

> Čím konkrétnější kontext skillu dáš, tím víc budou výstupy „tvoje". Univerzální skill = univerzální obrázky.

## Aktualizace skillu

Když stáhneš novější verzi repa, zopakuj krok 1 (přepíše starou verzi) a krok 2 (znovu nastav cestu). Pokud jsi měl vlastní `muj-styl.md`, ten zůstane — krok 1 přepisuje jen `SKILL.md`.
