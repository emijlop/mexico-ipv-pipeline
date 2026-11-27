# Decisions log

Newest first. One entry per analytic decision: what, why, alternatives, who.

## 2026-11-27 — Tabla armonizada (paso 4): prototipo Ciudad de México
- **Construido:** `src/harmonise.py` → `data/processed/tabla_armonizada_<años>[_<estado>].csv`. Prototipo con CDMX (`--state 09`, 2024 y 2025); el mismo comando sin `--state` produce los 32 estados.
- **Decisiones (confirmadas por Elena Mijares):**
  1. Formato largo: una fila = un conteo de una fuente, para un estado, año y grupo de edad. Cada fila lleva su unidad (carpetas, víctimas, mujeres atendidas, incidentes, atenciones, mujeres entrevistadas, mujeres estimadas), porque las fuentes cuentan cosas distintas.
  2. Grupos de edad: 15+, 18+, "todas" y "edad no registrada". No hay grupos quinquenales (la policía solo separa menores/adultas). La edad no registrada no se reparte entre los demás grupos.
  3. Año: cada fuente conserva su año; la ENDIREH queda como 2021.
  4. Estado: donde la institución registró el caso (fiscalía, CJM, unidad de salud por CLUES); en la encuesta, el estado de residencia.
  5. Sin conversiones ni estimaciones: carpetas siguen siendo carpetas (paso 3 pendiente); en CJM, mujeres por edad e incidentes de pareja van en filas separadas.
  6. Encuesta: dos filas por indicador (mujeres entrevistadas y estimación con factores de expansión de INEGI); se marca `precision_baja` con menos de 30 entrevistadas o CV > 30%.
  7. Vacío = no reportado (nunca se rellena con 0).
  8. Solo los indicadores más cercanos a violencia de pareja; abuso sexual, acoso y lesiones (carpetas) quedan en los archivos del paso 2.
- **Hallazgos CDMX 2024:** en CJM, 29,381 de 49,842 mujeres sin edad y 36,577 de 49,842 incidentes sin relación con el agresor; CDMX reporta 0 carpetas de "violencia de género distinta a la familiar" en 2024 y 2025 (probablemente no usa la categoría); apoyo pedido a CJM (12 entrevistadas) y salud (6) no es utilizable a nivel estatal.
- **Siguiente:** revisar con la profesora/el profesor y correr para los 32 estados.
- **Añadido (27 nov):** filas separadas para niñas y adolescentes, contadas directamente de los datos (no por resta): policía "menores (0–17)" (víctimas de feminicidio, homicidio doloso y lesiones dolosas); CJM y salud "menores de 15" y "15–17"; encuesta "15–17" (la ENDIREH no entrevista a menores de 15). Las filas "15+" siguen incluyendo a las adolescentes de 15–17; para mujeres adultas usar "18+". En salud, edades registradas en horas, días o meses cuentan como menores de 15.

## 2026-11-27 — Step 2 filters for SESNSP, DGIS and ENDIREH
- **Built:** `src/filter/sesnsp.py`, `dgis.py`, `endireh.py`, plus `all.py` to run every source for one year. All inclusion rules are in `docs/ipv_crosswalk.csv`; DGIS codes in `config/dgis_codes.yaml` are now verified against the 2024 manual.
- **SESNSP:** keeps *violencia familiar* carpetas as the core police proxy (all ages and sexes; no split exists before 2026), with related crimes (gender violence other than family violence, femicide, rape, sexual abuse, harassment, intentional injuries) next to it. Women 18+ victims only for femicide, intentional homicide and intentional injuries. Crimes → victims is left for step 3.
- **DGIS:** women 15+/18+, intentionality = family violence (2) and aggressor = spouse/partner (3). Counts are attentions, not women (no person ID). State = health unit's state (CLUES prefix); agrees with CodEstado for 95% of records. Family-violence records with no relationship kept as a separate lower-bound flag. In 2024, 81% of family-violence records of women 15+ with a known relationship were by a partner: a candidate for the police IPV adjustment (open question, PROJECT_BRIEF.md §8).
- **ENDIREH:** prevalence of partner violence (VPAR_12M = 1, VPAR_A = 1; coding confirmed 1 = yes) and help-seeking by institution (CJM, public health, police, Ministerio Público), women 15+ and 18+, national and by state, with survey-weighted SEs (Taylor linearisation; EST_DIS strata, UPM_DIS PSUs). Checks: 20.7% (last 12 months) and 39.9% (relationship) of ever-partnered women, matching INEGI's published figures.
- **Choices made (review):** (1) ENDIREH 'no especificado' (9) counts as 'no' and stays in the denominator, as INEGI does. (2) Help-seeking refers to the whole relationship; 'recent' versions use last request/complaint in 2020–2021 as a reference-period proxy. (3) Estimates with CV > 30% or fewer than 30 cases are flagged `low_precision`; 44% of state-level estimates are, mostly help-seeking by institution.
- **Not done:** RNID (2026) police data; DGIS 2025 (not downloaded yet); 911 *violencia de pareja* calls (manual download).
- **By:** Elena Mijares (built with Claude)

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
- **Open:** how to handle police data for 2025/2024 (external share, fiscalía requests, or add 2026). See PROJECT_BRIEF.md §8.
- **By:** Elena Mijares

## 2026-11-16 — Acquisition design
- **Decision:** One config-driven acquisition engine (`config/sources.yaml` + `src/acquire`), not one script per source. Every file is logged in `data/raw/manifest.csv` with URL, link text, retrieval time and SHA-256; raw files are never edited; re-downloads that change content keep the old version under `data/raw/_superseded/`.
- **Why:** Government URLs change often; editing one YAML file is easier and more auditable than editing code.
