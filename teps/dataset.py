"""
teps/dataset.py
===============
Unifica las planillas del TEPS (asistencia, nómina y calificaciones de 2025-2026)
en un dataset con UNA FILA POR ESTUDIANTE Y POR NIVEL CURSADO, usando solo la
información disponible hasta el 1° cierre de notas parcial de cada cuatrimestre.

Uso (desde el Anaconda Prompt, parada en la carpeta del proyecto):
    python teps/dataset.py "C:/Users/ga_so/Documents/TEPS_DATOS" data

(el primer argumento es la carpeta con las planillas originales; si se omite,
se usa data/raw)

Fuentes que lee dentro de esa carpeta:
    ASISTENCIA/             -> asistencia por clase, columna SITUACIÓN y nómina de cada cuatrimestre
    CALIFICACIONES CORTE/   -> versiones de las planillas de notas tal como estaban al 1° cierre
                               parcial (recuperadas del historial de versiones de Google Drive)

Genera:
    data/interim/registros_con_dni.csv      -> PRIVADO (tiene DNI). No se sube.
    data/interim/notas_sin_emparejar.csv    -> PRIVADO. Para revisar a mano.
    data/processed/dataset_real.csv         -> PRIVADO (seudonimizado). No se sube.
    data/processed/dataset_sintetico.csv    -> PÚBLICO. Solo para probar el código.
    reports/resumen_dataset.txt             -> conteos para la entrega.

Cambios respecto de la Entrega 2 (devolución del docente):
    1. La nómina se toma del MISMO cuatrimestre de cada cursada (antes: la más reciente).
    2. Las notas salen de las versiones al corte, no de las planillas finales.
    3. Los TPs previstos se cuentan desde los encabezados de cada materia, no desde las filas
       con datos; una materia sin registro del estudiante queda como dato faltante.
    4. La asistencia por campo (Electrónica / Formación General) usa el mismo criterio que la
       general: cada fecha se asigna a un campo y se cuentan también las ausencias con aviso.
"""

import re
import sys
import unicodedata
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import openpyxl

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN
# ---------------------------------------------------------------------------
# corte = 1° cierre de notas parcial -> MOMENTO DE PREDICCIÓN
CALENDARIO = {
    (2025, 1): dict(inicio="2025-05-08", corte="2025-06-02", cierre="2025-07-11", niveles=[1, 3]),
    (2025, 2): dict(inicio="2025-08-07", corte="2025-09-19", cierre="2025-11-14", niveles=[2, 4]),
    (2026, 1): dict(inicio="2026-04-23", corte="2026-05-18", cierre="2026-07-03", niveles=[3]),
    (2026, 2): dict(inicio="2026-08-12", corte="2026-09-25", cierre="2026-11-27", niveles=[4]),
}

ARCHIVOS_ASISTENCIA = {
    (2025, 1): "ASISTENCIA - 2025 - 1er semestre.xlsx",
    (2025, 2): "ASISTENCIA - 2025 - 2do semestre.xlsx",
    (2026, 1): "ASISTENCIA - 2026 - 1er semestre.xlsx",
    (2026, 2): "ASISTENCIA - 2026 - 2do semestre.xlsx",
}

# Carpeta con las versiones de las planillas de notas al corte.
# El cuatrimestre se deduce del mes de la versión (enero-julio = 1°, agosto-diciembre = 2°).
CARPETA_NOTAS_CORTE = "CALIFICACIONES CORTE"
# Para el cuatrimestre en curso (todavía sin versión "de corte" descargada) se usa la planilla actual,
# que la coordinación indicó que no tiene datos cargados después del corte.
CARPETA_NOTAS_ACTUALES = {(2026, 2): "CALIFICACIONES/2026"}

MATERIAS = {
    "NATURALES": "naturales", "SOCIALES": "sociales", "ELECTR": "electronica",
    "INGL": "ingles", "MATEM": "matematica", "LENGUAJE": "lengua",
}
N_MATERIAS = 6

