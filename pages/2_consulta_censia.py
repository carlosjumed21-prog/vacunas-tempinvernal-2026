import datetime
import json
import urllib.parse
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global
from google.oauth2 import service_account
import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from utils.sheets_esquemas import obtener_recomendaciones_paciente

aplicar_configuracion_global("Guía CENSIA y Consulta Operativa", "📋")

# --- OCULTAR LA BARRA SUPERIOR NATIVA DE STREAMLIT ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
    </style>
""",
    unsafe_allow_html=True,
)


# --- DIÁLOGO DE CONFIRMACIÓN PARA CERRAR SESIÓN ---
@st.dialog("⚠️ ¿ESTÁS SEGURO DE SALIR?")
def mostrar_dialogo_cerrar_sesion():
    st.markdown("<b>Todos los datos, dosis y lotes registrados se han guardado automáticamente en Google Sheets.</b>", unsafe_allow_html=True)
    st.markdown("¿Deseas cerrar sesión y regresar al menú principal?")
    
    col_dlg1, col_dlg2 = st.columns(2)
    with col_dlg1:
        if st.button("Sí, Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado_consulta = False
            st.session_state.correo_operativo_asignado = ""
            st.session_state.ultimo_comprobante_vacunacion = None
            if "input_busqueda_lupa" in st.session_state:
                st.session_state.input_busqueda_lupa = ""
            st.switch_page("app.py")
    with col_dlg2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


# --- BOTÓN DE CIERRE DE SESIÓN EN LA CABECERA ---
col_nav1, col_nav2, col_nav3 = st.columns([2, 1, 1])
with col_nav3:
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        mostrar_dialogo_cerrar_sesion()

st.markdown("---")

if "lote_influenza_memoria" not in st.session_state:
    st.session_state.lote_influenza_memoria = ""
if "lote_covid_memoria" not in st.session_state:
    st.session_state.lote_covid_memoria = ""

if "autenticado_consulta" not in st.session_state:
    st.session_state.autenticado_consulta = False
if "correo_operativo_asignado" not in st.session_state:
    st.session_state.correo_operativo_asignado = ""

if "ultimo_comprobante_vacunacion" not in st.session_state:
    st.session_state.ultimo_comprobante_vacunacion = None


@st.dialog("🎉 ¡VACUNACIÓN REGISTRADA - COMPROBANTE OFICIAL!")
def mostrar_modal_comprobante_vacunacion():
    p = st.session_state.ultimo_comprobante_vacunacion
    if p:
        nombre_val = p.get("nombre", "PACIENTE")
        folio_val = p.get("folio", "S/F")
        dosis_val = p.get("dosis_str", "N/A")
        lotes_val = p.get("lotes_str", "N/A")
        fecha_val = p.get("fecha_aplicacion", datetime.datetime.now().strftime("%d/%m/%Y"))

        texto_qr = (
            f"ISSSTE - COMPROBANTE OFICIAL VIGILE\n"
            f"FOLIO: {folio_val}\n"
            f"PACIENTE: {nombre_val}\n"
            f"DOSIS: {dosis_val}\n"
            f"LOTES: {lotes_val}\n"
            f"FECHA APLICACIÓN: {fecha_val}\n"
            f"ESTADO: VÁLIDO Y VERIFICADO"
        )
        url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={urllib.parse.quote(texto_qr)}"

        html_comprobante_component = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .card-comprobante {{ 
                position: relative; 
                background-color: #ffffff; 
                border: 3px solid #1e5b4f; 
                padding: 12px; 
                border-radius: 10px; 
                color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                margin-bottom: 10px; 
                overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.90rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin-top: 0; margin-bottom: 6px; z-index: 2; position: relative; }}
            .cuerpo-ticket {{ display: flex; align-items: center; gap: 12px; z-index: 2; position: relative; }}
            .info-container {{ flex: 1; z-index: 2; position: relative; }}
            .qr-container {{ text-align: center; z-index: 2; position: relative; }}
            .qr-container img {{ width: 100px; height: 100px; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; }}
            .folio-grande {{ font-size: 1.05rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 6px; z-index: 2; position: relative; }}
            .info-text {{ margin: 3px 0; font-size: 0.78rem; }}
            
            .watermark-overlay {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: space-evenly;
                align-items: center;
                pointer-events: none;
                z-index: 1;
                overflow: hidden;
            }}
            .watermark-row {{
                display: flex;
                gap: 15px;
                white-space: nowrap;
                font-size: 0.85rem;
                font-weight: 900;
                color: rgba(30, 91, 79, 0.10);
                text-transform: uppercase;
                letter-spacing: 1px;
                transform: rotate(-25deg);
            }}
            
            .btn-container {{ display: flex; gap: 8px; }}
            .btn {{ flex: 1; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; box-sizing: border-box; }}
            .btn-wa {{ background-color: #25D366; color: white; }}
            .btn-img {{ background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="watermark-overlay">
                    <div class="watermark-row">
                        <span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span>
                    </div>
                </div>
                <div class="titulo-ticket">COMPROBANTE DE VACUNACIÓN OFICIAL</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>Dosis:</b> {dosis_val}</p>
                        <p class="info-text"><b>Lotes:</b> {lotes_val}</p>
                        <p class="info-text"><b>Fecha de Aplicación:</b> {fecha_val}</p>
                    </div>
                    <div class="qr-container">
                        <img src="{url_qr_api}" alt="QR Verificación">
                    </div>
                </div>
                <div class="folio-grande">Folio: {folio_val}</div>
            </div>
            <div class="btn-container">
                <button class="btn btn-wa" onclick="compartirImagenWhatsApp()">💬 WhatsApp (Img)</button>
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar</button>
            </div>
            <script>
            function compartirImagenWhatsApp() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2, useCORS: true }}).then(canvas => {{
                    canvas.toBlob(blob => {{
                        const fileName = 'Comprobante_Vacunacion_{folio_val}.png';
                        const textoMensaje = `💉 *COMPROBANTE DE VACUNACIÓN*\\nPaciente: {nombre_val}\\nFolio: *{folio_val}*\\nDosis: {dosis_val}\\nLotes: {lotes_val}\\nFecha Aplicación: {fecha_val}\\n✅ Verificado con Sello QR Oficial.`;
                        
                        const enlace = document.createElement('a');
                        enlace.download = fileName;
                        enlace.href = URL.createObjectURL(blob);
                        enlace.click();
                        
                        window.open('https://wa.me/?text=' + encodeURIComponent(textoMensaje), '_blank');
                    }}, 'image/png');
                }});
            }}
            function descargarCaptura() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2, useCORS: true }}).then(canvas => {{
                    const enlace = document.createElement('a');
                    enlace.download = 'Comprobante_Vacunacion_{folio_val}.png';
                    enlace.href = canvas.toDataURL('image/png');
                    enlace.click();
                }});
            }}
            </script>
        </body>
        </html>
        """

        components.html(html_comprobante_component, height=330)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Cerrar Comprobante", use_container_width=True):
            st.session_state.ultimo_comprobante_vacunacion = None
            if "input_busqueda_lupa" in st.session_state:
                st.session_state.input_busqueda_lupa = ""
            st.rerun()


