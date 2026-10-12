import streamlit as st
import pandas as pd
import gspread
import json
import datetime
import urllib.request
import urllib.parse
from google.oauth2 import service_account

# --- INTENTO DE IMPORTACIÓN SEGURA DE CONFIG ---
try:
    from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global
except ImportError:
    GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    GOOGLE_SHEET_ID = st.secrets.get("GOOGLE_SHEET_ID", "")

# --- CONFIGURACIÓN DE PANTALLA ANCHA PARA OCUPAR TODO EL NAVEGADOR ---
st.set_page_config(page_title="Vista Detallada de Censo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        /* --- ELIMINAR ESPACIOS EN BLANCO SUPERIORES DE STREAMLIT --- */
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        [data-testid="stSidebar"] {display: none;}
        
        /* --- ESTILOS DE TARJETAS DE MÉTRICAS --- */
        .metric-card-0 { background-color: #f1f3f4; border: 2px solid #5f6368; padding: 10px; border-radius: 8px; text-align: center; } 
        .metric-card-1 { background-color: #eaf2f0; border: 2px solid #1e5b4f; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-2 { background-color: #e8f4fd; border: 2px solid #2980b9; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-3 { background-color: #d4edda; border: 2px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-4 { background-color: #f8d7da; border: 2px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; } 
        .metric-card-5 { background-color: #fff3cd; border: 2px solid #ffc107; padding: 10px; border-radius: 8px; text-align: center; } 
        .metric-card-6 { background-color: #e1f5fe; border: 2px solid #0288d1; padding: 10px; border-radius: 8px; text-align: center; } 
        .metric-card-7 { background-color: #f3e5f5; border: 2px solid #8e24aa; padding: 10px; border-radius: 8px; text-align: center; } 

        .metric-value { font-size: 1.3rem; font-weight: 800; color: #161a1d; }
        .metric-label { font-size: 0.75rem; font-weight: 700; color: #333333; text-transform: uppercase; }

        .main-header { 
            font-size: 1.6rem !important; 
            font-weight: 800 !important; 
            color: #1e5b4f !important; 
            margin-bottom: 0rem; 
            border-bottom: 3px solid #a57f2c; 
            padding-bottom: 4px; 
        }

        /* --- CONTENEDOR FIJO Y PEGADO ARRIBA --- */
        .fixed-top-container {
            position: sticky;
            top: -20px;
            z-index: 999;
            background-color: #ffffff;
            padding-top: 5px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# --- VALIDACIÓN DE SECRETOS Y CREDENCIALES ---
if not GOOGLE_SHEET_ID:
    st.error("❌ Falta configurar `GOOGLE_SHEET_ID` en los secretos de Streamlit o en tu archivo de configuración.")
    st.stop()

# --- CAPTURA DE LA HOJA AUTORIZADA DESDE LA URL ---
params = st.query_params
hoja_activa_tabla = params.get("hoja", "").strip()

if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Por favor abra la vista desde el Módulo Operativo principal.")
else:
    try:
        scope = GOOGLE_SCOPES
        creds_dict = None
        
        if "GOOGLE_CREDENTIALS" in st.secrets:
            raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        elif "gpex" in st.secrets:
            creds_dict = dict(st.secrets["gpex"])
        elif len(st.secrets.keys()) > 0:
            primera_llave = list(st.secrets.keys())[0]
            if primera_llave != "GOOGLE_SHEET_ID":
                creds_dict = dict(st.secrets[primera_llave])

        if not creds_dict:
            raise KeyError("No se encontraron credenciales de servicio válidas en `st.secrets`.")

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        ws = spreadsheet.worksheet(hoja_activa_tabla)
        gid_hoja = ws.id

        # --- GESTIÓN DE CACHÉ PARA EVITAR LÍMITE DE CUOTA (429) ---
        if f"datos_hoja_{hoja_activa_tabla}" not in st.session_state or st.button("🔄 Actualizar Datos", key="btn_reload"):
            st.session_state[f"datos_hoja_{hoja_activa_tabla}"] = ws.get_all_values()
            # Limpiar caché al forzar recarga
            st.rerun()

        todos_los_datos = st.session_state[f"datos_hoja_{hoja_activa_tabla}"]

        if len(todos_los_datos) >= 14:
            fila_cabecera_1 = todos_los_datos[11]
            fila_cabecera_2 = todos_los_datos[12]
            filas_tabla = todos_los_datos[13:]
            
            encabezados_combinados = []
            conteo_nombres = {}
            
            for idx in range(max(len(fila_cabecera_1), len(fila_cabecera_2))):
                val1 = fila_cabecera_1[idx].strip() if idx < len(fila_cabecera_1) else ""
                val2 = fila_cabecera_2[idx].strip() if idx < len(fila_cabecera_2) else ""
                
                if val1 and val2 and val1 != val2:
                    col_str = f"{val1} - {val2}"
                elif val2:
                    col_str = val2
                elif val1:
                    col_str = val1
                else:
                    col_str = f"Col_{idx+1}"
                
                if col_str in conteo_nombres:
                    conteo_nombres[col_str] += 1
                    col_str = f"{col_str}_{conteo_nombres[col_str]}"
                else:
                    conteo_nombres[col_str] = 0
                
                encabezados_combinados.append(col_str)

            # --- AGRUPAR CADA PAR DE FILAS (PACIENTE) EN UNA SOLA FILA PARA EL EDITOR ---
            filas_agrupadas = []
            indices_pares_reales = []
            
            for i in range(0, len(filas_tabla), 2):
                fila_1 = filas_tabla[i] if i < len(filas_tabla) else []
                f1_adj = fila_1 + [''] * max(0, len(encabezados_combinados) - len(fila_1))
                
                fila_base = list(f1_adj[:len(encabezados_combinados)])
                filas_agrupadas.append(fila_base)
                indices_pares_reales.append(i)

            df_tabla_segura = pd.DataFrame(filas_agrupadas, columns=encabezados_combinados)
            df_tabla_segura.insert(0, "Seleccionar", False)

            st.session_state["indices_pares_reales"] = indices_pares_reales

            # --- CÁLCULO DE MÉTRICAS DINÁMICAS (SALTANDO FILAS DE CURP) ---
            filas_principales = [filas_tabla[i] for i in range(0, len(filas_tabla), 2)]

            total_censo_registros = 0
            total_preregistros = 0
            registros_nuevos_hoy = 0
            total_aplicaciones = 0
            total_sin_aplicar = 0
            total_dosis_influenza = 0
            total_dosis_covid = 0
            total_simultaneas = 0

            fecha_hoy_str = datetime.datetime.now().strftime("%d/%m/%Y")

            for row in filas_principales:
                val_col_a = str(row[0]).strip() if len(row) > 0 else ""
                if val_col_a != "":
                    total_censo_registros += 1

                fecha_fila = row[48].strip() if len(row) > 48 else ""

                if fecha_fila == fecha_hoy_str:
                    registros_nuevos_hoy += 1
                else:
                    total_preregistros += 1

                tiene_aplicacion = False
                for i in range(32, min(43, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        tiene_aplicacion = True
                        break
                
                if tiene_aplicacion:
                    total_aplicaciones += 1
                else:
                    total_sin_aplicar += 1

                tiene_influenza = False
                for i in range(32, min(35, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        tiene_influenza = True
                        break

                tiene_covid = False
                for i in range(37, min(40, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        tiene_covid = True
                        break

                if tiene_influenza and not tiene_covid:
                    total_dosis_influenza += 1
                elif tiene_covid and not tiene_influenza:
                    total_dosis_covid += 1
                elif tiene_influenza and tiene_covid:
                    total_simultaneas += 1

            # --- ZONA FIJA SUPERIOR (ENCABEZADO Y MÉTRICAS) ---
            st.markdown('<div class="fixed-top-container">', unsafe_allow_html=True)

            col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
            with col_tit1:
                st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
            with col_tit2:
                if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_reload_header", help="Recargar datos más recientes desde Google Sheets"):
                    if f"datos_hoja_{hoja_activa_tabla}" in st.session_state:
                        del st.session_state[f"datos_hoja_{hoja_activa_tabla}"]
                    st.rerun()

            with col_tit3:
                try:
                    if not creds.valid:
                        from google.auth.transport.requests import Request
                        creds.refresh(Request())

                    url_export = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={gid_hoja}"
                    req = urllib.request.Request(
                        url_export,
                        headers={'Authorization': f'Bearer {creds.token}'}
                    )

                    with urllib.request.urlopen(req) as response:
                        excel_original_bytes = response.read()

                    st.download_button(
                        label="📥 Descargar Hoja Excel",
                        data=excel_original_bytes,
                        file_name=f"{hoja_activa_tabla}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        help=f"Descargar la hoja '{hoja_activa_tabla}' con el diseño original de Google Sheets"
                    )
                except Exception as err:
                    st.error(f"No se pudo descargar el archivo: {
