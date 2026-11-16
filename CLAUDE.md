# Mexico IPV Recognition-Gap: Administrative Data Collection Pipeline

**Owner:** Elena Mijares · **Collaborator:** Merike · **Protocol version:** 15 Oct 2026 · **Last updated:** 16 Nov 2026 (step 1 built; core year 2024)

## 1. What this project is

This project adds Mexico as a new case to the IPV (intimate partner violence) recognition-gap framework of Blofield, Danforth et al. The aim is to measure how much of the IPV that **adult women** experience is **recognised by state institutions**. To do that, it compares:

- **Prevalence and help-seeking** from the survey (INEGI ENDIREH), with
- **Cases that institutions record** in police/prosecutors, health services and women's justice centres.

The project produces a reproducible pipeline. Each step records where its data came from, and each step can be re-run from raw files.

## 2. Reference year and population

**Year priority (decided 16 Nov 2026):** **2024 is the core year**, because it is the only year that all four sectors cover (CJM data ends in 2024). 2025 is added for police and health as a robustness check. If time allows, extend backwards (2023, 2022, …) so there is a time series. The pipeline takes the year as a parameter (`--year`), so going back in time only means re-running it.

**Population:** women only, with two age cut-offs:
- **Primary: women aged 15+**, which matches ENDIREH's universe.
- **Secondary: women aged 18+**, because older SESNSP data can only split minors from adults.

Where a source can't produce one of the cut-offs, record that in `docs/coverage.csv` instead of approximating silently.

**What each source can provide (checked 16 Nov 2026):**

| Source | Latest complete year | Split by sex? | Split by age? | IPV-specific? |
|---|---|---|---|---|
| SESNSP carpetas (2015–2025, old methodology) | 2025 | Not for *violencia familiar* (carpetas count cases, not people) | No | No (*violencia familiar* also covers other relatives) |
| SESNSP víctimas (2015–2025, old methodology) | 2025 | Yes, for the crimes covered (femicide, homicide, *lesiones*, etc.) | Under 18 / 18+ only | No |
| SESNSP RNID (new methodology, Jan 2026 →) | 2026 is partial (Jan–Sep published as of Nov 2026) | **Yes, all crimes incl. *violencia familiar*** | Bands 0–12, 13–17, 18–29, 30–60, 60+, so **18+ is possible but 15+ is not** | Partial (check whether the relationship to the aggressor is recorded) |
| SESNSP 911 calls (in the *Informe VCM*) | 2025 | No (sex is assumed, not recorded) | No | **Yes:** there is a *violencia de pareja* call category |
| DGIS injuries (*Lesiones y causas de violencia*) | **2025** (file confirmed available) | Yes | Yes (single years) | **Yes:** the aggressor can be recorded as *Cónyuge/Pareja/Novio* |
| INEGI CJM 2025 edition (published 26 Mar 2026) | 2023 and 2024 (76 CJM, all 32 states) | Women only | **Yes**, 5-year groups, so 15+ and 18+ are exact | Partly: partner incidents are counted, but not by age |
| ENDIREH | 2021 is the latest; the 2026 round is being fielded and results are expected later | Women | 15+ | Yes |

**Implication:** for police data, the open data can split *violencia familiar* by sex and age only from **January 2026**. For 2025 and 2024 there are three options:
- (a) report all victims and use another source to estimate the share of adult women;
- (b) ask the 32 *fiscalías* for counts by sex and age through transparency requests;
- (c) add 2026 as an extra police year once it is complete.

This decision is open (see §8).

## 3. Goals (definition of done)

1. Raw data for each source is downloaded or requested, saved unchanged, and logged with its source URL and retrieval date.
2. The data is filtered to **women 15+ (and 18+)** and to IPV-attributable categories for the reference year, using a documented crosswalk.
3. Police crime counts (carpetas) are converted to victim counts. Unadjusted figures are reported next to the adjusted ones.
4. All sources are harmonised to state × year × age group (INEGI `cve_ent`).
5. Recognition-gap indicators are computed for each sector against ENDIREH prevalence.
6. There is a literature pipeline (PubMed + Semantic Scholar, deduplicated, with a screening sheet), shared with Merike as a repo.
7. There is a directory of CJMs and other centres, with templated transparency requests and a tracker for each request.
8. There is a written note on validation and limitations, including `docs/coverage.csv`, which records what each source can and can't split.

## 4. Sources

| Sector | Source | Use for IPV / adult women | How to get it |
|---|---|---|---|
| Police | SESNSP open data: carpetas, víctimas, *Informe de violencia contra las mujeres* (incl. 911 calls), RNID 2026 → | *Violencia familiar*, sexual crimes, femicide; 911 *violencia de pareja* calls; RNID gives sex and age from 2026 | Scripted download of the monthly files and data dictionaries. Store the old (2015–2025) and new (2026 →) methodologies separately; they are not directly comparable |
| Health | Secretaría de Salud DGIS: *Lesiones y causas de violencia* (SINBA-SEUL-17), CNEGSR | Filter: intent = *violencia familiar*, aggressor = *Cónyuge/Pareja/Novio*, sex = woman, age ≥ 15 | Download the open microdata or cubes; ask CNEGSR for registry counts |
| Women's centres | INEGI CJM 2025 edition (2024 data); CONAVIM; EQUIS | Women attended, by type of violence and relationship to the aggressor | Download the INEGI CJM tables; ask CONAVIM and EQUIS to fill gaps; shelters still to be mapped |
| Survey | INEGI ENDIREH 2021 (2026 round to come) | Prevalence of IPV in the last 12 months and help-seeking, women 15+ | Download the microdata; INEGI indicators API |

