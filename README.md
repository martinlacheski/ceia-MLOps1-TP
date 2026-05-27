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
- **Documentación inicial** de arquitectura y ejecución local.

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

## Estado actual

El proyecto ya cuenta con una primera base ejecutable:

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
- [ ] Entrenamiento real del modelo local de lluvia.
- [ ] DAGs reales de entrenamiento y predicción.

El reporte de entrega parcial está disponible en [`partial-delivery.md`](./partial-delivery.md).

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
- `docker/postgres/init-multiple-databases.sh` — creación de bases `airflow_db`, `mlflow_db` y `rainops_app`.
- `airflow/secrets/` — variables y conexiones locales para Airflow.
- `src/ceml_rain/smn/` — espacio reservado para parser del SMN.
- `src/ceml_rain/training/` — espacio reservado para entrenamiento del modelo local.
- `src/ceml_rain/inference/` — espacio reservado para lógica de inferencia/recomendación.
- `docs/architecture.md` — decisiones iniciales de arquitectura.

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

En Misiones existen las siguientes estaciones metereológicas:

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
3. Consultar una recomendación de guardia de reclamos.
4. Confirmar que el endpoint protegido devuelve una respuesta JSON.

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

1. Implementar parser del archivo `pron5d` del SMN.
2. Guardar pronóstico procesado por estación y día en MinIO.
3. Incorporar histórico local de lluvia al bucket `data`.
4. Crear features temporales para lluvia `t+1`.
5. Entrenar modelo local y registrar experimento en MLflow.
6. Crear DAG de Airflow para ingesta, entrenamiento y predicción diaria.
7. Reemplazar el stub de la API por inferencia real.

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
