import streamlit as st
import pandas as pd
import gspread
import json
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global

# Aplicar configuración global
aplicar_configuracion_global("Vista Detallada de Censo", "📊")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; }
        [data-testid="stSidebar"] {display: none;}
        .main-header { font-size: 1.5rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not GOOGLE_SHEET_ID:
    st.error("❌ Falta configurar `GOOGLE_SHEET_ID` en los secretos.")
    st.stop()

# Obtener la hoja activa desde los parámetros de la URL enviados por 2_consulta_censia.py
hoja_activa_tabla = st.query_params.get("hoja", "").strip()

if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Abra esta vista desde el Módulo Operativo.")
    st.stop()


# --- CONEXIÓN DIRECTA Y LIMPIA A GOOGLE SHEETS ---
@st.cache_resource
def obtener_client_gspread_directo():
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)


@st.cache_data(ttl=30, show_spinner="Sincronizando con Google Sheets...")
def cargar_datos_directos(worksheet_name):
    client = obtener_client_gspread_directo()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    ws = spreadsheet.worksheet(worksheet_name)
    datos = ws.get_all_values()
    return datos, ws.id


try:
    datos_brutos, gid_hoja = cargar_datos_directos(hoja_activa_tabla)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

if len(datos_brutos) < 14:
    st.info("La jornada seleccionada aún no cuenta con suficientes registros.")
    st.stop()

# Estructura de cabeceras de la hoja de censo
header1 = datos_brutos[11] if len(datos_brutos) > 11 else []
header2 = datos_brutos[12] if len(datos_brutos) > 12 else []
filas_pacientes = datos_brutos[13:]

# Construir nombres de columnas combinados de forma limpia
max_cols = max(len(header1), len(header2), 50)
columnas_combinadas = []
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
    columnas_combinadas.append(col_str)

# Ajustar filas al ancho de columnas
filas_procesadas = [f + [""] * max(0, len(columnas_combinadas) - len(f)) for f in filas_pacientes]
df_censo = pd.DataFrame(filas_procesadas, columns=columnas_combinadas)


# --- RENDERIZADO DE LA VISTA ---
st.markdown(f'<p class="main-header">📊 Censo en Vivo — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

col_ctrl1, _ = st.columns([1, 4])
with col_ctrl1:
    if st.button("🔄 Actualizar Datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# Visualización limpia y veloz basada en Apache Arrow (cero retrasos ni bucles)
st.dataframe(
    df_censo,
    width="stretch",
    height=600,
    hide_index=True
)