Key prior uses: Hoehn-Velasco et al. 2021 (SESNSP); Frías & Agoff 2015 and López Ramos & Frías 2020 (ENDIREH help-seeking); EQUIS Justicia para las Mujeres 2018–2021 (CJM).

## 5. Pipeline stages

1. **Acquire** ✅ *built*. One engine reads `config/sources.yaml` and downloads every source, for example `python -m src.acquire run --year 2025`. Files are saved unchanged to `data/raw/<source>/<year or edition>/<dataset>/` and logged in `data/raw/manifest.csv` (URL, link text, retrieval time, SHA-256, methodology). Manually obtained files are added with `python -m src.acquire register`. See README.md.
2. **Filter** 🔨 *in progress*. Keep women (15+ and 18+ flags), the reference year, and IPV-attributable categories. Every inclusion or exclusion has a stated reason. **CJM done** (`python -m src.filter.cjm --year 2024`; column map verified against the FD codebook in `config/cjm_2025_columns.csv`). DGIS waits for the coding manual; SESNSP and ENDIREH next.
3. **Crimes → victims.** Convert SESNSP carpetas to victims and keep both columns (`*_unadjusted`, `*_victims`).
4. **Harmonise.** Aggregate to state × year × age group and log what each source covers in `docs/coverage.csv`.
5. **Compute the recognition gap.** For each sector and state, compare institutional counts of adult women with the ENDIREH estimates of affected women and of women who sought help. Use survey weights and report confidence intervals.

## 6. Side workstreams

**Literature.** Run the original Boolean string and the MeSH query
`("Intimate Partner Violence"[MeSH] OR "Domestic Violence"[MeSH]) AND Mexico[MeSH]`
through PubMed E-utilities. Deduplicate against Semantic Scholar on DOI and then on normalised title. Export `lit_review/screening.csv` for manual title screening.

**Contacts.**
1. Build `contacts/cjm_directory.csv` (centre, state, host institution, contact) from the INEGI CJM tables and CONAVIM.
2. Generate one information request per centre from `contacts/templates/solicitud.md`. Requests ask for **2025 (or 2024) counts of women attended, split by age group and by relationship to the aggressor**.
3. Submit the requests manually through the Plataforma Nacional de Transparencia (now under Transparencia para el Pueblo). Log folio numbers, dates, deadlines and responses in `contacts/request_tracker.csv`.
4. *(Optional)* Send the same kind of request to the 32 state *fiscalías* for *violencia familiar* victims by sex and age for 2025.

## 7. Repository layout and conventions

```
config/sources.yaml    # every source, URL, link rule (edit this, not code)
data/
  raw/<source>/<year|edN>/<dataset>/  # immutable downloads + manifest.csv
  interim/             # filtered (women, ages, IPV categories)
  processed/           # harmonised state × year × age tables
src/
  acquire/             # step 1 engine + CLI (run, status, check, links, register)
  clean/               # filters + crosswalk application
  analysis/            # victim conversion, gap indicators
lit_review/            # pubmed.py, semantic_scholar.py, screening.csv
contacts/              # directory, templates, request tracker
docs/                  # ipv_crosswalk.csv, coverage.csv, codebook.md, decisions.md
```

- Python 3.11+. Every step is idempotent (it skips work already done unless `--force` is passed) and is parameterised by year.
- When a government URL changes, fix `config/sources.yaml`, not the code. Untested URLs there are marked `VERIFY`.
- Keep `python -m pytest -q` passing. The tests are offline and use a local server in place of the government sites.
- Variable names stay in their original Spanish, with English labels in `docs/codebook.md`.
- Every analytic decision gets a dated entry in `docs/decisions.md`.
- Don't hard-code numbers taken from reports. Derive them from raw files or cite them in the manifest.
- `data/` is git-ignored except for manifests. Microdata is not committed.

## 8. Open questions

- **Police data for adult women in 2025/2024.** Use all victims plus an external estimate of the share of adult women, send transparency requests to the *fiscalías*, or add 2026 (new methodology)?
- **Survey timing.** ENDIREH 2021 is several years older than the administrative data. Should the comparison be updated once ENDIREH 2026 is released, which would line up with the 2026 police data?
- **Age cut-off.** 15+ as the primary population and 18+ as a sensitivity check? SESNSP can only provide 18+, so police comparisons are 18+ by necessity.
- **IPV attribution in police data.** *Violencia familiar* is broader than IPV. Use the 911 *violencia de pareja* share or the DGIS *Cónyuge/Pareja* share as an adjustment?
- **CJM IPV count.** Women by age and incidents by relationship are separate tables in the CJM data. Use the estimate `women 15+ × partner share of incidents`, use partner incidents (all ages), or request a cross-tab from the centres? See docs/decisions.md.
- **Shelters and non-CJM centres.** These still need to be identified and mapped.

## 9. Known limitations

- Reporting is uneven across state prosecutors' offices, and the health sector is only partly covered.
- SESNSP changed methodology in January 2026, so the series breaks between 2025 and 2026.
- The survey and administrative data cover different periods.
- Administrative categories don't match the definition of IPV.
