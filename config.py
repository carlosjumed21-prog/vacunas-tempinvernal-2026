# config.py
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
GOOGLE_SHEET_ID = "TU_SHEET_ID_PRINCIPAL"

UNIDADES_ISSSTE = [
    "20N", "HGS", "OTRAS"
]

def aplicar_configuracion_global(titulo, icono):
    import streamlit as st
    # Aquí va la configuración global limpia si la usas en otras páginas
    pass
