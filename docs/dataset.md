# Descripción del dataset

## 1\. Descripción general

El dataset reúne la información de cursada de los estudiantes del **Programa de Terminalidad de Educación Profesional Secundaria (TEPS)**, que se dicta en las instalaciones de Newsan (Ushuaia, Tierra del Fuego) con propuesta pedagógica y docentes del Ministerio de Educación de la provincia de Tierra del Fuego - Argentina.

* **Unidad de análisis:** una fila por **estudiante y nivel cursado** (registro estudiante-nivel). Una persona que cursó dos niveles aparece en dos filas.
* **Período:** 1° cuatrimestre de 2025 a 2° cuatrimestre de 2026.
* **Momento de predicción:** todas las variables predictoras se calculan con la información registrada **hasta el 1° cierre de notas parcial** de cada cuatrimestre, una fecha institucional común a las 6 materias.
* **Variable objetivo:** `acredita` (1 = aprobó las 6 materias del nivel al cierre final del cuatrimestre, incluido el recuperatorio; 0 = no).

## 2\. Origen de los datos

Los datos provienen de los registros administrativos de la coordinadora pedagógica del programa, llevados en planillas de Excel. No es un dataset público: se construyó para este trabajo unificando las siguientes fuentes.

|Fuente|Contenido|Archivos usados|
|-|-|-|
|Planillas de asistencia|Una hoja por nivel con la asistencia de cada clase (códigos PE, PG, AE, AG, C/A, L/M, S/C, -) y la columna **SITUACIÓN** con el resultado del nivel|4 archivos (uno por cuatrimestre, 2025-2026)|
|Nómina (dentro de la planilla de asistencia)|Fecha de nacimiento, sexo, planta, turno laboral, departamento, convenio y empresa|Hoja "NOMINA ACTIVA" de cada archivo de asistencia|
|Planillas de calificaciones|Una planilla por materia, con una hoja por nivel: notas de Trabajos Prácticos (TPs), 1° y 2° nota parcial, TPI, recuperatorios y calificación definitiva|13 archivos (7 de 2025 y 6 de 2026)|
|Calendario|Fechas de inicio de clases, 1° cierre parcial y cierre final de cada cuatrimestre|Planilla de fechas armada por la coordinación|

La **Hoja de control** de la coordinadora registra qué planillas se descargaron de cada cuatrimestre y nivel. Los datos se recopilaron en noviembre de 2026.

**Alcance:** existen registros desde 2022, pero las planillas de 2022 a 2024 tienen formatos distintos y no incluyen la nómina. Por el tiempo disponible, este trabajo usa **2025 y 2026**, que comparten el formato más completo. La incorporación de los años anteriores queda como trabajo futuro.

### Calendario utilizado

|Cuatrimestre|Inicio de clases|1° cierre parcial (corte)|Cierre final|Niveles|
|-|-|-|-|-|
|1° 2025|08/05/2025|02/06/2025|11/07/2025|1 y 3|
|2° 2025|07/08/2025|19/09/2025|14/11/2025|2 y 4|
|1° 2026|23/04/2026|18/05/2026|03/07/2026|3|
|2° 2026|12/08/2026|25/09/2026|27/11/2026|4|

En los 1° cuatrimestres el corte llega antes (alrededor de la semana 4, con 2 TPs) que en los 2° (alrededor de la semana 6, con 3 TPs), porque las clases empiezan cuando la empresa autoriza el ingreso (en el 2° cuatrimestre esa traba administrativa ya está resuelta). Por eso las variables se expresan como **proporciones** y el cuatrimestre se incluye como variable.

## 3\. Proceso de construcción

El script [`teps/dataset.py`](../teps/dataset.py) realiza estos pasos:

