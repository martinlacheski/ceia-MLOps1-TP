# Arquitectura inicial

Este documento acompaña al README y registra las decisiones técnicas del proyecto.

## Decisiones actuales

| Área | Decisión |
|---|---|
| API | FastAPI con autenticación JWT desde la primera iteración. |
| Frontend | React + TypeScript mínimo para visualizar login y recomendación. |
| Orquestación | Airflow queda preparado para DAGs de entrenamiento, ingesta SMN y predicción diaria. |
| Tracking | MLflow se usará para registrar experimentos, métricas y artefactos. |
| Storage | MinIO simula S3 para datasets, modelos y salidas intermedias. |

## Principio guía

Primero cerramos el flujo end-to-end con stubs controlados. Después conectamos modelo real, parser SMN, MLflow y DAGs. Si arrancamos por el modelo antes de tener circuito, terminamos con otro notebook lindo pero poco productivo.
