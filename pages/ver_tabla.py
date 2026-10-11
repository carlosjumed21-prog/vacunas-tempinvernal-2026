import streamlit as st
import pandas as pd
import gspread
import json
import datetime
import urllib.request
import urllib.parse
import io
from google.oauth2 import service_account
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

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
        todos_los_datos = ws.get_all_values()

        # --- ZONA FIJA SUPERIOR (ENCABEZADO Y MÉTRICAS) ---
        st.markdown('<div class="fixed-top-container">', unsafe_allow_html=True)

        col_tit1, col_tit2, col_tit3 = st.columns([3, 1, 1])
        with col_tit1:
            st.markdown(f'<p class="main-header">📊 Censo General de Pacientes — Jornada: <code>{hoja_activa_tabla}</code></p>', unsafe_allow_html=True)
        with col_tit2:
            if st.button("🔄 Actualizar Datos", use_container_width=True, help="Recargar datos más recientes desde Google Sheets"):
                st.rerun()

        # --- BOTÓN DE DESCARGA EXCEL COMPATIBLE CON IMÁGENES QR ---
        with col_tit3:
            try:
                wb = openpyxl.Workbook()
                ws_excel = wb.active
                ws_excel.title = hoja_activa_tabla[:31]

                for row_idx, row_data in enumerate(todos_los_datos, start=1):
                    for col_idx, cell_value in enumerate(row_data, start=1):
                        if str(cell_value).startswith("=IMAGE("):
                            try:
                                url_qr = cell_value.split('"')[1]
                                req_img = urllib.request.Request(url_qr, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req_img) as img_resp:
                                    img_bytes = img_resp.read()
                                
                                img_io = io.BytesIO(img_bytes)
                                xl_img = OpenpyxlImage(img_io)
                                xl_img.width = 90
                                xl_img.height = 90
                                
                                col_letter = openpyxl.utils.get_column_letter(col_idx)
                                ws_excel.add_image(xl_img, f"{col_letter}{row_idx}")
                                ws_excel.cell(row=row_idx, column=col_idx, value="")
                            except Exception:
                                ws_excel.cell(row=row_idx, column=col_idx, value=cell_value)
                        else:
                            ws_excel.cell(row=row_idx, column=col_idx, value=cell_value)

                excel_buffer = io.BytesIO()
                wb.save(excel_buffer)
                excel_buffer.seek(0)

                st.download_button(
                    label="📥 Descargar Hoja Excel",
                    data=excel_buffer,
                    file_name=f"{hoja_activa_tabla}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help=f"Descargar la hoja '{hoja_activa_tabla}' con soporte compatible para códigos QR"
                )
            except Exception as err:
                st.error(f"No se pudo preparar la descarga: {err}")

        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

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
                st.markdown(f'<div class="metric-card-5"><div class="metric-label">Dosis Influenza</div><div class="metric-value">{total_dosis_influenza}</div></div>', unsafe_allow_html=True)
            with m7:
                st.markdown(f'<div class="metric-card-6"><div class="metric-label">Dosis COVID</div><div class="metric-value">{total_dosis_covid}</div></div>', unsafe_allow_html=True)
            with m8:
                st.markdown(f'<div class="metric-card-7"><div class="metric-label">Simultáneas</div><div class="metric-value">{total_simultaneas}</div></div>', unsafe_allow_html=True)

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            st.caption(f"🟢 *Los registros en verde indican aplicación registrada.*")
            st.markdown('</div>', unsafe_allow_html=True) # Cierre del contenedor fijo superior

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

            # --- TABLA NATIVA CON SCROLL INTERNO Y ENCABEZADOS FIJOS ---
            st.dataframe(
                df_estilizado,
                use_container_width=True,
                height=650,
                hide_index=True
            )

        else:
            st.info("La jornada seleccionada aún no cuenta con suficientes filas de estructura.")

    except Exception as ex:
        st.error(f"Error al conectar con la base de datos: {ex}")
