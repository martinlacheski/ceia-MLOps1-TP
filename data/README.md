# Datos usados por ML-RainOps

Esta carpeta versiona los datos mínimos necesarios para que el profesor pueda revisar el avance del TP sin depender del workspace original de Aprendizaje de Máquina. Incluye datos históricos provenientes del proyecto previo de AMQ y artifacts generados por la ingesta SMN del stack MLOps.

## Archivos incluidos

| Archivo | Descripción | Uso en este TP |
|---|---|---|
| `processed/lluvia_diaria_clean.parquet` | Serie diaria limpia de lluvia en Montecarlo/CEML. | Fuente histórica principal para features y targets. |
| `intermediate/lluvia_diaria_observada.parquet` | Observaciones válidas normalizadas antes de completar calendario. | Auditoría y trazabilidad. |
| `intermediate/exclusiones_lluvia.parquet` | Filas excluidas durante limpieza, con motivo. | Auditoría de calidad. |
| `raw/rain/rainfall_manual_recovered_months.csv` | Recuperaciones manuales usadas para completar meses problemáticos del OCR. | Evidencia de corrección de fuente. |
| `reports/phase3_rainfall_audit.md` | Reporte original de auditoría de lluvia. | Explica reglas de limpieza. |
| `reports/rain_feature_notes.md` | Notas sobre variables derivadas de observaciones de lluvia. | Referencia para features futuras. |
| `processed/smn_pron5d_daily.jsonl` | Última salida local generada por el DAG de ingesta SMN. | Evidencia de ingesta externa diaria y entrada futura para recomendación. |
| `processed/rain_training_base.parquet` | Dataset supervisado inicial generado desde la lluvia histórica AMQ. | Base para baseline y entrenamiento del modelo `t+1`. |
| `reports/rain_training_base_summary.json` | Resumen auditable del dataset supervisado. | Control rápido de filas, columnas, ventana temporal y distribución del target. |
| `reports/rain_baseline_metrics.json` | Métricas del baseline heurístico inicial. | Primera vara comparativa antes de entrenar modelos ML. |

## Cómo se obtuvieron en AMQ

Los datos provienen del repositorio del TP previo de Aprendizaje de Máquina:

