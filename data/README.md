# Datos usados por ML-RainOps

Esta carpeta versiona los datos mínimos necesarios para que el profesor pueda revisar el avance del TP sin depender del workspace original de Aprendizaje de Máquina. Los archivos provienen del proyecto previo de AMQ sobre lluvia y operación de CEML, y se usan acá como base histórica para entrenar el modelo de lluvia `t+1`.

## Archivos incluidos

| Archivo | Descripción | Uso en este TP |
|---|---|---|
| `processed/lluvia_diaria_clean.parquet` | Serie diaria limpia de lluvia en Montecarlo/CEML. | Fuente histórica principal para features y targets. |
| `intermediate/lluvia_diaria_observada.parquet` | Observaciones válidas normalizadas antes de completar calendario. | Auditoría y trazabilidad. |
| `intermediate/exclusiones_lluvia.parquet` | Filas excluidas durante limpieza, con motivo. | Auditoría de calidad. |
| `raw/rain/rainfall_manual_recovered_months.csv` | Recuperaciones manuales usadas para completar meses problemáticos del OCR. | Evidencia de corrección de fuente. |
| `reports/phase3_rainfall_audit.md` | Reporte original de auditoría de lluvia. | Explica reglas de limpieza. |
| `reports/rain_feature_notes.md` | Notas sobre variables derivadas de observaciones de lluvia. | Referencia para features futuras. |

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

## Relación con SMN

El histórico CEML representa la señal local observada. El pronóstico SMN `pron5d`, procesado desde `src/ceml_rain/smn/`, representa la señal externa futura. La recomendación operativa final combinará ambas fuentes:

```text
histórico CEML -> modelo local t+1
pronóstico SMN -> señal externa futura
modelo local + SMN -> recomendación de guardia
```

## Nota sobre alcance

Estos datos se incluyen para que la entrega sea reproducible y revisable. Mantienen origen académico dentro del TP de CEIA y deben usarse en ese contexto.
