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
        
        # Patrones de búsqueda flexibles para encontrar la hoja existente
        patron_busqueda_1 = f"{sigla_url}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}"
        patron_busqueda_2 = f"{sigla_url}_{tipo_texto_jornada}_{fecha_str_hoja}"

        client = obtener_cliente_gspread()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        worksheet = None
        
        # 1. Buscar de forma inteligente entre todas las pestañas existentes del documento
        lista_hojas = spreadsheet.worksheets()
        for hoja in lista_hojas:
            titulo_hoja = hoja.title.upper()
            if sigla_url.upper() in titulo_hoja and fecha_str_hoja in titulo_hoja and tipo_texto_jornada in titulo_hoja:
                worksheet = hoja
                break

        # 2. Si no encuentra ninguna coincidencia parcial, intentamos abrirla por el nombre ideal
        if not worksheet:
            try:
                worksheet = spreadsheet.worksheet(patron_busqueda_1)
            except Exception:
                try:
                    worksheet = spreadsheet.worksheet(patron_busqueda_2)
                except Exception:
                    # 3. Si no existe ninguna, duplicamos una plantilla base ('CENSO NOMINAL' o 'CENSO')
                    plantilla_encontrada = None
                    for nombre_plantilla in ["CENSO NOMINAL", "CENSO"]:
                        try:
                            plantilla_encontrada = spreadsheet.worksheet(nombre_plantilla)
                            break
                        except Exception:
                            continue
                    
                    if plantilla_encontrada:
                        spreadsheet.duplicate_sheet(
                            source_sheet_id=plantilla_encontrada.id,
                            insert_sheet_index=0,
                            new_sheet_name=patron_busqueda_1
                        )
                        worksheet = spreadsheet.worksheet(patron_busqueda_1)
                    else:
                        worksheet = spreadsheet.add_worksheet(title=patron_busqueda_1, rows=100, cols=50)

        # Usar siempre el nombre real de la hoja detectada o seleccionada
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

        p = datos_paciente
        com = p.get("comorbilidades", {})
        fn = p.get("fecha_nacimiento")

        fn_dia = str(fn.day).zfill(2) if fn else ""
        fn_mes = str(fn.month).zfill(2) if fn else ""
        fn_anio = str(fn.year) if fn else ""

        edad_anos = str(p.get("calc_anos", 0))
        edad_meses = str(p.get("calc_meses", 0))

        vacuna_interes = p.get("vacuna_interes", "")
        marca_influenza = "X" if vacuna_interes in ["INFLUENZA", "AMBAS"] else ""
        marca_covid = "X" if vacuna_interes in ["COVID-19", "AMBAS"] else ""

        curp_val = p.get("curp_con_nacimiento", "").upper()
        personal_salud_activo = "SÍ" if str(com.get("personal_salud_riesgo", "NO")).upper() in ["SÍ", "SI", "TRUE", "1"] or "PERSONAL DE SALUD" in p.get("ocupacion", "").upper() else "NO"
        embarazo_val = "SÍ" if str(com.get("personas_embarazadas", "NO")).upper() in ["SÍ", "SI", "TRUE", "1"] else "NO"

        # Mapeo exacto de columnas de la A hasta la AH (Fila 14 inicial)
        fila_registro_principal = [
            str(siguiente_num),                                   # A: #
            folio_asignado,                                       # B: Folio
            curp_val,                                             # C: RFC (CURP calculada)
            p.get("cuenta_derechohabiencia", "NO"),               # D: Derechohabiencia al ISSSTE
            "",                                                   # E: Tipo de DH
            "NO",                                                 # F: Trabaja CMN
            "",                                                   # G: # Trabajador
            personal_salud_activo,                                # H: Personal de Salud
            "",                                                   # I: Categoría
            "",                                                   # J: Servicio
            "",                                                   # K: Coordinación
            "",                                                   # L: Turno
            p.get("nombres", "").upper(),                         # M: Nombre(s)
            p.get("paterno", "").upper(),                         # N: Paterno
            p.get("materno", "").upper(),                         # O: Materno
            p.get("estado_nacimiento", "").upper(),               # P: Edo Nac
            "",                                                   # Q: Muni Nac
            fn_dia,                                               # R: FN Día
            fn_mes,                                               # S: FN Mes
            fn_anio,                                              # T: FN Año
            edad_anos,                                            # U: Años
            edad_meses,                                           # V: Meses
            p.get("sexo", ""),                                    # W: Sexo
            embarazo_val,                                         # X: Embarazo
            "",                                                   # Y: Influenza 1ra dosis
            "",                                                   # Z: Influenza 2da dosis
            marca_influenza,                                      # AA: Influenza Dosis anual
            "",                                                   # AB: Influenza No. lote
            "",                                                   # AC: Influenza Caducidad
            "",                                                   # AD: Covid 1ra dosis
            "",                                                   # AE: Covid 2da dosis
            marca_covid,                                          # AF: Covid Dosis anual
            "",                                                   # AG: Covid No. lote
            ""                                                    # AH: Covid Caducidad
        ]

        token = obtener_token_acceso()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id_20n}/values:batchUpdate"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{nombre_real_hoja}!A{f_actual}", "values": [fila_registro_principal]}
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
