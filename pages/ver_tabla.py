import streamlit as st
import pandas as pd
import gspread
import json
import io
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
        
        /* Estilo visual sincronizado para el par de filas del paciente con aplicación (#e2f0d9) */
        [data-testid="stDataEditor"] tr[data-row-highlight="true"] td {
            background-color: #e2f0d9 !important;
            color: #111111 !important;
        }
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


# --- FUNCIÓN DE CREDENCIALES PARA DESCARGA AUTENTICADA ---
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


# --- CARGA ROBUSTA RESPETANDO BLOQUES DE 2 FILAS POR PACIENTE ---
@st.cache_data(ttl=30, show_spinner="Sincronizando con Google Sheets...")
def load_sheet_minimal_cached(spreadsheet_id, worksheet_name):
    try:
        client_c = obtener_cliente_gspread()
        spreadsheet_c = client_c.open_by_key(spreadsheet_id)
        worksheet = spreadsheet_c.worksheet(worksheet_name)
        
        all_values = worksheet.get_all_values()
        if len(all_values) < 14:
            return [], [], [], worksheet.id

        header1 = all_values[11] if len(all_values) > 11 else [] # Fila 12
        header2 = all_values[12] if len(all_values) > 12 else [] # Fila 13
        data_rows = all_values[13:] # Desde la fila 14 en adelante

        # Garantizar estrictamente que los datos vayan en pares exactos de 2 filas por paciente
        if len(data_rows) % 2 != 0:
            data_rows.append([""] * max(len(header1), 50))

        return header1, header2, data_rows, worksheet.id

    except Exception as e:
        st.error(f"Error al leer la hoja {worksheet_name}: {e}")
        return [], [], [], None


key_estado_filas = f"filas_cargadas_piso_{hoja_activa_tabla}"

if key_estado_filas not in st.session_state:
    header1, header2, filas_tabla, gid_hoja = load_sheet_minimal_cached(GOOGLE_SHEET_ID, hoja_activa_tabla)
    st.session_state[key_estado_filas] = filas_tabla
    st.session_state[f"header1_{hoja_activa_tabla}"] = header1
    st.session_state[f"header2_{hoja_activa_tabla}"] = header2
    st.session_state[f"gid_{hoja_activa_tabla}"] = gid_hoja
else:
    header1 = st.session_state[f"header1_{hoja_activa_tabla}"]
    header2 = st.session_state[f"header2_{hoja_activa_tabla}"]
    filas_tabla = st.session_state[key_estado_filas]
    gid_hoja = st.session_state[f"gid_{hoja_activa_tabla}"]

if not filas_tabla:
    st.info("La jornada seleccionada no cuenta con registros suficientes.")
    st.stop()


# --- CONSTRUCCIÓN DEL DATASET Y MÉTRICAS (BASADO EN PARES DE 2 FILAS) ---
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

    # Recorrido estricto de 2 en 2 filas (cada iteración es un paciente completo)
    for i in range(0, len(filas_tabla), 2):
        f1 = filas_tabla[i] if i < len(filas_tabla) else []
        f2 = filas_tabla[i + 1] if i + 1 < len(filas_tabla) else []
        
        f1_adj = f1 + [""] * max(0, len(encabezados_combinados) - len(f1))
        f2_adj = f2 + [""] * max(0, len(encabezados_combinados) - len(f2))

        # Consideramos registro válido si cualquiera de las dos filas del bloque tiene datos en sus columnas principales
        tiene_datos_bloque = any(str(val).strip() != "" for val in f1_adj[:5]) or any(str(val).strip() != "" for val in f2_adj[:5])

        if tiene_datos_bloque:
            total_censo_registros += 1

            fecha_fila = f1_adj[48].strip() if len(f1_adj) > 48 else ""
            if fecha_fila == fecha_hoy_str:
                registros_nuevos_hoy += 1
            else:
                total_preregistros += 1

            tiene_aplicacion = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj)))) or \
                               any(str(f2_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f2_adj))))
            if tiene_aplicacion:
                total_aplicaciones += 1
            else:
                total_sin_aplicar += 1

            tiene_influenza = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(35, len(f1_adj)))) or \
                              any(str(f2_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(35, len(f2_adj))))
            tiene_covid = (any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(37, min(40, len(f1_adj)))) if len(f1_adj) > 37 else False) or \
                          (any(str(f2_adj[col_idx]).strip().upper() == "X" for col_idx in range(37, min(40, len(f2_adj)))) if len(f2_adj) > 37 else False)

            if tiene_influenza and not tiene_covid:
                total_dosis_influenza += 1
            elif tiene_covid and not tiene_influenza:
                total_dosis_covid += 1
            elif tiene_influenza and tiene_covid:
                total_simultaneas += 1

        # Si el paciente tiene aplicación, marcamos las 2 filas correspondientes en verde
        if any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj)))) or \
           any(str(f2_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f2_adj)))):
            indices_filas_verdes.add(len(filas_procesadas))
            indices_filas_verdes.add(len(filas_procesadas) + 1)

        indices_deseados = list(range(0, 12)) + list(range(32, 43))

        f1_filtrado = [f1_adj[idx] if idx < len(f1_adj) else "" for idx in indices_deseados]
        f2_filtrado = [f2_adj[idx] if idx < len(f2_adj) else "" for idx in indices_deseados]

        fila_v1 = [False] + f1_filtrado
        fila_v2 = [None] + f2_filtrado

        filas_procesadas.append(fila_v1)
        filas_procesadas.append(fila_v2)
        mapeo_indices_pares.append(i)

    indices_deseados = list(range(0, 12)) + list(range(32, 43))
    encabezados_filtrados = [encabezados_combinados[idx] for idx in indices_deseados if idx < len(encabezados_combinados)]

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

    return encabezados_filtrados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas

