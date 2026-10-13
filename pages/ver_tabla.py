# ver_tabla.py
import streamlit as st
import pandas as pd
import gspread
import json
import datetime
import urllib.request
import streamlit.components.v1 as components
from google.oauth2 import service_account
from utils.sheets import obtener_cliente_gspread
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID
from concurrent.futures import ThreadPoolExecutor

# --------------------
# CONFIG y CSS
# --------------------
st.set_page_config(page_title="Vista Detallada de Censo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        [data-testid="stSidebar"] {display: none;}
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
        .main-header { font-size: 1.6rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0rem; border-bottom: 3px solid #a57f2c; padding-bottom: 4px; }
        .fixed-top-container { position: sticky; top: -20px; z-index: 999; background-color: #ffffff; padding-top: 5px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; }

        /* Ocultar overlays/loader molestos (selector amplio) */
        .stStatusWidget, div[role="status"], .stSpinner, .stLoading, [data-testid="stAppViewContainer"] > div[role="status"] {
            visibility: hidden !important;
            display: none !important;
        }
        .overlay, .stApp, .main {
            pointer-events: auto !important;
        }
        .stMainBlockContainer {
            transition: opacity 0.12s ease;
        }
    </style>
""",
    unsafe_allow_html=True,
)

if not GOOGLE_SHEET_ID:
    st.error("❌ Falta configurar `GOOGLE_SHEET_ID` en los secretos de Streamlit o en tu archivo de configuración.")
    st.stop()

# --------------------
# Parámetros y auto-refresh
# --------------------
params = st.query_params
hoja_activa_tabla = params.get("hoja", "").strip()
if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Por favor abra la vista desde el Módulo Operativo principal.")
    st.stop()

auto_refresh = st.checkbox("🔄 Actualización automática cada 10 s", value=False)
if auto_refresh:
    components.html(
        """
        <script>
            const INTERVAL_MS = 10000;
            setInterval(() => { window.location.reload(); }, INTERVAL_MS);
        </script>
        """,
        height=0,
    )

# --------------------
# Caching y helpers centralizados (integrados)
# --------------------
def build_cache_key(hoja):
    return f"cached_hoja_values::{hoja}"

@st.cache_resource
def get_client_cached():
    # retorna cliente gspread cacheado (reutilizable)
    return obtener_cliente_gspread()

@st.cache_resource
def get_spreadsheet_cached(spreadsheet_id):
    client = get_client_cached()
    return client.open_by_key(spreadsheet_id)

def get_creds_from_secrets():
    creds_dict = None
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw) if isinstance(raw, str) else raw
    else:
        for k in st.secrets:
            if k != "GOOGLE_SHEET_ID":
                creds_dict = dict(st.secrets[k])
                break
    if not creds_dict:
        raise KeyError("No se encontraron credenciales de servicio válidas en st.secrets.")
    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)

def load_sheet_minimal(spreadsheet, worksheet_name):
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        col_b = worksheet.col_values(2)
        if len(col_b) < 14:
            return [], [], [], worksheet
        last_idx = len(col_b)
        while last_idx >= 14 and (not str(col_b[last_idx - 1]).strip()):
            last_idx -= 1
        if last_idx < 14:
            return [], [], [], worksheet
        range_headers_1 = "A12:AX12"
        range_headers_2 = "A13:AX13"
        range_data = f"A14:AX{last_idx}"
        header1_rows = worksheet.get(range_headers_1)
        header2_rows = worksheet.get(range_headers_2)
        data_rows = worksheet.get(range_data)
        header1 = header1_rows[0] if header1_rows and len(header1_rows) > 0 else []
        header2 = header2_rows[0] if header2_rows and len(header2_rows) > 0 else []
        return header1, header2, data_rows or [], worksheet
    except Exception as e:
        st.error(f"Error al leer la hoja {worksheet_name}: {e}")
        st.exception(e)
        return [], [], [], None

@st.cache_data(ttl=30)
def load_sheet_minimal_cached(spreadsheet_id, worksheet_name):
    # lee usando la spreadsheet cacheada (pero la lectura de valores no se cachea internamente)
    spreadsheet = get_spreadsheet_cached(spreadsheet_id)
    header1, header2, data_rows, _ = load_sheet_minimal(spreadsheet, worksheet_name)
    return header1, header2, data_rows

# --------------------
# Procesamiento a DataFrame con coloreado
# --------------------
def preprocess_rows(rows, encabezados_combinados):
    filas_procesadas = []
    mapeo_indices_pares = []
    indices_filas_verdes = []
    contador_df_idx = 0
    for i in range(0, len(rows), 2):
        f1 = rows[i] if i < len(rows) else []
        f2 = rows[i + 1] if i + 1 < len(rows) else []
        f1_adj = f1 + [''] * max(0, len(encabezados_combinados) - len(f1))
        f2_adj = f2 + [''] * max(0, len(encabezados_combinados) - len(f2))
        tiene_aplicacion_ag_aq = False
        for col_idx in range(32, min(43, len(f1_adj))):
            if str(f1_adj[col_idx]).strip().upper() == "X":
                tiene_aplicacion_ag_aq = True
                break
        if tiene_aplicacion_ag_aq:
            indices_filas_verdes.extend([contador_df_idx, contador_df_idx + 1])
        fila_v1 = [False] + list(f1_adj[:len(encabezados_combinados)])
        fila_v2 = [None] + list(f2_adj[:len(encabezados_combinados)])
        filas_procesadas.append(fila_v1)
        filas_procesadas.append(fila_v2)
        mapeo_indices_pares.append(i)
        contador_df_idx += 2
    columnas_con_check = ["Seleccionar"] + encabezados_combinados
    df = pd.DataFrame(filas_procesadas, columns=columnas_con_check)
    return df, mapeo_indices_pares, indices_filas_verdes

def compute_metrics(rows):
    filas_principales = [rows[i] for i in range(0, len(rows), 2)]
    total_censo_registros = sum(1 for row in filas_principales if len(row) > 0 and str(row[0]).strip() != "")
    total_preregistros = 0
    registros_nuevos_hoy = 0
    total_aplicaciones = 0
    total_sin_aplicar = 0
    total_dosis_influenza = 0
    total_dosis_covid = 0
    total_simultaneas = 0
    fecha_hoy_str = datetime.datetime.now().strftime("%d/%m/%Y")
    for row in filas_principales:
        fecha_fila = row[48].strip() if len(row) > 48 else ""
        if fecha_fila == fecha_hoy_str:
            registros_nuevos_hoy += 1
        else:
            total_preregistros += 1
        tiene_aplicacion = any(str(row[i]).strip().upper() == "X" for i in range(32, min(43, len(row))))
        if tiene_aplicacion:
            total_aplicaciones += 1
        else:
            total_sin_aplicar += 1
        tiene_influenza = any(str(row[i]).strip().upper() == "X" for i in range(32, min(35, len(row))))
        if len(row) > 37:
            tiene_covid = any(str(row[i]).strip().upper() == "X" for i in range(37, min(40, len(row))))
        else:
            tiene_covid = False
        if tiene_influenza and not tiene_covid:
            total_dosis_influenza += 1
        elif tiene_covid and not tiene_influenza:
            total_dosis_covid += 1
        elif tiene_influenza and tiene_covid:
            total_simultaneas += 1
    return {
        "total_censo_registros": total_censo_registros,
        "total_preregistros": total_preregistros,
        "registros_nuevos_hoy": registros_nuevos_hoy,
        "total_aplicaciones": total_aplicaciones,
        "total_sin_aplicar": total_sin_aplicar,
        "total_dosis_influenza": total_dosis_influenza,
        "total_dosis_covid": total_dosis_covid,
        "total_simultaneas": total_simultaneas,
    }

# --------------------
# Estado inicial unificado (una sola lectura integrada)
# --------------------
cache_key = build_cache_key(hoja_activa_tabla)

try:
    spreadsheet = get_spreadsheet_cached(GOOGLE_SHEET_ID)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

if "visible_rows" not in st.session_state or st.session_state.get("hoja_loaded") != hoja_activa_tabla:
    # lectura inicial
    header1, header2, filas_tabla = load_sheet_minimal_cached(GOOGLE_SHEET_ID, hoja_activa_tabla)
    if not filas_tabla:
        st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura o folios.")
        st.stop()
    st.session_state["visible_rows"] = filas_tabla
    st.session_state["header1"] = header1
    st.session_state["header2"] = header2
    st.session_state["hoja_loaded"] = hoja_activa_tabla
else:
    filas_tabla = st.session_state["visible_rows"]
    header1 = st.session_state.get("header1", [])
    header2 = st.session_state.get("header2", [])

# construir encabezados combinados (integrado y único)
fila_cabecera_1 = header1
fila_cabecera_2 = header2
encabezados_combinados = []
conteo_nombres = {}
max_cols = max(len(fila_cabecera_1), len(fila_cabecera_2))
for idx in range(max_cols):
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

# preparar df visible y mapeos
df_tabla_segura, mapeo_indices_pares, indices_filas_verdes = preprocess_rows(filas_tabla, encabezados_combinados)
st.session_state["mapeo_indices_pares"] = mapeo_indices_pares

# métricas integradas
metrics = compute_metrics(filas_tabla)

# --------------------
# Thread worker para eliminar y re-lectura (background)
# --------------------
BACKGROUND_RESULTS = {}
def delete_rows_worker(spreadsheet_id, worksheet_name, filas_gs_a_borrar, cache_key_local):
    try:
        # crear cliente directo (no cache_resource) en el thread
        client_local = obtener_cliente_gspread()
        spreadsheet_local = client_local.open_by_key(spreadsheet_id)
        ws_local = spreadsheet_local.worksheet(worksheet_name)
        filas_sorted = sorted(list(set(filas_gs_a_borrar)), reverse=True)
        for fila_gs in filas_sorted:
            try:
                ws_local.delete_rows(fila_gs)
            except Exception:
                pass
        # reajustar consecutivo en columna A
        datos_actualizados = ws_local.get_all_values()
        if len(datos_actualizados) >= 14:
            filas_actuales = datos_actualizados[13:]
            contador = 1
            updates = []
            for i in range(0, len(filas_actuales), 2):
                row = filas_actuales[i]
                if len(row) > 0 and row[0].strip() != "":
                    a1 = gspread.utils.rowcol_to_a1(i + 14, 1)
                    updates.append({'range': a1, 'values': [[str(contador)]]})
                    contador += 1
            if updates:
                try:
                    ws_local.batch_update(updates)
                except Exception:
                    pass
        # leer nuevamente (no usar cached decorator aquí para forzar frescura)
        header1_r, header2_r, data_rows_r, _ = load_sheet_minimal(spreadsheet_local, worksheet_name)
        BACKGROUND_RESULTS[cache_key_local] = {
            "status": "done",
            "header1": header1_r,
            "header2": header2_r,
            "data_rows": data_rows_r
        }
    except Exception as e:
        BACKGROUND_RESULTS[cache_key_local] = {
            "status": "error",
            "error": str(e)
        }

# --------------------
# CABECERA FIJA y botones (integrados)
# --------------------
st.markdown('<div class="fixed-top-container">', unsafe_allow_html=True)
col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
with col_tit1:
    st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
with col_tit2:
    if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_reload_header"):
        # invalidar la vista local y recargar una sola vez (integrado)
        header1_new, header2_new, filas_new = load_sheet_minimal_cached(GOOGLE_SHEET_ID, hoja_activa_tabla)
        st.session_state["visible_rows"] = filas_new
        st.session_state["header1"] = header1_new
        st.session_state["header2"] = header2_new
        st.experimental_rerun()
with col_tit3:
    if st.button("📥 Preparar Descarga", key="btn_prepare_download"):
        with st.spinner("Preparando exportación..."):
            try:
                creds = get_creds_from_secrets()
                if not creds.valid:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                ws_ref = spreadsheet.worksheet(hoja_activa_tabla)
                gid_hoja = ws_ref.id
                url_export = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={gid_hoja}"
                req = urllib.request.Request(url_export, headers={'Authorization': f'Bearer {creds.token}'})
                with urllib.request.urlopen(req) as response:
                    excel_original_bytes = response.read()
                st.session_state["_cached_download_bytes"] = excel_original_bytes
                st.success("Archivo preparado. Usa el botón de descarga a continuación.")
            except Exception as err:
                st.error(f"No se pudo preparar el archivo: {err}")

    if st.session_state.get("_cached_download_bytes"):
        st.download_button(
            label="📥 Descargar Hoja Excel",
            data=st.session_state["_cached_download_bytes"],
            file_name=f"{hoja_activa_tabla}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
st.markdown("</div>", unsafe_allow_html=True)

# métricas visuales
st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
st.markdown(f'<div class="metric-card-0"><div class="metric-label">Censo Total</div><div class="metric-value">{metrics["total_censo_registros"]}</div></div>', unsafe_allow_html=True, unsafe_allow_html_kwargs={})
with m2:
    st.markdown(f'<div class="metric-card-1"><div class="metric-label">Pre-Registros</div><div class="metric-value">{metrics["total_preregistros"]}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card-2"><div class="metric-label">Registros Hoy</div><div class="metric-value">{metrics["registros_nuevos_hoy"]}</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card-3"><div class="metric-label">Aplicaciones</div><div class="metric-value">{metrics["total_aplicaciones"]}</div></div>', unsafe_allow_html=True)
with m5:
    st.markdown(f'<div class="metric-card-4"><div class="metric-label">Sin Aplicar</div><div class="metric-value">{metrics["total_sin_aplicar"]}</div></div>', unsafe_allow_html=True)
with m6:
    st.markdown(f'<div class="metric-card-5"><div class="metric-label">Influenza</div><div class="metric-value">{metrics["total_dosis_influenza"]}</div></div>', unsafe_allow_html=True)
with m7:
    st.markdown(f'<div class="metric-card-6"><div class="metric-label">COVID</div><div class="metric-value">{metrics["total_dosis_covid"]}</div></div>', unsafe_allow_html=True)
with m8:
    st.markdown(f'<div class="metric-card-7"><div class="metric-label">Simultáneas</div><div class="metric-value">{metrics["total_simultaneas"]}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
col_btn1, _ = st.columns([2, 5])
with col_btn1:
    btn_eliminar = st.button("🗑️ Eliminar Paciente(s) Seleccionado(s)", type="primary", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --------------------
# Render tabla interactiva (con coloreado y flujo integrado)
# --------------------
@st.fragment
def render_seccion_tabla_interactiva():
    # coloreado por filas verdes
    def color_filas_completas(row):
        if row.name in indices_filas_verdes:
            return ['background-color: #e2f0d9; color: #111111'] * len(row)
        return [''] * len(row)

    # aplicar estilo y pasar al editor
    df_estilizado = df_tabla_segura.style.apply(color_filas_completas, axis=1)

    column_configs = {
        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", help="Marque la casilla para seleccionar este paciente", default=False)
    }
    for col in encabezados_combinados:
        if col != "Seleccionar":
            column_configs[col] = st.column_config.TextColumn(col, disabled=True)

    df_editado = st.data_editor(
        df_estilizado,
        use_container_width=True,
        height=550,
        hide_index=True,
        column_config=column_configs,
        key="editor_tabla_censo"
    )

    # si hay un resultado de background, aplicarlo (sin bloquear)
    if cache_key in globals() and cache_key in BACKGROUND_RESULTS:
        res = BACKGROUND_RESULTS.pop(cache_key)
        if res.get("status") == "done":
            st.session_state["header1"] = res["header1"]
            st.session_state["header2"] = res["header2"]
            st.session_state["visible_rows"] = res["data_rows"]
            # actualizar la vista local y forzar rerun corto para recargar todo con los datos remotos ya aplicados
            st.success("✅ Eliminación sincronizada con Google Sheets. Vista actualizada.")
            st.experimental_rerun()
        else:
            st.error(f"❌ Error en sincronización de fondo: {res.get('error')}")

    # botón eliminar: flujo optimista + worker en background (integrado)
    if btn_eliminar:
        # obtener índices marcados del editor
        try:
            # el editor retorna el DataFrame en session_state bajo la key; leerlo
            df_state = st.session_state.get("editor_tabla_censo")
            if df_state is None:
                # fallback a df_editado
                df_state = df_editado
            if isinstance(df_state, pd.DataFrame):
                df_current = df_state
            else:
                df_current = pd.DataFrame(df_state)
            indices_marcados = df_current[df_current["Seleccionar"] == True].index.tolist()
            pacientes_a_eliminar = set(idx // 2 for idx in indices_marcados)
            if not pacientes_a_eliminar:
                st.warning("⚠️ No ha seleccionado ningún paciente para marcar en las casillas.")
                return

            # calcular filas físicas a borrar usando mapeo actual
            mapeo_indices = st.session_state.get("mapeo_indices_pares", [])
            filas_gs_a_borrar = []
            for paciente_idx in sorted(pacientes_a_eliminar, reverse=True):
                if paciente_idx < len(mapeo_indices):
                    idx_par_real = mapeo_indices[paciente_idx]
                    filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])

            # actualización optimista local: quitar pares de visible_rows
            visible_rows = list(st.session_state.get("visible_rows", filas_tabla))
            for paciente_idx in sorted(pacientes_a_eliminar, reverse=True):
                if paciente_idx < len(mapeo_indices):
                    idx_par_real = mapeo_indices[paciente_idx]
                    if idx_par_real < len(visible_rows):
                        del visible_rows[idx_par_real: idx_par_real + 2]

            st.session_state["visible_rows"] = visible_rows

            # reconstruir df local inmediatamente para que la UI refleje la eliminación
            df_nuevo, mapeo_nuevo, indices_verdes_nuevo = preprocess_rows(visible_rows, encabezados_combinados)
            st.session_state["mapeo_indices_pares"] = mapeo_nuevo
            # escribir df visible local para que el siguiente run lo use
            st.session_state["df_visible_local"] = df_nuevo

            # lanzar worker en background para borrar realmente en Google Sheets y recuperar la hoja
            if "delete_executor" not in st.session_state:
                st.session_state["delete_executor"] = ThreadPoolExecutor(max_workers=1)
            future = st.session_state["delete_executor"].submit(
                delete_rows_worker,
                GOOGLE_SHEET_ID,
                hoja_activa_tabla,
                filas_gs_a_borrar,
                cache_key
            )
            st.session_state["delete_future"] = True  # marcador simple
            st.success("✅ Eliminación aplicada en la vista. Sincronizando con Google Sheets en segundo plano...")

        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar la eliminación: {e}")

render_seccion_tabla_interactiva()