# Códigos de asistencia (acordados con la coordinación)
PRESENTE = {"PE", "PG", "PV", "PGTM"}
AUSENTE_SIN_AVISO = {"AE", "AG"}
AUSENTE_CON_AVISO = {"C/A"}
LICENCIA = {"L/M"}
SIN_CLASE = {"S/C", ""}
BAJA = {"-", "--"}
CODIGOS_E = {"PE", "AE"}               # códigos que identifican una clase de Electrónica
CODIGOS_G = {"PG", "AG", "PGTM"}       # códigos que identifican una clase de Formación General

PLANTA_CURSADO = 4
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------
def texto(v):
    """Convierte una celda a texto limpio."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def normalizar(s):
    """Mayúsculas, sin tildes ni signos: para comparar nombres."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z ]", " ", s.upper()).split()


def limpiar_dni(v):
    d = re.sub(r"\D", "", texto(v).split(".")[0])
    return d if len(d) >= 7 else None


def a_fecha(v):
    if isinstance(v, datetime):
        return v.date()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", texto(v))
    if m:
        d, mth, y = map(int, m.groups())
        try:
            return datetime(y + 2000 if y < 100 else y, mth, d).date()
        except ValueError:      # fecha mal cargada en la planilla
            return None
    return None


def codigo(v):
    c = texto(v).upper().replace(" ", "").replace(".", "")
    if c.startswith("C/A"):
        return "C/A"            # incluye "C/A TRABAJANDO"
    if c.startswith(("PGT", "PET")):
        return "PGTM"           # presente en el turno contrario
    return c


def rango_edad(e):
    if pd.isna(e):
        return np.nan
    if e <= 25:
        return "18-25"
    if e <= 35:
        return "26-35"
    if e <= 45:
        return "36-45"
    return "46+"


def proporcion(a, b):
    return a / b if b else np.nan


# ---------------------------------------------------------------------------
# 2. ASISTENCIA + SITUACIÓN (resultado) desde las hojas "NIVEL X"
# ---------------------------------------------------------------------------
def leer_hoja_nivel(ws, anio, cuatri, nivel, cal):
    """Devuelve una fila por estudiante con sus indicadores de asistencia hasta el corte."""
    corte = pd.Timestamp(cal["corte"]).date()
    alumnos, fechas, grupo, col_sit = [], None, None, None
    for fila in ws.iter_rows(values_only=True):
        t = [texto(v) for v in fila]
        if any("12:30" in x for x in t[:4]):
            grupo = "12:30"
        if any("15:30" in x for x in t[:4]):
            grupo = "15:30"
        if "SITUACIÓN" in t:                       # fila de encabezado de un bloque
            col_sit = t.index("SITUACIÓN")
            f = {j: a_fecha(v) for j, v in enumerate(fila) if a_fecha(v)}
            if f:                                   # el 2° bloque reutiliza las fechas del 1°
                fechas = f
            continue
        dni = limpiar_dni(fila[1]) if len(fila) > 1 else None
        if not dni or col_sit is None or not fechas:
            continue
        cods = {j: codigo(fila[j]) if j < len(fila) else "" for j in fechas}
        alumnos.append(dict(dni=dni, grupo=grupo, apellido=texto(fila[2]), nombre=texto(fila[3]),
                            cods=cods, sit=texto(fila[col_sit]).upper() if col_sit < len(fila) else ""))

    # Campo de cada fecha (por grupo): mayoría de códigos PE/AE (Electrónica) o PG/AG (General).
    # Así las ausencias con aviso y las licencias de ese día se asignan al campo que correspondía.
    campo = {}
    for g in {a["grupo"] for a in alumnos}:
        for j in fechas or {}:
            c = Counter("E" if a["cods"][j] in CODIGOS_E else "G" if a["cods"][j] in CODIGOS_G else None
                        for a in alumnos if a["grupo"] == g)
            e, gg = c.get("E", 0), c.get("G", 0)
            campo[(g, j)] = "E" if e > gg else "G" if gg > e else None

    registros = []
    for a in alumnos:
        antes = [(j, a["cods"][j]) for j in sorted(fechas) if fechas[j] <= corte]
        todo = [a["cods"][j] for j in sorted(fechas)]
        dictadas = [(j, c) for j, c in antes if c not in SIN_CLASE and c not in BAJA]

        def indicadores(clases):
            pres = sum(c in PRESENTE for _, c in clases)
            lm = sum(c in LICENCIA for _, c in clases)
            return pres, len(clases) - lm, lm      # presentes, base (sin licencias), licencias

        pres, base, lm = indicadores(dictadas)
        pres_e, base_e, _ = indicadores([(j, c) for j, c in dictadas if campo.get((a["grupo"], j)) == "E"])
        pres_g, base_g, _ = indicadores([(j, c) for j, c in dictadas if campo.get((a["grupo"], j)) == "G"])
        codigos_antes = [c for _, c in antes]
        baja = bool(codigos_antes) and all(c in BAJA for c in codigos_antes[-3:]) and \
            sum(c in PRESENTE for c in codigos_antes) < len(codigos_antes)

        registros.append(dict(
            dni=a["dni"], anio=anio, cuatri=cuatri, nivel=nivel, grupo=a["grupo"],
            apellido=a["apellido"], nombre=a["nombre"],
            clases_dictadas_corte=len(dictadas),
            pct_asistencia=proporcion(pres, base),
            pct_asist_electronica=proporcion(pres_e, base_e),
            pct_asist_general=proporcion(pres_g, base_g),
            pct_ausente_sin_aviso=proporcion(sum(c in AUSENTE_SIN_AVISO for _, c in dictadas), base),
            pct_ausente_con_aviso=proporcion(sum(c in AUSENTE_CON_AVISO for _, c in dictadas), base),
            licencias_medicas=lm,
            presente_turno_contrario=sum(c == "PGTM" for _, c in dictadas),
            inicio=pres > 0,
            presente_alguna_vez=any(c in PRESENTE for c in todo),
            baja_avisada_antes_corte=baja,
            situacion=a["sit"],
        ))
    return registros


