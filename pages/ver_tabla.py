import streamlit as st
import pandas as pd
import gspread
import json
import io
import datetime
import urllib.request
import urllib.parse
from google.oauth2 import service_account
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global

# --- CONFIGURACIÓN DE PANTALLA ANCHA PARA OCUPAR TODO EL NAVEGADOR ---
st.set_page_config(page_title="Vista Detallada de Censo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .main-header { font-size: 1.8rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 6px; }
        [data-testid="stSidebar"] {display: none;}
        
        .metric-card-1 { background-color: #eaf2f0; border: 2px solid #1e5b4f; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-2 { background-color: #e8f4fd; border: 2px solid #2980b9; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-3 { background-color: #d4edda; border: 2px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-4 { background-color: #fff3cd; border: 2px solid #ffc107; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-5 { background-color: #fce8e6; border: 2px solid #611232; padding: 10px; border-radius: 8px; text-align: center; }
        .metric-card-6 { background-color: #e1f5fe; border: 2px solid #0288d1; padding: 10px; border-radius: 8px; text-align: center; }

        .metric-value { font-size: 1.3rem; font-weight: 800; color: #161a1d; }
        .metric-label { font-size: 0.75rem; font-weight: 700; color: #333333; text-transform: uppercase; }
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

        ws = spreadsheet.worksheet(hoja_activa_tabla)
        gid_hoja = ws.id
        todos_los_datos = ws.get_all_values()

        # --- ENCABEZADO CON TÍTULO Y BOTONES ---
        col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
        with col_tit1:
            st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
        with col_tit2:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar Datos", use_container_width=True, help="Recargar datos más recientes desde Google Sheets"):
                st.rerun()

        # --- BOTÓN DE DESCARGA EXCEL ORIGINAL DESDE GOOGLE DRIVE ---
        with col_tit3:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
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

            # --- CÁLCULO DE MÉTRICAS DINÁMICAS (SALTANDO FILAS DE CURP) ---
            filas_principales = [filas_tabla[i] for i in range(0, len(filas_tabla), 2)]

            total_preregistros = 0
            registros_nuevos_hoy = 0
            total_aplicaciones = 0
            total_sin_aplicar = 0
            total_dosis_influenza = 0
            total_dosis_covid = 0

            fecha_hoy_str = datetime.datetime.now().strftime("%d/%m/%Y")

            for row in filas_principales:
                # 1. Validar fecha de registro/aplicación (índice 11 aprox, o evaluando si corresponde a hoy o histórico)
                fecha_fila = row[11].strip() if len(row) > 11 else ""

                if fecha_fila == fecha_hoy_str:
                    registros_nuevos_hoy += 1
                else:
                    total_preregistros += 1  # Históricos / anteriores a hoy

                # 2. Verificar aplicaciones generales (AG a AQ -> índices 32 a 42)
                tiene_aplicacion = False
                for i in range(32, min(43, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        tiene_aplicacion = True
                        break
                
                if tiene_aplicacion:
                    total_aplicaciones += 1
                else:
                    total_sin_aplicar += 1

                # 3. Dosis de Influenza (AG, AH, AI -> índices 32, 33, 34)
                for i in range(32, min(35, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        total_dosis_influenza += 1

                # 4. Dosis de COVID (AL, AM, AN -> índices 37, 38, 39)
                for i in range(37, min(40, len(row))):
                    if str(row[i]).strip().upper() == "X":
                        total_dosis_covid += 1

            # --- BARRA SUPERIOR DE MÉTRICAS DINÁMICAS CON COLORES ---
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1:
                st.markdown(f'<div class="metric-card-1"><div class="metric-label">Pre-Registros</div><div class="metric-value">{total_preregistros}</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-card-2"><div class="metric-label">Registros Hoy</div><div class="metric-value">{registros_nuevos_hoy}</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card-3"><div class="metric-label">Aplicaciones</div><div class="metric-value">{total_aplicaciones}</div></div>', unsafe_allow_html=True)
            with m4:
                st.markdown(f'<div class="metric-card-4"><div class="metric-label">Sin Aplicar</div><div class="metric-value">{total_sin_aplicar}</div></div>', unsafe_allow_html=True)
            with m5:
                st.markdown(f'<div class="metric-card-5"><div class="metric-label">Dosis Influenza</div><div class="metric-value">{total_dosis_influenza}</div></div>', unsafe_allow_html=True)
            with m6:
                st.markdown(f'<div class="metric-card-6"><div class="metric-label">Dosis COVID</div><div class="metric-value">{total_dosis_covid}</div></div>', unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.caption(f"🟢 *Los registros en verde indican aplicación registrada.*")
            
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
                height=700,
                hide_index=True
            )
        else:
            st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura.")

    except Exception as ex:
        st.error(f"Error al conectar con la base de datos: {ex}")
