# Objetivos y alcance del proyecto

**Autora:** Gabriela Soledad Bacchiani · Aprendizaje Automático · Centro Politécnico Superior "Malvinas Argentinas"

*Predicción temprana de acreditación en un Programa de Terminalidad de Educación Profesional Secundaria para adultos*

Este documento recoge la propuesta presentada en la Entrega 1 y, al final, las precisiones incorporadas a partir de la devolución del docente.

## DESCRIPCIÓN Y CONTEXTO DEL PROYECTO

Este proyecto de aprendizaje automático se basa en mi experiencia como coordinadora pedagógica de un Proyecto de Terminalidad de Educación Profesional Secundaria (T.E.P.S.), que se dicta desde el año 2022 dentro de las instalaciones de la Empresa Newsan. Es un proyecto que depende de la Dirección Provincial de Educación Técnica de Tierra del Fuego (Ministerio de Educación TDF), en asociación con un ente privado como lo es la empresa Newsan; la propuesta pedagógica y el personal docente dependen del Ministerio de Educación, las instalaciones físicas son proporcionadas por la empresa.

La propuesta está destinada a personas adultas, mayores de 18 años, que no hayan concluido con sus estudios secundarios y que sean trabajadores de Newsan, que incluye empresas vinculadas como Jenizaros, GDS, Globale y Pulpo, con distintos convenios colectivos de trabajo, alcanzando también a sus familiares directos.

La modalidad es semipresencial, con clases presenciales y un trabajo virtual asincrónico a través de la plataforma Aulas Digitales, en la cual los docentes suben trabajos prácticos cada dos semanas, el cursado es por fuera del horario laboral. Está dividido en cuatro niveles, cada uno abarca un cuatrimestre, se cursan 6 materias:

- cinco corresponden a la formación general (matemática, prácticas del lenguaje, ciencias sociales, ciencias naturales, lengua extranjera inglés).

- una corresponde a la formación profesional: electrónica.

La cursada actualmente se organiza de la siguiente manera:

- dos grupos de cursada planificados según las jornadas laborales de la empresa: de 12:30 a 14:30 hs o de 15:30 a 17:30 hs.

- dos días por semana tienen clase de electrónica

- un día por semana tienen materias de la formación general, una hora cada una con un sistema de rotación de dichos espacios.

El criterio de aprobación, según la normativa vigente, es del 80 % de asistencia a los encuentros presenciales, 100 % de trabajos entregados y aprobados en la plataforma virtual, entrega y aprobación de un Trabajo Integrador final, nota de aprobación de 6.

Desde su inicio, se han recibido más de 300 inscripciones, contando en la actualidad con 86 egresados y 19 estudiantes cursando en nivel 4.

## PROBLEMA Y RELEVANCIA

El problema central desde su inicio es que muchos estudiantes adultos no inician con el cursado o van abandonando paulatinamente durante el mismo. Hoy el seguimiento se realiza en forma manual, la información está volcada en planillas de Excel guardadas en el drive personal de la coordinadora, a las que otros miembros del equipo solo acceden si se les otorga permiso. No hay una base de datos unificada, o una mirada integral acerca del proceso de cada estudiante. Esto conlleva a que pueda existir una intervención tardía, ya que cuando se detecta que un estudiante no acredita, ya puede ser tarde para convocarlo o revertir la situación.

Anticipar el riesgo permite acompañar a tiempo, ofreciendo diferentes alternativas que se ajusten a la realidad del estudiante. En mi experiencia trabajando hace muchos años con estudiantes adultos, cada estudiante que se pierde es una trayectoria que vuelve a interrumpirse por lo que es importante trabajar fuertemente en la prevención de esta problemática.

Si bien hay muchos trabajos similares en cuanto a predecir el riesgo de abandono escolar, como el realizado anteriormente en esta cátedra por la estudiante Maricel Rausch y el estudiante Gabriel García, ambos utilizando datos agregados oficiales, este proyecto utiliza registros individuales de estudiantes adultos trabajadores, con el registro del desempeño por materias, los datos acerca de su asistencia e incorporación de variables del contexto laboral, lo que permite predecir en forma temprana si logrará la acreditación.

## OBJETIVOS

### OBJETIVO GENERAL

- Desarrollar un modelo de clasificación que anticipe qué estudiantes podrán acreditar el nivel, para orientar intervenciones tempranas a partir de la información disponible.

### OBJETIVOS ESPECÍFICOS

- Construir una base de datos unificada y anonimizada a partir de los registros 2022 – 2026, con información recolectada de las fichas de inscripción, registros de asistencia por clases y calificaciones.

- Analizar el recorrido realizado entre la inscripción, el inicio de clases, acreditación y egreso, los momentos de abandono y sus motivos.

- Construir variables tempranas de asistencia y rendimiento, hasta la 1° nota parcial (mitad de cuatrimestre)

