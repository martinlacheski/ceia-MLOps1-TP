# ML-RainOps

## Predicción de lluvia para planificación de guardias en la Cooperativa de Electricidad de Montecarlo Limitada (CEML)

Este proyecto implementa un flujo MLOps para anticipar lluvia en **Montecarlo, Misiones**, usando histórico diario local y contrastándolo con el pronóstico numérico del Servicio Meteorológico Nacional. La idea es construir un sistema reproducible, trazable y usable para optimizar el trabajo operativo de las guardias de reclamo de la CEML.

## Problema

La CEML necesita planificar guardias operativas con anticipación. La lluvia afecta la presión sobre reclamos, recorridos y tiempos de atención, pero hoy esa decisión puede depender demasiado de revisión manual o intuición.

Este proyecto busca responder una pregunta concreta:

> ¿Conviene reforzar la guardia de mañana según el histórico local de lluvia y el pronóstico del SMN?

## Solución propuesta

El sistema combina dos fuentes:

| Fuente | Uso |
|---|---|
| Histórico local de lluvia | Entrenar un modelo para estimar lluvia del día siguiente. |
| Pronóstico SMN `pron5d` | Obtener precipitación futura por estación meteorológica de Misiones. |

Con esas señales se genera una recomendación operativa simple:

```text
modelo local + pronóstico SMN -> decisión de guardia
```

Ejemplo de salida esperada:

```json
{
  "predicted_date": "2026-05-27",
  "local_model": {
    "rain_probability": 0.72,
    "will_rain": true
  },
  "smn": {
    "reference_station": "OBERA_AERO",
    "daily_precipitation_mm": 4.2,
    "will_rain": true
  },
  "recommended_guard": "reforzada"
}
```

## Alcance

Para desarrollar el proyecto se proponen los siguientes pasos:

### Primera etapa

- [ ] Estructura del repositorio.
- [ ] `docker-compose` con servicios base.
- [ ] API FastAPI con `/health`.
- [ ] README operativo.
- [ ] Parser inicial del pronóstico SMN.

### Segunda etapa

- [ ] Dataset de lluvia CEML listo para entrenamiento.
- [ ] Features temporales: lags, rolling windows, calendario y estacionalidad.
- [ ] Modelo local `t+1` para lluvia.
- [ ] Tracking con MLflow.
- [ ] DAG de Airflow para entrenamiento y predicción diaria.

### Tercera etapa

- [ ] Endpoint protegido para consultar recomendación de guardia.
- [ ] Autenticación JWT mínima.
- [ ] Comparación entre modelo local y SMN.
- [ ] Documentación final de arquitectura y operación.

## Datos utilizados

El histórico base surge del trabajo previo de  [Aprendizaje de Máquina](https://github.com/martinlacheski/tp-ceia-amq) sobre reclamos, lluvia y carga operativa de CEML.


Rango histórico relevado hasta ahora:

```text
2021-01-01 -> 2026-03-31
```

La fuente externa para pronóstico futuro es provista por el [Pronóstico de 5 días del Servicio Meterológico Nacional de Argentina](https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=pron5d) y el listado de las [estaciones meteorológicas](https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=estaciones), de las cuales se saca la información para obtener las estaciones de la provincia de **Misiones**.

Para Misiones se consideran inicialmente:

- `POSADAS_AERO`
- `IGUAZU_AERO`
- `OBERA_AERO`
- `BERNARDO_DE_IRIGOYEN_AERO`

## Arquitectura objetivo

```text
               +----------------------+
               | Histórico lluvia local |
               +----------+-----------+
                          |
                          v
                    Airflow DAG
                          |
        +-----------------+-----------------+
        |                                   |
        v                                   v
  Entrenamiento                       Ingesta SMN pron5d
        |                                   |
        v                                   v
      MLflow                             MinIO/S3
        |                                   |
        +-----------------+-----------------+
                          |
                          v
                         FastAPI
                          |
                          v
              Recomendación de guardia
```

## Servicios previstos

| Servicio | Rol |
|---|---|
| FastAPI | API de predicción y recomendación operativa. |
| Airflow | Orquestación de entrenamiento, ingesta SMN y predicción diaria. |
| MLflow | Tracking de experimentos, métricas y artefactos. |
| MinIO | Almacenamiento tipo S3 para datasets, modelos y salidas. |
| PostgreSQL | Base relacional para metadatos de Airflow, MLflow y futuras tablas de aplicación. |
| Valkey | Broker de Celery para workers de Airflow. |

Airflow y MLflow usan PostgreSQL como backend de metadatos. MLflow guarda artefactos en MinIO usando buckets S3-compatible. Así evitamos el atajo de SQLite desde el principio y dejamos una arquitectura más parecida al TP de referencia.

Buckets creados al levantar el stack:

| Bucket | Uso |
|---|---|
| `mlflow` | Artefactos de experimentos y modelos registrados. |
| `data` | Datasets, predicciones batch y salidas intermedias del pipeline. |

Los nombres se pueden cambiar desde `.env` con `MLFLOW_BUCKET_NAME` y `DATA_REPO_BUCKET_NAME`.

## Ejecución local

Copiar variables de entorno de ejemplo:

```bash
cp .env.example .env
```

Levantar el stack base:

```bash
docker compose up --build
```

Servicios disponibles:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Airflow | http://localhost:8080 |
| MLflow | http://localhost:5000 |
| MinIO | http://localhost:9001 |

Si algún puerto te choca con servicios locales, cambiá los valores en `.env` antes de levantar el stack. Los principales son:

```text
API_PORT=8000
FRONTEND_PORT=5173
POSTGRES_PORT=5432
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MLFLOW_PORT=5000
AIRFLOW_PORT=8080
```

Para generar secretos locales seguros:

```bash
openssl rand -hex 32      # JWT_SECRET_KEY
openssl rand -base64 32   # AIRFLOW_API_JWT_SECRET
```

Credenciales demo de la API:

```text
usuario: operador
password: rainops-dev
```

Credenciales demo de Airflow:

```text
usuario: airflow
password: airflow
```

> Estas credenciales son solo para desarrollo. Más adelante se reemplazan por usuarios persistidos en base de datos.
> También son configurables desde `.env`; no uses estos valores fuera del entorno local del TP.

## Flujo operativo esperado

### Reentrenamiento mensual

```text
nuevo registro mensual CEML
-> limpieza y normalización
-> actualización del dataset histórico
-> reentrenamiento
-> registro de experimento y modelo en MLflow
```

### Predicción diaria

```text
descargar pron5d del SMN
-> parsear estaciones de Misiones
-> agregar precipitación por día
-> consultar modelo local
-> combinar señales
-> guardar recomendación de guardia
```
