# Brecha de reconocimiento de la violencia de pareja en México

Este repositorio añade a México al marco comparativo de la **brecha de reconocimiento** de
Blofield, Danforth et al. La pregunta es: de todas las mujeres que viven violencia de pareja,
¿cuántas quedan registradas por las instituciones del Estado?

Para responderla se comparan dos tipos de datos:

- **Cuántas mujeres viven violencia de pareja**, según la encuesta nacional ENDIREH (INEGI).
- **Cuántos casos registran las instituciones**: policía y fiscalías (SESNSP), servicios de
  salud (DGIS) y Centros de Justicia para las Mujeres (CJM).

La población son **mujeres de 15 años y más** (y de 18 y más, porque algunas fuentes solo
separan menores de adultas). El **año principal es 2024**, el último que cubren todas las fuentes;
2025 se usa como comprobación para policía y salud.

> Información de referencia: el plan completo del proyecto está en [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md)
> y una guía detallada con conteos está en [`docs/GUIDE.md`](docs/GUIDE.md) (ambos en inglés).

---

## Etapas del proyecto

| Etapa | Qué significa | Estado |
|---|---|---|
| 1. Recopilar | Descargar los archivos originales y registrar de dónde y cuándo se obtuvieron | Hecho (faltan algunas fuentes, ver abajo) |
| 2. Seleccionar | Quedarse solo con mujeres y con las categorías relacionadas con violencia de pareja | Hecho para las cuatro fuentes |
| 3. Casos → personas | La policía cuenta carpetas (casos); convertirlas a víctimas | Pendiente |
| 4. Alinear | Poner todas las fuentes en la misma tabla: estado × año × grupo de edad | Prototipo listo para Ciudad de México ([`data/processed/`](data/processed/)) |
| 5. Comparar | Comparar los registros institucionales con la encuesta para medir la brecha | Pendiente |

---

## Datos recopilados y datos que faltan

Resumen por fuente. Todos los archivos recopilados están listados, con su dirección web y fecha
de descarga, en [`data/raw/manifest.csv`](data/raw/manifest.csv).

| Fuente | Recopilado | Falta |
|---|---|---|
| Policía y fiscalías (SESNSP) | Carpetas y víctimas por estado, 2015–2025 | Llamadas al 911 por violencia de pareja; datos 2026 (nueva metodología); respuestas de fiscalías |
| Centros de Justicia para las Mujeres (CJM) | Base de datos INEGI 2025 (datos de 2023 y 2024, 76 centros) | Reporte de resultados (archivo perdido); datos de CONAVIM y EQUIS; refugios y otros centros |
| Salud (DGIS) | Registro de lesiones y violencia 2024 y su instructivo | Registro 2025; conteos del CNEGSR |
| Encuesta (ENDIREH) | Microdatos 2021, descriptor de archivos y cuestionario | ENDIREH 2026 (aún no publicada por INEGI) |

### Policía y fiscalías: SESNSP

**Recopilado** (descargado el 16 nov 2026, corte de septiembre 2026):
- Carpetas de investigación del fuero común por estado y mes, 2015–2025
  (`Estatal-Delitos-2015-2025_sep2026.zip`)
- Víctimas del fuero común por estado, mes, sexo y edad (menores / adultas), 2015–2025
  (`Estatal-Víctimas-2015-2025_sep2026.zip`)
- Diccionario de datos de la metodología 2015–2025

**Falta:**
- *Informe de violencia contra las mujeres*, que incluye las llamadas al 911 por **violencia de
  pareja**. Hay que descargarlo a mano.
- Datos de **2026 con la nueva metodología (RNID)**, la única que registra sexo y edad de las
  víctimas de violencia familiar. Hasta noviembre 2026 solo hay enero–septiembre.
- Datos a nivel municipal (opcional; los usa Hoehn-Velasco et al. 2021).
- *(Opcional)* Solicitudes de transparencia a las 32 fiscalías estatales para obtener víctimas de
  violencia familiar por sexo y edad en 2024–2025.

**Limitación importante:** antes de 2026, la violencia familiar no tiene sexo ni edad de la
víctima, e incluye violencia de otros familiares, no solo de la pareja.

### Centros de Justicia para las Mujeres: CJM