- Entrenar y comparar distintos modelos de clasificación.

- Evaluarlos con precisión, recall y F1, priorizando la detección de quienes no acreditarían el nivel.

- Identificar las variables con mayor influencia y revisar que el modelo no tenga un desempeño desigual entre grupos (por ejemplo, por sexo).

## TIPO DE PROBLEMA

Podemos especificar que se trata de un problema de clasificación binaria supervisada, en el que la variable objetivo es si el estudiante acredita el nivel (sí/no). La unidad de análisis será de una fila por estudiante y por nivel cursado.

El modelo se entrenará con los registros de las cohortes anteriores (2022 – 2025), utilizando solo la información disponible hasta la 1° nota parcial de cada cuatrimestre. Una vez entrenado, se aplicará a los estudiantes que actualmente cursan nivel 4. Esto se debe a que si utilizáramos datos del final de la cursada no se podría intervenir y además se produciría una fuga de datos (el modelo ya contaría con la información sobre quienes acreditaron o no).

## MODELOS DE APRENDIZAJE AUTOMÁTICO

| Modelo              | Rol en el proyecto                                                                                                |
|---------------------|-------------------------------------------------------------------------------------------------------------------|
| Regresión logística | Modelo base, interpretable                                                                                        |
| Árbol de decisión   | Genera reglas legibles para el equipo docente                                                                     |
| KNN y SVM           | Modelos de naturaleza distinta, basados en distancias y márgenes de separación, que permiten contrastar resultados |
| Random Forest       | Combina muchos árboles, por lo que es más robusto y menos propenso al sobreajuste que un árbol individual         |
| K-Means + PCA       | Complementario, no supervisado: describir perfiles de estudiantes                                                 |

**Validación:** Para evaluar los modelos se separarán los datos por estudiante, de modo que una misma persona no aparezca en entrenamiento y prueba a la vez, se probará entrenando con cohortes anteriores y validando con la más reciente.

## CONSIDERACIONES ÉTICAS Y DE DATOS

Se realizará una anonimización de los datos, reemplazando el DNI por un código, la edad se definirá en rangos y los puestos serán agrupados por sector, para evitar la identificación de los estudiantes.

En el repositorio no se guardarán datos personales de ningún estudiante.

Es importante destacar que el uso de este modelo tiene un carácter estrictamente pedagógico, las predicciones no se compartirán con la empresa ni tendrán injerencia en decisiones laborales, ya que el objetivo de este modelo es que funcione como un sistema de alertas tempranas que permitan la intervención para evitar la deserción, pero no para etiquetar a los estudiantes.

## Precisiones incorporadas a partir de la devolución de la Entrega 1

- **Acreditar, no acreditar y abandonar.** El modelo predice la acreditación entre quienes **iniciaron** la cursada. El **no inicio** (inscriptos que nunca asistieron) queda para el análisis descriptivo, porque ocurre antes del momento de predicción. Dentro de "no acredita" quedan tanto quienes abandonan como quienes siguen con materias pendientes; esa diferencia se tendrá en cuenta al interpretar los resultados.
- **Condición de acreditación.** Un estudiante acredita el nivel si aprueba las 6 materias (calificación definitiva de 6 o más) al **cierre final del cuatrimestre**, incluido el recuperatorio de ese cuatrimestre. En las planillas figura como *PROMUEVE* o *EGRESADO*.
- **Momento de predicción común.** Se usa la fecha institucional del **1° cierre de notas parcial**, que es la misma para las 6 materias de cada cuatrimestre (por ejemplo, 25/09/2026). Solo se utiliza lo registrado hasta esa fecha.
- **Estudiantes sin nota parcial.** No se excluyen: la falta de nota y los TPs no entregados se registran como variables, porque son justamente los casos que necesitan acompañamiento.
- **Alcance de los datos.** Por el tiempo disponible se trabaja con los registros de **2025 y 2026**. Los años 2022-2024 quedan como ampliación futura.
- **Validación.** Se entrena con 2025 y se prueba con el 1° cuatrimestre de 2026, quitando del entrenamiento a las personas que también están en la prueba. Los estudiantes que cursan actualmente nivel 4 recibirán una estimación, pero no se usan para calcular métricas.
- **Modelos.** Se comenzará con **regresión logística** y **árbol de decisión**; los demás modelos quedan como ampliación si los datos y el tiempo lo permiten. En el análisis no supervisado, K-Means es el que forma los grupos y PCA se usa para reducir dimensiones y visualizarlos.
- **Privacidad.** Reemplazar el DNI por un código es una seudonimización, no una anonimización completa. Por eso el repositorio publica el código y un **dataset sintético**; los registros reales quedan en un entorno restringido.

El detalle del dataset está en [`dataset.md`](dataset.md).