def leer_nomina(ws):
    """Nómina del cuatrimestre: se carga al inicio y no se actualiza durante la cursada."""
    filas = list(ws.iter_rows(values_only=True))
    h = [texto(v) for v in filas[1]]
    idx = {k: h.index(k) for k in ["DNI", "FECHA DE NACIMIENTO", "SEXO", "PLANTA", "TURNO",
                                   "DEPARTAMENTO", "CONVENIO", "EMPRESA"] if k in h}
    out = []
    for f in filas[2:]:
        dni = limpiar_dni(f[idx["DNI"]]) if len(f) > idx["DNI"] else None
        if not dni:
            continue
        g = lambda k: f[idx[k]] if k in idx and idx[k] < len(f) else None
        out.append(dict(dni=dni, fecha_nac=a_fecha(g("FECHA DE NACIMIENTO")),
                        sexo=texto(g("SEXO")).capitalize() or np.nan,
                        planta=texto(g("PLANTA")).upper(), turno_laboral=texto(g("TURNO")).capitalize(),
                        departamento=texto(g("DEPARTAMENTO")).upper(),
                        convenio=texto(g("CONVENIO")).upper(), empresa=texto(g("EMPRESA")).upper()))
    return out


def leer_asistencia(raw):
    regs, nom = [], []
    for (anio, cuatri), archivo in ARCHIVOS_ASISTENCIA.items():
        wb = openpyxl.load_workbook(raw / "ASISTENCIA" / archivo, data_only=True, read_only=True)
        cal = CALENDARIO[(anio, cuatri)]
        for ws in wb.worksheets:
            m = re.fullmatch(r"NIVEL (\d)", ws.title.strip())
            if m and int(m.group(1)) in cal["niveles"]:
                regs += leer_hoja_nivel(ws, anio, cuatri, int(m.group(1)), cal)
        for r in leer_nomina(wb["NOMINA ACTIVA"]):
            r.update(anio=anio, cuatri=cuatri)
            nom.append(r)
    return pd.DataFrame(regs), pd.DataFrame(nom)


# ---------------------------------------------------------------------------
# 3. CALIFICACIONES AL CORTE (TPs anteriores a la 1° nota y 1° nota parcial)
# ---------------------------------------------------------------------------
def es_1p(x):
    return bool(re.fullmatch(r"1\s*°?\s*(NP|NOTA PARCIAL)", x.upper()))


