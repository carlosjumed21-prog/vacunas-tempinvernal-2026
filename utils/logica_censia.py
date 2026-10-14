import datetime
import requests
import streamlit as st
from utils.sheets import obtener_token_acceso

SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def guardar_registro_censal_20_nov(datos):
    """
    Registra al paciente en la hoja nominal activa y realiza la migración dual 
    automática hacia la hoja 'CENSO' general del CMN 20 de Noviembre.
    """
    try:
        token = obtener_token_acceso()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Obtenemos el cliente gspread cacheado para interactuar con las pestañas
        from utils.sheets_esquemas import obtener_client_gspread_cacheado # O la función que uses para tu cliente
        client = obtener_client_gspread_cacheado()
        spreadsheet_20n = client.open_by_key(SHEET_ID_20_NOV)
        
        # 1. Identificar la hoja de la jornada activa (última pestaña o la que corresponda)
        hojas = spreadsheet_20n.worksheets()
        # Filtramos para asegurarnos de tomar una hoja nominal que no sea la sábana "CENSO"
        hojas_nominales = [h for h in hojas if h.title not in ["CENSO", "Influenza", "COVID"]]
        worksheet_activa = hojas_nominales[-1] if hojas_nominales else hojas[0]
        nombre_hoja_activa_esc = f"'{worksheet_activa.title}'"
        
        # 2. Hoja maestra continua
        hoja_censia_general = spreadsheet_20n.worksheet("CENSO")
        nombre_censo_esc = "'CENSO'"

        # Calcular la siguiente fila disponible en la hoja CENSO general
        valores_censo = hoja_censia_general.get_all_values()
        nueva_fila_idx = len(valores_censo) + 1
        if nueva_fila_idx < 14:
            nueva_fila_idx = 14

        folio_consecutivo = nueva_fila_idx - 13

        # Construir la fila de datos (Columnas B a X)
        fila_valores = [
            "", # A
            str(folio_consecutivo), # B - Folio
            datos.get("rfc", ""), # C - RFC
            datos.get("dh", ""), # D - Derechohabiencia
            datos.get("tipo_dh", ""), # E - Tipo DH
            datos.get("trabaja_cmn", ""), # F - Trabaja CMN
            datos.get("num_trabajador", ""), # G - Num Trabajador
            datos.get("personal_salud", ""), # H - Personal de Salud
            datos.get("categoria", ""), # I - Categoria
            datos.get("servicio", ""), # J - Servicio
            datos.get("coordinacion", ""), # K - Coordinacion
            datos.get("turno", ""), # L - Turno
            datos.get("nombre", ""), # M - Nombre
            datos.get("paterno", ""), # N - Paterno
            datos.get("materno", ""), # O - Materno
            datos.get("edo_nac", ""), # P - Edo Nac
            datos.get("muni_nac", ""), # Q - Muni Nac
            datos.get("fn_dia", ""), # R - Día Nac
            datos.get("fn_mes", ""), # S - Mes Nac
            datos.get("fn_ano", ""), # T - Año Nac
            str(datos.get("anos", 0)), # U - Años
            str(datos.get("meses", 0)), # V - Meses
            datos.get("sexo", ""), # W - Sexo
            datos.get("embarazo", "NO"), # X - Embarazo
        ]

        # Preparamos las actualizaciones duales para AMBAS hojas (la nominal activa y la CENSO general)
        updates_data = [
            {
                "range": f"{nombre_censo_esc}!B{nueva_fila_idx}:X{nueva_fila_idx}",
                "values": [fila_valores[1:]]
            },
            {
                "range": f"{nombre_hoja_activa_esc}!B{nueva_fila_idx}:X{nueva_fila_idx}",
                "values": [fila_valores[1:]]
            }
        ]

        # Si eligió vacuna de interés, marcamos las "X" correspondientes en ambas hojas
        vacuna_interes = datos.get("vacuna_interes", "AMBAS")
        
        if vacuna_interes in ["INFLUENZA", "AMBAS"]:
            updates_data.append({
                "range": f"{nombre_censo_esc}!Y{nueva_fila_idx}:AA{nueva_fila_idx}",
                "values": [["X", "", ""]]
            })
            updates_data.append({
                "range": f"{nombre_hoja_activa_esc}!Y{nueva_fila_idx}:AA{nueva_fila_idx}",
                "values": [["X", "", ""]]
            })

        if vacuna_interes in ["COVID-19", "AMBAS"]:
            updates_data.append({
                "range": f"{nombre_censo_esc}!AD{nueva_fila_idx}:AF{nueva_fila_idx}",
                "values": [["X", "", ""]]
            })
            updates_data.append({
                "range": f"{nombre_hoja_activa_esc}!AD{nueva_fila_idx}:AF{nueva_fila_idx}",
                "values": [["X", "", ""]]
            })

        url_values = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID_20_NOV}/values:batchUpdate"
        body_values = {
            "valueInputOption": "USER_ENTERED",
            "data": updates_data
        }
        
        resp = requests.post(url_values, headers=headers, json=body_values)
        if resp.status_code != 200:
            raise Exception(f"Error al guardar en Sheets: {resp.text}")

        st.cache_data.clear()
        return str(folio_consecutivo)

    except Exception as e:
        st.error(f"Error crítico en la función de guardado y migración: {e}")
        return "S/F"