**Recopilado** (16 nov 2026):
- Base de datos del Censo de CJM, edición 2025 (`BD_CJM_2025.csv`): datos de 2023 y 2024,
  76 centros en los 32 estados. Guardada a mano desde la página de INEGI.
- Descriptor de archivos (diccionario de variables)
- Presentación ejecutiva de resultados

**Falta:**
- Reporte de resultados (`cjm2025_RR.pdf`): aparece en el manifiesto pero el archivo no está
  en su carpeta. Hay que volver a descargarlo.
- Información de **CONAVIM** y **EQUIS Justicia para las Mujeres** para completar huecos.
- Identificar **refugios y otros centros** de atención que no son CJM.
- Solicitudes de transparencia a cada CJM pidiendo mujeres atendidas por edad y por relación
  con el agresor (la base de INEGI tiene estos datos en tablas separadas).

**Revisar:** un centro tiene la clave de estado de Jalisco (14) pero el nombre de estado "MÉXICO".

### Salud: DGIS

**Recopilado** (16 nov 2026):
- Registro de atención por violencia y/o lesión 2024, microdatos (`Lesiones_2024.zip`)
- Instructivo de llenado 2024, usado para verificar todos los códigos

**Falta:**
- Registro de **2025** (para la comprobación; el archivo está disponible pero no descargado).
  No hay instructivo 2025 publicado; se usaría el de 2024.
- Conteos de registros del **CNEGSR**, que hay que pedir directamente.

**Limitación importante:** el registro cuenta **atenciones, no mujeres** (una mujer atendida dos
veces cuenta dos veces) y cubre sobre todo unidades de la Secretaría de Salud e IMSS-Bienestar,
no IMSS, ISSSTE ni servicios privados.

### Encuesta: ENDIREH

**Recopilado** (16 nov 2026):
- Microdatos ENDIREH 2021 en CSV (110,127 mujeres entrevistadas)
- Descriptor de archivos y cuestionario B

**Falta:**
- **ENDIREH 2026**: en levantamiento; INEGI aún no ha publicado resultados.

**Limitación importante:** la encuesta es de 2021 y los registros institucionales son de 2024.

### Otras tareas pendientes

- **Búsqueda de literatura** (PubMed y Semantic Scholar) con hoja de revisión, para compartir con Merike.
- **Directorio de CJM y otros centros**, plantilla de solicitud de información y registro de
  solicitudes enviadas por la Plataforma Nacional de Transparencia.

---

## Dónde verificar la información

| Archivo | Qué contiene |
|---|---|
| [`data/raw/manifest.csv`](data/raw/manifest.csv) | **Lista de todos los archivos originales**: fuente, dirección web, fecha de descarga, si se descargó a mano o automáticamente, y una huella digital (SHA-256) que demuestra que el archivo no ha cambiado |
| [`docs/coverage.csv`](docs/coverage.csv) | Qué puede y qué no puede decirnos cada fuente: sexo, edad, relación con el agresor |
| [`docs/ipv_crosswalk.csv`](docs/ipv_crosswalk.csv) | Cada regla usada para seleccionar registros, con su motivo y la página del manual oficial donde se verificó |
| [`docs/decisions.md`](docs/decisions.md) | Registro con fecha de cada decisión del análisis |
| `data/interim/` | Datos ya seleccionados, una carpeta por fuente |
| [`data/processed/`](data/processed/) | **Tabla armonizada**: todas las fuentes en una sola tabla por estado, año y grupo de edad (por ahora, Ciudad de México) |

Los archivos de datos originales se guardan solo en la computadora local; en GitHub están el manifiesto y la tabla armonizada (conteos agregados, sin microdatos).

---

## Pipeline (resumen técnico)

El código está en `src/`: `src/acquire/` descarga y registra los archivos (etapa 1) y
`src/filter/` selecciona los registros de cada fuente (etapa 2). Las fuentes y sus direcciones
web están en `config/sources.yaml`. Instalación: `pip install -r requirements.txt`.

```bash
python -m src.acquire run --year 2024      # etapa 1: descargar
python -m src.acquire status --year 2024   # qué hay y qué falta
python -m src.filter.all --year 2024       # etapa 2: seleccionar
python -m src.harmonise --years 2024 2025 --state 09   # etapa 4: tabla armonizada (CDMX)
```

Para agregar un archivo obtenido a mano (por ejemplo, una respuesta de transparencia):
`python -m src.acquire register --help`.
