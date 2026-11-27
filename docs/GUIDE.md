# Project guide: Mexico IPV recognition gap

*Last updated: 27 November 2026 · Elena Mijares*

This guide explains, without code, what this project is, what has been done, where to find
things in this folder, and what comes next. If you only read one file, read this one.
The technical how-to is in [`README.md`](../README.md); the full brief is in [`CLAUDE.md`](../CLAUDE.md).

---

## 1. What the project is about

Many women experience violence from a partner (intimate partner violence, IPV), but only some
of them ever appear in official records. This project measures that difference for Mexico,
the **recognition gap**, as part of the comparative framework of Blofield, Danforth et al.

We put two kinds of numbers side by side:

- **How many women experience partner violence:** from a national survey of women (ENDIREH).
- **How many cases institutions record:** from the police and prosecutors, public health
  services, and women's justice centres.

The population is **women aged 15 and over** (and 18 and over, because some sources only
separate minors from adults). The main year is **2024**, the latest year all sources cover.

---

## 2. Where we are

The work has five steps. The first two are done.

| Step | In plain words | Status |
|---|---|---|
| 1. Collect | Download the original files and record where each came from | Done |
| 2. Select | Keep only women and only the categories related to partner violence | Done for all four sources |
| 3. Cases → people | Police data counts cases; convert them to people | Not started |
| 4. Line up | Put every source in the same table: state × year × age group | Not started |
| 5. Compare | Compare recorded cases with the survey to measure the gap | Not started |

Two side tasks have not started: a literature search (to share with Merike) and
transparency requests to women's centres.

---

## 3. The most important files to look at

You don't need to open the code. These files tell the whole story:

| File | What it tells you | Open it when you want to know… |
|---|---|---|
| [`data/raw/manifest.csv`](../data/raw/manifest.csv) | **The list of every original file we have**: source, web address, the date we downloaded it, and a fingerprint (checksum) proving it hasn't changed | …where a number comes from, or whether we have a file |
| [`docs/ipv_crosswalk.csv`](ipv_crosswalk.csv) | **Every rule used to select records**, one per line, with the reason and the page of the official manual it was checked against | …why something was counted or left out |
| [`docs/coverage.csv`](coverage.csv) | **What each source can and cannot tell us**: does it record sex? age? the relationship to the aggressor? | …whether a source can answer a question |
| [`docs/decisions.md`](decisions.md) | **A dated diary of every choice** made in the analysis, with the alternatives considered | …why we did it this way |
| `data/interim/` | **The selected data**, one folder per source (see section 5) | …the actual numbers |

### How to read the manifest

Each row is one file. The columns that matter:

| Column | Meaning |
|---|---|
| `source` | Who published it: `sesnsp` (police), `dgis` (health), `cjm` (women's centres), `endireh` (survey) |
| `dataset` | Which file from that source |
| `file` | Where it is saved in this folder |
| `url` | Where it was downloaded from (or, for files saved by hand, the page it came from) |
| `retrieved_at` | When it was downloaded |
| `sha256` | The file's fingerprint: if the file changes, this changes |
| `method` | `download` (by the script) or `manual` (saved by hand) |
| `status` | `current` = in use; `superseded` = an older version kept for the record |

The manifest has 13 files listed today. The original files themselves are kept on this
computer only (they are too large and some are microdata), not on GitHub.

---

## 4. The four sources

| Source | Who publishes it | What it records | Can it tell us… |
|---|---|---|---|
| **Police** (SESNSP) | Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública | Criminal investigation files (*carpetas*) opened by state prosecutors | …if the victim is a woman? Only for some crimes. Her age? Only under/over 18. A partner? No |
| **Women's centres** (CJM) | INEGI census of Centros de Justicia para las Mujeres | Women attended by each centre, and the violence they reported | …women? Yes (all are). Age? Yes. A partner? Yes, but for incidents, not women |
| **Health** (DGIS) | Secretaría de Salud, injury and violence register | Each time a person is treated for an injury or violence in a public health unit | …woman? Yes. Age? Yes. A partner? Yes |
| **Survey** (ENDIREH 2021) | INEGI, national survey of women 15+ | Women's own reports of violence and whether they asked for help | …all of it, but for 2021, and as estimates for the whole population |

---

## 5. What the selected data shows (2024)

These are **counts as they appear in the data**. No adjustments, averages or percentages
have been applied. Note that each source counts something different (cases, visits,
incidents, women), so the numbers are not directly comparable yet. That is what steps 3–5 are for.

### Police: SESNSP, 2024 ([`data/interim/sesnsp/`](../data/interim/sesnsp/))

| What is counted | Count |
|---|---|
| Investigation files for *violencia familiar* (family violence, all ages and sexes) | 278,276 |
| Investigation files for gender violence other than family violence | 6,614 |
| Investigation files for femicide | 826 |
| Investigation files for rape | 21,473 |
| Investigation files for intentional injuries (all victims) | 164,632 |
| Women 18+ victims of femicide | 723 |
| Women 18+ victims of intentional homicide | 2,063 |
| Women 18+ victims of intentional injuries | 59,786 |

*Family violence* is the closest police category to partner violence, but it also includes
violence by other relatives, and before 2026 it does not say whether the victim was a woman
or her age. The same file also holds 2025 and a 2015–2025 series by state.

### Women's centres: CJM, 2024 ([`data/interim/cjm/`](../data/interim/cjm/))

| What is counted | Count |
|---|---|
| Centres | 76 |
| Women attended (all ages) | 638,720 |
| Women attended aged 15+ | 351,621 |
| Women attended aged 18+ | 339,456 |
| Women attended with age not recorded | 261,790 |
| Violence incidents recorded (all relationships) | 640,911 |
| Incidents by a partner or ex-partner | 174,329 |
| Incidents with the relationship not recorded | 408,889 |
| Women who filed a criminal complaint | 128,022 |

The CJM data counts women by age and incidents by relationship in **separate tables**, so
we cannot yet say how many women 15+ came because of a partner.

### Health: DGIS, 2024 ([`data/interim/dgis/`](../data/interim/dgis/))

| What is counted | Count |
|---|---|
| All records in the register (any injury, anyone) | 1,074,543 |
| Health units reporting | 5,226 |
| Visits by women 15+ for family violence | 70,459 |
| … of which the aggressor was a spouse or partner | 52,187 |
| … of which the relationship was not recorded | 6,259 |
| Visits by women 18+ for violence by a partner | 46,638 |
| Partner-violence visits (women 15+) where the Ministerio Público was notified | 27,957 |

These are **visits, not women**: a woman treated twice is counted twice. The register mainly
covers Secretaría de Salud and IMSS-Bienestar units, not IMSS, ISSSTE or private clinics.

### Survey: ENDIREH 2021 ([`data/interim/endireh/`](../data/interim/endireh/))

The survey interviewed 110,127 women. INEGI turns each answer into an estimate for the whole
country using official weights, which is how INEGI itself reports the survey. Both numbers are shown.

| What is counted (women 15+) | Women interviewed | Estimated women in Mexico |
|---|---|---|
| All women 15+ | 110,127 | 50,523,469 |
| Had a partner or ex-partner | 105,278 | — |
| Partner violence in the last 12 months | 22,215 | 9,804,752 |
| Partner violence at any time in the current or last relationship | 41,576 | 18,880,163 |
| Of those, asked an institution for help or filed a complaint | 4,987 | 2,157,927 |
| … complained to the police or the Ministerio Público | 2,207 | 968,514 |
| … asked a Centro de Justicia para las Mujeres | 409 | 154,851 |
| … asked a public clinic or hospital | 195 | 88,736 |

INEGI reports partner violence as a share of women who have had a partner: **20.7%** in the
last 12 months and **39.9%** over the relationship. Our selected data reproduces both figures,
which confirms the selection is right. Per state, the counts behind some estimates are small
(sometimes under 30 women interviewed), so state figures for individual institutions are
flagged in the file as low precision.

---

## 6. Checklist against the protocol (15 October 2026)

| Protocol item | Status | Where it stands |
|---|---|---|
| Police: download SESNSP files | Done | Cases and victims 2015–2025 |
| Police: 911 calls for *violencia de pareja* | Not started | Has to be saved by hand |
| Survey: ENDIREH 2021 | Done | Downloaded and selected |
| Survey: INEGI indicators API | Not started | Not needed so far |
| Health: DGIS register | In progress | 2024 done; 2025 not downloaded yet |
| Health: request counts from CNEGSR | Not started | |
| Women's centres: INEGI CJM data | Done | 2025 edition (2023–2024 data) |
| Women's centres: CONAVIM, EQUIS, shelters | Not started | |
| Literature search, shared with Merike | Not started | |
| Directory of centres and transparency requests | Not started | |
| Save files with source and date | Done | See the manifest |
| Select partner-violence records for the year | Done | All four sources, 2024 |
| Convert police cases to people | Not started | Next step |
| Line up sources by state, year and age | Not started | |
| Compute the recognition gap | Not started | |
| Note on validation and limitations | In progress | `coverage.csv` and `decisions.md` exist; the note does not |

---

## 7. Decisions still to make

1. **Police data for adult women in 2024/2025.** Before 2026 the police data doesn't say
   whether a family-violence victim is a woman or an adult. Options: estimate it from another
   source; ask the 32 state prosecutors through transparency requests; or add 2026, when the
   new police data records sex and age.
2. **How much family violence is partner violence.** Police *family violence* includes other
   relatives. The health register (52,187 partner visits of 64,200 with a known relationship)
   and the women's centres (174,329 partner incidents of 232,022 with a known relationship)
   could be used to adjust it.
3. **Counting women at the centres.** The CJM data can't link age and relationship (see above).
   Options: estimate it, use partner incidents of all ages, or ask the centres for the combined table.
4. **Survey timing.** Keep ENDIREH 2021, or update when ENDIREH 2026 is published.
5. **Age.** Use 15+ as the main group and 18+ as a check (the police can only give 18+).

## 8. Known limitations

- Each source counts something different: cases (police), incidents (centres), visits (health), women (survey).
- The health register counts visits, not people, and misses IMSS, ISSSTE and private care.
- The police changed how they record crimes in January 2026, so 2025 and 2026 can't be joined directly.
- Some state prosecutors report more completely than others.
- The survey is from 2021; the institutional data is from 2024.
- Official crime categories don't match the definition of partner violence exactly.

---

## 9. Next steps

**Now**
- [ ] Review the choices in `docs/decisions.md` (27 Nov entry) and save the work to GitHub
- [ ] Decide on the police data and the partner adjustment (section 7, points 1–2)
- [ ] Check one CJM centre whose state key is Jalisco (14) but whose state name is "MÉXICO";
      it makes the CJM state file show 33 rows instead of 32

**Pipeline**
- [ ] Step 3: convert police cases to people, keeping the original counts next to the converted ones
- [ ] Step 4: line up all sources by state, year and age group
- [ ] Step 5: compute the recognition gap

**Data still to get**
- [ ] Health register 2025
- [ ] Police 911 calls (*Informe de violencia contra las mujeres*), saved by hand
- [ ] New police data from 2026 (RNID)
- [ ] CJM results report (`cjm2025_RR.pdf`), listed in the manifest but missing from its folder

**Side tasks**
- [ ] Literature search and screening sheet, shared with Merike
- [ ] Directory of women's centres, request template and request tracker
- [ ] Send transparency requests; contact CONAVIM, EQUIS and CNEGSR
- [ ] Map shelters and other centres

---

## 10. Glossary

| Term | Meaning |
|---|---|
| IPV | Intimate partner violence: violence by a current or former partner |
| *Carpeta de investigación* | An investigation file opened by a state prosecutor; one file can involve several victims |
| *Violencia familiar* | Family violence: a crime category covering partners and other relatives |
| *Ministerio Público* / *fiscalía* | The public prosecutor's office, where criminal complaints are filed |
| CJM | Centro de Justicia para las Mujeres: one-stop centres for women facing violence |
| SESNSP | The federal body that publishes crime statistics from state prosecutors |
| RNID | The new police recording system from January 2026, which records victims' sex and age |
| DGIS | Dirección General de Información en Salud, which publishes the health injury register |
| CLUES | The ID code of a health unit; its first two letters give the state |
| ENDIREH | INEGI's national survey on household relationships and violence against women |
| INEGI | Mexico's national statistics institute |
| Expansion factor (weight) | How many women in Mexico each interviewed woman represents |
| Manifest | The list of every original file, with where and when it was obtained |
| Crosswalk | The list of rules that decide which records count as partner violence |