1. Lee las hojas de cada nivel de las planillas de asistencia y traduce los códigos de cada clase anterior al corte.
2. Lee la nómina y toma, para cada estudiante, sus datos personales y laborales más recientes.
3. Lee las planillas de calificaciones, ubicando las columnas por su nombre (la cantidad de TPs varía entre niveles), y toma solo los TPs anteriores a la 1° nota parcial y la 1° nota parcial.
4. Como las planillas de notas no tienen DNI, **empareja cada nombre** con la asistencia del mismo año, cuatrimestre y nivel (comparación de palabras del nombre). Los casos que no se pueden emparejar se listan para revisión manual.
5. Agrega las notas de las 6 materias por estudiante-nivel.
6. Calcula la variable objetivo a partir de la columna SITUACIÓN.
7. Aplica las reglas de exclusión (sección 5).
8. Reemplaza el DNI por un código (`E001`, `E002`, ...) y genera un dataset sintético para publicar.

### Tratamiento de los códigos

|Código|Significado|Tratamiento|
|-|-|-|
|PE / PG|Presente en Electrónica / Formación General|Presente|
|PV|Presente virtual|Presente|
|PGtm / PGtt|Presente en el turno contrario|Presente|
|AE / AG|Ausente en Electrónica / Formación General|Ausente sin aviso|
|C/A|Ausente Con Aviso (incluye "C/A trabajando")|Ausente con aviso|
|L/M|Licencia Médica con certificado presentado|No se descuenta del % de asistencia|
|S/C|Sin clase|No se cuenta|
|- / --|Informó que no continúa|Baja|

En las calificaciones, una nota **1**, una celda vacía o un **"-"** en un TP significan **TP no entregado**. Esas notas no entran en el promedio; se cuentan como TP no entregado.

## 4\. Cantidad de instancias

||Registros|Estudiantes únicos|
|-|-|-|
|Total del dataset|153|83|
|Población del modelo|121|75|

Distribución de la variable objetivo en la población del modelo: **74 acreditan (61,2 %)** y **47 no acreditan (38,8 %)**.

|Cuatrimestre|Nivel|Registros|Acreditan|
|-|-|-|-|
|1° 2025|1|23|15|
|1° 2025|3|34|19|
|2° 2025|2|18|11|
|2° 2025|4|24|11|
|1° 2026|3|22|18|

## 5\. Reglas de exclusión

|Motivo|Registros|Justificación|
|-|-|-|
|En curso (nivel 4, 2° cuatrimestre 2026)|19|Todavía no tienen resultado. Recibirán una estimación del modelo, pero no se usan para entrenar ni evaluar.|
|No inició (ninguna asistencia hasta el corte)|12|El no inicio ocurre antes del momento de predicción; se analiza de forma descriptiva. 4 de estos estudiantes empezaron a asistir después del corte.|
|Situación no estándar|1|Estudiante reasignada de nivel 1 a nivel 3 durante el cuatrimestre por presentar documentación de equivalencias. Se excluye el registro del nivel de origen.|

Los estudiantes que figuran en las listas de un nivel pero **nunca asistieron** a él no aparecen en la planilla de asistencia de ese nivel y, por lo tanto, no forman parte del dataset (ver sección 8).

Los estudiantes **sin nota parcial** o con **TPs sin entregar** **no se excluyen**: son justamente quienes más necesitan acompañamiento.

## 6\. Diccionario de datos

