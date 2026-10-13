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


# --- CARGA OPTIMIZADA CON CACHÉ ---
@st.cache_data(ttl=60, show_spinner=False)
def cargar_y_procesar_hoja(spreadsheet_id, worksheet_name):
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(spreadsheet_id)
    ws = spreadsheet.worksheet(worksheet_name)
    
    data = ws.get_all_values()
    if len(data) < 14:
        return [], [], [], ws.id

    header1 = data[11] if len(data) > 11 else []
    header2 = data[12] if len(data) > 12 else []
    filas = data[13:]
    return header1, header2, filas, ws.id

# Permitir refrescar filas desde la sesión si se eliminó algo en vivo
if f"filas_override_{hoja_activa_tabla}" not in st.session_state:
    try:
        header1, header2, filas_tabla, gid_hoja = cargar_y_procesar_hoja(GOOGLE_SHEET_ID, hoja_activa_tabla)
        st.session_state[f"filas_override_{hoja_activa_tabla}"] = filas_tabla
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        st.stop()
else:
    # Obtener cabeceras rápidas para mantener la estructura
    try:
        client = obtener_cliente_gspread()
        ws = client.open_by_key(GOOGLE_SHEET_ID).worksheet(hoja_activa_tabla)
        data = ws.get_all_values()
        header1 = data[11] if len(data) > 11 else []
        header2 = data[12] if len(data) > 12 else []
        gid_hoja = ws.id
        filas_tabla = st.session_state[f"filas_override_{hoja_activa_tabla}"]
    except Exception:
        header1, header2, filas_tabla, gid_hoja = [], [], [], ""

if not filas_tabla:
    st.info("La jornada seleccionada no cuenta con registros suficientes.")
    st.stop()


# --- CONSTRUCCIÓN DEL DATASET Y MÉTRICAS ---
def construir_dataset_y_metricas(filas_tabla, header1, header2):
    encabezados_combinados = []
    conteo_nombres = {}
    max_cols = max(len(header1), len(header2), 50)

    for idx in range(max_cols):
        val1 = header1[idx].strip() if idx < len(header1) else ""
        val2 = header2[idx].strip() if idx < len(header2) else ""

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

    filas_procesadas = []
    mapeo_indices_pares = []
    indices_filas_verdes = set()

    total_censo_registros = 0
    total_preregistros = 0
    registros_nuevos_hoy = 0
    total_aplicaciones = 0
    total_sin_aplicar = 0
    total_dosis_influenza = 0
    total_dosis_covid = 0
    total_simultaneas = 0
    fecha_hoy_str = datetime.datetime.now().strftime("%d/%m/%Y")

    for i in range(0, len(filas_tabla), 2):
        f1 = filas_tabla[i] if i < len(filas_tabla) else []
        f2 = filas_tabla[i + 1] if i + 1 < len(filas_tabla) else []
        
        f1_adj = f1 + [""] * max(0, len(encabezados_combinados) - len(f1))
        f2_adj = f2 + [""] * max(0, len(encabezados_combinados) - len(f2))

        if len(f1_adj) > 0 and str(f1_adj[0]).strip() != "":
            total_censo_registros += 1

            fecha_fila = f1_adj[48].strip() if len(f1_adj) > 48 else ""
            if fecha_fila == fecha_hoy_str:
                registros_nuevos_hoy += 1
            else:
                total_preregistros += 1

            tiene_aplicacion = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj))))
            if tiene_aplicacion:
                total_aplicaciones += 1
            else:
                total_sin_aplicar += 1

            tiene_influenza = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(35, len(f1_adj))))
            tiene_covid = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(37, min(40, len(f1_adj)))) if len(f1_adj) > 37 else False

            if tiene_influenza and not tiene_covid:
                total_dosis_influenza += 1
            elif tiene_covid and not tiene_influenza:
                total_dosis_covid += 1
            elif tiene_influenza and tiene_covid:
                total_simultaneas += 1

        if any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj)))):
            indices_filas_verdes.add(len(filas_procesadas))
            indices_filas_verdes.add(len(filas_procesadas) + 1)

        fila_v1 = [False] + list(f1_adj[:len(encabezados_combinados)])
        fila_v2 = [None] + list(f2_adj[:len(encabezados_combinados)])

        filas_procesadas.append(fila_v1)
        filas_procesadas.append(fila_v2)
        mapeo_indices_pares.append(i)

    metricas = {
        "total_censo_registros": total_censo_registros,
        "total_preregistros": total_preregistros,
        "registros_nuevos_hoy": registros_nuevos_hoy,
        "total_aplicaciones": total_aplicaciones,
        "total_sin_aplicar": total_sin_aplicar,
        "total_dosis_influenza": total_dosis_influenza,
        "total_dosis_covid": total_dosis_covid,
        "total_simultaneas": total_simultaneas,
    }

    return encabezados_combinados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas

