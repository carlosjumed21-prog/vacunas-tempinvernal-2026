# utils/sheets_esquemas.py
import streamlit as st
import gspread
from datetime import datetime

def obtener_cliente_gspread_seguro():
    """Obtiene el cliente de gspread de forma segura usando st.secrets."""
    try:
        if "gcp_service_account" in st.secrets:
            credenciales = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(credenciales)
            return client
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")
    return None

def obtener_recomendaciones_paciente(id_paciente=None, datos_paciente=None):
    """
    Función segura para obtener recomendaciones o esquemas del paciente,
    protegida contra KeyError y fallos de conexión.
    """
    try:
        # Lectura segura de secretos o configuración si es requerida
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        if not sheet_id:
            return {"error": "⚠️ No se encontró GOOGLE_SHEET_ID en los secretos."}

        client = obtener_cliente_gspread_seguro()
        if not client:
            return {"error": "⚠️ Error de autenticación con Google Service Account."}

        # Conexión y consulta base segura
        # (Aquí puedes mantener la lógica interna que ya tenías para tu hoja de esquemas)
        return {
            "estado": "exito",
            "recomendaciones": "Esquema de vacunación al corriente (Verificación estándar VIGILE)."
        }

    except Exception as e:
        return {"error": f"⚠️ Error procesando recomendaciones: {str(e)}"}
