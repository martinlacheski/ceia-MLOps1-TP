# ML-RainOps: predicción de lluvia para planificación de guardias en CEML

Proyecto MLOps para el TP Final de **Operaciones de Aprendizaje Automático I** de la Carrera de Especialización en Inteligencia Artificial de la Universidad de Buenos Aires.

El caso de uso está orientado a la **Cooperativa de Electricidad de Montecarlo Limitada (CEML)** y busca anticipar la carga operativa en Montecarlo, Misiones, para apoyar la planificación de guardias y cuadrillas, mediante la predicción de lluvia.

La propuesta combina un modelo local entrenado con histórico diario de lluvia en la localidad de Montecarlo, y el pronóstico a 5 días del Servicio Meteorológico Nacional (SMN).

El objetivo del trabajo es obtener un sistema reproducible, trazable y operable.

### **Autor:** Martín Anibal Lacheski

## Qué incluye el repositorio

- **Stack MLOps dockerizado** con FastAPI, frontend, Airflow, MLflow, MinIO, PostgreSQL y Valkey.
- **API FastAPI protegida con JWT** para consultar recomendaciones operativas.
- **Frontend React + TypeScript** para probar login, consulta protegida y visualización de resultados.
- **MLflow configurado con PostgreSQL + MinIO** para tracking de experimentos y artefactos.
- **Airflow 3 con CeleryExecutor** preparado para DAGs de ingesta SMN, entrenamiento y predicción diaria.
- **Estructura de paquete Python** en `src/ceml_rain/` para separar parsing, entrenamiento e inferencia.
- **Documentación de arquitectura, ejecución local y operación del flujo MLOps.**

## Problema

La CEML necesita planificar guardias de reclamos con anticipación. La lluvia es un factor que modifica la presión sobre reclamos, los recorridos y los tiempos de atención. Si esa decisión depende solo de revisión manual o intuición, se vuelve difícil sostener un criterio consistente.

Este proyecto busca responder una pregunta concreta:

> ¿Conviene reforzar la guardia de mañana según el histórico local de lluvia y el pronóstico del SMN?

## Solución propuesta

El sistema combina dos fuentes:

| Fuente                    | Uso                                                                  |
| ------------------------- | -------------------------------------------------------------------- |
| Histórico local de lluvia | Entrenar un modelo para estimar lluvia del día siguiente.            |
| Pronóstico SMN `pron5d`   | Obtener precipitación futura por estación meteorológica de Misiones. |

Con esas señales se genera una recomendación operativa:

```text
modelo local + pronóstico SMN -> decisión de guardia
```

Ejemplo de respuesta esperada de la API:

```json
{
  "target_date": "2026-06-17",
  "prediction": {
    "source": "local_model",
    "model_name": "ceml-rain-rain-t1-classifier",
    "model_stage": "latest_registered",
    "rain_probability": 0.35,
    "threshold": 0.30,
    "will_rain": true
  },
  "forecast": {
    "source": "SMN pron5d",
    "reference_station": "OBERA_AERO",
    "precipitation_mm": 4.2,
    "will_rain": true
  },
  "decision": {
    "recommended_guard": "reforzada",
    "risk_level": "alto",
    "reason": "El modelo local supera el umbral operativo y el pronóstico SMN informa precipitación."
  },
  "metadata": {
    "generated_at": "2026-06-16T11:30:00Z",
    "mode": "model_artifact_and_smn",
    "training_summary_path": "data/reports/rain_t1_training_summary.json"
  }
}
```

Secciones del contrato:

- `prediction`: señal del modelo local y umbral operativo usado para decidir lluvia.
- `forecast`: señal externa del SMN con estación de referencia y precipitación esperada.
- `decision`: recomendación de guardia, nivel de riesgo y motivo operativo legible.
- `metadata`: trazabilidad mínima del momento y modo de generación de la respuesta.

## Estado actual

El proyecto ya cuenta con un circuito MLOps mínimo ejecutable:

