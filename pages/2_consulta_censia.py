import streamlit as st
import pandas as pd
import gspread
import json
import datetime
import urllib.request
from google.oauth2 import service_account
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global

aplicar_configuracion_global("Vista Detallada de Censo", "📊")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        [data-testid="stSidebar"] {display: none;}
        .main-header { font-size: 1.5rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.5rem; border-bottom: 3px solid #a57f2c; padding-bottom: 6px; }
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
    st.warning("⚠️ No se especificó ninguna jornada activa.")
    st.stop()

@st.cache_resource
def obtener_client_gspread_cacheado():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)

# --- CARGA ULTRA RÁPIDA CACHEADA (TTL Amplio para evitar retardos) ---
@st.cache_data(ttl=300, show_spinner="Cargando datos de la hoja...")
def cargar_datos_optimizados(spreadsheet_id, worksheet_name):
    client = obtener_client_gspread_cacheado()
    spreadsheet = client.open_by_key(spreadsheet_id)
    ws = spreadsheet.worksheet(worksheet_name)
    
    # Obtener valores directamente en bloque optimizado
    data = ws.get_all_values()
    if len(data) < 14:
        return [], [], [], ws.id
    
    header1 = data[11] if len(data) > 11 else []
    header2 = data[12] if len(data) > 12 else []
    filas = data[13:]
    return header1, header2, filas, ws.id

try:
    header1, header2, filas_tabla, gid_hoja = cargar_datos_optimizados(GOOGLE_SHEET_ID, hoja_activa_tabla)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

if not filas_tabla:
    st.info("La jornada no cuenta con registros suficientes.")
    st.stop()

# Procesamiento rápido con Pandas en memoria (Cero lentitud)
max_cols = max(len(header1), len(header2), 50)
cols = [f"Col_{i}" for i in range(max_cols)]

# Rellenar filas para que tengan el mismo ancho
filas_limpias = [f + [""] * (max_cols - len(f)) for f in filas_tabla]
df = pd.DataFrame(filas_limpias, columns=cols)

st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

# Botones de control rápido
c1, c2, _ = st.columns([1, 1, 3])
with c1:
    if st.button("🔄 Actualizar Datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()

with c2:
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
            label="📥 Descargar Excel",
            data=excel_bytes,
            file_name=f"{hoja_activa_tabla}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )
    except Exception:
        pass

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# Visualización ultrarrápida con st.dataframe nativo (Mucho más veloz que st.data_editor para tablas grandes)
st.dataframe(
    df,
    width="stretch",
    height=600,
    hide_index=True
)
