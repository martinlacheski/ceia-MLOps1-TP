# Entrega parcial — ML-RainOps

Esta entrega parcial muestra el avance actual del TP MLOps1: un entorno productivo contenedorizado para predicción de lluvia `t+1` y recomendación operativa de guardias CEML. El foco de esta etapa no es presentar el modelo final, sino demostrar que el proyecto ya tiene datos, servicios, orquestación, ingesta externa y una primera vara de modelado reproducible.

## Autor

- Martín Anibal Lacheski

## Objetivo del proyecto

Implementar en un entorno MLOps el trabajo iniciado en Aprendizaje de Máquina para el caso CEML. En esta versión se acota el problema a una dimensión concreta y operable:

```text
predecir lluvia del día siguiente
-> contrastar con pronóstico SMN
-> generar recomendación de guardia
```

El alcance elegido evita mezclar de entrada costos, zonas y ruteo. Primero se busca cerrar un circuito MLOps trazable; luego se puede ampliar el modelo operativo.

## Alineación con la materia

El criterio de aprobación para nivel contenedores pide implementar el modelo del trabajo de Aprendizaje de Máquina en un ambiente productivo usando servicios como Airflow, MLflow, PostgreSQL, MinIO, FastAPI y Docker.

Esta parcial ya incluye:

| Requisito / tema | Estado actual                                                                 |
| ---------------- | ----------------------------------------------------------------------------- |
| Docker Compose   | Stack completo levantable localmente.                                         |
| FastAPI          | API con JWT y endpoint protegido de recomendación.                            |
| Frontend         | Interfaz web agregada para probar login, endpoint protegido y recomendación.  |
| Airflow          | DAG real de ingesta SMN ejecutado con éxito.                                  |
| MLflow           | Servicio disponible con backend PostgreSQL y artifacts en MinIO.              |
| MinIO/S3         | Buckets `data` y `mlflow`; artifact SMN subido al bucket `data`.              |
| Datos AMQ        | Histórico de lluvia versionado en `data/`.                                    |
| Modelado inicial | Dataset supervisado `t+1` y comparación de baselines.                         |
| Documentación    | README principal, documentación de datos y este documento de entrega parcial. |

El frontend no reemplaza a FastAPI ni forma parte del stack base obligatorio de la materia. Se agrega como mejora de usabilidad para que la revisión pueda probar visualmente el flujo disponible: autenticación demo, consumo del endpoint protegido y visualización de la respuesta operativa.

## Qué está implementado

### Stack MLOps

Servicios actuales:

- FastAPI: `http://localhost:8000`
- Frontend de prueba: `http://localhost:5173`
- Airflow: `http://localhost:8080`
- MLflow: `http://localhost:5000`
- MinIO: `http://localhost:9001`
- PostgreSQL
- Valkey

El frontend permite probar el flujo completo disponible en esta etapa: login demo, llamada al endpoint protegido y visualización de la recomendación provisoria.

### Ingesta SMN `pron5d`

Se implementó un parser real del pronóstico de 5 días del Servicio Meteorológico Nacional.

El comando local es:

```bash
PYTHONPATH=src python3 -m ceml_rain.smn --output data/processed/smn_pron5d_daily.jsonl
```

También está orquestado por Airflow mediante el DAG:

```text
smn_pron5d_ingestion
```

Ese DAG hace:

```text
descargar pron5d
-> parsear estaciones de Misiones
-> agregar precipitación diaria
-> guardar data/processed/smn_pron5d_daily.jsonl
-> subir a MinIO bucket data
```

Artifact esperado en MinIO:

```text
data/smn/pron5d/processed/forecast_daily_precipitation_YYYY-MM-DD.jsonl
```

### Datos históricos AMQ

Se incorporaron al repositorio los artifacts mínimos del trabajo previo de AMQ:

- `data/processed/lluvia_diaria_clean.parquet`
- `data/intermediate/lluvia_diaria_observada.parquet`
- `data/intermediate/exclusiones_lluvia.parquet`
- `data/raw/rain/rainfall_manual_recovered_months.csv`
- `data/reports/phase3_rainfall_audit.md`
- `data/reports/rain_feature_notes.md`

El origen y proceso de limpieza están documentados en:

```text
data/README.md
```

El repositorio de referencia del TP previo es:

```text
https://github.com/martinlacheski/tp-ceia-amq
```

### Dataset supervisado inicial

Se generó un dataset para lluvia `t+1`:

```text
data/processed/rain_training_base.parquet
data/reports/rain_training_base_summary.json
```

Comando:

```bash
PYTHONPATH=src python3 -m ceml_rain.training \
  --input data/processed/lluvia_diaria_clean.parquet \
  --output data/processed/rain_training_base.parquet \
  --summary data/reports/rain_training_base_summary.json
```

Resumen actual:

| Métrica                 |                      Valor |
| ----------------------- | -------------------------: |
| Filas                   |                     `1885` |
| Ventana                 | `2021-01-31 -> 2026-03-30` |
| Positivos `y_llueve_t1` |                      `554` |
| Tasa positiva           |                   `0.2939` |

Features incluidas:

- lags de lluvia 1, 2, 3, 7, 14 y 30 días,
- acumulados y medias móviles 7, 14 y 30 días,
- días con lluvia en ventanas móviles,
- mes, día del año y día de semana,
- targets `y_llueve_t1` y `y_lluvia_mm_t1`.

### Baselines iniciales

El TP AMQ original usaba la lluvia como feature dentro de un baseline operativo más amplio. En ML-RainOps se implementó una comparación específica para la dimensión lluvia `t+1`.

Comando:

```bash
PYTHONPATH=src python3 -m ceml_rain.training.baseline \
  --input data/processed/rain_training_base.parquet \
  --output data/reports/rain_baseline_metrics.json
```

Baselines comparados:

| Baseline                       | Regla                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `recent_rain_any_7d`           | Predice lluvia si hubo al menos un día lluvioso en los últimos 7 días.                                  |
| `recent_rain_mm_7d`            | Predice lluvia si el acumulado de los últimos 7 días es `>= 10 mm`.                                     |
| `monthly_rate_or_recent_mm_7d` | Predice lluvia si la tasa histórica mensual past-only es `>= 0.35` o el acumulado 7 días es `>= 10 mm`. |

Métricas actuales:

| Baseline                       | Accuracy | Precision |   Recall |       F1 |
| ------------------------------ | -------: | --------: | -------: | -------: |
| `recent_rain_any_7d`           | `0.3565` |  `0.2942` | `0.8502` | `0.4371` |
| `recent_rain_mm_7d`            | `0.4297` |  `0.2944` | `0.6733` | `0.4097` |
| `monthly_rate_or_recent_mm_7d` | `0.4249` |  `0.2995` | `0.7148` | `0.4222` |

Lectura: `recent_rain_any_7d` gana por F1 por su recall alto, pero sobrepredice lluvia. Las reglas con umbral son más conservadoras. Este benchmark deja una vara inicial para modelos posteriores.

## Cómo verificar la entrega

### 1. Levantar servicios

```bash
docker compose up -d
```

Si Airflow necesita usar el UID local:

```bash
AIRFLOW_UID=1000 docker compose up -d airflow-init airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker airflow-triggerer
```

### 2. Ver servicios activos

```bash
docker compose ps
```

### 3. Verificar API

```bash
python3 - <<'PY'
import urllib.request

for url in [
    "http://localhost:8000/health",
    "http://localhost:5000",
    "http://localhost:8080/api/v2/version",
]:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(url, response.status)
PY
```

### 4. Ejecutar ingesta SMN local

```bash
PYTHONPATH=src python3 -m ceml_rain.smn --output data/processed/smn_pron5d_daily.jsonl
```

### 5. Ejecutar DAG SMN en Airflow

```bash
docker compose exec airflow-scheduler airflow dags unpause smn_pron5d_ingestion
docker compose exec airflow-scheduler airflow dags trigger smn_pron5d_ingestion
docker compose exec airflow-scheduler airflow dags list-runs smn_pron5d_ingestion
```

### 6. Ver artifact en MinIO

```bash
docker compose exec minio mc alias set local http://localhost:9000 minio minio123
docker compose exec minio mc ls local/data/smn/pron5d/processed/
```

### 7. Regenerar dataset supervisado

```bash
docker compose exec airflow-scheduler bash -lc 'cd /opt/ml-rainops && PYTHONPATH=src python -m ceml_rain.training --input data/processed/lluvia_diaria_clean.parquet --output data/processed/rain_training_base.parquet --summary data/reports/rain_training_base_summary.json'
```

### 8. Regenerar baselines

```bash
docker compose exec airflow-scheduler bash -lc 'cd /opt/ml-rainops && PYTHONPATH=src python -m ceml_rain.training.baseline --input data/processed/rain_training_base.parquet --output data/reports/rain_baseline_metrics.json'
```

## Limitaciones actuales

- El endpoint de recomendación todavía usa una implementación provisoria.
- MLflow está disponible, pero aún no se registró un experimento/modelo real.
- Airflow orquesta la ingesta SMN, pero todavía no orquesta entrenamiento.
- Los baselines no son el modelo final; son una vara inicial.
- La recomendación final todavía no combina modelo local + SMN en producción.

## Plan para la entrega final

1. Entrenar modelos reales sobre `rain_training_base.parquet`.
2. Registrar experimentos, métricas y artifacts en MLflow.
3. Crear DAG de entrenamiento.
4. Crear DAG de recomendación diaria combinando modelo local y SMN.
5. Reemplazar el endpoint provisorio por inferencia real.
6. Actualizar frontend para mostrar recomendación real.
7. Completar README final con instrucciones de operación.
