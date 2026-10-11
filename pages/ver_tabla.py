import streamlit as st
import pandas as pd
import gspread
import json
import io
from google.oauth2 import service_account
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

        # --- ENCABEZADO CON BOTONES DE ACTUALIZAR Y DESCARGA EXCEL DE LA HOJA ACTUAL ---
        col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
        with col_tit1:
            st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
        with col_tit2:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar Datos", use_container_width=True, help="Recargar datos más recientes desde Google Sheets"):
                st.rerun()

        ws = spreadsheet.worksheet(hoja_activa_tabla)
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

            # --- LÓGICA PARA EXPORTAR EXCLUSIVAMENTE ESTA HOJA EN .XLSX ---
            with col_tit3:
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # Escribimos las cabeceras originales tal como están en las filas 12 y 13 del sheets opcionalmente, 
                        # o el dataframe estructurado limpio con los nombres de columna combinados:
                        df_tabla_segura.to_excel(writer, sheet_name=hoja_activa_tabla, index=False)
                    
                    excel_data = output.getvalue()

                    st.download_button(
                        label="📥 Descargar Hoja Excel",
                        data=excel_data,
                        file_name=f"{hoja_activa_tabla}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        help=f"Descargar únicamente la hoja autorizada '{hoja_activa_tabla}' en formato Excel"
                    )
                except Exception as err:
                    st.error(f"Error al preparar la descarga de la hoja: {err}")
            
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
