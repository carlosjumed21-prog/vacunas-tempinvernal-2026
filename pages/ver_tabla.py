import streamlit as st
import pandas as pd
import urllib.request
from google.auth.transport.requests import Request
from utils.logica_ver_tabla import (
    obtener_sheet_id_activo,
    get_creds_from_secrets,
    load_sheet_minimal_cached,
    construir_dataset_y_metricas,
    eliminar_pacientes_seleccionados
)

# --- CONFIGURACIÓN DE PANTALLA ANCHA ---
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
        .main-header { font-size: 1.5rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.5rem; border-bottom: 3px solid #a57f2c; padding-bottom: 6px; }
        
        /* Botón rojo para el popover de eliminación superior */
        div[data-testid="stPopover"] > button {
            background-color: #dc3545 !important;
            color: white !important;
            border-color: #dc3545 !important;
        }
        div[data-testid="stPopover"] > button:hover {
            background-color: #bb2d3b !important;
            border-color: #b02a37 !important;
            color: white !important;
        }
        div[data-testid="stPopover"] > button:disabled {
            background-color: #e9ecef !important;
            color: #adb5bd !important;
            border-color: #ced4da !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

params = st.query_params
hoja_activa_tabla = params.get("hoja", "").strip()
unidad_param = params.get("unidad", "").strip()

sheet_id_tabla = obtener_sheet_id_activo(hoja_activa_tabla, unidad_param)

if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Abra esta vista desde el Módulo Operativo.")
    st.stop()

key_estado_filas = f"filas_cargadas_piso_{sheet_id_tabla}_{hoja_activa_tabla}"

if key_estado_filas not in st.session_state:
    header1, header2, filas_tabla, gid_hoja, error_msg = load_sheet_minimal_cached(sheet_id_tabla, hoja_activa_tabla)
    if error_msg:
        st.error(error_msg)
        st.stop()
    st.session_state[key_estado_filas] = filas_tabla
    st.session_state[f"header1_{hoja_activa_tabla}"] = header1
    st.session_state[f"header2_{hoja_activa_tabla}"] = header2
    st.session_state[f"gid_{hoja_activa_tabla}"] = gid_hoja
else:
    header1 = st.session_state.get(f"header1_{hoja_activa_tabla}", [])
    header2 = st.session_state.get(f"header2_{hoja_activa_tabla}", [])
    filas_tabla = st.session_state.get(key_estado_filas, [])
    gid_hoja = st.session_state.get(f"gid_{hoja_activa_tabla}", None)

if not filas_tabla:
    st.info("La jornada seleccionada no cuenta con registros suficientes o la estructura de la tabla no coincide (se esperan datos a partir de la fila 14).")
    st.stop()

encabezados_combinados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas = construir_dataset_y_metricas(filas_tabla, header1, header2)
columnas_con_check = ["SELECCIONAR"] + encabezados_combinados
df_tabla_segura = pd.DataFrame(filas_procesadas, columns=columnas_con_check)

# Detectar si hay filas seleccionadas en el estado actual del editor
editor_df = st.session_state.get("editor_tabla_censo", df_tabla_segura)
hay_seleccionados = False
if isinstance(editor_df, pd.DataFrame) and "SELECCIONAR" in editor_df.columns:
    hay_seleccionados = editor_df["SELECCIONAR"].eq(True).any()

# --- INTERFAZ FIJA ---
st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

# --- BOTONES SUPERIORES: ACTUALIZAR, ELIMINAR (BLOQUEADO SI NO HAY SELECCIÓN) Y DESCARGAR ---
col_btn1, col_btn2, col_btn3, _ = st.columns([1.2, 1.2, 1.2, 2.0])

with col_btn1:
    if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_reload_header"):
        st.cache_data.clear()
        if key_estado_filas in st.session_state:
            del st.session_state[key_estado_filas]
        st.rerun()

with col_btn2:
    with st.popover("🗑️ Eliminar Seleccionado(s)", use_container_width=True, disabled=not hay_seleccionados):
        st.markdown("### ⚠️ Confirmación de Seguridad")
        st.markdown("¿Desea eliminar permanentemente los pacientes seleccionados de la hoja de Google Sheets?")
        
        col_pop1, col_pop2 = st.columns(2)
        with col_pop1:
            if st.button("Sí, confirmar", type="primary", use_container_width=True, key="btn_confirmar_popover"):
                indices_marcados = []
                if isinstance(editor_df, pd.DataFrame) and "SELECCIONAR" in editor_df.columns:
                    indices_marcados = editor_df[editor_df["SELECCIONAR"] == True].index.tolist()

                pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}
                
                if not pacientes_a_eliminar:
                    st.warning("⚠️ No ha seleccionado ningún paciente.")
                else:
                    try:
                        with st.spinner("Sincronizando con Google Sheets..."):
                            eliminar_pacientes_seleccionados(
                                sheet_id_tabla, 
                                hoja_activa_tabla, 
                                indices_marcados, 
                                mapeo_indices_pares, 
                                filas_tabla, 
                                key_estado_filas
                            )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al intentar eliminar: {e}")
        with col_pop2:
            if st.button("Cancelar", use_container_width=True, key="btn_cancelar_popover"):
                st.rerun()

with col_btn3:
    try:
        creds = get_creds_from_secrets()
        if not creds.valid:
            creds.refresh(Request())

        url_export = f"https://docs.google.com/spreadsheets/d/{sheet_id_tabla}/export?format=xlsx&gid={gid_hoja}"
        req = urllib.request.Request(url_export, headers={"Authorization": f"Bearer {creds.token}"})

        with urllib.request.urlopen(req) as response:
            excel_original_bytes = response.read()

        st.download_button(
            label="📥 Descargar Hoja Excel",
            data=excel_original_bytes,
            file_name=f"{hoja_activa_tabla}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as err:
        st.error(f"No se pudo descargar el archivo: {err}")

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# --- TABLERO DE MÉTRICAS ARRIBA ---
m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
with m1: st.markdown(f'<div class="metric-card-0"><div class="metric-label">Censo Total</div><div class="metric-value">{metricas["total_censo_registros"]}</div></div>', unsafe_allow_html=True)
with m2: st.markdown(f'<div class="metric-card-1"><div class="metric-label">Pre-Registros</div><div class="metric-value">{metricas["total_preregistros"]}</div></div>', unsafe_allow_html=True)
with m3: st.markdown(f'<div class="metric-card-2"><div class="metric-label">Registros Hoy</div><div class="metric-value">{metricas["registros_nuevos_hoy"]}</div></div>', unsafe_allow_html=True)
with m4: st.markdown(f'<div class="metric-card-3"><div class="metric-label">Aplicaciones</div><div class="metric-value">{metricas["total_aplicaciones"]}</div></div>', unsafe_allow_html=True)
with m5: st.markdown(f'<div class="metric-card-4"><div class="metric-label">Sin Aplicar</div><div class="metric-value">{metricas["total_sin_aplicar"]}</div></div>', unsafe_allow_html=True)
with m6: st.markdown(f'<div class="metric-card-5"><div class="metric-label">Influenza</div><div class="metric-value">{metricas["total_dosis_influenza"]}</div></div>', unsafe_allow_html=True)
with m7: st.markdown(f'<div class="metric-card-6"><div class="metric-label">COVID</div><div class="metric-value">{metricas["total_dosis_covid"]}</div></div>', unsafe_allow_html=True)
with m8: st.markdown(f'<div class="metric-card-7"><div class="metric-label">Simultáneas</div><div class="metric-value">{metricas["total_simultaneas"]}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# --- FRAGMENTO AISLADO PARA LA TABLA ---
@st.fragment
def render_tabla_con_estilos():
    def color_filas_completas(row):
        if row.name in indices_filas_verdes:
            return ["background-color: #e2f0d9; color: #111111"] * len(row)
        return [""] * len(row)

    df_estilizado = df_tabla_segura.style.apply(color_filas_completas, axis=1)

    column_configs = {
        "SELECCIONAR": st.column_config.CheckboxColumn(
            "¿Seleccionar?",
            help="Marque la casilla para seleccionar este paciente",
            default=False,
        )
    }
    for col in encabezados_combinados:
        column_configs[col] = st.column_config.TextColumn(col, disabled=True)

    return st.data_editor(
        df_estilizado,
        use_container_width=True,
        height=550,
        hide_index=True,
        column_config=column_configs,
        key="editor_tabla_censo",
    )

df_editado = render_tabla_con_estilos()