[https://github.com/martinlacheski/tp-ceia-amq](https://github.com/martinlacheski/tp-ceia-amq)

En ese trabajo se procesaron registros pluviométricos diarios de CEML. La limpieza principal quedó implementada en:

```text
helpers/rainfall_cleaning.py
notebooks/2_lluvia_depuration.ipynb
```

El flujo aplicado fue:

1. Leer el CSV base extraído desde registros de lluvia:

   ```text
   data/raw/rain/dataset_lluvias_diario_con_obs.csv
   ```

2. Incorporar recuperaciones manuales para meses con problemas de OCR:

   ```text
   data/raw/rain/rainfall_manual_recovered_months.csv
   ```

3. Normalizar mes, año, día, lluvia y observaciones.
4. Construir la fecha final usando `año_extraido`, `mes_extraido` y `dia`.
5. Excluir filas con:
   - mes inválido,
   - fecha imposible,
   - lluvia no numérica,
   - lluvia negativa,
   - fecha fuera de la ventana de modelado.
6. Agrupar observaciones válidas por fecha.
7. Completar la serie contra calendario diario.
8. Persistir artifacts limpios y reportes de auditoría.

## Ventana temporal

La ventana retenida para modelado es:

```text
2021-01-01 -> 2026-03-31
```

Según la auditoría original:

- Filas crudas analizadas: `2012`.
- Filas excluidas: `96`.
- Días observados dentro del rango: `1916`.
- Días calendario persistidos: `1916`.
- Días sin observación (`missing_source`): `0`.
- Días con duplicados colapsados: `0`.

## Regla de limpieza resumida

El dataset `lluvia_diaria_clean.parquet` no inventa lluvia. Si existieran huecos de fuente, se marcarían como `missing_source` en `lluvia_status`. Para la ventana retenida no quedaron días faltantes.

Las columnas esperadas para la primera etapa son:

| Columna | Significado |
|---|---|
| `fecha` | Fecha diaria normalizada. |
| `lluvia_mm` | Milímetros de lluvia del día. |
| `observacion_codigo` | Código textual recuperado de la fuente, si corresponde. |
| `source_row_count` | Cantidad de filas fuente que alimentaron ese día. |
| `source_file_count` | Cantidad de archivos fuente asociados al día. |
| `lluvia_status` | Estado de observación/limpieza del día. |

## Uso en ML-RainOps

Para la primera entrega, estos datos permiten demostrar un avance real del modelo desarrollado en AMQ:

1. Cargar `processed/lluvia_diaria_clean.parquet`.
2. Crear variable `llovio = lluvia_mm > 0`.
3. Crear features temporales:
   - lags de lluvia,
   - ventanas móviles,
   - mes,
   - día del año,
   - día de semana.
4. Crear target:

   ```text
   y_llueve_t+1 = lluvia_mm del día siguiente > 0
   ```

5. Entrenar baseline/modelo inicial y registrar experimento en MLflow.

El dataset supervisado inicial se genera con:

```bash
PYTHONPATH=src python3 -m ceml_rain.training \
  --input data/processed/lluvia_diaria_clean.parquet \
  --output data/processed/rain_training_base.parquet \
  --summary data/reports/rain_training_base_summary.json
```

La salida actual contiene:

- filas: `1885`,
- ventana: `2021-01-31 -> 2026-03-30`,
- target positivo `y_llueve_t1`: `554` filas,
- tasa de lluvia del target: `0.2939`.

Como el TP AMQ original usaba la lluvia como una feature dentro de un baseline operativo más amplio, en ML-RainOps se implementa una comparación específica para la dimensión lluvia `t+1`.

Los baselines se ejecutan con:

```bash
PYTHONPATH=src python3 -m ceml_rain.training.baseline \
  --input data/processed/rain_training_base.parquet \
  --output data/reports/rain_baseline_metrics.json
```

Las reglas comparadas son:

- `recent_rain_any_7d`: predice lluvia si hubo al menos un día lluvioso en los últimos 7 días.
- `recent_rain_mm_7d`: predice lluvia si la lluvia acumulada de los últimos 7 días es `>= 10 mm`.
- `monthly_rate_or_recent_mm_7d`: predice lluvia si la tasa histórica mensual past-only es `>= 0.35` o si la lluvia acumulada de los últimos 7 días es `>= 10 mm`.

Métricas actuales:

| Baseline | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| `recent_rain_any_7d` | `0.3565` | `0.2942` | `0.8502` | `0.4371` |
| `recent_rain_mm_7d` | `0.4297` | `0.2944` | `0.6733` | `0.4097` |
| `monthly_rate_or_recent_mm_7d` | `0.4249` | `0.2995` | `0.7148` | `0.4222` |

La mejor regla por F1 es `recent_rain_any_7d`, aunque sobrepredice lluvia. Las otras reglas son más conservadoras y sirven para mostrar la tensión entre recall y falsos positivos. Este benchmark es una vara inicial para modelos posteriores, no una solución final.

## Relación con SMN

El histórico CEML representa la señal local observada. El pronóstico SMN `pron5d`, procesado desde `src/ceml_rain/smn/`, representa la señal externa futura.

La ingesta SMN puede ejecutarse desde consola:

```bash
PYTHONPATH=src python3 -m ceml_rain.smn --output data/processed/smn_pron5d_daily.jsonl
```

También queda orquestada por el DAG de Airflow:

```text
smn_pron5d_ingestion
```

Ese DAG guarda el JSONL en `data/processed/smn_pron5d_daily.jsonl` y lo sube al bucket MinIO `data` bajo la clave:

```text
smn/pron5d/processed/forecast_daily_precipitation_YYYY-MM-DD.jsonl
```

La recomendación operativa final combinará ambas fuentes:

```text
histórico CEML -> modelo local t+1
pronóstico SMN -> señal externa futura
modelo local + SMN -> recomendación de guardia
```

## Nota sobre alcance

Estos datos se incluyen para que la entrega sea reproducible y revisable. Mantienen origen académico dentro del TP de CEIA y deben usarse en ese contexto.
