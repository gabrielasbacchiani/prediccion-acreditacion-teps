# Descripción del dataset

## 1\. Descripción general

El dataset reúne la información de cursada de los estudiantes del **Programa de Terminalidad de Educación Profesional Secundaria (TEPS)**, que se dicta en las instalaciones de Newsan (Ushuaia, Tierra del Fuego) con propuesta pedagógica y docentes del Ministerio de Educación de la provincia de Tierra del Fuego - Argentina.

* **Unidad de análisis:** una fila por **estudiante y nivel cursado** (registro estudiante-nivel). Una persona que cursó dos niveles aparece en dos filas.
* **Período:** 1° cuatrimestre de 2025 a 2° cuatrimestre de 2026.
* **Momento de predicción:** todas las variables predictoras se calculan con la información registrada **hasta el 1° cierre de notas parcial** de cada cuatrimestre, una fecha institucional común a las 6 materias.
* **Variable objetivo:** `no_acredita` (1 = no aprobó las 6 materias del nivel al cierre final del cuatrimestre, incluido el recuperatorio; 0 = acreditó). Se codifica así porque la clase que interesa detectar es la de quienes no acreditan. Se conserva también `acredita` (su inversa) como referencia.

## 2\. Origen de los datos

Los datos provienen de los registros administrativos de la coordinadora pedagógica del programa, llevados en planillas de Excel. No es un dataset público: se construyó para este trabajo unificando las siguientes fuentes.

|Fuente|Contenido|Archivos usados|
|-|-|-|
|Planillas de asistencia|Una hoja por nivel con la asistencia de cada clase (códigos PE, PG, AE, AG, C/A, L/M, S/C, -) y la columna **SITUACIÓN** con el resultado del nivel|4 archivos (uno por cuatrimestre, 2025-2026)|
|Nómina (dentro de la planilla de asistencia)|Fecha de nacimiento, sexo, planta, turno laboral, departamento, convenio y empresa|Hoja "NOMINA ACTIVA" de cada archivo de asistencia|
|Planillas de calificaciones **al corte**|Una planilla por materia, con una hoja por nivel: notas de Trabajos Prácticos (TPs) y 1° nota parcial, tal como estaban al 1° cierre parcial|20 versiones recuperadas del historial de Google Drive (14 de 2025 y 6 de 2026); para el nivel 4 en curso, la planilla actual|
|Calendario|Fechas de inicio de clases, 1° cierre parcial y cierre final de cada cuatrimestre|Planilla de fechas armada por la coordinación|

**Por qué se usan versiones al corte.** Las planillas de notas se completan durante todo el cuatrimestre: los TPs entregados después del cierre parcial se cargan más tarde y algunas notas se modifican. La planilla final, por lo tanto, no muestra lo que se sabía al momento de predecir. Para evitar esa fuga de datos se descargó, del historial de versiones de Google Drive, la versión de cada planilla correspondiente al 1° cierre parcial. Algunas de esas versiones tienen fecha unos días posterior al cierre (por ejemplo, 06/06/2025 para el cierre del 02/06/2025) porque los docentes cargaron las notas al asistir presencialmente; cada docente registró solo las notas hasta la fecha de cierre.

| Cuatrimestre | Fecha de corte | Versiones utilizadas |
|---|---|---|
| 1° 2025 | 02/06/2025 | entre el 05/06 y el 09/06/2025 (7 planillas) |
| 2° 2025 | 19/09/2025 | entre el 19/09 y el 26/09/2025 (7 planillas) |
| 1° 2026 | 18/05/2026 | entre el 21/05 y el 27/05/2026 (6 planillas) |
| 2° 2026 (en curso) | 25/09/2026 | planilla actual: según la coordinación, sin notas cargadas después del corte |

**Nómina.** Se carga al inicio de cada cuatrimestre y no se actualiza durante la cursada; por eso cada registro usa la nómina de su propio cuatrimestre, que ya estaba disponible al momento del corte.

**Columna SITUACIÓN.** Refleja el resultado al cierre final del cuatrimestre, incluido el recuperatorio. En el 1° cuatrimestre de 2025 se completó más tarde, pero registra cómo cerró cada estudiante en ese momento, no regularizaciones posteriores.

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

