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
        vacuna_interes = p.get("vacuna_interes", "")

        # --- Modificación para que AMBAS sea independiente ---
        marca_influenza = "X" if vacuna_interes == "INFLUENZA" else ""
        marca_covid = "X" if vacuna_interes == "COVID-19" else ""
        marca_ambas = "X" if vacuna_interes == "AMBAS" else ""

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
            str(consecutivo),                                                       # A (0)
            folio_asignado,                                                         # B (1)
            p.get("paterno", "").upper(),                                           # C (2)
            p.get("materno", "").upper(),                                           # D (3)
            p.get("nombres", "").upper(),                                           # E (4)
            fn_dia, fn_mes, fn_anio,                                                # F, G, H (5, 6, 7)
            edad_anos, edad_meses,                                                  # I, J (8, 9)
            p.get("sexo", ""),                                                      # K (10)
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app), # L (11)
            p.get("calle", "").upper(), p.get("numero", "").upper(), p.get("colonia", "").upper(), # M, N, O (12, 13, 14)
            marca_6_59m,                                                            # P (15) - 6 A 59 MESES
            marca_60_mas,                                                           # Q (16) - 60 Y MÁS
            check_activo(com.get("personas_embarazadas")),                          # R (17) - EMBARAZADAS
            check_activo(com.get("personal_salud_riesgo")),                         # S (18) - PERSONAL DE SALUD
            check_activo(com.get("vih")),                                           # T (19) - VIH/sida
            check_activo(com.get("diabetes")),                                      # U (20) - DIABETES MELLITUS
            check_activo(com.get("obesidad")),                                      # V (21) - OBESIDAD MÓRBIDA
            check_activo(com.get("cardiopatias")),                                  # W (22) - CARDIOPATÍAS AGUDAS O CRÓNICAS
            check_activo(com.get("enfermedad_pulmonar")),                           # X (23) - ENFERMEDAD PULMONAR CRÓNICA
            check_activo(com.get("cancer")),                                        # Y (24) - CÁNCER
            check_activo(com.get("cardiacas_congenitas")),                          # Z (25) - ENFERMEDADES CARDIACAS O PULMONARES CONGÉNITAS
            check_activo(com.get("insuficiencia_renal")),                           # AA (26) - INSUFICIENCIA RENAL
            check_activo(com.get("inmunosupresion")),                               # AB (27) - INMUNOSUPRESIÓN ADQUIRIDA
            check_activo(com.get("discapacidades")),                                # AC (28) - DISCAPACIDADES
            check_activo(com.get("fibrosis_quistica")),                             # AD (29) - FIBROSIS QUÍSTICA
            check_activo(com.get("hipertension")),                                  # AE (30) - HIPERTENSIÓN ARTERIAL
            com.get("texto_otro", "").upper(),                                      # AF (31) - OTROS GRUPOS DE RIESGO (TEXTO)
            "", "", "", "", "", "", "", "", "", "",                                 # AG a AP (Espacios vacíos intermedios si aplican)
            p.get("cuenta_derechohabiencia", "NO"),
            p.get("antecedente_influenza", "NO"),
            p.get("antecedente_covid", "NO"),
            marca_influenza,
            marca_covid,
            marca_ambas,
            fecha_registro_actual,
            correo_paciente_val,
        ]

        curp_val = p.get("curp_con_nacimiento", "").upper()
        fila_curp = fila_destino + 1

        # Petición HTTP directa vía Google Sheets API v4 utilizando rango abierto !A{fila_destino}
        token = obtener_token_acceso()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEET_ID}/values:batchUpdate"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{nombre_hoja}!A{fila_destino}", "values": [fila_registro_principal]},
                {"range": f"{nombre_hoja}!C{fila_curp}", "values": [[curp_val]]},
                {"range": f"{nombre_hoja}!AW{fila_curp}", "values": [[fecha_registro_actual]]}
            ]
        }
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(resp.text)

        return folio_asignado, False, None

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
