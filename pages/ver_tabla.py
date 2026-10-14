import streamlit as st
import pandas as pd
import gspread
import json
import io
import datetime
import urllib.request
import logging
from google.oauth2 import service_account
from utils.sheets import obtener_cliente_gspread
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID

logging.basicConfig(level=logging.INFO)

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


# --- CARGA OPTIMIZADA Y CACHEADA ---
@st.cache_data(ttl=300, show_spinner=False)
def load_and_build_dataset(spreadsheet_id: str, worksheet_name: str):
    """Carga la hoja, normaliza encabezados y construye el DataFrame filtrado y métricas.
    Esta función está cacheada para evitar cargas repetidas costosas.
    Retorna: encabezados_filtrados, df_tabla_segura, mapeo_indices_pares, indices_filas_verdes, metricas, gid_hoja
    """
    try:
        client_c = obtener_cliente_gspread()
        spreadsheet_c = client_c.open_by_key(spreadsheet_id)
        worksheet = spreadsheet_c.worksheet(worksheet_name)

        # Leemos la columna B para determinar último índice de datos tal como antes
        col_b = worksheet.col_values(2)

        if len(col_b) < 14:
            return [], pd.DataFrame(), [], set(), {}, worksheet.id

        last_idx = len(col_b)
        while last_idx >= 14 and (not str(col_b[last_idx - 1]).strip()):
            last_idx -= 1
        if last_idx < 14:
            return [], pd.DataFrame(), [], set(), {}, worksheet.id

        filas_data_count = last_idx - 13
        if filas_data_count % 2 != 0:
            last_idx += 1

        range_headers_1 = "A12:AX12"
        range_headers_2 = "A13:AX13"
        range_data = f"A14:AX{last_idx}"

        header1_rows = worksheet.get(range_headers_1)
        header2_rows = worksheet.get(range_headers_2)
        data_rows = worksheet.get(range_data)

        header1 = header1_rows[0] if header1_rows and len(header1_rows) > 0 else []
        header2 = header2_rows[0] if header2_rows and len(header2_rows) > 0 else []

        # Construcción de encabezados combinados (idéntico a antes)
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

        # Procesamiento de filas: pares
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

        rows = data_rows or []

        for i in range(0, len(rows), 2):
            f1 = rows[i] if i < len(rows) else []
            f2 = rows[i + 1] if i + 1 < len(rows) else []

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

        # Construir DataFrame final
        columnas_con_check = ["SELECCIONAR"] + encabezados_filtrados
        df_tabla_segura = pd.DataFrame(filas_procesadas, columns=columnas_con_check)

        return encabezados_filtrados, df_tabla_segura, mapeo_indices_pares, indices_filas_verdes, metricas, worksheet.id

    except Exception as e:
        logging.exception("Error al cargar y construir dataset")
        st.error(f"Error al leer la hoja {worksheet_name}: {e}")
        return [], pd.DataFrame(), [], set(), {}, None


# Cargar (cacheado)
key_estado_filas = f"filas_cargadas_piso_{hoja_activa_tabla}"

if key_estado_filas not in st.session_state:
    encabezados_combinados, df_tabla_segura, mapeo_indices_pares, indices_filas_verdes, metricas, gid_hoja = load_and_build_dataset(GOOGLE_SHEET_ID, hoja_activa_tabla)
    st.session_state[key_estado_filas] = df_tabla_segura
    st.session_state[f"header1_{hoja_activa_tabla}"] = encabezados_combinados
    st.session_state[f"mapeo_{hoja_activa_tabla}"] = mapeo_indices_pares
    st.session_state[f"indices_verdes_{hoja_activa_tabla}"] = indices_filas_verdes
    st.session_state[f"metricas_{hoja_activa_tabla}"] = metricas
    st.session_state[f"gid_{hoja_activa_tabla}"] = gid_hoja
else:
    df_tabla_segura = st.session_state[key_estado_filas]
    encabezados_combinados = st.session_state.get(f"header1_{hoja_activa_tabla}", [])
    mapeo_indices_pares = st.session_state.get(f"mapeo_{hoja_activa_tabla}", [])
    indices_filas_verdes = st.session_state.get(f"indices_verdes_{hoja_activa_tabla}", set())
    metricas = st.session_state.get(f"metricas_{hoja_activa_tabla}", {})
    gid_hoja = st.session_state.get(f"gid_{hoja_activa_tabla}")

if df_tabla_segura is None or df_tabla_segura.empty:
    st.info("La jornada seleccionada no cuenta con registros suficientes.")
    st.stop()

