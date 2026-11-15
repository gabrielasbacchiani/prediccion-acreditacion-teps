# Predicción temprana de acreditación – TEPS Tierra del Fuego

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

**Autora:** Gabriela Soledad Bacchiani · Aprendizaje Automático · Tecnicatura en Ciencias de Datos e Inteligencia Artificial

## Video de presentación

▶️ [Ver el video en YouTube](https://youtu.be/3c3iGL-DUQo)

## El proyecto

El **Programa de Terminalidad de Educación Profesional Secundaria (TEPS)** permite que adultos que trabajan en el grupo Newsan terminen la secundaria con formación en electrónica. Una parte importante de los estudiantes no completa el nivel, y hoy el seguimiento se hace a mano en planillas de Excel separadas, por lo que muchas veces la situación se detecta cuando ya es tarde para intervenir.

**Objetivo:** desarrollar un modelo de **clasificación binaria** que, con la información disponible al **1° cierre de notas parcial** (asistencia, entrega de TPs y 1° nota de cada materia, más datos personales y laborales), anticipe qué estudiantes no acreditarán el nivel, para orientar intervenciones tempranas.

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Objetivos y alcance del proyecto | [`docs/objetivos_y_alcance.md`](docs/objetivos_y_alcance.md) |
| Descripción del dataset, origen y diccionario de datos | [`docs/dataset.md`](docs/dataset.md) |
| Construcción del dataset a partir de las planillas originales | [`teps/dataset.py`](teps/dataset.py) |
| Carga, análisis exploratorio y preprocesamiento | [`notebooks/01-gsb-eda-preprocesamiento.ipynb`](notebooks/01-gsb-eda-preprocesamiento.ipynb) |
| Modelado, evaluación e interpretación | [`notebooks/02-gsb-modelado.ipynb`](notebooks/02-gsb-modelado.ipynb) |
| Gráficos generados | [`reports/figures/`](reports/figures) |
| Dataset publicado (sintético) | [`data/processed/dataset_sintetico.csv`](data/processed/dataset_sintetico.csv) |

## Sobre los datos

Los datos son registros reales del programa (2025-2026) e incluyen información personal, por lo que **no se publican**. El repositorio incluye un **dataset sintético** con la misma estructura, en el que ninguna fila corresponde a una persona real. El sintético sirve solo para comprobar que el código funciona: no conserva las trayectorias de los estudiantes ni las relaciones entre variables, así que las conclusiones se basan únicamente en los datos reales. Ver [`docs/dataset.md`](docs/dataset.md#7-privacidad-y-dataset-sintético).

## Cómo ejecutarlo

**Para ver los resultados no hace falta ejecutar nada:** las notebooks se muestran en GitHub con las tablas, gráficos y métricas obtenidos con los datos reales.

**Para ejecutarlas en otra computadora:**

1. Descargá el repositorio completo (botón **Code → Download ZIP**) y descomprimilo.
2. Instalá las dependencias: `pip install -r requirements.txt`
3. Abrí Jupyter y ejecutá las notebooks en orden: primero `01-gsb-eda-preprocesamiento.ipynb` y después `02-gsb-modelado.ipynb`. Cada notebook busca sola la carpeta del proyecto, desde donde se abra.

**Qué datos usa.** Si existe `data/processed/dataset_real.csv` (solo en la computadora de la coordinación), las notebooks usan los datos reales. Si no, usan `data/processed/dataset_sintetico.csv` y muestran un aviso. Con el sintético el código corre de punta a punta, pero **los resultados son distintos y no sirven para sacar conclusiones**: el sintético no conserva las trayectorias de los estudiantes ni las relaciones entre variables. Los resultados publicados corresponden a los datos reales.

**Reconstruir el dataset real** (requiere las planillas originales, que no se publican):

```bash
python teps/dataset.py "<carpeta con las planillas>" data
```

## Estructura del proyecto

```
├── README.md          <- Este archivo
├── data
│   ├── raw            <- Planillas originales (no se suben)
│   ├── interim        <- Datos intermedios con DNI (no se suben)
│   └── processed      <- Dataset final; solo se sube el sintético
├── docs               <- Documentación del dataset
├── models             <- Vacía: los modelos se entrenan dentro de la notebook 02
├── notebooks          <- Notebooks de Jupyter
├── references         <- Material de referencia
├── reports/figures    <- Gráficos generados
├── requirements.txt   <- Dependencias
└── teps               <- Código fuente del proyecto
    └── dataset.py     <- Script que construye el dataset
```
