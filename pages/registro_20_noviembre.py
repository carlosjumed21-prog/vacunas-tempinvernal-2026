import datetime
import requests
import streamlit as st
from utils.sheets import obtener_token_acceso
from config import GOOGLE_SHEET_ID

SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def guardar_registro_censal_20_nov(datos):
    """
    Registra al paciente en la hoja de censo nominal activa y realiza la migración dual 
    automática hacia la hoja 'CENSO' general del CMN 20 de Noviembre usando celdas exactas.
    """
    try:
        token = obtener_token_acceso()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        client = obtener_client_gspread_cacheado() # O tu cliente gspread activo
        spreadsheet_20n = client.open_by_key(SHEET_ID_20_NOV)
        
        # 1. Determinar la hoja de jornada activa (por ejemplo, la última o la seleccionada)
        # Si tienes la hoja activa en la sesión o recuperas la última pestaña nominal:
        hojas = spreadsheet_20n.worksheets()
        # Buscamos la hoja nominal correspondiente o la última activa
        worksheet_activa = hojas[-1] # Ajusta esto según tu lógica de selección de jornada
        nombre_hoja_activa_esc = f"'{worksheet_activa.title}'"
        
        hoja_censia_general = spreadsheet_20n.worksheet("CENSO")
        nombre_censo_esc = "'CENSO'"

        # Obtener valores actuales para calcular el siguiente folio consecutivo y la siguiente fila disponible
        valores_censo = hoja_censia_general.get_all_values()
        nueva_fila_idx = len(valores_censo) + 1 # Asumiendo que se agrega al final, o buscar la primera fila libre
        if nueva_fila_idx < 14:
            nueva_fila_idx = 14

        folio_consecutivo = nueva_fila_idx - 13 # Si la fila 14 es el folio 1

        # Construir los valores a insertar/actualizar para la fila
        # Mapeo de columnas para CENSO general:
        # B: Folio, C: RFC, D: DH, E: Tipo DH, F: Trabaja CMN, G: Num Trabajador, H: Personal Salud, 
        # I: Categoria, J: Servicio, K: Coordinacion, L: Turno, M: Nombre, N: Paterno, O: Materno, 
        # P: Edo Nac, Q: Muni Nac, R,S,T: Fecha Nac (D, M, A), U,V: Anios, Meses, W: Sexo, X: Embarazo
        
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

        # Si el usuario seleccionó alguna vacuna de interés o dosis inicial al registrar:
        vacuna_interes = datos.get("vacuna_interes", "AMBAS")
        
        # Mapeo de columnas de vacunas en CENSO general:
        # Y: Inf 1ra, Z: Inf 2da, AA: Inf Anual, AB: Lote Inf, AC: Cad Inf
        # AD: Cov 1ra, AE: Cov 2da, AF: Cov Anual, AG: Lote Cov, AH: Cad Cov
        
        if vacuna_interes in ["INFLUENZA", "AMBAS"]:
            updates_data.append({
                "range": f"{nombre_censo_esc}!Y{nueva_fila_idx}:AA{nueva_fila_idx}",
                "values": [["X", "", ""]] # O marca la dosis correspondiente
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