def periodo_de_archivo(archivo):
    """Año y cuatrimestre de una versión: año del nombre, cuatrimestre según el mes de la versión."""
    nombre = archivo.stem.lower()
    anio = int(re.search(r"20\d\d", nombre).group())
    mes = next((n for m, n in MESES.items() if m in nombre), None)
    return anio, (1 if mes and mes <= 7 else 2)


def entregado(v):
    """TP entregado: nota de 2 a 10 o un texto de aprobación. 1, '-', '--' o vacío = no entregado."""
    if isinstance(v, (int, float)):
        return v >= 2
    return texto(v).upper().startswith("APROB")


def leer_hoja_notas(ws, anio, cuatri, nivel, materia, archivo):
    filas = list(ws.iter_rows(values_only=True))
    i_hdr = next((i for i, f in enumerate(filas) if any(es_1p(texto(v)) for v in f)), None)
    if i_hdr is None:
        return []
    h = [texto(v) for v in filas[i_hdr]]
    col_1p = next(j for j, x in enumerate(h) if es_1p(x))
    col_nombre = next((j for j, x in enumerate(h[:col_1p]) if "APELLIDO" in x.upper()), None)
    inicio_tp = (col_nombre + 1) if col_nombre is not None else 2
    alumnos = []
    for fila in filas[i_hdr + 1:]:
        t = [texto(v) for v in fila] + ["", ""]
        if col_nombre is not None:
            nombre = t[col_nombre] if col_nombre < len(t) else ""
        else:
            nombre = f"{t[0]} {t[1]}"
        if (len(normalizar(nombre)) < 2 or len(nombre) > 45
                or re.search(r"TURNO|DE \d|RECUPER|DEBER|APELLIDO", nombre.upper())):
            continue
        alumnos.append((nombre, [fila[j] if j < len(fila) else None for j in range(inicio_tp, col_1p)],
                        fila[col_1p] if col_1p < len(fila) else None))
    # Un TP es "previsto" (exigible al corte) si tiene encabezado y al menos un estudiante lo tiene cargado
    previstos = [k for k in range(col_1p - inicio_tp)
                 if h[inicio_tp + k] and any(texto(a[1][k]) for a in alumnos)]
    regs = []
    for nombre, tps, nota in alumnos:
        ent = [tps[k] for k in previstos if entregado(tps[k])]
        notas = [float(v) for v in ent if isinstance(v, (int, float))]
        regs.append(dict(anio=anio, cuatri=cuatri, nivel=nivel, materia=materia, archivo=archivo,
                         nombre_notas=nombre, tps_previstos=len(previstos), tps_entregados=len(ent),
                         suma_notas_tp=sum(notas), n_notas_tp=len(notas),
                         nota_1p=float(nota) if isinstance(nota, (int, float)) and nota >= 2 else np.nan))
    return regs


def leer_calificaciones(raw):
    archivos = [(a, periodo_de_archivo(a)) for a in sorted((raw / CARPETA_NOTAS_CORTE).glob("*.xlsx"))]
    for (anio, cuatri), carpeta in CARPETA_NOTAS_ACTUALES.items():
        archivos += [(a, (anio, cuatri)) for a in sorted((raw / carpeta).glob("*.xlsx"))]
    regs = []
    for archivo, (anio, cuatri) in archivos:
        materia = next((v for k, v in MATERIAS.items() if k in archivo.name.upper()), None)
        niveles = CALENDARIO[(anio, cuatri)]["niveles"]
        wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
        for ws in wb.worksheets:
            m = re.search(r"(?:NIVEL\s*|N)(\d)", ws.title.upper())
            if m and int(m.group(1)) in niveles:
                regs += leer_hoja_notas(ws, anio, cuatri, int(m.group(1)), materia, archivo.name)
    return pd.DataFrame(regs)