1. Lee las hojas de cada nivel de las planillas de asistencia y traduce los códigos de cada clase anterior al corte. Asigna cada fecha a un campo (Electrónica o Formación General) según los códigos de ese día en cada grupo, para calcular la asistencia por campo con el mismo criterio que la general.
2. Lee la nómina **del mismo cuatrimestre** de cada cursada para los datos laborales. El sexo y la fecha de nacimiento, que no cambian, se toman de cualquier nómina.
3. Lee las **versiones al corte** de las planillas de calificaciones, ubicando las columnas por su nombre, y toma solo los TPs anteriores a la 1° nota parcial y la 1° nota parcial.
4. Como las planillas de notas no tienen DNI, **empareja cada nombre** con la asistencia del mismo año, cuatrimestre y nivel (comparación de palabras del nombre).
5. Agrega las notas de las 6 materias por estudiante-nivel.
6. Calcula la variable objetivo a partir de la columna SITUACIÓN.
7. Aplica las reglas de exclusión (sección 5).
8. Reemplaza el DNI por un código (`E001`, `E002`, ...) y genera un dataset sintético para probar el código.

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

En las calificaciones, una nota **1**, una celda vacía o un **"-"** en un TP significan **TP no entregado**. Esas notas no entran en el promedio.

**TPs previstos.** El denominador del porcentaje de TPs entregados se construye desde los encabezados de cada materia: un TP es exigible al corte si su columna tiene encabezado y al menos un estudiante del grupo lo tiene cargado. No depende de que el estudiante tenga notas.

Se distinguen tres situaciones:

| Situación | Tratamiento |
|---|---|
| El estudiante figura en la planilla de la materia y no entregó el TP | Cuenta como **TP no entregado** |
| El estudiante **no figura** en la planilla de esa materia (por ejemplo, porque ya la tenía aprobada) | Dato faltante: esa materia no entra en el porcentaje |
| El nombre **no se pudo emparejar** con la asistencia | Dato faltante: esa materia no entra en el porcentaje |

La cantidad de materias sin registro queda en la variable `materias_sin_registro`, que se usa solo como control de calidad y no como predictor.

## 4. Cantidad de instancias

| | Registros | Estudiantes únicos |
|---|---|---|
| Total del dataset | 153 | 83 |
| Población del modelo | 121 | 75 |

Distribución de la variable objetivo en la población del modelo: **47 no acreditan (38,8 %)** y **74 acreditan (61,2 %)**.

| Cuatrimestre | Nivel | Registros | No acreditan |
|---|---|---|---|
| 1° 2025 | 1 | 23 | 8 |
| 1° 2025 | 3 | 34 | 15 |
| 2° 2025 | 2 | 18 | 7 |
| 2° 2025 | 4 | 24 | 13 |
| 1° 2026 | 3 | 22 | 4 |

**Separación para el modelado** (orden de cohortes y sin personas repetidas):

| Conjunto | Registros | No acreditan |
|---|---|---|
| Entrenamiento (2025) | 75 | 39 (52,0 %) |
| Prueba (1° cuatrimestre 2026) | 22 | 4 (18,2 %) |

