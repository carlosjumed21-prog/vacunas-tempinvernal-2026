import streamlit as st
import pandas as pd
import gspread
import json
import datetime
import urllib.request
from google.oauth2 import service_account
from utils.sheets import obtener_cliente_gspread
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID

# --- CONFIGURACIÓN DE PANTALLA ANCHA ---
st.set_page_config(page_title="Vista Detallada de Censo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        [data-testid="stSidebar"] {display: none;}
        .metric-card { background-color: #f8f9fa; border: 2px solid #1e5b4f; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 1.2rem; font-weight: 800; color: #161a1d; }
        .metric-label { font-size: 0.7rem; font-weight: 700; color: #333333; text-transform: uppercase; }
        .main-header { font-size: 1.5rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.5rem; border-bottom: 3px solid #a57f2c; padding-bottom: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not GOOGLE_SHEET_ID:
    st.error("❌ Falta configurar `GOOGLE_SHEET_ID` en los secretos de Streamlit.")
    st.stop()

params = st.query_params
hoja_activa_tabla = params.get("hoja", "").strip()

if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Abra esta vista desde el Módulo Operativo.")
    st.stop()


# --- CARGA ULTRA RÁPIDA CON CACHÉ DE LARGO ALCANCE ---
@st.cache_data(ttl=60, show_spinner="Cargando censo en tiempo real...")
def cargar_y_procesar_hoja(spreadsheet_id, worksheet_name):
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(spreadsheet_id)
    ws = spreadsheet.worksheet(worksheet_name)
    
    data = ws.get_all_values()
    if len(data) < 14:
        return pd.DataFrame(), [], ws.id

    header1 = data[11] if len(data) > 11 else []
    header2 = data[12] if len(data) > 12 else []
    filas = data[13:]

    # Combinar encabezados de manera eficiente
    max_cols = max(len(header1), len(header2), 50)
    encabezados = []
    conteo = {}
    for idx in range(max_cols):
        v1 = header1[idx].strip() if idx < len(header1) else ""
        v2 = header2[idx].strip() if idx < len(header2) else ""
        
        if v1 and v2 and v1 != v2:
            col_str = f"{v1} - {v2}"
        elif v2:
            col_str = v2
        elif v1:
            col_str = v1
        else:
            col_str = f"Col_{idx+1}"
            
        if col_str in conteo:
            conteo[col_str] += 1
            col_str = f"{col_str}_{conteo[col_str]}"
        else:
            conteo[col_str] = 0
        encabezados.append(col_str)

    # Ajustar filas en matriz limpia
    filas_limpias = [f + [""] * max(0, len(encabezados) - len(f)) for f in filas]
    df = pd.DataFrame(filas_limpias, columns=encabezados)
    
    return df, filas, ws.id

try:
    df_censo, filas_raw, gid_hoja = cargar_y_procesar_hoja(GOOGLE_SHEET_ID, hoja_activa_tabla)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

if df_censo.empty:
    st.info("La jornada seleccionada no cuenta con registros suficientes.")
    st.stop()


# --- INTERFAZ FLUIDA TIPO EPIDEMIOMANAGER ---
st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

# Barra de acciones superiores fluidas
col_act1, col_act2, _ = st.columns([1, 1, 3])
with col_act1:
    if st.button("🔄 Actualizar Datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()

with col_act2:
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"]) if isinstance(st.secrets["GOOGLE_CREDENTIALS"], str) else st.secrets["GOOGLE_CREDENTIALS"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)
        if not creds.valid:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        
        url_export = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={gid_hoja}"
        req = urllib.request.Request(url_export, headers={"Authorization": f"Bearer {creds.token}"})
        with urllib.request.urlopen(req) as response:
            excel_bytes = response.read()

        st.download_button(
            label="📥 Descargar Excel Oficial",
            data=excel_bytes,
            file_name=f"{hoja_activa_tabla}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )
    except Exception:
        pass

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# Métricas rápidas calculadas directamente con Pandas (Cero bucles lentos)
total_registros = len([r for r in filas_raw if len(r) > 0 and str(r[0]).strip() != ""])
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Registros Totales en Censo</div><div class="metric-value">{total_registros}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Estado de Sincronización</div><div class="metric-value" style="color:#28a745;">En Línea (En Vivo)</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Motor de Vista</div><div class="metric-value" style="color:#1e5b4f;">Apache Arrow / Pandas</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# --- VISUALIZACIÓN ULTRA FLUIDA ---
st.markdown("##### 📋 Listado General de Pacientes (Vista de Alto Rendimiento)")
st.dataframe(
    df_censo,
    width="stretch",
    height=600,
    hide_index=True
)
