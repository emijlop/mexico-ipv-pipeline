# Decisions log

Newest first. One entry per analytic decision: what, why, alternatives, who.

## 2026-11-16 — CJM: how to count women attended for IPV (OPEN)
- **Constraint (from the FD codebook):** women by age (q5.1.9) and incidents by relationship to the aggressor (q5.1.14) are separate tables; there is no women x age x relationship cross-tab. Relationship counts are incidents (one woman can have several), not women.
- **Implemented:** the step outputs all ingredients plus one estimate, `est_women_15plus_partner = women_15plus x (partner incidents / all incidents)`, where partner = pareja + expareja + novio + novia.
- **Missing values:** a multi-part count (e.g. partner = 4 categories) sums the parts a centre reported; it is missing only if all parts are missing, and `<measure>_n_missing` flags partial sums (lower bounds). The partner share is computed only over centres reporting both partner and total incidents.
- **Reporting:** q5.2.1 'Total' includes women who did not report; `women_reported` = denuncia + querella.
- **Added (16 Nov):** `share_partner_known_rel` (partner / incidents with relationship recorded) next to the all-incidents share; `women_15plus_adj` / `women_18plus_adj` spread 'age not specified' (41% of women in 2024) in proportion to known ages. Raw counts kept. INEGI's results report shows 51.1% of 2023-24 incidents have no violence type recorded and 5 states record none, so CJM detail rests on a subset of centres.
- **To decide:** use the estimate, partner incidents (all ages) as an upper-bound proxy, or request a women x age x relationship cross-tab from CJMs via transparency requests.

## 2026-11-16 — Core year = 2024
- **Decision:** 2024 is the core analysis year; 2025 is added for SESNSP and DGIS as a robustness check.
- **Why:** 2024 is the latest year with all four sectors (CJM 2025 edition ends at 2024); DGIS 2024 has a matching coding manual (no 2025 manual yet).
- **Alternative considered:** 2025 as core year: more recent, but no CJM data and DGIS 2025 may be preliminary.
- **By:** Elena Mijares

## 2026-11-16 — Reference year and population
- **Decision:** Target 2025, fall back to 2024; extend backwards (2023, 2022) if time allows. Population = women 15+ (primary), 18+ (secondary).
- **Why:** Most recent data is most policy-relevant; 15+ matches ENDIREH.
- **Constraint found:** SESNSP open data splits violencia familiar by sex/age only from Jan 2026 (new RNID methodology), with age bands 0-12/13-17/18-29/30-60/60+, so a 15+ cut is impossible from SESNSP and 18+ is the best available. Pre-2026 victim data cover only some crimes and split minors/adults.
- **Open:** how to handle police data for 2025/2024 (external share, fiscalía requests, or add 2026). See CLAUDE.md §8.
- **By:** Elena Mijares

## 2026-11-16 — Acquisition design
- **Decision:** One config-driven acquisition engine (`config/sources.yaml` + `src/acquire`), not one script per source. Every file is logged in `data/raw/manifest.csv` with URL, link text, retrieval time and SHA-256; raw files are never edited; re-downloads that change content keep the old version under `data/raw/_superseded/`.
- **Why:** Government URLs change often; editing one YAML file is easier and more auditable than editing code.
