# Mexico IPV recognition-gap pipeline

> **New here or not technical?** Start with [`docs/GUIDE.md`](docs/GUIDE.md): what the project is, what has been done, the key files (such as the manifest) and next steps, in plain language.

Code for adding Mexico to the IPV recognition-gap framework (Blofield, Danforth et al.).
The full brief, including goals, sources and open questions, is in **CLAUDE.md**.

## Setup (once)

```bash
python -m venv .venv
source .venv/bin/activate          
pip install -r requirements.txt
python -m pytest -q                # offline tests, should all pass
```

## Step 1 – Acquire

```bash
# 1. Check the configured URLs work from your machine (shows HTTP status for each)
python -m src.acquire check --year 2024

# 2. See what would be downloaded
python -m src.acquire run --year 2024 --dry-run

# 3. Download
python -m src.acquire run --year 2025
python -m src.acquire run --year 2024          # CJM data and fallback year

# 4. See what you have and what's missing
python -m src.acquire status --year 2024
```

Every file goes to `data/raw/<source>/<year or edition>/<dataset>/` and gets a row in
`data/raw/manifest.csv`. Each row records the URL, the link text, the retrieval time and a SHA-256 hash.

**Re-running is safe.** Files already in the manifest are skipped. With `--force`, the file is
downloaded again. If the content changed, the old version is kept in `data/raw/_superseded/`.

### When a download fails

Government URLs move. If a dataset shows `✗ failed`:

1. List the links on that source's page and find the right file:
   ```bash
   python -m src.acquire links sesnsp --grep víctimas
   ```
2. Paste the exact URL into the dataset's `urls:` list in `config/sources.yaml` and run again.
   Google Drive share links, which SESNSP uses, are converted to direct downloads automatically.
3. Or download the file in your browser and register it (see below).

### Manually obtained files

Use this for transparency-request responses (PNT), CNEGSR counts, and the SESNSP women's report PDF:

```bash
python -m src.acquire register --source cnegsr --dataset solicitud_registros --year 2025 \
    --file ~/Downloads/respuesta.xlsx --url "PNT folio 330024..." --notes "received 2026-12-01"
```

The original file stays where it is; a copy is logged in the manifest.

## Step 2 – Filter

```bash
python -m src.filter.all --year 2024      # SESNSP, CJM, DGIS for the year + ENDIREH 2021
python -m src.filter.sesnsp --year 2025   # or one source at a time
python -m src.filter.endireh --edition 2021   # ~2 min (survey standard errors)
```

Outputs go to `data/interim/<source>/`. Every inclusion and exclusion rule, with its reason and
where it was checked, is in `docs/ipv_crosswalk.csv`; what each source can split is in
`docs/coverage.csv`; analytic choices are in `docs/decisions.md`.

| Source | Output | Population | IPV definition |
|---|---|---|---|
| SESNSP | `sesnsp_<year>_states.csv`, `sesnsp_trend_2015_2025.csv` | cases: all; victims: women 18+ | *violencia familiar* carpetas (proxy) + related crimes |
| CJM | `cjm_<year>_centres.csv`, `cjm_<year>_states.csv` | women 15+/18+ | partner incidents (estimate, see decisions) |
| DGIS | `dgis_<year>_states.csv` | women 15+/18+ (attentions) | family violence by spouse/partner |
| ENDIREH | `endireh_2021_estimates.csv` (long, with SE/CI) | women 15+/18+ | VPAR_12M / VPAR_A, help-seeking by institution |

## Layout

```
config/sources.yaml   every source, URL and link-matching rule (edit this, not the code)
src/acquire/          step 1 engine + command-line interface
src/filter/           step 2 filters (one module per source) + all.py
data/raw/             immutable downloads + manifest.csv (only the manifest is in git)
docs/GUIDE.md         plain-language guide: status, key files, next steps
docs/ipv_crosswalk.csv  every inclusion/exclusion rule, with reason
docs/coverage.csv     what each source can split (sex, age, IPV), and how it was checked
docs/decisions.md     dated log of analytic decisions
tests/                offline tests (a local server stands in for the government sites)
```