encabezados_combinados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas = construir_dataset_y_metricas(filas_tabla, header1, header2)
columnas_con_check = ["SELECCIONAR"] + encabezados_combinados
df_tabla_segura = pd.DataFrame(filas_procesadas, columns=columnas_con_check)


# --- INTERFAZ FIJA ---
st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

col_btn1, col_btn2, _ = st.columns([1.2, 1.2, 2.6])
with col_btn1:
    if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_reload_header"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if "piso" in key or "header" in key or "gid" in key:
                del st.session_state[key]
        st.rerun()

with col_btn2:
    try:
        creds = get_creds_from_secrets()
        if not creds.valid:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

        url_export = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={gid_hoja}"
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


# --- FRAGMENTO INTERACTIVO: ELIMINACIÓN EXACTA DE BLOQUES DE 2 FILAS Y SINCRONIZACIÓN ---
@st.fragment
def render_bloque_interactivo_tabla():
    col_del, _ = st.columns([2, 5])
    with col_del:
        btn_eliminar = st.button("🗑️ Eliminar Paciente(s) Seleccionado(s)", type="primary", use_container_width=True)

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    column_configs = {
        "SELECCIONAR": st.column_config.CheckboxColumn(
            "¿Seleccionar?",
            help="Marque la casilla para seleccionar este paciente",
            default=False,
        )
    }
    for col in encabezados_combinados:
        column_configs[col] = st.column_config.TextColumn(col, disabled=True)

    df_editado = st.data_editor(
        df_tabla_segura,
        use_container_width=True,
        height=550,
        hide_index=True,
        column_config=column_configs,
        key="editor_tabla_censo",
    )

    filas_verdes_js_list = list(indices_filas_verdes)
    st.markdown(
        f"""
        <script>
            const targetRows = {filas_verdes_js_list};
            const doc = window.parent.document;
            const rows = doc.querySelectorAll('[data-testid="stDataEditor"] tbody tr');
            rows.forEach((row, index) => {{
                if (targetRows.includes(index)) {{
                    row.setAttribute('data-row-highlight', 'true');
                }}
            }});
        </script>
        """,
        unsafe_allow_html=True,
    )

    if btn_eliminar:
        indices_marcados = df_editado[df_editado["SELECCIONAR"] == True].index.tolist()
        # Cada paciente equivale a un par de filas (índice dividido entre 2)
        pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}

        if not pacientes_a_eliminar:
            st.warning("⚠️ No ha seleccionado ningún paciente para eliminar.")
        else:
            try:
                with st.spinner("Eliminando el bloque de 2 filas por paciente en Google Sheets..."):
                    pacientes_sorted = sorted(pacientes_a_eliminar, reverse=True)
                    filas_gs_a_borrar = []
                    
                    for paciente_idx in pacientes_sorted:
                        if paciente_idx < len(mapeo_indices_pares):
                            idx_par_real = mapeo_indices_pares[paciente_idx]
                            # Como cada paciente ocupa estrictamente 2 filas físicas a partir de la fila 14:
                            # Fila principal = idx_par_real + 14
                            # Fila complementaria = idx_par_real + 15
                            filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])

                    # 1. Conectar a Google Sheets
                    client = obtener_cliente_gspread()
                    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
                    ws = spreadsheet.worksheet(hoja_activa_tabla)

                    # 2. Borrar las filas físicas en orden estrictamente descendente para no alterar los índices previos
                    filas_gs_a_borrar = sorted(set(filas_gs_a_borrar), reverse=True)
                    for fila_gs in filas_gs_a_borrar:
                        try:
                            ws.delete_rows(fila_gs)
                        except Exception:
                            pass

                    # 3. Reordenar de forma limpia los contadores de folios de los pacientes restantes (en bloques de 2)
                    datos_actualizados = ws.get_all_values()
                    if len(datos_actualizados) >= 14:
                        filas_actuales = datos_actualizados[13:]
                        contador = 1
                        updates = []
                        for i in range(0, len(filas_actuales), 2):
                            row = filas_actuales[i]
                            if len(row) > 0 and row[0].strip() != "":
                                a1 = gspread.utils.rowcol_to_a1(i + 14, 1)
                                updates.append({"range": a1, "values": [[str(contador)]]})
                                contador += 1
                        if updates:
                            try:
                                ws.batch_update(updates)
                            except Exception:
                                pass

                    # 4. Limpiar caché completa y estado para refrescar al instante con los datos reales
                    st.cache_data.clear()
                    for key in list(st.session_state.keys()):
                        if "piso" in key or "header" in key or "gid" in key:
                            del st.session_state[key]

                st.success("✅ Pacientes eliminados correctamente de Google Sheets en tiempo real.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Ocurrió un error al intentar eliminar: {e}")

render_bloque_interactivo_tabla()
