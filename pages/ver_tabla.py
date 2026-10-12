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

        /* --- ESTILO PARA FILAS VACUNADAS (VERDE SUAVE) EN ST.DATA_EDITOR --- */
        tr.fila-ag-aq-aplicada td {
            background-color: #e2f0d9 !important;
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
        cache_key = f"datos_hoja_{hoja_activa_tabla}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = ws.get_all_values()

        todos_los_datos = st.session_state[cache_key]

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

            # --- CONSTRUCCIÓN DE FILAS Y DETECCIÓN DE AG-AQ ---
            filas_procesadas = []
            mapeo_indices_pares = []
            filas_con_dosis_aplicada = set() # Para identificar qué índices visuales se deben pintar de verde

            contador_df_idx = 0
            for i in range(0, len(filas_tabla), 2):
                f1 = filas_tabla[i] if i < len(filas_tabla) else []
                f2 = filas_tabla[i+1] if i+1 < len(filas_tabla) else []

                f1_adj = f1 + [''] * max(0, len(encabezados_combinados) - len(f1))
                f2_adj = f2 + [''] * max(0, len(encabezados_combinados) - len(f2))

                # Comprobar si tiene alguna "X" en las columnas de AG-AQ (aproximadamente índices 32 al 42)
                tiene_aplicacion_ag_aq = False
                for col_idx in range(32, min(43, len(f1_adj))):
                    if str(f1_adj[col_idx]).strip().upper() == "X":
                        tiene_aplicacion_ag_aq = True
                        break

                # Si tiene dosis aplicada, marcamos ambas filas visuales (la principal y la de CURP) para pintarlas completas
                if tiene_aplicacion_ag_aq:
                    filas_con_dosis_aplicada.add(contador_df_idx)     # Fila 1 (Datos paciente)
                    filas_con_dosis_aplicada.add(contador_df_idx + 1) # Fila 2 (CURP)

                # Fila 1 principal del paciente
                fila_v1 = [False] + list(f1_adj[:len(encabezados_combinados)])
                # Fila 2 de CURP (La casilla de selección inicia vacía/False, pero la vincularemos lógicamente)
                fila_v2 = [False] + list(f2_adj[:len(encabezados_combinados)])

                filas_procesadas.append(fila_v1)
                filas_procesadas.append(fila_v2)
                
                mapeo_indices_pares.append(i)
                contador_df_idx += 2

            columnas_con_check = ["Seleccionar"] + encabezados_combinados
            df_tabla_segura = pd.DataFrame(filas_procesadas, columns=columnas_con_check)

            # Forzar la columna de selección a booleano para evitar bloqueos
            df_tabla_segura["Seleccionar"] = df_tabla_segura["Seleccionar"].astype(bool)

            st.session_state["mapeo_indices_pares"] = mapeo_indices_pares

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
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
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
                    st.error(f"No se pudo descargar el archivo: {err}")

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

            # --- BARRA SUPERIOR DE MÉTRICAS DINÁMICAS (8 COLUMNAS) ---
            m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
            
            with m1:
                st.markdown(f'<div class="metric-card-0"><div class="metric-label">Censo Total</div><div class="metric-value">{total_censo_registros}</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-card-1"><div class="metric-label">Pre-Registros</div><div class="metric-value">{total_preregistros}</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card-2"><div class="metric-label">Registros Hoy</div><div class="metric-value">{registros_nuevos_hoy}</div></div>', unsafe_allow_html=True)
            with m4:
                st.markdown(f'<div class="metric-card-3"><div class="metric-label">Aplicaciones</div><div class="metric-value">{total_aplicaciones}</div></div>', unsafe_allow_html=True)
            with m5:
                st.markdown(f'<div class="metric-card-4"><div class="metric-label">Sin Aplicar</div><div class="metric-value">{total_sin_aplicar}</div></div>', unsafe_allow_html=True)
            with m6:
                st.markdown(f'<div class="metric-card-5"><div class="metric-label">Influenza</div><div class="metric-value">{total_dosis_influenza}</div></div>', unsafe_allow_html=True)
            with m7:
                st.markdown(f'<div class="metric-card-6"><div class="metric-label">COVID</div><div class="metric-value">{total_dosis_covid}</div></div>', unsafe_allow_html=True)
            with m8:
                st.markdown(f'<div class="metric-card-7"><div class="metric-label">Simultáneas</div><div class="metric-value">{total_simultaneas}</div></div>', unsafe_allow_html=True)

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            
            # --- BOTÓN DE ELIMINACIÓN SUPERIOR ---
            col_btn1, col_btn_rest = st.columns([2, 5])
            with col_btn1:
                btn_eliminar = st.button("🗑️ Eliminar Paciente(s) Seleccionado(s)", type="primary", use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True) # Cierre del contenedor fijo superior

            # --- TABLA EDITABLE ---
            df_editado = st.data_editor(
                df_tabla_segura,
                use_container_width=True,
                height=550,
                hide_index=True,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn(
                        "Seleccionar",
                        help="Marque la casilla para seleccionar este paciente",
                        default=False,
                    )
                }
            )

            # --- SCRIPT JS PARA UNIFICAR LA SELECCIÓN Y COLOREAR LAS FILAS COMPLETAS EN EL DOM ---
            filas_verde_json = json.dumps(list(filas_con_dosis_aplicada))
            st.markdown(
                f"""
                <script>
                    const indicesVerdes = {filas_verde_json};
                    function actualizarInterfaz() {{
                        const doc = window.parent.document;
                        const filas = doc.querySelectorAll('div[data-testid="stDataEditor"] tbody tr, [data-testid="stTable"] tbody tr, .glideDataEditor tbody tr');
                        
                        filas.forEach((tr, index) => {{
                            // 1. Pintar fila completa si tiene AG-AQ aplicada
                            if (indicesVerdes.includes(index)) {{
                                tr.classList.add('fila-ag-aq-aplicada');
                            }}

                            // 2. Sincronizar selección de pares (Fila Principal de Paciente + Fila de CURP)
                            // Cada paciente ocupa dos filas consecutivas: 2k y 2k+1
                            if (index % 2 === 0) {{
                                const checkboxActual = tr.querySelector('input[type="checkbox"]');
                                const siguienteTr = filas[index + 1];
                                if (checkboxActual && siguienteTr) {{
                                    const checkboxSiguiente = siguienteTr.querySelector('input[type="checkbox"]');
                                    if (checkboxSiguiente) {{
                                        // Si el estado cambia en una, replicarlo en la otra para que actúen como una unidad
                                        if (checkboxActual.checked !== checkboxSiguiente.checked) {{
                                            checkboxSiguiente.checked = checkboxActual.checked;
                                            checkboxSiguiente.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        }}
                                    }}
                                }}
                            }}
                        }});
                    }}
                    
                    // Ejecutar periódicamente para asegurar sincronización con la renderización virtual
                    setTimeout(actualizarInterfaz, 500);
                    setTimeout(actualizarInterfaz, 1500);
                    
                    // Escuchar cambios de clics para respuesta inmediata
                    window.parent.document.addEventListener('click', () => {{
                        setTimeout(actualizarInterfaz, 200);
                    }});
                </script>
                """,
                unsafe_allow_html=True
            )

            # --- ACCIÓN DEL BOTÓN DE ELIMINACIÓN ---
            if btn_eliminar:
                # Detectar cualquier fila marcada (ya sea la principal o la de la CURP) y asociarla al paciente correspondiente (dividiendo por 2)
                filas_seleccionadas_verdaderas = df_editado[df_editado["Seleccionar"] == True].index.tolist()
                pacientes_a_eliminar = set([idx // 2 for idx in filas_seleccionadas_verdaderas])

                if not pacientes_a_eliminar:
                    st.warning("⚠️ No ha seleccionado ningún paciente para eliminar.")
                else:
                    try:
                        mapeo_indices = st.session_state.get("mapeo_indices_pares", [])
                        
                        filas_gs_a_borrar = []
                        for paciente_idx in pacientes_a_eliminar:
                            if paciente_idx < len(mapeo_indices):
                                idx_par_real = mapeo_indices[paciente_idx]
                                fila_fisica_1 = idx_par_real + 14
                                fila_fisica_2 = idx_par_real + 15
                                filas_gs_a_borrar.extend([fila_fisica_1, fila_fisica_2])

                        filas_gs_a_borrar = sorted(list(set(filas_gs_a_borrar)), reverse=True)

                        for fila_gs in filas_gs_a_borrar:
                            ws.delete_rows(fila_gs)

                        # --- RECALCULAR Y REORGANIZAR LA COLUMNA A (CONSECUTIVO) ---
                        datos_actualizados = ws.get_all_values()
                        if len(datos_actualizados) >= 14:
                            filas_actuales = datos_actualizados[13:]
                            
                            contador = 1
                            updates = []
                            for i in range(0, len(filas_actuales), 2):
                                row = filas_actuales[i]
                                if len(row) > 0 and row[0].strip() != "":
                                    cell_coord = gspread.utils.rowcol_to_a1(i + 14, 1)
                                    updates.append({
                                        'range': cell_coord,
                                        'values': [[str(contador)]]
                                    })
                                    contador += 1

                            if updates:
                                ws.batch_update(updates)

                        if cache_key in st.session_state:
                            del st.session_state[cache_key]

                        st.success(f"✅ Se eliminaron correctamente los registros seleccionados y se actualizó el consecutivo.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Ocurrió un error al intentar eliminar las filas en Google Sheets: {e}")

        else:
            st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura.")

    except Exception as ex:
        st.error(f"Error al conectar con la base de datos: {ex}")