- [x] Estructura inicial del repositorio.
- [x] `docker-compose.yaml` con servicios base.
- [x] FastAPI con `/health`.
- [x] Autenticación JWT mínima.
- [x] Endpoint protegido de recomendación operativa.
- [x] Frontend mínimo para visualizar login, consulta y resultado.
- [x] PostgreSQL con bases separadas para Airflow, MLflow y aplicación.
- [x] MinIO con buckets `data` y `mlflow`.
- [x] MLflow usando PostgreSQL como backend store y MinIO como artifact store.
- [x] Airflow 3 levantando con CeleryExecutor y Valkey.
- [x] Parser real del pronóstico SMN `pron5d`.
- [x] DAG Airflow para ingesta SMN con persistencia en MinIO.
- [x] Dataset supervisado inicial de lluvia `t+1`.
- [x] Comparación de baselines iniciales para lluvia `t+1`.
- [x] Primer entrenamiento supervisado de lluvia `t+1` con tracking en MLflow.
- [x] DAG real de entrenamiento supervisado en Airflow.
- [x] Promoción de artefacto local de serving desde entrenamiento.
- [x] Endpoint protegido con recomendación real basada en artefacto local + SMN.

Queda como mejora futura opcional agregar un DAG de predicción batch diaria. Para esta entrega, la recomendación operativa ya está disponible de forma on-demand desde el endpoint protegido y el frontend.

## Estructura principal

```text
ml-rainops/
  backend/
    app/
      api/
      core/
    Dockerfile
    requirements.txt
  frontend/
    src/
    Dockerfile
    package.json
  airflow/
    dags/
    plugins/
    secrets/
  docker/
    airflow/
    mlflow/
    postgres/
  src/
    ceml_rain/
      inference/
      smn/
      training/
  docs/
  docker-compose.yaml
  .env.example
```

## Componentes clave

- `backend/app/main.py` — aplicación FastAPI principal.
- `backend/app/api/auth/` — login demo, emisión de JWT y usuario autenticado.
- `backend/app/api/predictions/` — endpoint protegido de recomendación de guardia.
- `frontend/src/App.tsx` — interfaz mínima para usar el flujo completo.
- `docker-compose.yaml` — definición del stack local.
- `docker/airflow/` — imagen extendida de Airflow con dependencias MLOps.
- `docker/mlflow/` — imagen extendida de MLflow con soporte PostgreSQL y S3.
- `docker/postgres/` — imagen de PostgreSQL con inicialización reproducible de bases `airflow_db`, `mlflow_db` y `rainops_app`.
- `airflow/secrets/` — variables y conexiones locales para Airflow.
- `src/ceml_rain/smn/` — parser del pronóstico SMN `pron5d` y serialización de precipitación diaria.
- `src/ceml_rain/training/` — generación del dataset supervisado, baselines y entrenamiento supervisado con MLflow.
- `src/ceml_rain/inference/` — lógica de serving, inferencia local y recomendación modelo + SMN.
- `docs/architecture.md` — decisiones iniciales de arquitectura.

## Entrenamiento supervisado `rain t+1`

El trabajo previo de AMQ mostró que **XGBoost** era un candidato fuerte para targets operativos de regresión (costo, reclamos y tiempo). En ML-RainOps no se copia ese resultado de forma ciega: el target cambió a una **clasificación binaria** (`y_llueve_t1`), así que el primer workflow reevalúa candidatos defendibles con split temporal y logging completo en MLflow.

Comando local o dentro del contenedor de Airflow:

```bash
PYTHONPATH=src python3 -m ceml_rain.training.train \
  --input data/processed/rain_training_base.parquet \
  --output data/reports/rain_t1_training_summary.json \
  --serving-output-dir data/models/rain_t1/current
```

El script entrena `LogisticRegression` y `RandomForest` siempre, e incorpora `XGBoost` cuando la dependencia está disponible. La selección prioriza **average precision** si existe score probabilístico; si no, usa **F1** para balancear precisión/recall sobre un target desbalanceado.

Durante `airflow-init`, el stack prepara permisos de `data/processed/` y `data/reports/` para que los DAGs puedan escribir sus salidas sobre los bind-mounts sin pasos manuales.

Resultado actual versionado para revisión rápida:

```text
data/reports/rain_t1_training_summary.json
```

Ese archivo permite ver métricas, split temporal, candidatos evaluados y modelo elegido sin depender de que MLflow conserve estado local.

Además, cada entrenamiento exitoso promueve un bundle estable de serving en:

```text
data/models/rain_t1/current/
```

Contenido esperado:

- `model.joblib` — modelo serializado para la API.
- `metadata.json` — features exactas, threshold operativo, métricas y referencia al resumen de entrenamiento.

## Ejecutar el entrenamiento desde Airflow UI

