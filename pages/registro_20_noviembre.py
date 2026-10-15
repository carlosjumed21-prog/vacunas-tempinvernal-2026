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


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread utilizando los secretos del proyecto."""
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


def _normalizar_texto(v):
    if v is None:
        return ""
    return str(v).strip()


def _normalizar_mayus(v):
    return _normalizar_texto(v).upper()


def _obtener_spreadsheet():
    client = obtener_cliente_gspread()
    return client.open_by_key(SHEET_ID_20N)


def _obtener_o_crear_worksheet(spreadsheet, nombre_hoja, plantilla_prioritaria=("CENSO NOMINAL", "CENSO")):
    """
    Busca la hoja por nombre. Si no existe, intenta duplicar una plantilla.
    Si no hay plantilla, la crea vacía.
    """
    try:
        return spreadsheet.worksheet(nombre_hoja)
    except Exception:
        pass

    plantilla_encontrada = None
    for nombre_plantilla in plantilla_prioritaria:
        try:
            plantilla_encontrada = spreadsheet.worksheet(nombre_plantilla)
            break
        except Exception:
            continue

    if plantilla_encontrada:
        try:
            spreadsheet.duplicate_sheet(
                source_sheet_id=plantilla_encontrada.id,
                insert_sheet_index=0,
                new_sheet_name=nombre_hoja,
            )
        except Exception:
            # Si ya existiera por carrera/concurrencia, la volvemos a pedir
            pass

        return spreadsheet.worksheet(nombre_hoja)

    return spreadsheet.add_worksheet(title=nombre_hoja, rows=200, cols=80)


def _siguiente_fila_disponible_por_pares(worksheet, columna=2, fila_inicio=14):
    """
    Busca la primera fila libre considerando registros de 2 filas.
    Si la columna está vacía o dice POR ASIGNAR, usa ese espacio.
    """
    columna_vals = worksheet.col_values(columna)
    idx = fila_inicio - 1

    while idx < len(columna_vals):
        val_actual = _normalizar_texto(columna_vals[idx])
        if val_actual == "" or "POR ASIGNAR" in val_actual.upper():
            return idx + 1
        idx += 2

    fila = max(fila_inicio, len(columna_vals) + 1)
    if (fila - fila_inicio) % 2 != 0:
        fila += 1
    return fila


def _folio_consecutivo(fila_inicio, fila_base=14):
    return ((fila_inicio - fila_base) // 2) + 1


def _marcar_x(condicion):
    return "X" if condicion else ""


def _obtener_grupo_objetivo(datos_paciente):
    """
    Devuelve:
    - grupo_6a59: True/False
    - grupo_60ymas: True/False
    Usa el valor ya calculado por la interfaz si existe.
    """
    grupo = _normalizar_mayus(datos_paciente.get("grupo_sugerido", ""))
    edad_meses = int(datos_paciente.get("anos", datos_paciente.get("calc_anos", 0)) or 0) * 12 + int(datos_paciente.get("meses", datos_paciente.get("calc_meses", 0)) or 0)

    grupo_6a59 = False
    grupo_60ymas = False

    if "6 A 59" in grupo or "6 A 59 MESES" in grupo:
        grupo_6a59 = True
    elif "60 Y MÁS" in grupo or "60 Y MAS" in grupo:
        grupo_60ymas = True
    else:
        # fallback por edad
        if edad_meses <= 59:
            grupo_6a59 = True
        else:
            grupo_60ymas = True

    return grupo_6a59, grupo_60ymas


def _obtener_grupo_riesgo(datos_paciente):
    com = datos_paciente.get("comorbilidades", {}) or {}

    personal_salud = str(com.get("personal_salud_riesgo", False)).lower() in ["true", "1", "sí", "si", "s"]
    embarazo = str(com.get("personas_embarazadas", False)).lower() in ["true", "1", "sí", "si", "s"]

    def b(*keys):
        return any(str(com.get(k, False)).lower() in ["true", "1", "sí", "si", "s"] for k in keys)

    return {
        "embarazadas": embarazo,
        "personal_salud": personal_salud,
        "vih": b("vih"),
        "diabetes": b("diabetes"),
        "obesidad": b("obesidad"),
        "cardiopatias": b("cardiopatias"),
        "enfermedad_pulmonar": b("enfermedad_pulmonar"),
        "cancer": b("cancer"),
        "cardiacas_congenitas": b("cardiacas_congenitas"),
        "insuficiencia_renal": b("insuficiencia_renal", "insufren"),
        "inmunosupresion": b("inmunosupresion"),
        "discapacidades": b("discapacidades"),
        "fibrosis_quistica": b("fibrosis_quistica"),
        "hipertension": b("hipertension"),
        "otro_texto": _normalizar_mayus(com.get("texto_otro", "")),
        "otro": b("otro"),
    }


def _mapear_nominal(datos_paciente, folio_asignado):
    """
    Mapeo NOMINAL:
    A: número consecutivo
    B: folio
    C: CURP
    D-AH: datos generales y vacunas según tu especificación
    """
    fecha_nacimiento = datos_paciente.get("fecha_nacimiento")
    val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())

    fn_dia = str(fecha_nacimiento.day).zfill(2) if fecha_nacimiento else ""
    fn_mes = str(fecha_nacimiento.month).zfill(2) if fecha_nacimiento else ""
    fn_anio = str(fecha_nacimiento.year) if fecha_nacimiento else ""

    edad_anos = str(datos_paciente.get("calc_anos", 0))
    edad_meses = str(datos_paciente.get("calc_meses", 0))

    grupo_6a59, grupo_60ymas = _obtener_grupo_objetivo(datos_paciente)
    riesgos = _obtener_grupo_riesgo(datos_paciente)

    vacuna_interes = _normalizar_mayus(datos_paciente.get("vacuna_interes", ""))
    antecedente_influenza = _normalizar_mayus(datos_paciente.get("antecedente_influenza", ""))
    antecedente_covid = _normalizar_mayus(datos_paciente.get("antecedente_covid", ""))

    inflam_1 = _marcar_x(False)
    inflam_2 = _marcar_x(False)
    inflam_anual = _marcar_x(vacuna_interes in ["INFLUENZA", "AMBAS"])
    covid_1 = _marcar_x(False)
    covid_2 = _marcar_x(False)
    covid_anual = _marcar_x(vacuna_interes in ["COVID-19", "COVID", "AMBAS"])

    fila = [
        "",  # A: consecutivo -> se llena fuera
        folio_asignado,  # B
        _normalizar_mayus(datos_paciente.get("curp_con_nacimiento", "")),  # C
        _normalizar_texto(datos_paciente.get("cuenta_derechohabiencia", "")),  # D
        "",  # E tipo DH
        "",  # F trabaja CMN
        "",  # G # trabajador
        "SÍ" if riesgos["personal_salud"] else "NO",  # H personal de salud
        "",  # I categoría
        "",  # J servicio
        "",  # K coordinación
        "",  # L turno
        _normalizar_mayus(datos_paciente.get("nombres", "")),  # M
        _normalizar_mayus(datos_paciente.get("paterno", "")),  # N
        _normalizar_mayus(datos_paciente.get("materno", "")),  # O
        _normalizar_mayus(datos_paciente.get("estado_nacimiento", "")),  # P
        "",  # Q municipio nac
        fn_dia,  # R
        fn_mes,  # S
        fn_anio,  # T
        edad_anos,  # U
        edad_meses,  # V
        _normalizar_texto(datos_paciente.get("sexo", "")),  # W
        "SÍ" if riesgos["embarazadas"] else "NO",  # X
        inflam_1,  # Y
        inflam_2,  # Z
        inflam_anual,  # AA
        "",  # AB lote influenza
        "",  # AC caducidad influenza
        covid_1,  # AD
        covid_2,  # AE
        covid_anual,  # AF
        "",  # AG lote covid
        "",  # AH caducidad covid
        _marcar_x(_normalizar_mayus(antecedente_influenza) == "SÍ"),  # AI antecedente influenza
        _marcar_x(_normalizar_mayus(antecedente_covid) == "SÍ"),  # AJ antecedente covid
        _marcar_x(vacuna_interes == "INFLUENZA"),  # AK vacuna solicitada influenza
        _marcar_x(vacuna_interes == "COVID-19"),  # AL vacuna solicitada covid
        _marcar_x(vacuna_interes == "AMBAS"),  # AM vacuna solicitada ambas
        "",  # AN reserva
        "",  # AO reserva
        "",  # AP reserva
        _normalizar_texto(datos_paciente.get("cuenta_derechohabiencia", "")),  # AQ derechohabiencia
        "",  # AR reserva
        "",  # AS reserva
        "",  # AT reserva
        "",  # AU reserva
        "",  # AV reserva
        datetime.date.today().strftime("%d/%m/%Y"),  # AW fecha de registro
        _normalizar_texto(datos_paciente.get("correo_paciente", "")),  # AX correo
    ]

    # Ajuste de grupos de objetivo:
    # P = 6 a 59 meses, Q = 60 y más
    fila[16] = _marcar_x(grupo_6a59)
    fila[17] = _normalizar_texto(fn_dia)
    fila[18] = _normalizar_texto(fn_mes)
    fila[19] = _normalizar_texto(fn_anio)

    # Mapeo solicitado en tu especificación:
    # 6 A 59 MESES -> P
    # 60 Y MÁS -> Q
    # Grupo de riesgo -> R:AF
    fila[24] = _marcar_x(riesgos["embarazadas"])
    fila[25] = _marcar_x(riesgos["personal_salud"])
    fila[26] = _marcar_x(riesgos["vih"])
    fila[27] = _marcar_x(riesgos["diabetes"])
    fila[28] = _marcar_x(riesgos["obesidad"])
    fila[29] = _marcar_x(riesgos["cardiopatias"])
    fila[30] = _marcar_x(riesgos["enfermedad_pulmonar"])
    fila[31] = _marcar_x(riesgos["cancer"])
    fila[32] = _marcar_x(riesgos["cardiacas_congenitas"])
    fila[33] = _marcar_x(riesgos["insuficiencia_renal"])
    fila[34] = _marcar_x(riesgos["inmunosupresion"])
    fila[35] = _marcar_x(riesgos["discapacidades"])
    fila[36] = _marcar_x(riesgos["fibrosis_quistica"])
    fila[37] = _marcar_x(riesgos["hipertension"])
    fila[38] = _normalizar_texto(riesgos["otro_texto"])

    # Reacomodo correcto de antecedente y vacunas solicitadas
    # AR/AS antecedente vacunal
    # AT/AU/AV vacuna solicitada
    fila[41] = _marcar_x(antecedente_influenza == "SÍ")  # AR
    fila[42] = _marcar_x(antecedente_covid == "SÍ")       # AS
    fila[43] = _marcar_x(vacuna_interes == "INFLUENZA")   # AT
    fila[44] = _marcar_x(vacuna_interes == "COVID-19")    # AU
    fila[45] = _marcar_x(vacuna_interes == "AMBAS")       # AV

    return fila


def _mapear_censo(datos_paciente, folio_asignado):
    """
    Mapeo CENSO:
    A consecutivo, B folio, C RFC, D derechohabiencia, E tipo DH...
    Hasta AH según tu tabla.
    """
    fecha_nacimiento = datos_paciente.get("fecha_nacimiento")

    fn_dia = str(fecha_nacimiento.day).zfill(2) if fecha_nacimiento else ""
    fn_mes = str(fecha_nacimiento.month).zfill(2) if fecha_nacimiento else ""
    fn_anio = str(fecha_nacimiento.year) if fecha_nacimiento else ""

    fila = [
        "",  # A consecutivo
        folio_asignado,  # B
        _normalizar_mayus(datos_paciente.get("rfc", "")),  # C
        _normalizar_texto(datos_paciente.get("cuenta_derechohabiencia", "")),  # D
        _normalizar_texto(datos_paciente.get("tipo_dh", "NO APLICA")),  # E
        _normalizar_texto(datos_paciente.get("trabaja_cmn", "NO")),  # F
        _normalizar_texto(datos_paciente.get("num_trabajador", "")),  # G
        "SÍ" if str(datos_paciente.get("personal_salud", "NO")).upper() == "SÍ" else "NO",  # H
        _normalizar_texto(datos_paciente.get("categoria", "")),  # I
        _normalizar_texto(datos_paciente.get("servicio", "")),  # J
        _normalizar_texto(datos_paciente.get("coordinacion", "")),  # K
        _normalizar_texto(datos_paciente.get("turno", "")),  # L
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
        _normalizar_texto(datos_paciente.get("sexo", "")),  # W
        "SÍ" if _normalizar_mayus(datos_paciente.get("embarazo", "")) == "SÍ" else "NO",  # X
        "",  # Y influenza 1ra
        "",  # Z influenza 2da
        "",  # AA influenza anual
        "",  # AB lote influenza
        "",  # AC caducidad influenza
        "",  # AD covid 1ra
        "",  # AE covid 2da
        "",  # AF covid anual
        "",  # AG lote covid
        "",  # AH caducidad covid
    ]

    # Vacunas en CENSO según tu especificación
    fila[24] = "X" if _normalizar_mayus(datos_paciente.get("vacuna_interes", "")) in ["INFLUENZA", "AMBAS"] else ""
    fila[25] = "X" if _normalizar_mayus(datos_paciente.get("vacuna_interes", "")) in ["COVID-19", "AMBAS"] else ""
    fila[26] = "X" if _normalizar_mayus(datos_paciente.get("vacuna_interes", "")) in ["INFLUENZA", "AMBAS"] else ""
    fila[27] = ""
    fila[28] = ""
    fila[29] = ""
    fila[30] = ""
    fila[31] = ""
    fila[32] = ""
    fila[33] = ""
    fila[34] = ""
    fila[35] = ""
    fila[36] = ""
    fila[37] = ""
    fila[38] = ""

    return fila


def _guardar_en_hoja(spreadsheet, nombre_hoja, datos_paciente, sufijo, tipo_jornada, val_fecha_app, sigla_url, sufijo_js):
    fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
    tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
    nombre_ideal = f"{sigla_url}_{tipo_texto_jornada}_{fecha_str_hoja}_{sufijo}"

    worksheet = _obtener_o_crear_worksheet(spreadsheet, nombre_ideal)

    nombre_real_hoja = worksheet.title
    fila_inicio_destino = _siguiente_fila_disponible_por_pares(worksheet, columna=2, fila_inicio=14)
    siguiente_num = _folio_consecutivo(fila_inicio_destino, fila_base=14)
    folio_asignado = f"{val_fecha_app.strftime('%y%m%d')}-{tipo_jornada}{sigla_url}-{str(siguiente_num).zfill(3)}"

    if sufijo.upper() == "NOMINAL":
        fila = _mapear_nominal(datos_paciente, folio_asignado)
    else:
        fila = _mapear_censo(datos_paciente, folio_asignado)

    fila[0] = str(siguiente_num)

    token = obtener_token_acceso()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID_20N}/values:batchUpdate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"{nombre_real_hoja}!A{fila_inicio_destino}", "values": [fila]}
        ],
    }

    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise Exception(resp.text)

    return folio_asignado


def guardar_registro_censal(
    sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente
):
    """
    Guarda el registro en dos hojas:
    - ..._NOMINAL
    - ..._CENSO
    """
    try:
        spreadsheet = _obtener_spreadsheet()

        folio_nominal = _guardar_en_hoja(
            spreadsheet=spreadsheet,
            nombre_hoja=None,
            datos_paciente=datos_paciente,
            sufijo="NOMINAL",
            tipo_jornada=tipo_jornada,
            val_fecha_app=val_fecha_app,
            sigla_url=sigla_url,
            sufijo_js=sufijo_js,
        )

        _guardar_en_hoja(
            spreadsheet=spreadsheet,
            nombre_hoja=None,
            datos_paciente=datos_paciente,
            sufijo="CENSO",
            tipo_jornada=tipo_jornada,
            val_fecha_app=val_fecha_app,
            sigla_url=sigla_url,
            sufijo_js=sufijo_js,
        )

        st.cache_data.clear()
        if hasattr(st, "cache_resource"):
            st.cache_resource.clear()

        return folio_nominal

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    """Guarda el registro censal específico del CMN '20 de Noviembre' utilizando el mapeo dual."""
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
