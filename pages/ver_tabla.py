
import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2 import service_account
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global

aplicar_configuracion_global("Vista Detallada de Censo", "📊")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .main-header { font-size: 2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 1rem; border-bottom: 3px solid #a57f2c; padding-bottom: 8px; }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="main-header">📊 Censo General de Pacientes (Vista Exclusiva)</p>', unsafe_allow_html=True)

# Validamos sesión activa
if "autenticado_consulta" not in st.session_state or not st.session_state.autenticado_consulta:
    st.warning("⚠️ No ha iniciado sesión en el módulo operativo. Por favor regrese al módulo principal e inicie sesión.")
else:
    correo_sesion = st.session_state.get("correo_operativo_asignado", "")
    
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

        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        todas_las_hojas = spreadsheet.worksheets()
        hojas_plantillas_excluir = ["CENSO NOMINAL", "CENSO", "Influenza", "COVID"]
        h_autorizadas = []

        if correo_sesion == "carlosju.med21@gmail.com":
            for h in todas_las_hojas:
                if h.title not in hojas_plantillas_excluir:
                    h_autorizadas.append(h.title)
        else:
            for h in todas_las_hojas:
                if h.title not in hojas_plantillas_excluir:
                    try:
                        val_au4 = h.acell("AU4").value
                        if val_au4 and val_au4.strip().lower() == correo_sesion.strip().lower():
                            h_autorizadas.append(h.title)
                    except:
                        pass

        if not h_autorizadas:
            st.error("❌ No se encontró ninguna jornada asignada a su cuenta.")
        else:
            col_sel1, col_sel2 = st.columns([3, 1])
            with col_sel1:
                hoja_activa_tabla = st.selectbox("Seleccione la Jornada a Visualizar:", options=h_autorizadas)
            with col_sel2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
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
                
                st.markdown(f"**Total de pacientes en censo:** `{len(filas_tabla)}`")
                
                st.dataframe(
                    df_tabla_segura,
                    use_container_width=True,
                    height=650,
                    hide_index=True
                )
            else:
                st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura.")

    except Exception as ex:
        st.error(f"Error al conectar con la base de datos: {ex}")