1. Abrí Airflow en http://localhost:8080.
2. Habilitá y dispará manualmente el DAG `rain_t1_training`.
3. Revisá la corrida y los artefactos en MLflow: http://localhost:5000.
4. El resumen JSON local queda en `data/reports/rain_t1_training_summary.json`.
5. El artefacto promovido para serving queda en `data/models/rain_t1/current/`.

El DAG usa por defecto `MLFLOW_TRACKING_URI=http://mlflow:5000` dentro de Docker, pero permite override por variable de entorno si necesitás apuntar a otro tracking server.

## Ejecutar la ingesta SMN desde Airflow UI

Al levantar el stack, el servicio `smn-bootstrap` ejecuta una ingesta inicial para dejar disponible:

```text
data/processed/smn_pron5d_daily.jsonl
```

Además, Airflow mantiene el DAG `smn_pron5d_ingestion` programado todos los días a las `09:00 UTC` y también permite dispararlo manualmente:

1. Abrí Airflow en http://localhost:8080.
2. Habilitá o dispará manualmente el DAG `smn_pron5d_ingestion`.
3. Verificá la salida procesada en `data/processed/smn_pron5d_daily.jsonl`.

## Probar la recomendación real

Una vez ejecutados los DAGs `smn_pron5d_ingestion` y `rain_t1_training`, la API usa:

- artefacto local promovido en `data/models/rain_t1/current/`,
- dataset supervisado `data/processed/rain_training_base.parquet`,
- pronóstico `data/processed/smn_pron5d_daily.jsonl`.

El stack también ejecuta `smn-bootstrap` al levantar Docker para dejar una primera versión del pronóstico procesado antes de usar la API.

Comandos demo:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=operador&password=rainops-dev' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://localhost:8000/api/predictions/guard-recommendation \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"target_date":"2026-05-29"}'
```

Ejemplo de corrida validada con SMN actualizado para `2026-06-19`:

```text
prediction.rain_probability = 0.6322
prediction.will_rain = true
forecast.reference_station = OBERA_AERO
forecast.precipitation_mm = 24.2
forecast.will_rain = true
```

La respuesta incluye `metadata.degradation_reasons` cuando corresponde. En la corrida validada, el endpoint informó:

```text
Prediction alignment: beyond_available_local_features
```

Esto significa que el SMN estaba actualizado, pero la última fila de features locales disponible era anterior a la fecha objetivo. Es una limitación honesta de datos históricos, no un fallback silencioso.

El histórico de lluvia AMQ/CEML se usa como fuente observada para entrenamiento y construcción de features pasadas. No se extiende con el pronóstico SMN, porque SMN `pron5d` es una fuente futura de contraste operativo, no lluvia observada. Incorporar pronóstico como si fuera observación mezclaría fuentes y contaminaría el entrenamiento. Para extender el histórico local harían falta nuevos registros observados de CEML u otra fuente observada documentada explícitamente.

La UI demo del frontend sigue disponible en http://localhost:5173.

Última corrida validada:

| Campo | Valor |
| --- | --- |
| Experimento MLflow | `rain-t1-training` |
| Modelo registrado | `ceml-rain-rain-t1-classifier` |
| Mejor modelo aprendido | `xgboost_classifier` |
| Average precision | `0.3533` |
| F1 | `0.3492` |
| Baseline de referencia | `recent_rain_any_7d`, F1 `0.4371` |

Lectura honesta para defensa:

- **XGBoost** sigue siendo el mejor modelo aprendido por **average precision** en este workflow.
- El baseline `recent_rain_any_7d` todavía tiene **mejor F1** que los modelos aprendidos actuales.
- Para la entrega final, el foco es la trazabilidad operativa end-to-end; no inflar artificialmente la performance.

El `run_id` y la versión concreta del modelo quedan en el JSON generado por cada corrida. No se fija una versión en la documentación porque, en un entorno limpio, MLflow asigna versiones nuevas desde cero.

Persistencia importante:

- Las corridas de MLflow viven en servicios locales: metadatos en PostgreSQL y artefactos en MinIO.
- Si se ejecuta `docker compose down`, los volúmenes se conservan y las corridas siguen disponibles.
- Si se ejecuta `docker compose down -v`, se eliminan los volúmenes y se pierden las corridas locales de MLflow.
- Para que otra persona vea los experimentos en una instalación nueva, debe levantar el stack y volver a ejecutar el comando de entrenamiento. El repositorio versiona el código, los datos mínimos y el resumen JSON para que esa corrida sea reproducible.

## Arquitectura actual

```text
               +------------------------+
               | Histórico lluvia local |
               +-----------+------------+
                           |
                           v
                     Airflow DAGs
                           |
         +-----------------+-----------------+
         |                                   |
         v                                   v
   Entrenamiento                       Ingesta SMN pron5d
         |                                   |
         v                                   v
       MLflow                            MinIO / S3
         |                                   |
         +-----------------+-----------------+
                           |
                           v
                    FastAPI + JWT
                           |
                           v
                  Frontend operativo