Se quitaron 24 registros de 2025 del entrenamiento porque esas personas están en la prueba. Con solo 4 casos de "no acredita" en la prueba, sus métricas deben leerse con prudencia.

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
|`id_estudiante`|texto|Código seudonimizado del estudiante (reemplaza el DNI)|
|`anio`|entero|Año de cursada (2025, 2026)|
|`cuatri`|entero|Cuatrimestre (1 o 2)|
|`nivel`|entero|Nivel cursado (1 a 4)|
|`grupo`|categórica|Grupo horario de cursada: 12:30 o 15:30|
|`rango_edad`|categórica|Edad al inicio del cuatrimestre, en rangos: 18-25, 26-35, 36-45, 46+|
|`sexo`|categórica|Sexo registrado en la nómina|
|`empresa_grupo`|categórica|Newsan / Empresa vinculada del grupo (Jenizaros, GDS, Globale, Pulpo) / Familiar de trabajador / Otro|
|`sector`|categórica|Departamento agrupado: Producción, Vigilancia, Logística/abastecimiento, Otro|
|`turno_laboral`|categórica|Turno de trabajo: Mañana, Tarde, Noche, Rotativo, Sin dato|
|`lugar_trabajo`|categórica|Lugar de trabajo respecto del cursado (planta 4): misma planta, otra planta, rotativo, sin dato|
|`convenio_uom`|binaria|1 si está bajo convenio UOM, 0 si no|
|`clases_dictadas_corte`|entero|Clases dictadas al estudiante hasta el corte|
|`pct_asistencia`|real (0-1)|Presentes / clases dictadas hasta el corte. Las ausencias con y sin aviso cuentan como inasistencia; las licencias médicas no se cuentan.|
|`pct_asist_electronica`|real (0-1)|Igual que `pct_asistencia`, solo con las clases de Electrónica|
|`pct_asist_general`|real (0-1)|Igual que `pct_asistencia`, solo con las clases de Formación General|
|`pct_ausente_sin_aviso`|real (0-1)|Proporción de ausencias sin aviso hasta el corte|
|`pct_ausente_con_aviso`|real (0-1)|Proporción de ausencias con aviso hasta el corte|
|`licencias_medicas`|entero|Cantidad de clases con licencia médica hasta el corte|
|`presente_turno_contrario`|entero|Clases a las que asistió en el turno contrario hasta el corte|
|`materias_sin_registro`|entero (0-6)|Materias en las que el estudiante no figura en la planilla de notas al corte o no se pudo emparejar. Solo control de calidad.|
|`pct_tps_entregados`|real (0-1)|TPs entregados / TPs previstos antes de la 1° nota, sumando las materias en las que el estudiante figura (ver sección 3)|
|`promedio_tps`|real (2-10)|Promedio de las notas de los TPs entregados antes de la 1° nota|
|`promedio_1p`|real (2-10)|Promedio de la 1° nota parcial en las materias que la tienen|
|`materias_1p_menor6`|entero|Materias con 1° nota parcial menor a 6|
|`materias_sin_1p`|entero (0-6)|Materias sin 1° nota parcial, entre las que el estudiante figura|
|`situacion`|texto|Resultado tal como figura en la planilla (PROMUEVE N2, EGRESADO, NIVEL 3...). **No se usa como predictor** (es el resultado).|
|`acredita`|binaria|1 = acredita el nivel; 0 = no acredita; vacío = sin resultado. Referencia, no se usa como predictor.|
|`no_acredita`|binaria|**Variable objetivo.** 1 = no acredita; 0 = acredita; vacío = sin resultado|
|`motivo_exclusion`|texto|Vacío si el registro forma parte del modelo; si no, el motivo de exclusión|

## 7. Privacidad y dataset sintético

* Las planillas originales y los datos reales **no se suben** al repositorio. El archivo `.gitignore` indica a Git que no agregue `data/raw`, `data/interim` ni los archivos de `data/processed` salvo el sintético. Si se suben archivos arrastrándolos desde la web de GitHub, `.gitignore` no actúa, así que hay que verificar a mano que no se incluyan.
* Reemplazar el DNI por un código es una **seudonimización**, no una anonimización completa: en un grupo pequeño, la combinación de edad, sector y cohorte podría identificar a una persona.
* Por eso el repositorio incluye solo `data/processed/dataset_sintetico.csv`, que tiene la misma estructura pero se construye mezclando por separado los valores de cada variable dentro de cada clase, con un identificador distinto para cada fila.
* **El dataset sintético sirve solo para comprobar que el código funciona.** No conserva las trayectorias de una misma persona (cada fila es un "estudiante" distinto) ni las relaciones entre variables, por lo que la separación por estudiante y cualquier resultado obtenido con él no reproducen el procedimiento aplicado a los datos reales. Las conclusiones se basan únicamente en los datos reales.
* Las notebooks muestran los resultados de los datos reales solo de forma agregada.

## 8. Limitaciones

* **Tamaño de la muestra:** 75 registros de entrenamiento y 22 de prueba, con solo 4 casos de "no acredita" en la prueba. Se priorizan modelos simples (regresión logística y árbol de decisión) y las métricas de la prueba deben leerse con prudencia.
* **Versiones al corte:** las planillas no guardan automáticamente una copia del cierre parcial; las versiones se recuperaron del historial de Google Drive. Algunas tienen fecha unos días posterior al corte porque los docentes cargaron las notas al asistir presencialmente; según la coordinación, contienen solo lo registrado hasta el cierre.
* **Emparejamiento por nombre:** 6 estudiantes figuran en las planillas de notas de un nivel pero no en su asistencia; se verificó que ninguno llegó a cursar ese nivel. Además, 2 estudiantes de nivel 3 (1° cuatrimestre 2025) figuraban en la planilla de notas de nivel 1 al corte por un cambio de nivel, y sus notas quedan como dato faltante.
* **Datos laborales:** son los de la nómina cargada al inicio de cada cuatrimestre; los cambios de turno o de sector durante la cursada no se registran.
* **Distinta duración hasta el corte** entre 1° y 2° cuatrimestre (ver sección 2).
