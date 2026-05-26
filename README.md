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
  "fecha_predicha": "2026-05-27",
  "modelo_local": {
    "probabilidad_lluvia": 0.72,
    "llueve_predicho": true
  },
  "smn": {
    "estacion_referencia": "OBERA_AERO",
    "precipitacion_mm_dia": 4.2,
    "llueve_predicho": true
  },
  "guardia_recomendada": "reforzada"
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
| PostgreSQL | Backend de metadatos para servicios del stack. |

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
