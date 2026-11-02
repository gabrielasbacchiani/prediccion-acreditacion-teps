# Predicción temprana de acreditación – TEPS Tierra del Fuego

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

**Autora:** Gabriela Soledad Bacchiani · Aprendizaje Automático · Tecnicatura en Ciencias de Datos e Inteligencia Artificial

## El proyecto

El **Programa de Terminalidad de Educación Profesional Secundaria (TEPS)** permite que adultos que trabajan en el grupo Newsan terminen la secundaria con formación en electrónica. Una parte importante de los estudiantes no completa el nivel, y hoy el seguimiento se hace a mano en planillas de Excel separadas, por lo que muchas veces la situación se detecta cuando ya es tarde para intervenir.

**Objetivo:** desarrollar un modelo de **clasificación binaria** que, con la información disponible al **1° cierre de notas parcial** (asistencia, entrega de TPs y 1° nota de cada materia, más datos personales y laborales), anticipe qué estudiantes acreditarán el nivel, para orientar intervenciones tempranas.

## Estructura

| Qué | Dónde |
|---|---|
| Descripción del dataset, origen y diccionario de datos | [`docs/dataset.md`](docs/dataset.md) |
| Construcción del dataset a partir de las planillas originales | [`teps/dataset.py`](teps/dataset.py) |
| Carga, análisis exploratorio y preprocesamiento | [`notebooks/01-gsb-eda-preprocesamiento.ipynb`](notebooks/01-gsb-eda-preprocesamiento.ipynb) |
| Gráficos generados | [`reports/figures/`](reports/figures) |
| Dataset publicado (sintético) | [`data/processed/dataset_sintetico.csv`](data/processed/dataset_sintetico.csv) |

## Sobre los datos

Los datos son registros reales del programa (2025-2026) e incluyen información personal, por lo que **no se publican**. El repositorio incluye un **dataset sintético** con la misma estructura, en el que ninguna fila corresponde a una persona real. Ver [`docs/dataset.md`](docs/dataset.md#7-privacidad).

## Cómo reproducirlo

```bash
pip install -r requirements.txt
# 1. Construir el dataset (requiere las planillas originales)
python teps/dataset.py "<carpeta con las planillas>" data
# 2. Abrir la notebook
jupyter lab notebooks/01-gsb-eda-preprocesamiento.ipynb
```

Sin las planillas originales, la notebook funciona con el dataset sintético.

## Estructura del proyecto

```
├── README.md          <- Este archivo
├── data
│   ├── raw            <- Planillas originales (no se suben)
│   ├── interim        <- Datos intermedios con DNI (no se suben)
│   └── processed      <- Dataset final; solo se sube el sintético
├── docs               <- Documentación del dataset
├── models             <- Modelos entrenados (Entrega 3)
├── notebooks          <- Notebooks de Jupyter
├── references         <- Material de referencia
├── reports/figures    <- Gráficos generados
├── requirements.txt   <- Dependencias
└── teps               <- Código fuente del proyecto
    └── dataset.py     <- Script que construye el dataset
```
