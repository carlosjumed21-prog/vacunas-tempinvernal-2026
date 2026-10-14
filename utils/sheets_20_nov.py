# utils/sheets_20_nov.py
import datetime
import json
from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import gspread
import streamlit as st
from config import GOOGLE_SCOPES

def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread utilizando los secretos del proyecto."""
    scope = GOOGLE_SCOPES
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = (
            json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        )
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

def guardar_registro_censal(
    sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente
):
    try:
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        nombre_hoja_destino = (
            f"{sigla_url}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}"
        )

        client = obtener_cliente_gspread()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        # Intentar abrir la hoja del día; si no existe, crearla automáticamente o buscar respaldos
        try:
            worksheet = spreadsheet.worksheet(nombre_hoja_destino)
        except Exception:
            try:
                # Opcional: Crear la hoja automáticamente si no existe para mantener el flujo de la jornada
                worksheet = spreadsheet.add_worksheet(title=nombre_hoja_destino, rows=100, cols=50)
            except Exception:
                try:
                    worksheet = spreadsheet.worksheet("CENSO NOMINAL")
                except Exception:
                    worksheet = spreadsheet.worksheet("CENSO")

        # Usar siempre el nombre real de la hoja obtenida (evita errores de parseo de rangos)
        nombre_real_hoja = worksheet.title

        columna_b = worksheet.col_values(2)
        fila_inicio_destino = 14
        
        idx = 13
        while idx < len(columna_b):
            val_actual = str(columna_b[idx]).strip()
            if val_actual == "" or "POR ASIGNAR" in val_actual.upper():
                fila_inicio_destino = idx + 1
                break
            idx += 2
        else:
            fila_inicio_destino = max(14, len(columna_b) + 1)
            if (fila_inicio_destino - 14) % 2 != 0:
                fila_inicio_destino += 1

        siguiente_num = ((fila_inicio_destino - 14) // 2) + 1
        aammmdd = val_fecha_app.strftime("%y%m%d")
        folio_asignado = f"{aammmdd}-{tipo_jornada}{sigla_url}-{str(siguiente_num).zfill(3)}"

        f_actual = fila_inicio_destino
        f_siguiente = fila_inicio_destino + 1

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

        marca_influenza = "X" if vacuna_interes == "INFLUENZA" else ""
        marca_covid = "X" if vacuna_interes == "COVID-19" else ""
        marca_ambas = "X" if vacuna_interes == "AMBAS" else ""

        fecha_registro_actual = datetime.date.today().strftime("%d/%m/%Y")
        correo_paciente_val = p.get("correo_paciente", "").strip()

        def check_activo(val):
            if isinstance(val, bool):
                return "X" if val else ""
            if isinstance(val, str):
                return "X" if val.upper() in ["SÍ", "SI", "TRUE", "1"] else ""
            return ""

        # Mapeo idéntico al estándar asegurando columnas C, D, E para nombres
        fila_registro_principal = [
            str(siguiente_num),
            folio_asignado,
            p.get("paterno", "").upper(),
            p.get("materno", "").upper(),
            p.get("nombres", "").upper(),
            fn_dia, fn_mes, fn_anio,
            edad_anos, edad_meses,
            p.get("sexo", ""),
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app),
            p.get("calle", "").upper(), p.get("numero", "").upper(), p.get("colonia", "").upper(),
            marca_6_59m,
            marca_60_mas,
            check_activo(com.get("personas_embarazadas")),
            check_activo(com.get("personal_salud_riesgo")),
            check_activo(com.get("vih")),
            check_activo(com.get("diabetes")),
            check_activo(com.get("obesidad")),
            check_activo(com.get("cardiopatias")),
            check_activo(com.get("enfermedad_pulmonar")),
            check_activo(com.get("cancer")),
            check_activo(com.get("cardiacas_congenitas")),
            check_activo(com.get("insuficiencia_renal")),
            check_activo(com.get("inmunosupresion")),
            check_activo(com.get("discapacidades")),
            check_activo(com.get("fibrosis_quistica")),
            check_activo(com.get("hipertension")),
            com.get("texto_otro", "").upper(),
            "", "", "", "", "", "", "", "", "", "",
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
        curp_fila = f"C{f_siguiente}"
        fecha_fila = f"AW{f_siguiente}"

        token = obtener_token_acceso()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id_20n}/values:batchUpdate"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{nombre_real_hoja}!A{f_actual}", "values": [fila_registro_principal]},
                {"range": f"{nombre_real_hoja}!{curp_fila}", "values": [[curp_val]]},
                {"range": f"{nombre_real_hoja}!{fecha_fila}", "values": [[fecha_registro_actual]]}
            ]
        }
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(resp.text)

        st.cache_data.clear()
        if hasattr(st, "cache_resource"):
            st.cache_resource.clear()

        return folio_asignado

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    """Guarda el registro censal específico del CMN '20 de Noviembre'
    utilizando el mapeo estándar unificado.
    """
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
            datos_paciente=datos_paciente
        )

    except Exception as e:
        raise e
