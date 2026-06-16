# Arquitectura actual

Este documento acompaña al README y registra las decisiones técnicas del proyecto.

## Decisiones actuales

| Área | Decisión |
|---|---|
| API | FastAPI con autenticación JWT desde la primera iteración. |
| Frontend | React + TypeScript con flujo de login, consulta, resumen operativo, detalle textual y JSON técnico. |
| Orquestación | Airflow ejecuta ingesta SMN y entrenamiento supervisado; la ingesta SMN queda programada diariamente. |
| Tracking | MLflow registra experimentos, métricas, artefactos y modelos; FastAPI sirve un artefacto local promovido. |
| Storage | MinIO simula S3 para datasets, modelos y salidas intermedias. |
| Serving | FastAPI combina artefacto local del modelo, features históricas y pronóstico SMN procesado. |

## Principio guía

El proyecto separa responsabilidades: Airflow ingesta y entrena, MLflow registra evidencia del ciclo de vida del modelo, MinIO/PostgreSQL sostienen metadatos y artefactos, y FastAPI sirve recomendaciones operativas desde un artefacto local promovido. SMN `pron5d` se usa como señal futura externa; el histórico AMQ/CEML observado alimenta entrenamiento y features pasadas.
