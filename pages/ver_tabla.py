import streamlit as st
import pandas as pd
import gspread
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global

# --- CONFIGURACIÓN DE PANTALLA ANCHA PARA OCUPAR TODO EL NAVEGADOR ---
st.set_page_config(page_title="Vista Detallada de Censo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .main-header { font-size: 1.8rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.5rem; border-bottom: 3px solid #a57f2c; padding-bottom: 6px; }
        [data-testid="stSidebar"] {display: none;}
    </style>
""",
    unsafe_allow_html=True,
)

# --- CAPTURA DE LA HOJA AUTORIZADA DESDE LA URL ---
params = st.query_params
hoja_activa_tabla = params.get("hoja", "").strip()

if not hoja_activa_tabla:
    st.warning("⚠️ No se especificó ninguna jornada activa. Por favor abra la vista desde el Módulo Operativo principal.")
else:
    try:
        scope = GOOGLE_SCOPES
        if "GOOGLE_CREDENTIALS" in st.secrets:
            raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        elif "gpex" in st.secrets:
            creds_dict = dict(st.secrets["gpex"])
        else:
            primera_llave = list(st.secrets.keys())[0]
            creds_dict = dict(st.secrets[primera_llave])

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Obtenemos la hoja de trabajo activa para extraer su ID único (gid) y asegurar la descarga exacta
        ws = spreadsheet.worksheet(hoja_activa_tabla)
        gid_hoja = ws.id

        # --- ENCABEZADO CON BOTONES DE ACTUALIZAR Y DESCARGA EXCEL ORIGINAL DE LA HOJA ---
        col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
        with col_tit1:
            st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
        with col_tit2:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar Datos", use_container_width=True, help="Recargar datos más recientes desde Google Sheets"):
                st.rerun()

        # --- BOTÓN DE DESCARGA EXCEL DIRECTO DE LA PESTAÑA ESPECÍFICA EN GOOGLE SHEETS ---
        with col_tit3:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            try:
                import urllib.request
                # URL de exportación nativa de Google Sheets para una pestaña específica usando su gid
                url_export_xlsx = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx&gid={gid_hoja}"
                
                req = urllib.request.Request(
                    url_export_xlsx,
                    headers={'Authorization': f'Bearer {creds.token}'}
                )
                
                # Refrescar credenciales si es necesario
                if not creds.valid:
                    creds.refresh(google.auth.transport.requests.Request())
                    req.add_header('Authorization', f'Bearer {creds.token}')

                with urllib.request.urlopen(req) as response:
                    excel_original_bytes = response.read()

                st.download_button(
                    label="📥 Descargar Hoja Excel",
                    data=excel_original_bytes,
                    file_name=f"{hoja_activa_tabla}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help=f"Descargar la hoja '{hoja_activa_tabla}' exactamente con el formato y estructura original de Google Sheets"
                )
            except Exception as err:
                # Fallback alternativo mediante openpyxl conservando la estructura de filas y cabeceras institucionales
                try:
                    output = io.BytesIO()
                    todos_los_datos_full = ws.get_all_values()
                    df_full = pd.DataFrame(todos_los_datos_full)
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_full.to_excel(writer, sheet_name=hoja_activa_tabla, header=False, index=False)
                    excel_fallback_bytes = output.getvalue()

                    st.download_button(
                        label="📥 Descargar Hoja Excel",
                        data=excel_fallback_bytes,
                        file_name=f"{hoja_activa_tabla}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        help=f"Descargar la hoja '{hoja_activa_tabla}' en formato Excel"
                    )
                except Exception as ex_inner:
                    st.error(f"No se pudo generar el archivo Excel: {ex_inner}")

        todos_los_datos = ws.get_all_values()

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

            filas_ajustadas = [row[:len(encabezados_combinados)] + [''] * max(0, len(encabezados_combinados) - len(row)) for row in filas_tabla]

            df_tabla_segura = pd.DataFrame(filas_ajustadas, columns=encabezados_combinados)
            
            st.caption(f"Total de registros activos en censo: **{len(filas_tabla)}** — 🟢 *Los registros en verde indican aplicación registrada (rango AG-AQ).*")
            
            # --- FUNCIÓN DE ESTILIZACIÓN ESTRICTA (RANGO AG A AQ) ---
            def colorear_completados(row):
                completado = False
                try:
                    for i in range(32, min(43, len(row))):
                        val = str(row.iloc[i]).strip().upper()
                        if val == "X":
                            completado = True
                            break
                except:
                    pass
                
                return ['background-color: #d4edda; color: #155724; font-weight: 600;' if completado else '' for _ in row]

            df_estilizado = df_tabla_segura.style.apply(colorear_completados, axis=1)

            st.dataframe(
                df_estilizado,
                use_container_width=True,
                height=750,
                hide_index=True
            )
        else:
            st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura.")

    except Exception as ex:
        st.error(f"Error al conectar con la base de datos: {ex}")