def emparejar_nombres(notas, asis):
    """Asigna el DNI a cada fila de notas comparando el nombre con la asistencia del mismo nivel."""
    dnis = []
    for _, r in notas.iterrows():
        cand = asis[(asis.anio == r.anio) & (asis.cuatri == r.cuatri) & (asis.nivel == r.nivel)]
        a = set(normalizar(r.nombre_notas))
        puntajes = sorted(((len(a & set(normalizar(f"{c.apellido} {c.nombre}"))) /
                            max(len(a | set(normalizar(f"{c.apellido} {c.nombre}"))), 1), c.dni)
                           for c in cand.itertuples()), reverse=True)
        ok = puntajes and puntajes[0][0] >= 0.5 and (len(puntajes) == 1 or puntajes[0][0] > puntajes[1][0])
        dnis.append(puntajes[0][1] if ok else None)
    return notas.assign(dni=dnis)


# ---------------------------------------------------------------------------
# 4. ARMADO DEL DATASET
# ---------------------------------------------------------------------------
def categorizar(df):
    emp = df.empresa.fillna("")
    df["empresa_grupo"] = np.select(
        [emp.str.contains("NEWSAN"), emp.str.contains("JENIZAROS|GDS|GLOBALE|PULPO"),
         emp.str.contains("FAMILIAR")],
        ["Newsan", "Empresa vinculada", "Familiar"], "Otro/sin dato")
    dep = df.departamento.fillna("")
    df["sector"] = np.select(
        [dep.str.contains("PRODUC|OPERARI|SOLDAD|MANTEN|CALIDAD|INGENIER"),
         dep.str.contains("VIGILAN"), dep.str.contains("ABASTEC|LOGIST")],
        ["Producción", "Vigilancia", "Logística/abastecimiento"], "Otro/sin dato")
    tl = df.turno_laboral.fillna("").str.upper()
    df["turno_laboral"] = np.select(
        [tl.str.contains("MAÑANA|MANANA"), tl.str.contains("TARDE"), tl.str.contains("NOCHE"),
         tl.str.contains("24|ROTA")], ["Mañana", "Tarde", "Noche", "Rotativo"], "Sin dato")
    pl = df.planta.fillna("").str.upper()
    df["lugar_trabajo"] = np.select(
        [pl.str.contains("ROTA"), pl.str.match(rf"^{PLANTA_CURSADO}(\.0)?$"), pl.str.match(r"^\d")],
        ["Rotativo", "Misma planta que el cursado", "Otra planta"], "Sin dato")
    df["convenio_uom"] = np.where(df.convenio.isna(), np.nan,
                                  df.convenio.fillna("").str.contains("U.O.M", regex=False).astype(float))
    return df


