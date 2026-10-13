# utils/sheets.py
import datetime
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
from config import GOOGLE_SHEET_ID, GOOGLE_SCOPES
import gspread
import streamlit as st

@st.cache_resource
def obtener_cliente_gspread():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)

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

def guardar_registro_censal(
    sigla_url,
    sufijo_js,
    tipo_jornada,
    val_fecha_app,
    nombre_unidad_completo,
    datos_paciente,
):
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # --- Construcción dinámica del nombre de la hoja según modalidad y fecha ---
        modalidad_texto = str(datos_paciente.get("modalidad", "INTRAMUROS")).upper()
        
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"
        elif tipo_jornada.upper() == "E" or "EXTRA" in modalidad_texto:
            fecha_hoja_str = val_fecha_app.strftime("%d%m%y") if isinstance(val_fecha_app, datetime.date) else datetime.date.today().strftime("%d%m%y")
            nombre_hoja = f"{sigla_url}_EXTRA_{fecha_hoja_str}"
        else:
            fecha_hoja_str = val_fecha_app.strftime("%d%m%y") if isinstance(val_fecha_app, datetime.date) else datetime.date.today().strftime("%d%m%y")
            nombre_hoja = f"{sigla_url}_INTRA_{fecha_hoja_str}" if tipo_jornada.upper() == "I" else sigla_url

        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            ws = None
            for h in spreadsheet.worksheets():
                if sigla_url.upper() in h.title.upper():
                    ws = h
                    break
            if ws is None:
                ws = spreadsheet.add_worksheet(title=nombre_hoja, rows=2000, cols=60)

        col_b = ws.col_values(2)
        fila_destino = 14
        if len(col_b) >= 14:
            idx = 13
            while idx < len(col_b):
                if idx >= len(col_b) or not str(col_b[idx]).strip():
                    fila_destino = idx + 1
                    break
                idx += 2
            else:
                fila_destino = len(col_b) + 1
                if (fila_destino - 14) % 2 != 0:
                    fila_destino += 1

        consecutivo = ((fila_destino - 14) // 2) + 1

        fecha_str = val_fecha_app.strftime("%Y%m%d") if isinstance(val_fecha_app, datetime.date) else datetime.date.today().strftime("%Y%m%d")
        mod_str = "INT" if "INTRA" in modalidad_texto else "EXT"
        siglas_3 = sigla_url[:3].upper().ljust(3, 'X')
        secuencial_str = str(consecutivo).zfill(4)

        folio_asignado = f"{fecha_str}-{mod_str}-{siglas_3}-{secuencial_str}"

        p = datos_paciente
        com = p.get("comorbilidades", {})
        fn = p.get("fecha_nacimiento")

        fn_dia = str(fn.day).zfill(2) if fn else ""
        fn_mes = str(fn.month).zfill(2) if fn else ""
        fn_anio = str(fn.year) if fn else ""

        edad_anos = str(p.get("calc_anos", 0))
        edad_meses = str(p.get("calc_meses", 0))

        es_menor_59m = (p.get("calc_anos", 0) * 12) + p.get("calc_meses", 0) <= 59
        es_mayor_60 = p.get("calc_anos", 0) >= 60

        marca_6_59m = "X" if es_menor_59m else ""
        marca_60_mas = "X" if es_mayor_60 else ""
        
        # 6. Antecedentes Vacunales (AR para COVID-19, AS para Influenza)
        ant_cov_val = p.get("antecedente_covid", "")
        ant_cov_str = str(ant_cov_val).upper().strip() if ant_cov_val else ""
        val_ant_cov = ant_cov_str if ant_cov_str in ["SÍ", "SI", "NO", "LO DESCONOCE"] else ""

        ant_inf_val = p.get("antecedente_influenza", "")
        ant_inf_str = str(ant_inf_val).upper().strip() if ant_inf_val else ""
        val_ant_inf = ant_inf_str if ant_inf_str in ["SÍ", "SI", "NO", "LO DESCONOCE"] else ""

        # 8. Vacuna de Interés (AT = INFLUENZA, AU = COVID-19, AV = AMBAS)
        vacuna_interes = p.get("vacuna_interes", "")
        vacuna_interes_str = str(vacuna_interes).upper().strip() if vacuna_interes else ""

        if "SELECCIONE" in vacuna_interes_str or not vacuna_interes_str:
            marca_inf = ""
            marca_cov = ""
            marca_amb = ""
        else:
            marca_inf = "X" if vacuna_interes_str == "INFLUENZA" else ""
            marca_cov = "X" if vacuna_interes_str in ["COVID-19", "COVID"] else ""
            marca_amb = "X" if "AMBAS" in vacuna_interes_str else ""

        fecha_registro_actual = datetime.date.today().strftime("%d/%m/%Y")
        correo_paciente_val = p.get("correo_paciente", "").strip()

        # Función auxiliar para validar comorbilidades de forma segura
        def check_activo(val):
            if isinstance(val, bool):
                return "X" if val else ""
            if isinstance(val, str):
                return "X" if val.upper() in ["SÍ", "SI", "TRUE", "1"] else ""
            return ""

        fila_registro_principal = [
            str(consecutivo),                                                               # A (0)
            folio_asignado,                                                                 # B (1)
            p.get("paterno", "").upper(),                                                   # C (2)
            p.get("materno", "").upper(),                                                   # D (3)
            p.get("nombres", "").upper(),                                                   # E (4)
            fn_dia, fn_mes, fn_anio,                                                        # F, G, H (5, 6, 7)
            edad_anos, edad_meses,                                                          # I, J (8, 9)
            p.get("sexo", ""),                                                              # K (10)
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app), # L (11)
            p.get("calle", "").upper(), p.get("numero", "").upper(), p.get("colonia", "").upper(), # M, N, O (12, 13, 14)
            marca_6_59m,                                                                    # P (15) - 6 A 59 MESES
            marca_60_mas
