# utils/sheets_20_nov.py
import datetime
import json
from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import gspread
import streamlit as st
from config import GOOGLE_SCOPES

SHEET_ID_20N = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
FILA_INICIAL = 14
FILAS_POR_REGISTRO = 2

# En NOMINAL: True -> C = Materno, D = Paterno
#             False -> C = Paterno, D = Materno
NOMINAL_APELLIDOS_INVERTIDOS = True


# ----------------------------------------------------------------------
# Autenticación
# ----------------------------------------------------------------------
def _credenciales_dict():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw = st.secrets["GOOGLE_CREDENTIALS"]
        creds = json.loads(raw) if isinstance(raw, str) else dict(raw)
    elif "gcp_service_account" in st.secrets:
        creds = dict(st.secrets["gcp_service_account"])
    elif "gpex" in st.secrets:
        creds = dict(st.secrets["gpex"])
    else:
        primera = list(st.secrets.keys())[0]
        valor = st.secrets[primera]
        creds = dict(valor) if hasattr(valor, "keys") else json.loads(valor)

    if "private_key" in creds and isinstance(creds["private_key"], str):
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    return creds


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread utilizando los secretos del proyecto."""
    return gspread.service_account_from_dict(_credenciales_dict(), scopes=GOOGLE_SCOPES)


def obtener_token_acceso():
    creds = service_account.Credentials.from_service_account_info(
        _credenciales_dict(), scopes=GOOGLE_SCOPES
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _txt(v):
    return "" if v is None else str(v).strip()


def _up(v):
    return _txt(v).upper()


def _x(cond):
    return "X" if cond else ""


def _es_si(v):
    return str(v).strip().upper() in ("TRUE", "1", "SÍ", "SI", "S", "X")


def _nombre_hoja(sigla, tipo_jornada, fecha_app, sufijo):
    tipo = "INTRA" if tipo_jornada == "I" else "EXTRA"
    return f"{sigla}_{tipo}_{fecha_app.strftime('%d%m%y')}_{sufijo}"


def _obtener_o_crear_hoja(spreadsheet, sigla, tipo_jornada, fecha_app, sufijo):
    """Busca la pestaña SIGLA_[INTRA|EXTRA]_DDMMAA_[sufijo]; si no existe, duplica
    la plantilla 'NOMINAL' o 'CENSO' según corresponda."""
    nombre_ideal = _nombre_hoja(sigla, tipo_jornada, fecha_app, sufijo)
    tipo = "INTRA" if tipo_jornada == "I" else "EXTRA"
    fecha_str = fecha_app.strftime("%d%m%y")

    hojas = spreadsheet.worksheets()
    for h in hojas:
        t = h.title.upper()
        if (sigla.upper() in t and fecha_str in t and tipo in t and t.endswith(sufijo.upper())):
            return h

    for h in hojas:
        if h.title == nombre_ideal:
            return h

    plantilla = None
    for h in hojas:
        if h.title.strip().upper() == sufijo.upper():
            plantilla = h
            break

    if plantilla is not None:
        spreadsheet.duplicate_sheet(
            source_sheet_id=plantilla.id,
            insert_sheet_index=0,
            new_sheet_name=nombre_ideal,
        )
        return spreadsheet.worksheet(nombre_ideal)

    return spreadsheet.add_worksheet(title=nombre_ideal, rows=300, cols=60)


def _siguiente_fila_libre(worksheet):
    """Primera fila libre (14, 16, 18...) revisando la columna B de 2 en 2.
    Libre = vacía o 'POR ASIGNAR'."""
    col_b = worksheet.col_values(2)
    idx = FILA_INICIAL - 1
    while idx < len(col_b):
        v = _txt(col_b[idx])
        if v == "" or "POR ASIGNAR" in v.upper():
            return idx + 1
        idx += FILAS_POR_REGISTRO
    fila = max(FILA_INICIAL, len(col_b) + 1)
    if (fila - FILA_INICIAL) % FILAS_POR_REGISTRO != 0:
        fila += 1
    return fila


def _consecutivo(fila):
    return ((fila - FILA_INICIAL) // FILAS_POR_REGISTRO) + 1


def _escribir_celdas(nombre_hoja, celdas):
    """celdas: lista de (referencia_A1_sin_hoja, valor). Una sola llamada batchUpdate."""
    token = obtener_token_acceso()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID_20N}/values:batchUpdate"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = [
        {"range": f"'{nombre_hoja}'!{ref}", "values": [[valor]]}
        for ref, valor in celdas
    ]
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        raise Exception(resp.text)


# ----------------------------------------------------------------------
# Datos comunes del paciente
# ----------------------------------------------------------------------
def _datos_comunes(p, fecha_app):
    com = p.get("comorbilidades", {}) or {}
    fn = p.get("fecha_nacimiento")
    ocupacion = _up(p.get("ocupacion", ""))

    personal_salud = (
        _es_si(com.get("personal_salud_riesgo", False))
        or _es_si(p.get("personal_salud", "NO"))
        or "PERSONAL DE SALUD" in ocupacion
    )
    embarazo = _es_si(com.get("personas_embarazadas", False)) or _es_si(p.get("embarazo", "NO"))

    grupo = _up(p.get("grupo_sugerido", ""))
    meses_totales = int(p.get("calc_anos", 0) or 0) * 12 + int(p.get("calc_meses", 0) or 0)
    if "6 A 59" in grupo:
        g_6_59, g_60 = True, False
    elif "60" in grupo:
        g_6_59, g_60 = False, True
    else:
        g_6_59 = 6 <= meses_totales < 60
        g_60 = meses_totales >= 60

    vacuna = _up(p.get("vacuna_interes", ""))

    return {
        "com": com,
        "fn_dia": str(fn.day).zfill(2) if fn else "",
        "fn_mes": str(fn.month).zfill(2) if fn else "",
        "fn_anio": str(fn.year) if fn else "",
        "anos": str(p.get("calc_anos", 0)),
        "meses": str(p.get("calc_meses", 0)),
        "personal_salud": personal_salud,
        "embarazo": embarazo,
        "g_6_59": g_6_59,
        "g_60": g_60,
        "vacuna": vacuna,
        "fecha_app_str": fecha_app.strftime("%d/%m/%Y"),
        "fecha_registro_str": datetime.date.today().strftime("%d/%m/%Y"),
    }


# ----------------------------------------------------------------------
# Mapeo NOMINAL
# ----------------------------------------------------------------------
def _celdas_nominal(p, folio, consecutivo, fila, fecha_app):
    d = _datos_comunes(p, fecha_app)
    com = d["com"]
    f1 = fila
    f2 = fila + 1

    paterno = _up(p.get("paterno", ""))
    materno = _up(p.get("materno", ""))
    c_val, d_val = (materno, paterno) if NOMINAL_APELLIDOS_INVERTIDOS else (paterno, materno)

    ant_inf = _up(p.get("antecedente_influenza", ""))
    ant_cov = _up(p.get("antecedente_covid", ""))
    vacuna = d["vacuna"]

    def r(k):
        return _es_si(com.get(k, False))

    celdas = [
        (f"A{f1}", str(consecutivo)),
        (f"B{f1}", folio),
        (f"C{f1}", c_val),
        (f"D{f1}", d_val),
        (f"E{f1}", _up(p.get("nombres", ""))),
        (f"C{f2}", _up(p.get("curp_con_nacimiento", ""))),
        (f"F{f1}", d["fn_dia"]),
        (f"G{f1}", d["fn_mes"]),
        (f"H{f1}", d["fn_anio"]),
        (f"I{f1}", d["anos"]),
        (f"J{f1}", d["meses"]),
        (f"K{f1}", _txt(p.get("sexo", ""))),
        (f"L{f1}", d["fecha_app_str"]),
        (f"M{f1}", _up(p.get("calle", ""))),
        (f"N{f1}", _up(p.get("numero", ""))),
        (f"O{f1}", _up(p.get("colonia", ""))),
        (f"P{f1}", _x(d["g_6_59"])),
        (f"Q{f1}", _x(d["g_60"])),
        (f"R{f1}", _x(d["embarazo"])),
        (f"S{f1}", _x(d["personal_salud"])),
        (f"T{f1}", _x(r("vih"))),
        (f"U{f1}", _x(r("diabetes"))),
        (f"V{f1}", _x(r("obesidad"))),
        (f"W{f1}", _x(r("cardiopatias"))),
        (f"X{f1}", _x(r("enfermedad_pulmonar"))),
        (f"Y{f1}", _x(r("cancer"))),
        (f"Z{f1}", _x(r("cardiacas_congenitas"))),
        (f"AA{f1}", _x(r("insuficiencia_renal"))),
        (f"AB{f1}", _x(r("inmunosupresion"))),
        (f"AC{f1}", _x(r("discapacidades"))),
        (f"AD{f1}", _x(r("fibrosis_quistica"))),
        (f"AE{f1}", _x(r("hipertension"))),
        (f"AF{f1}", _up(com.get("texto_otro", "")) if r("otro") else ""),
        (f"AQ{f1}", _up(p.get("cuenta_derechohabiencia", ""))),
        (f"AR{f1}", ant_inf),
        (f"AS{f1}", ant_cov),
        (f"AT{f1}", _x(vacuna == "INFLUENZA")),
        (f"AU{f1}", _x(vacuna in ("COVID-19", "COVID"))),
        (f"AV{f1}", _x(vacuna == "AMBAS")),
        (f"AW{f1}", d["fecha_registro_str"]),
        (f"AX{f1}", _txt(p.get("correo_paciente", ""))),
    ]
    return celdas


# ----------------------------------------------------------------------
# Mapeo CENSO
# ----------------------------------------------------------------------
def _celdas_censo(p, folio, consecutivo, fila, fecha_app):
    d = _datos_comunes(p, fecha_app)
    f1 = fila

    tipo_dh = _up(p.get("tipo_dh", ""))
    if tipo_dh in ("", "NO APLICA", "SELECCIONE"):
        tipo_dh = ""

    celdas = [
        (f"A{f1}", str(consecutivo)),
        (f"B{f1}", folio),
        (f"C{f1}", _up(p.get("rfc", ""))),
        (f"D{f1}", _up(p.get("cuenta_derechohabiencia", ""))),
        (f"E{f1}", tipo_dh),
        (f"F{f1}", _up(p.get("trabaja_cmn", "")) if p.get("trabaja_cmn") else "NO"),
        (f"G{f1}", _up(p.get("num_trabajador", ""))),
        (f"H{f1}", "SÍ" if d["personal_salud"] else "NO"),
        (f"I{f1}", _up(p.get("categoria", "")) if _up(p.get("categoria", "")) not in ("NO APLICA", "SELECCIONE") else ""),
        (f"J{f1}", _up(p.get("servicio", "")) if _up(p.get("servicio", "")) not in ("NO APLICA", "SELECCIONE") else ""),
        (f"K{f1}", _up(p.get("coordinacion", "")) if _up(p.get("coordinacion", "")) not in ("NO APLICA", "SELECCIONE") else ""),
        (f"L{f1}", _up(p.get("turno", "")) if _up(p.get("turno", "")) not in ("NO APLICA", "SELECCIONE") else ""),
        (f"M{f1}", _up(p.get("nombres", ""))),
        (f"N{f1}", _up(p.get("paterno", ""))),
        (f"O{f1}", _up(p.get("materno", ""))),
        (f"P{f1}", _up(p.get("estado_nacimiento", ""))),
        (f"Q{f1}", _up(p.get("muni_nac", ""))),
        (f"R{f1}", d["fn_dia"]),
        (f"S{f1}", d["fn_mes"]),
        (f"T{f1}", d["fn_anio"]),
        (f"U{f1}", d["anos"]),
        (f"V{f1}", d["meses"]),
        (f"W{f1}", _txt(p.get("sexo", ""))),
        (f"X{f1}", "SÍ" if d["embarazo"] else "NO"),
    ]
    return celdas


# ----------------------------------------------------------------------
# Guardado
# ----------------------------------------------------------------------
def _guardar_en_hoja(spreadsheet, sigla, sufijo, tipo_jornada, fecha_app, p, folio_forzado=None):
    ws = _obtener_o_crear_hoja(spreadsheet, sigla, tipo_jornada, fecha_app, sufijo)
    fila = _siguiente_fila_libre(ws)
    consecutivo = _consecutivo(fila)

    folio = folio_forzado or f"{fecha_app.strftime('%y%m%d')}-{tipo_jornada}{sigla}-{str(consecutivo).zfill(3)}"

    if sufijo == "NOMINAL":
        celdas = _celdas_nominal(p, folio, consecutivo, fila, fecha_app)
    else:
        celdas = _celdas_censo(p, folio, consecutivo, fila, fecha_app)

    _escribir_celdas(ws.title, celdas)
    return folio


def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    """Guarda el registro en las dos hojas: ..._NOMINAL y ..._CENSO."""
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20N)

    folio = _guardar_en_hoja(spreadsheet, sigla_url, "NOMINAL", tipo_jornada, val_fecha_app, datos_paciente)
    _guardar_en_hoja(
        spreadsheet,
        sigla_url,
        "CENSO",
        tipo_jornada,
        val_fecha_app,
        datos_paciente,
        folio_forzado=folio,
    )

    st.cache_data.clear()
    if hasattr(st, "cache_resource"):
        st.cache_resource.clear()

    return folio


def guardar_registro_censal_20_nov(datos_paciente):
    val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
    tipo_jornada = datos_paciente.get("tipo_jornada", "I")
    siglas_unidad = st.session_state.get("siglas_unidad", "20N")
    sufijo_js = st.session_state.get("sufijo_js", "")

    return guardar_registro_censal(
        sigla_url=siglas_unidad,
        sufijo_js=sufijo_js,
        tipo_jornada=tipo_jornada,
        val_fecha_app=val_fecha_app,
        nombre_unidad_completo=st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE"),
        datos_paciente=datos_paciente,
    )
