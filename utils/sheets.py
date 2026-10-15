# utils/sheets.py
import datetime
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
from config import GOOGLE_SCOPES
import gspread
import streamlit as st

# ID exclusivo para las demás unidades
SHEET_ID_OTRAS_UNIDADES = "1-1_BSmgN9QPnO5saVT-qQysSBm9NYMyqaMJXYRRD_Do"

FILA_INICIAL = 14
FILAS_POR_REGISTRO = 2


@st.cache_resource
def obtener_cliente_gspread():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "gpex" in st.secrets:
        creds_dict = dict(st.secrets["gpex"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        valor = st.secrets[primera_llave]
        creds_dict = dict(valor) if hasattr(valor, "keys") else json.loads(valor)

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)


def obtener_token_acceso():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "gpex" in st.secrets:
        creds_dict = dict(st.secrets["gpex"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        valor = st.secrets[primera_llave]
        creds_dict = dict(valor) if hasattr(valor, "keys") else json.loads(valor)

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def _txt(v):
    return "" if v is None else str(v).strip()


def _up(v):
    return _txt(v).upper()


def _x(cond):
    return "X" if cond else ""


def _es_si(v):
    return str(v).strip().upper() in ("TRUE", "1", "SÍ", "SI", "S", "X")


def _nombre_hoja(sigla, tipo_jornada, fecha_app):
    tipo = "INTRA" if tipo_jornada == "I" else "EXTRA"
    return f"{sigla}_{tipo}_{fecha_app.strftime('%d%m%y')}"


def _obtener_o_crear_hoja(spreadsheet, sigla, tipo_jornada, fecha_app):
    nombre_ideal = _nombre_hoja(sigla, tipo_jornada, fecha_app)
    tipo = "INTRA" if tipo_jornada == "I" else "EXTRA"
    fecha_str = fecha_app.strftime("%d%m%y")

    for h in spreadsheet.worksheets():
        t = h.title.upper()
        if t == nombre_ideal.upper():
            return h

    for h in spreadsheet.worksheets():
        t = h.title.upper()
        if sigla.upper() in t and tipo in t and fecha_str in t:
            return h

    for plantilla in ["NOMINAL", "CENSO NOMINAL", "CENSO"]:
        try:
            base = spreadsheet.worksheet(plantilla)
            spreadsheet.duplicate_sheet(
                source_sheet_id=base.id,
                insert_sheet_index=0,
                new_sheet_name=nombre_ideal,
            )
            return spreadsheet.worksheet(nombre_ideal)
        except Exception:
            continue

    return spreadsheet.add_worksheet(title=nombre_ideal, rows=300, cols=60)


def _siguiente_fila_libre(worksheet):
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
    token = obtener_token_acceso()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID_OTRAS_UNIDADES}/values:batchUpdate"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = [
        {"range": f"'{nombre_hoja}'!{ref}", "values": [[valor]]}
        for ref, valor in celdas
    ]
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        raise Exception(resp.text)


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


def _celdas_nominal(p, folio, consecutivo, fila, fecha_app):
    d = _datos_comunes(p, fecha_app)
    com = d["com"]
    f1 = fila
    f2 = fila + 1

    paterno = _up(p.get("paterno", ""))
    materno = _up(p.get("materno", ""))
    c_val = materno
    d_val = paterno

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


def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_OTRAS_UNIDADES)

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

    return folio, False, None


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
        nombre_unidad_completo=st.session_state.get("nombre_unidad", "20 DE NOVIEMBRE"),
        datos_paciente=datos_paciente,
    )
