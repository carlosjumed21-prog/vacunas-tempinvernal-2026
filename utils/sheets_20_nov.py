import datetime
import json
from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import gspread
import streamlit as st
from config import GOOGLE_SCOPES

SHEET_ID_20N = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"


def obtener_cliente_gspread():
    scope = GOOGLE_SCOPES
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gpex" in st.secrets:
        creds_dict = dict(st.secrets["gpex"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=scope)


def obtener_token_acceso():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def _normalizar(v):
    return "" if v is None else str(v).strip()


def _normalizar_mayus(v):
    return _normalizar(v).upper()


def _obtener_spreadsheet():
    client = obtener_cliente_gspread()
    return client.open_by_key(SHEET_ID_20N)


def _obtener_o_crear_worksheet(spreadsheet, nombre_hoja):
    try:
        return spreadsheet.worksheet(nombre_hoja)
    except Exception:
        pass

    for plantilla in ["CENSO NOMINAL", "CENSO"]:
        try:
            base = spreadsheet.worksheet(plantilla)
            spreadsheet.duplicate_sheet(
                source_sheet_id=base.id,
                insert_sheet_index=0,
                new_sheet_name=nombre_hoja,
            )
            return spreadsheet.worksheet(nombre_hoja)
        except Exception:
            continue

    return spreadsheet.add_worksheet(title=nombre_hoja, rows=200, cols=80)


def _siguiente_fila_disponible(worksheet, columna=2, fila_inicio=14):
    valores = worksheet.col_values(columna)
    idx = fila_inicio - 1

    while idx < len(valores):
        actual = _normalizar(valores[idx])
        if actual == "" or "POR ASIGNAR" in actual.upper():
            return idx + 1
        idx += 2

    fila = max(fila_inicio, len(valores) + 1)
    if (fila - fila_inicio) % 2 != 0:
        fila += 1
    return fila


def _folio_consecutivo(fila_inicio, fila_base=14):
    return ((fila_inicio - fila_base) // 2) + 1


def _marcar_x(condicion):
    return "X" if condicion else ""


def _nombre_hoja(sigla_url, tipo_jornada, fecha_app, sufijo):
    fecha_str = fecha_app.strftime("%d%m%y")
    tipo_texto = "INTRA" if tipo_jornada == "I" else "EXTRA"
    return f"{sigla_url}_{tipo_texto}_{fecha_str}_{sufijo}"


def _mapear_nominal(datos_paciente, folio):
    fecha_nacimiento = datos_paciente.get("fecha_nacimiento")
    val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())

    fn_dia = str(fecha_nacimiento.day).zfill(2) if fecha_nacimiento else ""
    fn_mes = str(fecha_nacimiento.month).zfill(2) if fecha_nacimiento else ""
    fn_anio = str(fecha_nacimiento.year) if fecha_nacimiento else ""

    edad_anos = str(datos_paciente.get("calc_anos", 0))
    edad_meses = str(datos_paciente.get("calc_meses", 0))

    grupo = _normalizar_mayus(datos_paciente.get("grupo_sugerido", ""))
    grupo_6_59 = "6 A 59" in grupo
    grupo_60 = "60 Y MÁS" in grupo or "60 Y MAS" in grupo

    com = datos_paciente.get("comorbilidades", {}) or {}
    personal_salud = str(com.get("personal_salud_riesgo", False)).lower() in ["true", "1", "sí", "si"]
    embarazo = str(com.get("personas_embarazadas", False)).lower() in ["true", "1", "sí", "si"]

    vacuna = _normalizar_mayus(datos_paciente.get("vacuna_interes", ""))
    ant_inf = _normalizar_mayus(datos_paciente.get("antecedente_influenza", ""))
    ant_cov = _normalizar_mayus(datos_paciente.get("antecedente_covid", ""))

    fila = [
        "",  # A
        folio,  # B
        _normalizar_mayus(datos_paciente.get("curp_con_nacimiento", "")),  # C
        _normalizar(datos_paciente.get("cuenta_derechohabiencia", "")),  # D
        "",  # E
        "",  # F
        "",  # G
        "SÍ" if personal_salud else "NO",  # H
        "",  # I
        "",  # J
        "",  # K
        "",  # L
        _normalizar_mayus(datos_paciente.get("nombres", "")),  # M
        _normalizar_mayus(datos_paciente.get("paterno", "")),  # N
        _normalizar_mayus(datos_paciente.get("materno", "")),  # O
        _normalizar_mayus(datos_paciente.get("estado_nacimiento", "")),  # P
        "",  # Q
        fn_dia,  # R
        fn_mes,  # S
        fn_anio,  # T
        edad_anos,  # U
        edad_meses,  # V
        _normalizar(datos_paciente.get("sexo", "")),  # W
        "SÍ" if embarazo else "NO",  # X
        "",  # Y
        "",  # Z
        "",  # AA
        "",  # AB
        "",  # AC
        "",  # AD
        "",  # AE
        "",  # AF
        "",  # AG
        "",  # AH
        "",  # AI
        "",  # AJ
        "",  # AK
        "",  # AL
        "",  # AM
        "",  # AN
        "",  # AO
        "",  # AP
        _normalizar(datos_paciente.get("cuenta_derechohabiencia", "")),  # AQ
        _marcar_x(ant_inf == "SÍ"),  # AR
        _marcar_x(ant_cov == "SÍ"),  # AS
        _marcar_x(vacuna == "INFLUENZA"),  # AT
        _marcar_x(vacuna == "COVID-19"),  # AU
        _marcar_x(vacuna == "AMBAS"),  # AV
        val_fecha_app.strftime("%d/%m/%Y"),  # AW
        _normalizar(datos_paciente.get("correo_paciente", "")),  # AX
    ]

    fila[16] = _marcar_x(grupo_6_59)  # P
    fila[17] = _marcar_x(grupo_60)    # Q

    return fila


def _mapear_censo(datos_paciente, folio):
    fecha_nacimiento = datos_paciente.get("fecha_nacimiento")

    fn_dia = str(fecha_nacimiento.day).zfill(2) if fecha_nacimiento else ""
    fn_mes = str(fecha_nacimiento.month).zfill(2) if fecha_nacimiento else ""
    fn_anio = str(fecha_nacimiento.year) if fecha_nacimiento else ""

    fila = [
        "",  # A
        folio,  # B
        _normalizar_mayus(datos_paciente.get("rfc", "")),  # C
        _normalizar(datos_paciente.get("cuenta_derechohabiencia", "")),  # D
        _normalizar(datos_paciente.get("tipo_dh", "NO APLICA")),  # E
        _normalizar(datos_paciente.get("trabaja_cmn", "NO")),  # F
        _normalizar(datos_paciente.get("num_trabajador", "")),  # G
        _normalizar(datos_paciente.get("personal_salud", "NO")),  # H
        _normalizar(datos_paciente.get("categoria", "")),  # I
        _normalizar(datos_paciente.get("servicio", "")),  # J
        _normalizar(datos_paciente.get("coordinacion", "")),  # K
        _normalizar(datos_paciente.get("turno", "")),  # L
        _normalizar_mayus(datos_paciente.get("nombres", "")),  # M
        _normalizar_mayus(datos_paciente.get("paterno", "")),  # N
        _normalizar_mayus(datos_paciente.get("materno", "")),  # O
        _normalizar_mayus(datos_paciente.get("estado_nacimiento", "")),  # P
        _normalizar_mayus(datos_paciente.get("muni_nac", "")),  # Q
        fn_dia,  # R
        fn_mes,  # S
        fn_anio,  # T
        str(datos_paciente.get("calc_anos", 0)),  # U
        str(datos_paciente.get("calc_meses", 0)),  # V
        _normalizar(datos_paciente.get("sexo", "")),  # W
        _normalizar(datos_paciente.get("embarazo", "NO")),  # X
        "",  # Y
        "",  # Z
        "",  # AA
        "",  # AB
        "",  # AC
        "",  # AD
        "",  # AE
        "",  # AF
        "",  # AG
        "",  # AH
    ]

    return fila


def _guardar_en_hoja(spreadsheet, sigla_url, sufijo, tipo_jornada, val_fecha_app, datos_paciente):
    nombre_hoja = _nombre_hoja(sigla_url, tipo_jornada, val_fecha_app, sufijo)
    worksheet = _obtener_o_crear_worksheet(spreadsheet, nombre_hoja)

    fila_inicio = _siguiente_fila_disponible(worksheet, columna=2, fila_inicio=14)
    consecutivo = _folio_consecutivo(fila_inicio, fila_base=14)
    folio = f"{val_fecha_app.strftime('%y%m%d')}-{tipo_jornada}{sigla_url}-{str(consecutivo).zfill(3)}"

    fila = _mapear_nominal(datos_paciente, folio) if sufijo == "NOMINAL" else _mapear_censo(datos_paciente, folio)
    fila[0] = str(consecutivo)

    token = obtener_token_acceso()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID_20N}/values:batchUpdate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"{worksheet.title}!A{fila_inicio}", "values": [fila]}
        ],
    }

    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise Exception(resp.text)

    return folio


def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    try:
        spreadsheet = _obtener_spreadsheet()

        folio = _guardar_en_hoja(
            spreadsheet=spreadsheet,
            sigla_url=sigla_url,
            sufijo="NOMINAL",
            tipo_jornada=tipo_jornada,
            val_fecha_app=val_fecha_app,
            datos_paciente=datos_paciente,
        )

        _guardar_en_hoja(
            spreadsheet=spreadsheet,
            sigla_url=sigla_url,
            sufijo="CENSO",
            tipo_jornada=tipo_jornada,
            val_fecha_app=val_fecha_app,
            datos_paciente=datos_paciente,
        )

        st.cache_data.clear()
        if hasattr(st, "cache_resource"):
            st.cache_resource.clear()

        return folio

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    try:
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
    except Exception as e:
        raise e
