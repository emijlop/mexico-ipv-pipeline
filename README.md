# Mexico IPV recognition-gap pipeline

Code for adding Mexico to the IPV recognition-gap framework (Blofield, Danforth et al.).
The full brief, including goals, sources and open questions, is in **CLAUDE.md**.

## Setup (once)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # offline tests, should all pass
```

## Step 1 – Acquire

```bash
# 1. Check the configured URLs work from your machine (shows HTTP status for each)
python -m src.acquire check --year 2025

# 2. See what would be downloaded
python -m src.acquire run --year 2025 --dry-run

# 3. Download
python -m src.acquire run --year 2025
python -m src.acquire run --year 2024          # CJM data and fallback year

# 4. See what you have and what's missing
python -m src.acquire status --year 2025
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

## Layout

```
config/sources.yaml   every source, URL and link-matching rule (edit this, not the code)
src/acquire/          step 1 engine + command-line interface
data/raw/             immutable downloads + manifest.csv (only the manifest is in git)
docs/coverage.csv     what each source can split (sex, age, IPV), and how it was checked
docs/decisions.md     dated log of analytic decisions
tests/                offline tests (a local server stands in for the government sites)
```

## Step 2 – Filter (in progress)

```bash
python -m src.filter.cjm --year 2024     # women's centres: women 15+/18+, partner incidents, reporting
```

Output goes to `data/interim/<source>/`. Each script checks its column choices against the source's
codebook before running, and stops with an error if something doesn't match.