|Variable|Tipo|Descripción|
|-|-|-|
|`id\\\\\\\_estudiante`|texto|Código seudonimizado del estudiante (reemplaza el DNI)|
|`anio`|entero|Año de cursada (2025, 2026)|
|`cuatri`|entero|Cuatrimestre (1 o 2)|
|`nivel`|entero|Nivel cursado (1 a 4)|
|`grupo`|categórica|Grupo horario de cursada: 12:30 o 15:30|
|`rango\\\\\\\_edad`|categórica|Edad al inicio del cuatrimestre, en rangos: 18-25, 26-35, 36-45, 46+|
|`sexo`|categórica|Sexo registrado en la nómina|
|`empresa\\\\\\\_grupo`|categórica|Newsan / Empresa vinculada del grupo (Jenizaros, GDS, Globale, Pulpo) / Familiar de trabajador / Otro|
|`sector`|categórica|Departamento agrupado: Producción, Vigilancia, Logística/abastecimiento, Otro|
|`turno\\\\\\\_laboral`|categórica|Turno de trabajo: Mañana, Tarde, Noche, Rotativo, Sin dato|
|`lugar\\\\\\\_trabajo`|categórica|Lugar de trabajo respecto del cursado (planta 4): misma planta, otra planta, rotativo, sin dato|
|`convenio\\\\\\\_uom`|binaria|1 si está bajo convenio UOM, 0 si no|
|`clases\\\\\\\_dictadas\\\\\\\_corte`|entero|Clases dictadas al estudiante hasta el corte|
|`pct\\\\\\\_asistencia`|real (0-1)|Presentes / clases dictadas hasta el corte (sin contar licencias médicas)|
|`pct\\\\\\\_asist\\\\\\\_electronica`|real (0-1)|Asistencia a Electrónica hasta el corte|
|`pct\\\\\\\_asist\\\\\\\_general`|real (0-1)|Asistencia a Formación General hasta el corte|
|`pct\\\\\\\_ausente\\\\\\\_sin\\\\\\\_aviso`|real (0-1)|Proporción de ausencias sin aviso hasta el corte|
|`pct\\\\\\\_ausente\\\\\\\_con\\\\\\\_aviso`|real (0-1)|Proporción de ausencias con aviso hasta el corte|
|`licencias\\\\\\\_medicas`|entero|Cantidad de clases con licencia médica hasta el corte|
|`presente\\\\\\\_turno\\\\\\\_contrario`|entero|Clases a las que asistió en el turno contrario hasta el corte|
|`pct\\\\\\\_tps\\\\\\\_entregados`|real (0-1)|TPs entregados / TPs previstos antes de la 1° nota, sumando las 6 materias|
|`promedio\\\\\\\_tps`|real (2-10)|Promedio de las notas de los TPs entregados antes de la 1° nota|
|`promedio\\\\\\\_1p`|real (2-10)|Promedio de la 1° nota parcial en las materias que la tienen|
|`materias\\\\\\\_1p\\\\\\\_menor6`|entero|Materias con 1° nota parcial menor a 6|
|`materias\\\\\\\_sin\\\\\\\_1p`|entero (0-6)|Materias sin 1° nota parcial|
|`situacion`|texto|Resultado tal como figura en la planilla (PROMUEVE N2, EGRESADO, NIVEL 3...). **No se usa como predictor** (es el resultado).|
|`acredita`|binaria|**Variable objetivo.** 1 = acredita el nivel; 0 = no acredita; vacío = sin resultado|
|`motivo\\\\\\\_exclusion`|texto|Vacío si el registro forma parte del modelo; si no, el motivo de exclusión|

## 7\. Privacidad

* Las planillas originales y el dataset real **no se suben** al repositorio (`.gitignore` los excluye); quedan solo en la computadora de la coordinadora.
* Reemplazar el DNI por un código es una **seudonimización**, no una anonimización completa: en un grupo pequeño, la combinación de edad, sector y cohorte podría identificar a una persona.
* Por eso, el repositorio incluye solo `data/processed/dataset\\\\\\\_sintetico.csv`: tiene la misma estructura y distribuciones parecidas, pero se construye mezclando por separado los valores de cada variable dentro de cada clase y agregando ruido, de modo que **ninguna fila corresponde a una persona real** y no se puedan identificar.
* Las notebooks muestran los resultados de los datos reales solo de forma agregada.

## 8\. Limitaciones

* **Tamaño de la muestra:** 121 registros para el modelo. Es suficiente para modelos simples (regresión logística, árbol de decisión), pero las métricas tendrán variabilidad.
* **Emparejamiento por nombre:** 6 estudiantes figuran en las planillas de notas de un nivel pero no en su asistencia. Se verificó que ninguno llegó a cursar ese nivel (bajas antes de empezar, cambios de nivel por equivalencias sin asistencia, y estudiantes que pasaron a nivel 4 adeudando materias de nivel 3 y no asistieron). Como el dataset se construye a partir de la asistencia, quedan fuera, igual que el resto de los casos de no inicio.
* **Turno laboral:** es el registrado en la nómina y puede haber cambiado durante el cuatrimestre debido a la dinámica de la empresa.
* **Distinta duración hasta el corte** entre 1° y 2° cuatrimestre (ver sección 2).