if st.session_state.ultimo_comprobante_vacunacion is not None:
    mostrar_modal_comprobante_vacunacion()

if not st.session_state.autenticado_consulta:
    st.markdown(
        '<p class="main-header">Acceso Restringido - Módulo Operativo CENSIA</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Ingrese su correo electrónico y contraseña institucional</p>',
        unsafe_allow_html=True,
    )

    with st.form("form_login_consulta"):
        correo_operador_input = st.text_input(
            "📧 Correo Electrónico Institucional:",
            placeholder="ejemplo@issste.gob.mx"
        )
        password = st.text_input("Contraseña:", type="password")
        
        btn_login = st.form_submit_button("Iniciar Sesión Operativa", use_container_width=True)

        if btn_login:
            correo_limpio = correo_operador_input.strip().lower()
            if not correo_limpio:
                st.error("⚠️ Debe ingresar su correo electrónico.")
            elif not password:
                st.error("⚠️ Debe ingresar su contraseña.")
            else:
                if correo_limpio == "carlosju.med21@gmail.com" and password == "OtaniOrochi26":
                    st.session_state.autenticado_consulta = True
                    st.session_state.correo_operativo_asignado = correo_limpio
                    st.rerun()
                elif password == "OperativoInv26":
                    st.session_state.autenticado_consulta = True
                    st.session_state.correo_operativo_asignado = correo_limpio
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas. Verifique su correo y contraseña.")
else:
    st.markdown(
        '<p class="main-header">Módulo Operativo de Aplicación y Guía CENSIA</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Selección de jornada autorizada, evaluación'
        " clínica y registro de biológicos</p>",
        unsafe_allow_html=True,
    )

    try:
        scope = GOOGLE_SCOPES
        if "GOOGLE_CREDENTIALS" in st.secrets:
            raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = (
                json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
            )
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

        todas_las_hojas = spreadsheet.worksheets()
        
        correo_sesion = st.session_state.get("correo_operativo_asignado", "").strip().lower()
        h_autorizadas = []
        hojas_plantillas_excluir = ["CENSO NOMINAL", "CENSO", "Influenza", "COVID"]

        # --- LLAVE UNIVERSAL: Si eres tú (Admin), ves todas las hojas del libro ---
        if correo_sesion == "carlosju.med21@gmail.com":
            for h in todas_las_hojas:
                if h.title not in hojas_plantillas_excluir:
                    h_autorizadas.append(h.title)
        else:
            # Para operativos, filtramos buscando estrictamente su correo en la celda AU4
            for h in todas_las_hojas:
                if h.title not in hojas_plantillas_excluir:
                    try:
                        val_au4 = h.acell("AU4").value
                        if val_au4 and val_au4.strip().lower() == correo_sesion:
                            h_autorizadas.append(h.title)
                    except:
                        pass

    except Exception as e:
        h_autorizadas = []
        st.error(f"Error al conectar con Google Sheets para listar jornadas: {e}")

    # --- SELECTOR SEGÚN ROL ---
    if correo_sesion == "carlosju.med21@gmail.com":
        st.markdown(
            f'<div class="section-title">👑 Vista Administrador Universal: <code>{correo_sesion}</code></div>',
            unsafe_allow_html=True,
        )
        if h_autorizadas:
            hoja_seleccionada = st.selectbox("Seleccione la Hoja / Jornada a Operar:", options=h_autorizadas)
        else:
            hoja_seleccionada = None
            st.warning("⚠️ No se encontraron hojas operativas en el libro.")
    else:
        st.markdown(
            f'<div class="section-title">1. Jornada Operativa Asignada a: <code>{correo_sesion}</code></div>',
            unsafe_allow_html=True,
        )
        if not h_autorizadas:
            st.warning(
                f"⚠️ No se encontró ninguna hoja autorizada en Google Sheets asociada al correo: **{correo_sesion}**. "
                "Verifique que su correo coincida exactamente con el registrado en la celda AU4."
            )
            hoja_seleccionada = None
        else:
            hoja_seleccionada = h_autorizadas[0]
            st.info(f"📋 Pestaña asignada automáticamente a tu cuenta: **{hoja_seleccionada}**")

    # Ignoramos parámetros URL externos para operativos comunes
    if correo_sesion != "carlosju.med21@gmail.com":
        params_url = st.query_params
        hoja_enlace = params_url.get("hoja_activa", "")
        if hoja_enlace and hoja_enlace in h_autorizadas:
            hoja_seleccionada = hoja_enlace

    if hoja_seleccionada:
        try:
            try:
                worksheet_activa = spreadsheet.worksheet(hoja_seleccionada)
            except:
                worksheet_activa = spreadsheet.worksheet("CENSO NOMINAL")

            todos_los_datos = worksheet_activa.get_all_values()

            # --- EXTRACCIÓN DE LA FECHA DE APLICACIÓN DESDE LA FILA 9, COLUMNA AB (Índice 27) ---
            fecha_aplicacion_hoja = datetime.datetime.now().strftime("%d/%m/%Y")
            if len(todos_los_datos) >= 9 and len(todos_los_datos[8]) > 27:
                val_ab9 = todos_los_datos[8][27].strip()
                if val_ab9:
                    fecha_aplicacion_hoja = val_ab9

            pacientes_cargados = []
            if len(todos_los_datos) >= 13:
                for idx, row in enumerate(todos_los_datos[12:], start=13):
                    if len(row) > 3 and row[1].strip() and row[2].strip():
                        pacientes_cargados.append({
                            "fila": idx,
                            "folio": row[1].strip(),
                            "paterno": row[2].strip(),
                            "materno": row[3].strip() if len(row) > 3 else "",
                            "nombres": row[4].strip() if len(row) > 4 else "",
                        })

        except Exception as e:
            pacientes_cargados = []
            st.error(f"Error al leer los datos de la hoja {hoja_seleccionada}: {e}")

        # --- VISUALIZACIÓN ESTILO GOOGLE SHEETS DENTRO DE LA APP (CON LIMPIEZA DE COLUMNAS) ---
        st.markdown(
            '<div class="section-title">📊 Visualización de Censo (Estilo Hoja de Cálculo)</div>',
            unsafe_allow_html=True,
        )
        
        try:
            if len(todos_los_datos) >= 12:
                encabezados_tabla = todos_los_datos[11]
                filas_tabla = todos_los_datos[12:]
                
                # Limpieza automática de nombres vacíos o duplicados para evitar conflictos en Pandas
                columnas_limpias = []
                conteo_nombres = {}
                for idx, col in enumerate(encabezados_tabla):
                    col_str = str(col).strip()
                    if not col_str:
                        col_str = f"Col_{idx+1}"
                    
                    if col_str in conteo_nombres:
                        conteo_nombres[col_str] += 1
                        col_str = f"{col_str}_{conteo_nombres[col_str]}"
                    else:
                        conteo_nombres[col_str] = 0
                    
                    columnas_limpias.append(col_str)

                filas_ajustadas = [row[:len(columnas_limpias)] + [''] * max(0, len(columnas_limpias) - len(row)) for row in filas_tabla]

                df_tabla_segura = pd.DataFrame(filas_ajustadas, columns=columnas_limpias)
                
                st.dataframe(
                    df_tabla_segura,
                    use_container_width=True,
                    height=350,
                    hide_index=True
                )
            else:
                st.info("La jornada no tiene suficientes filas para renderizar la cuadrícula.")
        except Exception as tbl_err:
            st.warning(f"No se pudo renderizar la tabla tabulada: {tbl_err}")

        st.markdown(
            '<div class="section-title">2. Lupa de Búsqueda Rápida y Registro</div>',
            unsafe_allow_html=True,
        )
        if not pacientes_cargados:
            st.info(
                "La jornada seleccionada aún no cuenta con pacientes registrados en"
                " el censo."
            )
        else:
            col_busq1, col_busq2 = st.columns([4, 1])
            with col_busq1:
                query_busqueda = st.text_input(
                    "🔍 Buscar por Folio, Apellido o Nombre:",
                    placeholder="Escriba parte del folio, apellido o nombre...",
                    key="input_busqueda_lupa",
                    help="Presione Enter para procesar la búsqueda"
                )
            with col_busq2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Actualizar", use_container_width=True, help="Actualizar listado de pacientes en vivo"):
                    st.rerun()
            st.caption("💡 Tip: Presione **Enter** después de escribir en el buscador.")

            if not query_busqueda.strip():
                st.info(
                    "ℹ️ Escriba en la lupa de búsqueda para localizar rápidamente a un"
                    " paciente."
                )
            else:
                q_clean = query_busqueda.strip().upper()
                pacientes_filtrados = [
                    p
                    for p in pacientes_cargados
                    if q_clean in p["folio"].upper()
                    or q_clean in p["paterno"].upper()
                    or q_clean in p["materno"].upper()
                    or q_clean in p["nombres"].upper()
                ]

                if not pacientes_filtrados:
                    st.warning(
                        "No se encontraron pacientes que coincidan con la búsqueda."
                    )
                else:
                    opciones_busqueda = [
                        f"{p['folio']} - {p['paterno']} {p['materno']}, {p['nombres']}||{p['fila']}"
                        for p in pacientes_filtrados
                    ]

                    seleccion_paciente = st.selectbox(
                        "Seleccione del listado de coincidencias:",
                        options=opciones_busqueda,
                        format_func=lambda x: x.split("||")[0],
                    )

                    if seleccion_paciente:
                        fila_idx = int(seleccion_paciente.split("||")[1])
                        fila_datos = todos_los_datos[fila_idx - 1]

                        folio_p = fila_datos[1] if len(fila_datos) > 1 else ""
                        paterno_p = fila_datos[2] if len(fila_datos) > 2 else ""
                        materno_p = fila_datos[3] if len(fila_datos) > 3 else ""
                        nombres_p = fila_datos[4] if len(fila_datos) > 4 else ""
                        nombre_completo = f"{paterno_p} {materno_p}, {nombres_p}"

                        dd_n = fila_datos[5] if len(fila_datos) > 5 else "01"
                        mm_n = fila_datos[6] if len(fila_datos) > 6 else "01"
                        yy_n = fila_datos[7] if len(fila_datos) > 7 else "2000"
                        fecha_nac_str = f"{dd_n}/{mm_n}/{yy_n}"

                        sexo_p = fila_datos[10] if len(fila_datos) > 10 else "H"
                        sexo_texto = "HOMBRE" if sexo_p == "H" else "MUJER"

                        # --- LECTURA DEL CURP (Fila siguiente, Columna C -> Índice 2) ---
                        curp_actual = ""
                        fila_curp_idx = fila_idx
                        if len(todos_los_datos) > fila_curp_idx and len(todos_los_datos[fila_curp_idx]) > 2:
                            curp_actual = todos_los_datos[fila_curp_idx][2].strip()

                        vacuna_registrada = "AMBAS"
                        if len(fila_datos) > 47:
                            at_val = fila_datos[45].strip().upper() if len(fila_datos) > 45 else ""
                            au_val = fila_datos[46].strip().upper() if len(fila_datos) > 46 else ""
                            av_val = fila_datos[47].strip().upper() if len(fila_datos) > 47 else ""
                            
                            if av_val == "X" or (at_val == "X" and au_val == "X"):
                                vacuna_registrada = "AMBAS"
                            elif at_val == "X":
                                vacuna_registrada = "INFLUENZA"
                            elif au_val == "X":
                                vacuna_registrada = "COVID-19"

                        lista_riesgos_detectados = []
                        def tiene_equis(col_idx):
                            return len(fila_datos) > col_idx and fila_datos[col_idx].strip().upper() == "X"

                        es_riesgo = False
                        if tiene_equis(15) or tiene_equis(16):
                            lista_riesgos_detectados.append("6 A 59 MESES" if tiene_equis(15) else "60 AÑOS Y MAS")
                            categoria_paciente = "POBLACIÓN OBJETIVO"
                        else:
                            categoria_paciente = "POBLACIÓN DE RIESGO"

                        comorb_map = {17: "EMBARAZADAS", 18: "PERSONAL DE SALUD", 19: "VIH", 20: "DIABETES", 21: "OBESIDAD", 22: "CARDIOPATÍAS", 23: "ENFERMEDAD PULMONAR", 24: "CÁNCER", 25: "CONGÉNITAS", 26: "RENAL", 27: "INMUNOSUPRESIÓN", 28: "DISCAPACIDADES", 29: "FIBROSIS", 30: "HIPERTENSIÓN"}
                        for idx_c, nom_c in comorb_map.items():
                            if tiene_equis(idx_c):
                                lista_riesgos_detectados.append(nom_c)
                                es_riesgo = True

                        if len(fila_datos) > 31 and fila_datos[31].strip():
                            lista_riesgos_detectados.append(fila_datos[31].strip().upper())
                            es_riesgo = True

                        if es_riesgo:
                            categoria_paciente = "POBLACIÓN DE RIESGO"

                        grupo_riesgos_str = ", ".join(lista_riesgos_detectados) if lista_riesgos_detectados else "NINGUNO"
                        grupo_detallado_vista = f"{categoria_paciente} ({grupo_riesgos_str})"

                        st.markdown(
                            '<div class="section-title">Vista Previa y Datos Generales'
                            " del Paciente</div>",
                            unsafe_allow_html=True,
                        )
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Folio:** {folio_p}")
                            st.markdown(f"**Nombre:** {nombre_completo}")
                        with col2:
                            st.markdown(f"**Nacimiento:** {fecha_nac_str}")
                            st.markdown(f"**Sexo:** {sexo_texto}")
                        with col3:
                            st.markdown(f"**Grupo / Riesgo:** {grupo_detallado_vista}")
                            st.markdown(f"**Vacuna Solicitada:** {vacuna_registrada}")

                        # --- CAMPO EDITABLE DE CURP Y ACTUALIZACIÓN DIRECTA EN SHEETS ---
                        with st.form(f"form_curp_{fila_idx}"):
                            c_curp1, c_curp2 = st.columns([3, 1])
                            with c_curp1:
                                nuevo_curp = st.text_input("CURP (Editable):", value=curp_actual, max_chars=18, key=f"input_curp_{fila_idx}")
                            with c_curp2:
                                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                                btn_guardar_curp = st.form_submit_button("💾 Actualizar CURP", use_container_width=True)

                            if btn_guardar_curp:
                                try:
                                    fila_curp_excel = fila_idx + 1
                                    worksheet_activa.update(f"C{fila_curp_excel}", [[nuevo_curp.upper()]])
                                    st.success("✅ CURP actualizado correctamente en la hoja de origen.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar el CURP en Sheets: {e}")

                        st.markdown(
                            '<div class="section-title">3. Guía y Lineamientos'
                            " CENSIA (Tarjetas de Grupos Prioritarios)</div>",
                            unsafe_allow_html=True,
                        )

                        matches_inf, matches_covid = obtener_recomendaciones_paciente(
                            categoria_paciente, lista_riesgos_detectados, vacuna_registrada
                        )

                        mostrar_influenza = vacuna_registrada in ["INFLUENZA", "AMBAS"]
                        mostrar_covid = vacuna_registrada in ["COVID-19", "AMBAS"]

                        biologico_covid_elegido = "Moderna"
                        if mostrar_covid:
                            matches_moderna = [m for m in matches_covid if "moderna" in m.get('tipo_vacuna', '').lower() or "spikevax" in m.get('tipo_vacuna', '').lower()]
                            matches_pfizer = [m for m in matches_covid if "pfizer" in m.get('tipo_vacuna', '').lower() or "comirnaty" in m.get('tipo_vacuna', '').lower()]

                            col_bio1, col_bio2 = st.columns(2)
                            with col_bio1:
                                biologico_covid_elegido = st.radio(
                                    "💉 Seleccione Biológico COVID-19:",
                                    options=["Moderna", "Pfizer/BioNTech (Comirnaty)"],
                                    horizontal=True,
                                    key="radio_biologico_covid"
                                )
                            
                            if biologico_covid_elegido == "Moderna":
                                matches_covid_filtrados = matches_moderna if matches_moderna else matches_covid
                            else:
                                matches_covid_filtrados = matches_pfizer if matches_pfizer else matches_covid
                        else:
                            matches_covid_filtrados = matches_covid

                        match_inf_prioritario = matches_inf[0] if matches_inf else None
                        match_cov_prioritario = matches_covid_filtrados[0] if matches_covid_filtrados else None

                        # --- RENDERIZADO DE LAS TARJETAS CENSIA LADO A LADO (MISMA ALTURA) ---
                        col_card1, col_card2 = st.columns(2)

                        with col_card1:
                            if mostrar_influenza and match_inf_prioritario:
                                st.markdown(
                                    f"""
                                    <div style="background-color: #f7f4eb; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; margin-bottom: 15px; min-height: 280px;">
                                        <h4 style="color: #1e5b4f; margin-top: 0;">💉 Influenza Estacional</h4>
                                        <p><b>Categoría:</b> {match_inf_prioritario.get('categoria', 'N/A')}</p>
                                        <p><b>Grupos blancos:</b> {match_inf_prioritario.get('grupos_blancos', 'N/A')}</p>
                                        <p><b>Esquema:</b> {match_inf_prioritario.get('esquema', 'N/A')}</p>
                                        <p><b>Dosis:</b> {match_inf_prioritario.get('dosis', 'N/A')}</p>
                                        <p><b>Intervalo:</b> {match_inf_prioritario.get('intervalo', 'N/A')}</p>
                                        <p><b>Recomendación:</b> {match_inf_prioritario.get('recomendacion', 'N/A')}</p>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                        with col_card2:
                            if mostrar_covid and match_cov_prioritario:
                                tipo_biologico_covid = match_cov_prioritario.get('tipo_vacuna', biologico_covid_elegido)
                                st.markdown(
                                    f"""
                                    <div style="background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; margin-bottom: 15px; min-height: 280px;">
                                        <h4 style="color: #611232; margin-top: 0;">🦠 COVID-19 ({tipo_biologico_covid})</h4>
                                        <p><b>Categoría:</b> {match_cov_prioritario.get('categoria', 'N/A')}</p>
                                        <p><b>Grupos blancos:</b> {match_cov_prioritario.get('grupos_blancos', 'N/A')}</p>
                                        <p><b>Esquema:</b> {match_cov_prioritario.get('esquema', 'N/A')}</p>
                                        <p><b>Dosis:</b> {match_cov_prioritario.get('dosis', 'N/A')}</p>
                                        <p><b>Intervalo:</b> {match_cov_prioritario.get('intervalo', 'N/A')}</p>
                                        <p><b>Recomendación:</b> {match_cov_prioritario.get('recomendacion', 'N/A')}</p>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                        # --- AVISO INDEPENDIENTE DE APLICACIÓN SIMULTÁNEA (SOLO SI SE ELIGE AMBAS) ---
                        if vacuna_registrada == "AMBAS":
                            texto_simultanea = ""
                            if match_inf_prioritario and match_inf_prioritario.get("aplicacion_simultanea"):
                                texto_simultanea = match_inf_prioritario.get("aplicacion_simultanea")
                            elif match_cov_prioritario and match_cov_prioritario.get("aplicacion_simultanea"):
                                texto_simultanea = match_cov_prioritario.get("aplicacion_simultanea")
                            else:
                                texto_simultanea = "Ambas vacunas podrán aplicarse de forma simultánea en extremidades distintas, o respetando de 2.5 a 5 cm de distancia si se aplican en el mismo sitio de punción."

                            st.markdown(
                                f"""
                                <div style="background-color: #eaf2f0; border-left: 5px solid #1e5b4f; border: 1px solid #cce3de; padding: 12px 15px; border-radius: 6px; margin-bottom: 20px;">
                                    <p style="color: #1e5b4f; font-weight: 700; margin: 0 0 4px 0;">🔄 Lineamiento de Aplicación Simultánea:</p>
                                    <p style="color: #161a1d; margin: 0; font-size: 0.95rem;">{texto_simultanea}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            '<div class="section-title">4. Registro de Dosis Aplicadas, Lotes y Caducidad</div>',
                            unsafe_allow_html=True,
                        )

                        with st.form("form_aplicacion_lotes"):
                            st.markdown("##### 💉 INFLUENZA")
                            c_inf1, c_inf2, c_inf3, c_inf4, c_inf5 = st.columns([1, 1, 1, 1.5, 1.5])
                            with c_inf1:
                                inf_1ra = st.checkbox("1ra dosis", key="chk_inf_1ra")
                            with c_inf2:
                                inf_2da = st.checkbox("2da dosis", key="chk_inf_2da")
                            with c_inf3:
                                inf_anual = st.checkbox("Anual", key="chk_inf_anual")
                            with c_inf4:
                                lote_inf_input = st.text_input(
                                    "Lote Influenza",
                                    value=st.session_state.lote_influenza_memoria,
                                    placeholder="Ej. A1234",
                                )
                            with c_inf5:
                                cad_inf_input = st.date_input("Caducidad Influenza", value=datetime.date.today(), format="DD/MM/YYYY", key="cad_inf")

                            st.markdown(f"##### 🦠 COVID-19 ({biologico_covid_elegido})")
                            c_cov1, c_cov2, c_cov3, c_cov4, c_cov5 = st.columns([1, 1, 1, 1.5, 1.5])
                            with c_cov1:
                                cov_1ra = st.checkbox("COVID 1ra", key="chk_cov_1ra")
                            with c_cov2:
                                cov_2da = st.checkbox("COVID 2da", key="chk_cov_2da")
                            with c_cov3:
                                cov_anual = st.checkbox("Anual", key="chk_cov_anual")
                            with c_cov4:
                                lote_cov_input = st.text_input(
                                    "Lote COVID-19",
                                    value=st.session_state.lote_covid_memoria,
                                    placeholder="Ej. C5678",
                                )
                            with c_cov5:
                                cad_cov_input = st.date_input("Caducidad COVID", value=datetime.date.today(), format="DD/MM/YYYY", key="cad_cov")

                            btn_actualizar_dosis = st.form_submit_button(
                                "💾 Guardar Aplicación y Actualizar Hoja Sheets",
                                use_container_width=True,
                            )

                            if btn_actualizar_dosis:
                                try:
                                    if lote_inf_input:
                                        st.session_state.lote_influenza_memoria = lote_inf_input.upper()
                                    if lote_cov_input:
                                        st.session_state.lote_covid_memoria = lote_cov_input.upper()

                                    f_actual = fila_idx
                                    f_siguiente = fila_idx + 1

                                    dosis_aplicadas_lista = []
                                    datos_a_actualizar = []

                                    # --- Mapeo exacto de columnas para INFLUENZA ---
                                    if inf_1ra:
                                        datos_a_actualizar.append({"range": f"AG{f_actual}:AG{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append("Influenza (1ra Dosis)")
                                    if inf_2da:
                                        datos_a_actualizar.append({"range": f"AH{f_actual}:AH{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append("Influenza (2da Dosis)")
                                    if inf_anual:
                                        datos_a_actualizar.append({"range": f"AI{f_actual}:AI{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append("Influenza (Dosis Anual)")

                                    if lote_inf_input:
                                        lote_i = lote_inf_input.upper()
                                        datos_a_actualizar.append({"range": f"AJ{f_actual}:AJ{f_siguiente}", "values": [[lote_i], [lote_i]]})
                                    if cad_inf_input:
                                        cad_i_str = cad_inf_input.strftime("%d/%m/%Y")
                                        datos_a_actualizar.append({"range": f"AK{f_actual}:AK{f_siguiente}", "values": [[cad_i_str], [cad_i_str]]})

                                    # --- Mapeo exacto de columnas para COVID ---
                                    if cov_1ra:
                                        datos_a_actualizar.append({"range": f"AL{f_actual}:AL{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (1ra Dosis)")
                                    if cov_2da:
                                        datos_a_actualizar.append({"range": f"AM{f_actual}:AM{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (2da Dosis)")
                                    if cov_anual:
                                        datos_a_actualizar.append({"range": f"AN{f_actual}:AN{f_siguiente}", "values": [["X"], ["X"]]})
                                        dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (Dosis Anual)")

                                    if lote_cov_input:
                                        lote_c = lote_cov_input.upper()
                                        datos_a_actualizar.append({"range": f"AO{f_actual}:AO{f_siguiente}", "values": [[lote_c], [lote_c]]})
                                    if cad_cov_input:
                                        cad_c_str = cad_cov_input.strftime("%d/%m/%Y")
                                        datos_a_actualizar.append({"range": f"AP{f_actual}:AP{f_siguiente}", "values": [[cad_c_str], [cad_c_str]]})

                                    if datos_a_actualizar:
                                        worksheet_activa.batch_update(datos_a_actualizar)

                                    lote_final_partes = []
                                    if lote_inf_input:
                                        lote_final_partes.append(f"Inf: {lote_inf_input.upper()} (Cad: {cad_inf_input.strftime('%d/%m/%Y')})")
                                    if lote_cov_input:
                                        lote_final_partes.append(f"Cov: {lote_cov_input.upper()} (Cad: {cad_cov_input.strftime('%d/%m/%Y')})")
                                    lote_final_str = " / ".join(lote_final_partes) if lote_final_partes else "N/A"

                                    dosis_str = ", ".join(dosis_aplicadas_lista) if dosis_aplicadas_lista else "Ninguna seleccionada"

                                    st.session_state.ultimo_comprobante_vacunacion = {
                                        "nombre": nombre_completo,
                                        "folio": folio_p,
                                        "dosis_str": dosis_str,
                                        "lotes_str": lote_final_str,
                                        "fecha_aplicacion": fecha_aplicacion_hoja
                                    }
                                    st.rerun()

                                except Exception as e:
                                    st.error(
                                        "Error al actualizar la base de datos en Google"
                                        f" Sheets: {e}"
                                    )
