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

Genera:
    data/interim/registros_con_dni.csv      -> PRIVADO (tiene DNI). No se sube.
    data/interim/nombres_sin_emparejar.csv  -> PRIVADO. Para revisar a mano.
    data/processed/dataset_real.csv         -> PRIVADO (seudonimizado). No se sube.
    data/processed/dataset_sintetico.csv    -> PÚBLICO. Se sube al repositorio.
    reports/resumen_dataset.txt             -> conteos para la entrega.
"""

import re
import sys
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import openpyxl

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN: calendario de cada cuatrimestre (planilla FECHAS.xlsx)
# ---------------------------------------------------------------------------
# corte = 1° cierre de notas parcial -> MOMENTO DE PREDICCIÓN
CALENDARIO = {
    (2025, 1): dict(inicio="2025-05-08", corte="2025-06-02", cierre="2025-07-11", niveles=[1, 3]),
    (2025, 2): dict(inicio="2025-08-07", corte="2025-09-19", cierre="2025-11-14", niveles=[2, 4]),
    (2026, 1): dict(inicio="2026-04-23", corte="2026-05-18", cierre="2026-07-03", niveles=[3]),
    (2026, 2): dict(inicio="2026-08-12", corte="2026-09-25", cierre="2026-11-27", niveles=[4]),
}

# Archivo de asistencia de cada cuatrimestre (dentro de la carpeta ASISTENCIA)
ARCHIVOS_ASISTENCIA = {
    (2025, 1): "ASISTENCIA - 2025 - 1er semestre.xlsx",
    (2025, 2): "ASISTENCIA - 2025 - 2do semestre.xlsx",
    (2026, 1): "ASISTENCIA - 2026 - 1er semestre.xlsx",
    (2026, 2): "ASISTENCIA - 2026 - 2do semestre.xlsx",
}

# Materia según el nombre del archivo de calificaciones
MATERIAS = {
    "NATURALES": "naturales", "SOCIALES": "sociales", "ELECTR": "electronica",
    "INGL": "ingles", "MATEM": "matematica", "LENGUAJE": "lengua",
}

# Códigos de asistencia (acordados con la coordinación)
PRESENTE = {"PE", "PG", "PV", "PGTM", "PGTT", "PETM", "PETT"}
AUSENTE_SIN_AVISO = {"AE", "AG"}
AUSENTE_CON_AVISO = {"C/A", "C/A TRABAJANDO"}
LICENCIA = {"L/M"}
SIN_CLASE = {"S/C", ""}
BAJA = {"-", "--"}

PLANTA_CURSADO = 4


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
    c = texto(v).upper().replace(" ", "")
    c = c.replace("C/ATRABAJANDO", "C/A").replace(".", "")
    if c.startswith(("PGT", "PET")):
        return "PGTM"            # presente en el turno contrario
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


# ---------------------------------------------------------------------------
# 2. ASISTENCIA + SITUACIÓN (resultado) desde las hojas "NIVEL X"
# ---------------------------------------------------------------------------
def leer_hoja_nivel(ws, anio, cuatri, nivel, cal):
    corte = pd.Timestamp(cal["corte"]).date()
    filas = list(ws.iter_rows(values_only=True))
    registros, fechas, grupo = [], None, None
    col_sit = None
    for fila in filas:
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
        cods = [(fechas[j], codigo(fila[j])) for j in sorted(fechas) if j < len(fila)]
        antes = [c for d, c in cods if d <= corte]
        todo = [c for d, c in cods]

        dictadas = [c for c in antes if c not in SIN_CLASE and c not in BAJA]
        pres = sum(c in PRESENTE for c in dictadas)
        lm = sum(c in LICENCIA for c in dictadas)
        base = max(len(dictadas) - lm, 0)
        pres_e = sum(c in ("PE",) for c in dictadas)
        pres_g = sum(c in ("PG", "PV", "PGTM") for c in dictadas)
        aus_e = sum(c == "AE" for c in dictadas)
        aus_g = sum(c == "AG" for c in dictadas)

        # baja avisada: a partir de cierta clase todo es "-"/"--"
        baja_antes_corte = bool(antes) and all(c in BAJA for c in antes[-3:]) and \
            sum(c in PRESENTE for c in antes) < len(antes)
        sit = texto(fila[col_sit]).upper() if col_sit < len(fila) else ""

        registros.append(dict(
            dni=dni, anio=anio, cuatri=cuatri, nivel=nivel, grupo=grupo,
            apellido=texto(fila[2]), nombre=texto(fila[3]),
            clases_dictadas_corte=len(dictadas),
            pct_asistencia=pres / base if base else np.nan,
            pct_asist_electronica=pres_e / (pres_e + aus_e) if pres_e + aus_e else np.nan,
            pct_asist_general=pres_g / (pres_g + aus_g) if pres_g + aus_g else np.nan,
            pct_ausente_sin_aviso=sum(c in AUSENTE_SIN_AVISO for c in dictadas) / base if base else np.nan,
            pct_ausente_con_aviso=sum(c in AUSENTE_CON_AVISO for c in dictadas) / base if base else np.nan,
            licencias_medicas=lm,
            presente_turno_contrario=sum(c == "PGTM" for c in dictadas),
            inicio=pres > 0,
            presente_alguna_vez=any(c in PRESENTE for c in todo),
            baja_avisada_antes_corte=baja_antes_corte,
            situacion=sit,
        ))
    return registros


def leer_nomina(ws):
    filas = list(ws.iter_rows(values_only=True))
    h = [texto(v) for v in filas[1]]
    idx = {}
    for nombre in ["DNI", "FECHA DE NACIMIENTO", "SEXO", "PLANTA", "TURNO",
                   "DEPARTAMENTO", "CONVENIO", "EMPRESA"]:
        if nombre in h:
            idx[nombre] = h.index(nombre)       # primera aparición = datos laborales
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
# 3. CALIFICACIONES (solo TPs y 1° nota parcial = info hasta el corte)
# ---------------------------------------------------------------------------
def es_1p(x):
    return bool(re.fullmatch(r"1\s*°?\s*(NP|NOTA PARCIAL)", x.upper()))


def leer_calificaciones(raw):
    regs = []
    for archivo in sorted((raw / "CALIFICACIONES").rglob("*.xlsx")):
        anio = int(re.search(r"20\d\d", archivo.parent.name + archivo.name).group())
        if anio not in (2025, 2026):
            continue
        materia = next((v for k, v in MATERIAS.items() if k in archivo.name.upper()), None)
        wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
        for ws in wb.worksheets:
            m = re.search(r"(?:NIVEL\s*|N)(\d)", ws.title.upper())
            if not m:
                continue
            nivel = int(m.group(1))
            cuatri = next((c for (a, c), cal in CALENDARIO.items()
                           if a == anio and nivel in cal["niveles"]), None)
            if cuatri is None:
                continue
            col_1p, cols_tp, col_nombre = None, [], None
            for fila in ws.iter_rows(values_only=True):
                t = [texto(v) for v in fila]
                if any(es_1p(x) for x in t):                 # encabezado
                    col_1p = next(j for j, x in enumerate(t) if es_1p(x))
                    primero = next(j for j, x in enumerate(t) if j < col_1p and x)
                    col_nombre = primero if "APELLIDO" in t[primero].upper() else None
                    tp_ini = next(j for j, x in enumerate(t) if j < col_1p and re.match(r"TP|PLATAF|1° ?TP|TPMAGN", x.upper()))
                    cols_tp = [j for j in range(tp_ini, col_1p) if t[j].upper() != "N/C" and t[j]]
                    continue
                if col_1p is None:
                    continue
                if col_nombre is not None:                   # 2025: "APELLIDO Y NOMBRE"
                    nombre = t[col_nombre] if col_nombre < len(t) else ""
                else:                                        # 2026: APELLIDO | NOMBRE
                    nombre = f"{t[0]} {t[1]}"
                if (len(normalizar(nombre)) < 2 or re.search(r"TURNO|DE \d|RECUPER|DEBER|APELLIDO", nombre.upper())
                        or len(nombre) > 45):
                    continue
                vals = [fila[j] if j < len(fila) else None for j in cols_tp]
                nota1p = fila[col_1p] if col_1p < len(fila) else None
                if all(texto(v) == "" for v in vals + [nota1p]):
                    continue
                entregados = [float(v) for v in vals if isinstance(v, (int, float)) and v >= 2]
                regs.append(dict(
                    anio=anio, cuatri=cuatri, nivel=nivel, materia=materia, nombre_notas=nombre,
                    tps_previstos=len(cols_tp), tps_entregados=len(entregados),
                    suma_notas_tp=sum(entregados),
                    nota_1p=float(nota1p) if isinstance(nota1p, (int, float)) and nota1p >= 2 else np.nan,
                ))
    return pd.DataFrame(regs)


def emparejar_nombres(notas, asis):
    """Asigna el DNI a cada fila de notas comparando el nombre con la asistencia."""
    dnis, sin = [], []
    for _, r in notas.iterrows():
        cand = asis[(asis.anio == r.anio) & (asis.cuatri == r.cuatri) & (asis.nivel == r.nivel)]
        a = set(normalizar(r.nombre_notas))
        mejor, puntaje, segundo = None, 0, 0
        for _, c in cand.iterrows():
            b = set(normalizar(f"{c.apellido} {c.nombre}"))
            p = len(a & b) / max(len(a | b), 1)
            if p > puntaje:
                mejor, segundo, puntaje = c.dni, puntaje, p
            elif p > segundo:
                segundo = p
        if puntaje >= 0.5 and puntaje > segundo:
            dnis.append(mejor)
        else:
            dnis.append(None)
            sin.append(dict(anio=r.anio, cuatri=r.cuatri, nivel=r.nivel,
                            materia=r.materia, nombre_en_notas=r.nombre_notas))
    notas = notas.assign(dni=dnis)
    return notas, pd.DataFrame(sin).drop_duplicates()


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
    df["convenio_uom"] = df.convenio.fillna("").str.contains("U.O.M", regex=False).astype(int)
    return df


def main(raw, salida):
    raw, salida = Path(raw), Path(salida)
    for sub in ["interim", "processed"]:
        (salida / sub).mkdir(parents=True, exist_ok=True)
    reportes = salida.parent / "reports"
    reportes.mkdir(exist_ok=True)

    asis, nomina = leer_asistencia(raw)
    notas, sin_emparejar = emparejar_nombres(leer_calificaciones(raw), asis)

    # --- notas agregadas por estudiante-nivel ---
    n = notas.dropna(subset=["dni"])
    # si un estudiante aparece dos veces en la misma materia (p. ej. en las dos planillas de
    # Electrónica por turno), se conserva la fila con más información
    n = (n.sort_values(["tps_entregados", "nota_1p"], ascending=False, na_position="last")
          .drop_duplicates(["dni", "anio", "cuatri", "nivel", "materia"]))
    agg = n.groupby(["dni", "anio", "cuatri", "nivel"]).agg(
        tps_previstos=("tps_previstos", "sum"), tps_entregados=("tps_entregados", "sum"),
        suma_notas_tp=("suma_notas_tp", "sum"), promedio_1p=("nota_1p", "mean"),
        materias_con_nota=("materia", "nunique"),
        materias_1p_menor6=("nota_1p", lambda s: int((s < 6).sum())),
        materias_sin_1p=("nota_1p", lambda s: int(s.isna().sum())),
    ).reset_index()
    agg["pct_tps_entregados"] = agg.tps_entregados / agg.tps_previstos.replace(0, np.nan)
    agg["promedio_tps"] = agg.suma_notas_tp / agg.tps_entregados.replace(0, np.nan)

    df = asis.merge(agg, on=["dni", "anio", "cuatri", "nivel"], how="left")
    df["materias_sin_1p"] = df.materias_sin_1p.fillna(0) + (6 - df.materias_con_nota.fillna(0)).clip(lower=0)

    # --- perfil desde la nómina (el dato más reciente de cada DNI) ---
    perfil = nomina.sort_values(["anio", "cuatri"]).groupby("dni").last().reset_index()
    df = df.merge(perfil.drop(columns=["anio", "cuatri"]), on="dni", how="left")
    inicio_cuatri = df.apply(lambda r: pd.Timestamp(CALENDARIO[(r.anio, r.cuatri)]["inicio"]), axis=1)
    edad = (inicio_cuatri - pd.to_datetime(df.fecha_nac)).dt.days / 365.25
    df["rango_edad"] = edad.apply(rango_edad)
    df = categorizar(df)

    # --- variable objetivo ---
    sit = df.situacion.fillna("")
    df["acredita"] = np.select([sit.str.contains("PROMUEVE|EGRESAD"), sit.str.match(r"^NIVEL \d$")],
                               [1, 0], -1)
    df.loc[df.acredita == -1, "acredita"] = np.nan

    # --- reglas de exclusión (cada una queda documentada en el reporte) ---
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
    sin_emparejar.to_csv(salida / "interim" / "nombres_sin_emparejar.csv", index=False, encoding="utf-8-sig")

    # --- seudonimización: DNI -> código ---
    orden = np.random.default_rng(2026).permutation(sorted(df.dni.unique()))   # orden aleatorio pero fijo
    codigos = {d: f"E{i:03d}" for i, d in enumerate(orden, 1)}
    columnas = ["id_estudiante", "anio", "cuatri", "nivel", "grupo", "rango_edad", "sexo",
                "empresa_grupo", "sector", "turno_laboral", "lugar_trabajo", "convenio_uom",
                "clases_dictadas_corte", "pct_asistencia", "pct_asist_electronica", "pct_asist_general",
                "pct_ausente_sin_aviso", "pct_ausente_con_aviso", "licencias_medicas",
                "presente_turno_contrario", "pct_tps_entregados", "promedio_tps", "promedio_1p",
                "materias_1p_menor6", "materias_sin_1p", "situacion", "acredita", "motivo_exclusion"]
    real = df.assign(id_estudiante=df.dni.map(codigos))[columnas]
    real.to_csv(salida / "processed" / "dataset_real.csv", index=False, encoding="utf-8-sig")

    # --- dataset sintético (misma estructura, ninguna fila es una persona real) ---
    rng = np.random.default_rng(42)
    partes = []
    for clase, g in real.groupby(real.acredita.fillna(-1)):
        s = g.sample(len(g), replace=True, random_state=1).reset_index(drop=True)
        fijas = {"id_estudiante", "anio", "cuatri", "nivel", "situacion", "acredita", "motivo_exclusion"}
        for c in [c for c in columnas if c not in fijas]:   # se mezcla cada variable por separado
            s[c] = rng.permutation(s[c].values)
        for c in ["pct_asistencia", "pct_asist_electronica", "pct_asist_general",
                  "pct_ausente_sin_aviso", "pct_ausente_con_aviso", "pct_tps_entregados"]:
            s[c] = (s[c] + rng.normal(0, 0.05, len(s))).clip(0, 1).round(2)
        for c in ["promedio_tps", "promedio_1p"]:
            s[c] = (s[c] + rng.normal(0, 0.5, len(s))).clip(1, 10).round(1)
        s["acredita"] = np.nan if clase == -1 else clase
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
        "", f"Registros para el modelo: {len(modelo)}  |  estudiantes únicos: {modelo.id_estudiante.nunique()}",
        "Distribución de la variable objetivo (1 = acredita):",
        modelo.acredita.value_counts().sort_index().to_string(),
        "", "Por cuatrimestre y nivel:",
        modelo.groupby(["anio", "cuatri", "nivel"]).acredita.agg(["count", "sum"]).rename(
            columns={"count": "registros", "sum": "acreditan"}).to_string(),
        f"(de los que no iniciaron antes del corte, {int(df.empezo_despues_del_corte.sum())} empezaron a asistir después)",
        "", f"Filas de notas sin emparejar con asistencia: {len(sin_emparejar)} (ver nombres_sin_emparejar.csv)",
        "", "Valores faltantes por variable (en el modelo):",
        modelo.isna().sum()[lambda s: s > 0].to_string(),
    ]
    (reportes / "resumen_dataset.txt").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw",
         sys.argv[2] if len(sys.argv) > 2 else "data")