encabezados_combinados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas = construir_dataset_y_metricas(filas_tabla, header1, header2)
columnas_con_check = ["Seleccionar"] + encabezados_combinados
df_tabla_segura = pd.DataFrame(filas_procesadas, columns=columnas_con_check)


# --- INTERFAZ FLUIDA ---
st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

col_btn1, col_btn2, _ = st.columns([1.2, 1.2, 2.6])
with col_btn1:
    if st.button("🔄 Actualizar Datos", width="stretch", key="btn_reload_header"):
        st.cache_data.clear()
        if f"filas_override_{hoja_activa_tabla}" in st.session_state:
            del st.session_state[f"filas_override_{hoja_activa_tabla}"]
        st.rerun()

with col_btn2:
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"]) if isinstance(st.secrets["GOOGLE_CREDENTIALS"], str) else st.secrets["GOOGLE_CREDENTIALS"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)
        if not creds.valid:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

        client_exp = obtener_cliente_gspread()
        ws_exp = client_exp.open_by_key(GOOGLE_SHEET_ID).worksheet(hoja_activa_tabla)
        url_export = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={ws_exp.id}"
        req = urllib.request.Request(url_export, headers={"Authorization": f"Bearer {creds.token}"})

        with urllib.request.urlopen(req) as response:
            excel_bytes = response.read()

        st.download_button(
            label="📥 Descargar Hoja Excel",
            data=excel_bytes,
            file_name=f"{hoja_activa_tabla}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    except Exception as err:
        st.error(f"No se pudo descargar el archivo: {err}")

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# Métricas
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

col_del, _ = st.columns([2, 5])
with col_del:
    btn_eliminar = st.button("🗑️ Eliminar Paciente(s) Seleccionado(s)", type="primary", width="stretch")

st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

def color_filas_completas(row):
    if row.name in indices_filas_verdes:
        return ["background-color: #e2f0d9; color: #111111"] * len(row)
    return [""] * len(row)

df_estilizado = df_tabla_segura.style.apply(color_filas_completas, axis=1)

column_configs = {
    "Seleccionar": st.column_config.CheckboxColumn(
        "Seleccionar",
        help="Marque la casilla para seleccionar este paciente",
        default=False,
    )
}
for col in encabezados_combinados:
    if col != "Seleccionar":
        column_configs[col] = st.column_config.TextColumn(col, disabled=True)

df_editado = st.data_editor(
    df_estilizado,
    width="stretch",
    height=550,
    hide_index=True,
    column_config=column_configs,
    key="editor_tabla_censo",
)

# --- ELIMINACIÓN INSTANTÁNEA EN VIVO (ACTUALIZACIÓN OPTIMISTA) ---
if btn_eliminar:
    indices_marcados = df_editado[df_editado["Seleccionar"] == True].index.tolist()
    pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}

    if not pacientes_a_eliminar:
        st.warning("⚠️ No ha seleccionado ningún paciente para eliminar.")
    else:
        try:
            pacientes_sorted = sorted(pacientes_a_eliminar, reverse=True)
            
            # 1. Actualizar memoria local en vivo de forma instantánea
            filas_actualizadas = list(filas_tabla)
            filas_gs_a_borrar = []
            
            for paciente_idx in pacientes_sorted:
                if paciente_idx < len(mapeo_indices_pares):
                    idx_par_real = mapeo_indices_pares[paciente_idx]
                    filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])
                    # Remover las dos filas del paciente en memoria local de inmediato
                    del filas_actualizadas[idx_par_real:idx_par_real + 2]

            # Guardar el cambio visual inmediato en la sesión
            st.session_state[f"filas_override_{hoja_activa_tabla}"] = filas_actuales
            
            # 2. Sincronizar en Google Sheets de fondo de manera rápida
            client = obtener_cliente_gspread()
            ws = client.open_by_key(GOOGLE_SHEET_ID).worksheet(hoja_activa_tabla)
            
            filas_gs_a_borrar = sorted(set(filas_gs_a_borrar), reverse=True)
            for fila_gs in filas_gs_a_borrar:
                try:
                    ws.delete_rows(fila_gs)
                except Exception:
                    pass

            # Reordenar contadores de folios en Google Sheets
            datos_actuales_gs = ws.get_all_values()
            if len(datos_actuales_gs) >= 14:
                filas_s = datos_actuales_gs[13:]
                contador = 1
                updates = []
                for i in range(0, len(filas_s), 2):
                    row = filas_s[i]
                    if len(row) > 0 and row[0].strip() != "":
                        a1 = gspread.utils.rowcol_to_a1(i + 14, 1)
                        updates.append({"range": a1, "values": [[str(contador)]]})
                        contador += 1
                if updates:
                    try:
                        ws.batch_update(updates)
                    except Exception:
                        pass

            st.success("⚡ ¡Eliminado en vivo y sincronizado!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al eliminar en Google Sheets: {e}")