def main(raw, salida):
    raw, salida = Path(raw), Path(salida)
    for sub in ["interim", "processed"]:
        (salida / sub).mkdir(parents=True, exist_ok=True)
    reportes = salida.parent / "reports"
    reportes.mkdir(exist_ok=True)

    asis, nomina = leer_asistencia(raw)
    notas = emparejar_nombres(leer_calificaciones(raw), asis)
    clave = ["dni", "anio", "cuatri", "nivel"]

    # --- notas por materia: si un estudiante aparece dos veces en la misma materia
    #     (p. ej. en las dos planillas de Electrónica), se conserva la fila con más información
    n = (notas.dropna(subset=["dni"])
              .sort_values(["tps_entregados", "nota_1p"], ascending=False, na_position="last")
              .drop_duplicates(clave + ["materia"]))
    agg = n.groupby(clave).agg(
        materias_con_registro=("materia", "nunique"),
        tps_previstos=("tps_previstos", "sum"), tps_entregados=("tps_entregados", "sum"),
        suma_notas_tp=("suma_notas_tp", "sum"), n_notas_tp=("n_notas_tp", "sum"),
        promedio_1p=("nota_1p", "mean"),
        materias_1p_menor6=("nota_1p", lambda s: int((s < 6).sum())),
        materias_sin_1p=("nota_1p", lambda s: int(s.isna().sum())),
    ).reset_index()
    # El porcentaje usa como denominador los TPs previstos de las materias donde el estudiante FIGURA.
    # Una materia sin registro (planilla ausente o nombre no emparejado) NO se cuenta como falta de entrega.
    agg["pct_tps_entregados"] = agg.tps_entregados / agg.tps_previstos.replace(0, np.nan)
    agg["promedio_tps"] = agg.suma_notas_tp / agg.n_notas_tp.replace(0, np.nan)

    df = asis.merge(agg, on=clave, how="left")
    df["materias_con_registro"] = df.materias_con_registro.fillna(0).astype(int)
    df["materias_sin_registro"] = N_MATERIAS - df.materias_con_registro
    for c in ["materias_1p_menor6", "materias_sin_1p"]:
        df.loc[df.materias_con_registro == 0, c] = np.nan

    # --- perfil: nómina del MISMO cuatrimestre (se carga al inicio, antes del corte) ---
    laborales = ["planta", "turno_laboral", "departamento", "convenio", "empresa"]
    df = df.merge(nomina[["dni", "anio", "cuatri"] + laborales].drop_duplicates(["dni", "anio", "cuatri"]),
                  on=["dni", "anio", "cuatri"], how="left")
    # Sexo y fecha de nacimiento no cambian con el tiempo: se toman de cualquier nómina disponible
    fijos = nomina.dropna(subset=["fecha_nac"]).drop_duplicates("dni")[["dni", "sexo", "fecha_nac"]]
    df = df.merge(fijos, on="dni", how="left")
    inicio_cuatri = df.apply(lambda r: pd.Timestamp(CALENDARIO[(r.anio, r.cuatri)]["inicio"]), axis=1)
    edad = (inicio_cuatri - pd.to_datetime(df.fecha_nac)).dt.days / 365.25
    df["rango_edad"] = edad.apply(rango_edad)
    df = categorizar(df)

    # --- variable objetivo ---
    sit = df.situacion.fillna("")
    df["acredita"] = np.select([sit.str.contains("PROMUEVE|EGRESAD"), sit.str.match(r"^NIVEL \d$")],
                               [1, 0], -1).astype(float)
    df.loc[df.acredita == -1, "acredita"] = np.nan
    df["no_acredita"] = 1 - df.acredita            # clase de interés para el modelo (1 = no acredita)

    # --- reglas de exclusión ---
    df["motivo_exclusion"] = ""
    dup = df.duplicated(["dni", "anio", "cuatri"], keep=False)
    reasignado = dup & (df.groupby(["dni", "anio", "cuatri"]).nivel.transform("max") != df.nivel)
    df.loc[reasignado, "motivo_exclusion"] = "reasignado de nivel por equivalencias"
    df.loc[(df.motivo_exclusion == "") & ~df.inicio, "motivo_exclusion"] = "no inició (sin asistencia hasta el corte)"
    df.loc[(df.motivo_exclusion == "") & df.baja_avisada_antes_corte, "motivo_exclusion"] = "baja avisada antes del corte"
    en_curso = df.apply(lambda r: pd.Timestamp(CALENDARIO[(r.anio, r.cuatri)]["cierre"]) > pd.Timestamp.today(), axis=1)
    df.loc[(df.motivo_exclusion == "") & df.acredita.isna() & en_curso, "motivo_exclusion"] = "en curso (sin resultado todavía)"
    df.loc[(df.motivo_exclusion == "") & df.acredita.isna(), "motivo_exclusion"] = "situación no estándar (revisar a mano)"
    df["empezo_despues_del_corte"] = ~df.inicio & df.presente_alguna_vez

    df.to_csv(salida / "interim" / "registros_con_dni.csv", index=False, encoding="utf-8-sig")
    sin_emp = notas[notas.dni.isna()][["anio", "cuatri", "nivel", "materia", "archivo", "nombre_notas",
                                       "tps_entregados", "nota_1p"]]
    sin_emp.to_csv(salida / "interim" / "notas_sin_emparejar.csv", index=False, encoding="utf-8-sig")

    # --- seudonimización: DNI -> código ---
    orden = np.random.default_rng(2026).permutation(sorted(df.dni.unique()))   # orden aleatorio pero fijo
    codigos = {d: f"E{i:03d}" for i, d in enumerate(orden, 1)}
    columnas = ["id_estudiante", "anio", "cuatri", "nivel", "grupo", "rango_edad", "sexo",
                "empresa_grupo", "sector", "turno_laboral", "lugar_trabajo", "convenio_uom",
                "clases_dictadas_corte", "pct_asistencia", "pct_asist_electronica", "pct_asist_general",
                "pct_ausente_sin_aviso", "pct_ausente_con_aviso", "licencias_medicas",
                "presente_turno_contrario", "materias_sin_registro", "pct_tps_entregados", "promedio_tps",
                "promedio_1p", "materias_1p_menor6", "materias_sin_1p",
                "situacion", "acredita", "no_acredita", "motivo_exclusion"]
    real = df.assign(id_estudiante=df.dni.map(codigos))[columnas]
    real.to_csv(salida / "processed" / "dataset_real.csv", index=False, encoding="utf-8-sig")

    # --- dataset sintético: SOLO para probar que el código funciona ---
    # Cada variable se mezcla por separado dentro de cada clase y cada fila recibe un id distinto,
    # por lo que NO conserva trayectorias de una misma persona ni las relaciones entre variables.
    # No sirve para sacar conclusiones ni para reproducir la separación por estudiante.
    rng = np.random.default_rng(42)
    partes = []
    fijas = {"id_estudiante", "anio", "cuatri", "nivel", "situacion", "acredita", "no_acredita", "motivo_exclusion"}
    for clase, g in real.groupby(real.acredita.fillna(-1)):
        s = g.sample(len(g), replace=True, random_state=1).reset_index(drop=True)
        for c in [c for c in columnas if c not in fijas]:
            s[c] = rng.permutation(s[c].values)
        for c in ["pct_asistencia", "pct_asist_electronica", "pct_asist_general",
                  "pct_ausente_sin_aviso", "pct_ausente_con_aviso", "pct_tps_entregados"]:
            s[c] = (s[c] + rng.normal(0, 0.05, len(s))).clip(0, 1).round(2)
        for c in ["promedio_tps", "promedio_1p"]:
            s[c] = (s[c] + rng.normal(0, 0.5, len(s))).clip(1, 10).round(1)
        partes.append(s)
    sint = pd.concat(partes).sample(frac=1, random_state=7).reset_index(drop=True)
    sint["id_estudiante"] = [f"S{i:03d}" for i in range(1, len(sint) + 1)]
    sint.to_csv(salida / "processed" / "dataset_sintetico.csv", index=False, encoding="utf-8-sig")

    # --- reporte de conteos ---
    modelo = real[real.motivo_exclusion == ""]
    lineas = [
        "RESUMEN DEL DATASET (2025-2026)",
        f"Registros estudiante-nivel totales: {len(real)}",
        f"Estudiantes únicos: {real.id_estudiante.nunique()}",
        "", "Exclusiones:", real.motivo_exclusion.replace("", "(incluido en el modelo)").value_counts().to_string(),
        f"(de los que no iniciaron antes del corte, {int(df.empezo_despues_del_corte.sum())} empezaron a asistir después)",
        "", f"Registros para el modelo: {len(modelo)}  |  estudiantes únicos: {modelo.id_estudiante.nunique()}",
        "Distribución de la variable objetivo (no_acredita: 1 = no acredita):",
        modelo.no_acredita.value_counts().sort_index().to_string(),
        "", "Por cuatrimestre y nivel:",
        modelo.groupby(["anio", "cuatri", "nivel"]).no_acredita.agg(["count", "sum"]).rename(
            columns={"count": "registros", "sum": "no_acreditan"}).to_string(),
        "", "Materias sin registro de notas (planilla ausente o nombre no emparejado), en el modelo:",
        modelo.materias_sin_registro.value_counts().sort_index().to_string(),
        f"Filas de notas sin emparejar con la asistencia: {len(sin_emp)} (ver notas_sin_emparejar.csv;"
        " incluye inscriptos que figuran en las listas de notas pero no cursaron)",
        "", "Valores faltantes por variable (en el modelo):",
        modelo.isna().sum()[lambda s: s > 0].to_string(),
    ]
    (reportes / "resumen_dataset.txt").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw",
         sys.argv[2] if len(sys.argv) > 2 else "data")