# --- INTERFAZ FIJA ---
st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)

col_btn1, col_btn2, _ = st.columns([1.2, 1.2, 2.6])
with col_btn1:
    if st.button("🔄 Actualizar Datos", width="stretch", key="btn_reload_header"):
        # limpiar cache y forzar recarga
        try:
            st.cache_data.clear()
        except Exception:
            pass
        for k in list(st.session_state.keys()):
            if str(k).startswith(f"filas_cargadas_piso_{hoja_activa_tabla}") or str(k).startswith(f"header1_{hoja_activa_tabla}"):
                del st.session_state[k]
        st.experimental_rerun()

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
            width="stretch",
        )
    except Exception as err:
        logging.exception("Error al preparar descarga Excel")
        st.error(f"No se pudo descargar el archivo: {err}")

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# Métricas
m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
with m1: st.markdown(f'<div class="metric-card-0"><div class="metric-label">Censo Total</div><div class="metric-value">{metricas.get("total_censo_registros", 0)}</div></div>', unsafe_allow_html=True)
with m2: st.markdown(f'<div class="metric-card-1"><div class="metric-label">Pre-Registros</div><div class="metric-value">{metricas.get("total_preregistros", 0)}</div></div>', unsafe_allow_html=True)
with m3: st.markdown(f'<div class="metric-card-2"><div class="metric-label">Registros Hoy</div><div class="metric-value">{metricas.get("registros_nuevos_hoy", 0)}</div></div>', unsafe_allow_html=True)
with m4: st.markdown(f'<div class="metric-card-3"><div class="metric-label">Aplicaciones</div><div class="metric-value">{metricas.get("total_aplicaciones", 0)}</div></div>', unsafe_allow_html=True)
with m5: st.markdown(f'<div class="metric-card-4"><div class="metric-label">Sin Aplicar</div><div class="metric-value">{metricas.get("total_sin_aplicar", 0)}</div></div>', unsafe_allow_html=True)
with m6: st.markdown(f'<div class="metric-card-5"><div class="metric-label">Influenza</div><div class="metric-value">{metricas.get("total_dosis_influenza", 0)}</div></div>', unsafe_allow_html=True)
with m7: st.markdown(f'<div class="metric-card-6"><div class="metric-label">COVID</div><div class="metric-value">{metricas.get("total_dosis_covid", 0)}</div></div>', unsafe_allow_html=True)
with m8: st.markdown(f'<div class="metric-card-7"><div class="metric-label">Simultáneas</div><div class="metric-value">{metricas.get("total_simultaneas", 0)}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

col_del, _ = st.columns([2, 5])
with col_del:
    btn_eliminar = st.button("🗑️ Eliminar Paciente(s) Seleccionado(s)", type="primary", width="stretch")

st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

# --- VISTA ESTILIZADA (READ-ONLY) Y PAGINACIÓN LIGERA ---
# Para evitar lag mostramos por defecto sólo las primeras N filas estilizadas.
if "rows_preview_limit" not in st.session_state:
    st.session_state["rows_preview_limit"] = 200

rows_limit = st.session_state["rows_preview_limit"]

st.markdown("#### Vista previa (solo lectura, filas resaltadas)")

def style_preview(df, indices_verdes):
    def _row_style(row):
        if row.name in indices_verdes:
            return ["background-color: #e2f0d9; color: #111111"] * len(row)
        return [""] * len(row)
    return df.style.apply(_row_style, axis=1)

with st.container():
    try:
        preview_df = df_tabla_segura.head(rows_limit)
        st.dataframe(style_preview(preview_df, indices_filas_verdes), use_container_width=True)
    except Exception as e:
        logging.exception("Error al renderizar vista previa")
        st.dataframe(df_tabla_segura.head(100), use_container_width=True)

col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("Mostrar más filas (+200)", key="btn_more_rows"):
        st.session_state["rows_preview_limit"] += 200
        st.experimental_rerun()
with col_b:
    if st.button("Restablecer vista", key="btn_reset_preview"):
        st.session_state["rows_preview_limit"] = 200
        st.experimental_rerun()

st.markdown("---")

# --- AREA DE EDICIÓN: tabla ligera para seleccionar filas ---
# Creamos un DataFrame "ligero" con sólo las columnas necesarias para edición y selección
editable_columns = ["SELECCIONAR"] + encabezados_combinados[:12]  # limitar a columnas principales para edición

df_editable = df_tabla_segura[editable_columns].copy()
# Asegurar booleanos en SELECCIONAR
if df_editable["SELECCIONAR"].dtype != bool:
    df_editable["SELECCIONAR"] = df_editable["SELECCIONAR"].fillna(False).astype(bool)

st.markdown("#### Editar / Seleccionar (solo columnas esenciales para evitar lag)")
# data_editor con un número de filas mayor pero sin estilo para mantener fluidez
try:
    df_editor_result = st.data_editor(
        df_editable,
        width="stretch",
        height=420,
        hide_index=True,
        key="editor_tabla_censo_optimized",
    )
except Exception:
    # compatibilidad con versiones antiguas
    df_editor_result = df_editable

# --- ACCIÓN DE ELIMINACIÓN CON CONFIRMACIÓN Y SPINNER ---
if btn_eliminar:
    indices_marcados = df_editor_result[df_editor_result["SELECCIONAR"] == True].index.tolist()
    pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}

    if not pacientes_a_eliminar:
        st.warning("⚠️ No ha seleccionado ningún paciente para eliminar.")
    else:
        # Pedir confirmación explícita para evitar clicks accidentales
        with st.expander("Confirmar eliminación"):
            st.write(f"Se han seleccionado {len(pacientes_a_eliminar)} paciente(s). Marca la casilla para confirmar y luego pulsa 'Confirmar eliminación'.")
            confirm = st.checkbox("Confirmo que deseo eliminar las filas seleccionadas", key="confirm_delete_checkbox")
            if st.button("Confirmar eliminación", key="confirm_delete_button") and confirm:
                try:
                    with st.spinner("Eliminando filas en Google Sheets..."):
                        filas_actualizadas = list(st.session_state[key_estado_filas])
                        pacientes_sorted = sorted(pacientes_a_eliminar, reverse=True)
                        filas_gs_a_borrar = []

                        for paciente_idx in pacientes_sorted:
                            if paciente_idx < len(st.session_state.get(f"mapeo_{hoja_activa_tabla}", [])):
                                idx_par_real = st.session_state[f"mapeo_{hoja_activa_tabla}"][paciente_idx]
                                filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])
                                # borrar localmente
                                del filas_actualizadas[idx_par_real:idx_par_real + 2]

                        # Actualizar sesión local inmediatamente (optimista)
                        st.session_state[key_estado_filas] = filas_actualizadas

                        # Conectar a Google Sheets y borrar (manejo robusto con logging)
                        client = obtener_cliente_gspread()
                        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
                        ws = spreadsheet.worksheet(hoja_activa_tabla)

                        filas_gs_a_borrar = sorted(set(filas_gs_a_borrar), reverse=True)
                        failed_deletes = []
                        for fila_gs in filas_gs_a_borrar:
                            try:
                                ws.delete_rows(fila_gs)
                            except Exception as e:
                                logging.exception(f"Error borrando fila {fila_gs}")
                                failed_deletes.append((fila_gs, str(e)))

                        # Reindexar folios de forma segura
                        try:
                            datos_actualizados = ws.get_all_values()
                            if len(datos_actualizados) >= 14:
                                filas_actuales = datos_actualizados[13:]
                                contador = 1
                                updates = []
                                # recorrer filas reales y actualizar la primera columna si corresponde
                                real_row_number = 14
                                for i in range(0, len(filas_actuales), 2):
                                    row = filas_actuales[i]
                                    if len(row) > 0 and row[0].strip() != "":
                                        a1 = gspread.utils.rowcol_to_a1(real_row_number + i, 1)
                                        updates.append({"range": a1, "values": [[str(contador)]]})
                                        contador += 1
                                if updates:
                                    try:
                                        ws.batch_update(updates)
                                    except Exception:
                                        logging.exception("Error aplicando batch_update de reindexado")
                        except Exception:
                            logging.exception("Error obteniendo datos actualizados para reindexado")

                        if failed_deletes:
                            st.error(f"Algunas filas no pudieron borrarse: {failed_deletes}")
                        else:
                            st.success("✅ Eliminación completada correctamente.")

                        # Forzar recarga ligera: limpiar cache y recargar sólo el dataset
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        # eliminar claves relacionadas y recargar
                        keys_to_remove = [k for k in st.session_state.keys() if str(k).startswith(f"filas_cargadas_piso_{hoja_activa_tabla}") or str(k).startswith(f"header1_{hoja_activa_tabla}") or str(k).startswith(f"mapeo_{hoja_activa_tabla}")]
                        for k in keys_to_remove:
                            del st.session_state[k]
                        st.experimental_rerun()

                except Exception as e:
                    logging.exception("Error en flujo de eliminación")
                    st.error(f"❌ Ocurrió un error al intentar eliminar: {e}")