```

## Servicios del stack

| Servicio   | Rol                                | URL local por defecto      |
| ---------- | ---------------------------------- | -------------------------- |
| Frontend   | Interfaz de uso del sistema        | http://localhost:5173      |
| FastAPI    | API de predicción y recomendación  | http://localhost:8000      |
| Swagger    | Documentación interactiva de API   | http://localhost:8000/docs |
| Airflow    | Orquestación de pipelines          | http://localhost:8080      |
| MLflow     | Tracking de experimentos y modelos | http://localhost:5000      |
| MinIO      | Almacenamiento S3-compatible       | http://localhost:9001      |
| PostgreSQL | Metadatos de Airflow, MLflow y app | localhost:5432             |
| Valkey     | Broker de Celery para Airflow      | Interno del compose        |

Airflow y MLflow usan PostgreSQL como backend de metadatos. MLflow guarda artefactos en MinIO usando buckets S3-compatible.

Buckets creados al levantar el stack:

| Bucket   | Uso                                                              |
| -------- | ---------------------------------------------------------------- |
| `mlflow` | Artefactos de experimentos y modelos registrados.                |
| `data`   | Datasets, predicciones batch y salidas intermedias del pipeline. |

Los nombres se pueden cambiar desde `.env` con `MLFLOW_BUCKET_NAME` y `DATA_REPO_BUCKET_NAME`.

## Datos del trabajo y alcance de uso

El histórico base surge del trabajo previo de [Aprendizaje de Máquina](https://github.com/martinlacheski/tp-ceia-amq) sobre reclamos, lluvia y carga operativa de CEML.

Rango histórico relevado hasta ahora:

```text
2021-01-01 -> 2026-03-31
```

La fuente externa para pronóstico futuro es provista por el [Pronóstico de 5 días del Servicio Meteorológico Nacional de Argentina](https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=pron5d) y el listado de [estaciones meteorológicas](https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=estaciones).

En Misiones existen las siguientes estaciones meteorológicas:

- `POSADAS_AERO`
- `IGUAZU_AERO`
- `OBERA_AERO`
- `BERNARDO_DE_IRIGOYEN_AERO`

### Sobre los datos

Los datos históricos de CEML se usan únicamente con fines académicos y de evaluación del trabajo práctico. No forman parte de una licencia abierta del código ni deben redistribuirse sin autorización.

Por lo tanto:

- el código fuente del proyecto puede versionarse en el repositorio,
- los datos operativos/históricos deben tratarse como material restringido,
- cualquier publicación pública debe revisar con cuidado qué archivos de datos se incluyen.

## Requisitos

- Docker y Docker Compose.
- Puertos disponibles o configurables desde `.env`.
- Memoria suficiente para correr Airflow, MLflow, MinIO, Postgres, frontend y API al mismo tiempo.

## Configuración local

Crear el archivo `.env` desde el ejemplo:

```bash
cp .env.example .env
```

Si algún puerto choca con servicios locales, cambiar estos valores antes de levantar el stack:

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

## Cómo ejecutar el proyecto

Levantar el stack completo:

```bash
docker compose up --build
```

PostgreSQL se construye con una imagen local que copia el script de inicialización dentro de `/docker-entrypoint-initdb.d/`. Esto evita depender de un bind-mount para crear las bases y permite que el stack levante de forma reproducible en Docker Desktop y Linux.

Verificar servicios:

```bash
docker compose ps
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

Credenciales demo de MinIO:

```text
usuario: minio
password: minio123
```

> Estas credenciales son solo para desarrollo local. Están parametrizadas en `.env` y no deben usarse como secretos reales.

## Verificación rápida

### 1. Levantar el stack

Desde la raíz del repositorio:

```bash
cp .env.example .env
docker compose up --build
```

Si ya tenías contenedores creados y cambia alguna dependencia del backend o de Airflow, reconstruir explícitamente antes de probar:

```bash
docker compose build api airflow-scheduler airflow-worker airflow-init airflow-apiserver airflow-dag-processor airflow-triggerer
docker compose up --force-recreate
```

Durante el arranque se ejecutan inicializaciones automáticas:

- PostgreSQL crea las bases de Airflow, MLflow y aplicación desde una imagen propia.
- MinIO crea los buckets `data` y `mlflow`.
- `smn-bootstrap` descarga/procesa una primera versión del pronóstico SMN en `data/processed/smn_pron5d_daily.jsonl`.
- Airflow queda disponible para ejecutar los DAGs desde la UI.

En otra terminal, verificar servicios:

```bash
docker compose ps
```

### 2. Validar servicios principales

Con el stack levantado, validar API, MLflow y Airflow:

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

Resultado esperado:

```text
http://localhost:8000/health 200
http://localhost:5000 200
http://localhost:8080/api/v2/version 200
```

También se puede probar el flujo desde el frontend:

1. Abrir http://localhost:5173.
2. Iniciar sesión con el usuario demo.
3. Consultar una recomendación de guardia.
4. Ver el resumen operativo.
5. Usar `Ver detalle` y `Ver JSON` para auditar modelo, SMN, decisión y trazabilidad.

### 3. Ejecutar entrenamiento desde Airflow

El stack puede usar el artefacto versionado en `data/models/rain_t1/current/`, pero para reproducir el entrenamiento y generar evidencia propia:

1. Abrir Airflow: http://localhost:8080.
2. Iniciar sesión con `airflow / airflow`.
3. Buscar el DAG `rain_t1_training`.
4. Presionar `Trigger`.
5. Confirmar que `train_model` y `persist_summary` terminen en verde.

Esto actualiza:

```text
data/reports/rain_t1_training_summary.json
data/models/rain_t1/current/
```

Y registra corrida/modelo en MLflow:

```text
http://localhost:5000
```

### 4. Actualizar pronóstico SMN

El servicio `smn-bootstrap` corre una ingesta inicial al levantar Docker. Además, el DAG `smn_pron5d_ingestion` queda programado diariamente a las `09:00 UTC`.

Para forzar una actualización manual desde Airflow:

1. Abrir http://localhost:8080.
2. Buscar `smn_pron5d_ingestion`.
3. Presionar `Trigger`.
4. Confirmar salida en:

```text
data/processed/smn_pron5d_daily.jsonl
```

### 5. Probar endpoint por terminal

Ejemplo usando una fecha disponible en el pronóstico SMN procesado:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=operador&password=rainops-dev" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://localhost:8000/api/predictions/guard-recommendation \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_date":"2026-06-19"}' \
  | python3 -m json.tool
```

La respuesta debe incluir:

```text
prediction  -> señal del modelo local promovido
forecast    -> señal SMN procesada
metadata    -> trazabilidad y modo de respuesta
```

Si `metadata.mode` aparece como `degraded_fallback`, revisar `metadata.degradation_reasons`. En la entrega actual esto puede ocurrir porque el histórico observado AMQ/CEML llega hasta marzo de 2026, mientras SMN aporta pronóstico actualizado. Esa limitación está documentada y evita mezclar pronóstico con observación histórica.

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

## Próximos pasos

1. Mantener actualizado el histórico local observado para reducir el modo degradado cuando la fecha objetivo supera la última ventana de features disponible.
2. Ajustar umbral/features del modelo para intentar superar el baseline heurístico en F1 sin perder trazabilidad.
3. Completar una pasada final de documentación y capturas si la entrega exige evidencia visual.

## Comandos rápidos

```bash
cp .env.example .env
docker compose up --build
docker compose ps
```

Apagar servicios:

```bash
docker compose down
```

Apagar y eliminar volúmenes locales:

```bash
docker compose down -v
```

> Usar `down -v` con cuidado: borra bases y buckets locales. Para desarrollo inicial está bien; cuando haya experimentos y datos útiles, ya no es gratis.

## Referencias útiles

- `docs/architecture.md`
- `backend/app/api/auth/`
- `backend/app/api/predictions/`
- `frontend/src/App.tsx`
- `airflow/secrets/variables.yaml`
- `airflow/secrets/connections.yaml`
- `docker-compose.yaml`

## Licencia

Pendiente de definir para este repositorio.

Los datos históricos de CEML no forman parte de la licencia del código y mantienen el criterio de uso restringido indicado en la sección de datos.
