# pages/2_consulta_censia.py
import datetime
import json
import urllib.parse
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global
import gspread
import streamlit as st
import streamlit.components.v1 as components
from utils.sheets_esquemas import obtener_recomendaciones_paciente
from utils.logica_censia import procesar_guardado_aplicacion
from utils.email_sender import enviar_comprobante_correo

aplicar_configuracion_global("Guía CENSIA y Consulta Operativa", "📋")

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

# --- OCULTAR LA BARRA SUPERIOR NATIVA DE STREAMLIT Y AJUSTAR ESTILOS ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        input:disabled, select:disabled { color: #2c3e50 !important; -webkit-text-fill-color: #2c3e50 !important; background-color: #fcfcfc !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# CLIENTE GOOGLE SEGURO Y NATIVO
# ============================================================
@st.cache_resource
def obtener_client_gspread_cacheado():
    """Autentica y retorna el cliente de gspread de forma nativa mediante service_account_from_dict."""
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)
    
@st.cache_data(ttl=300)
def obtener_hojas_autorizadas_cacheadas(correo_sesion: str):
    """
    Lista las hojas autorizadas tanto del libro general como del CMN 20 de Noviembre.
    """
    h_autorizadas = []
    hojas_plantillas_excluir = ["CENSO NOMINAL", "CENSO", "Influenza", "COVID"]

    try:
        client = obtener_client_gspread_cacheado()
        
        # 1. Revisar Libro General
        spreadsheet_gen = client.open_by_key(GOOGLE_SHEET_ID)
        for h in spreadsheet_gen.worksheets():
            if h.title not in hojas_plantillas_excluir:
                if correo_sesion == "carlosju.med21@gmail.com":
                    h_autorizadas.append({"titulo": h.title, "sheet_id": GOOGLE_SHEET_ID})
                else:
                    try:
                        val_au4 = h.acell("AU4").value
                        if val_au4 and val_au4.strip().lower() == correo_sesion:
                            h_autorizadas.append({"titulo": h.title, "sheet_id": GOOGLE_SHEET_ID})
                    except Exception:
                        pass

        # 2. Revisar Libro CMN 20 de Noviembre
        spreadsheet_20n = client.open_by_key(SHEET_ID_20_NOV)
        for h in spreadsheet_20n.worksheets():
            if h.title not in hojas_plantillas_excluir and "_CENSO" not in h.title:
                if correo_sesion == "carlosju.med21@gmail.com":
                    h_autorizadas.append({"titulo": h.title, "sheet_id": SHEET_ID_20_NOV})
                else:
                    try:
                        val_au4 = h.acell("AU4").value
                        if val_au4 and val_au4.strip().lower() == correo_sesion:
                            h_autorizadas.append({"titulo": h.title, "sheet_id": SHEET_ID_20_NOV})
                    except Exception:
                        pass
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets para listar jornadas: {e}")
        return []

    return h_autorizadas


@st.cache_data(ttl=300)
def cargar_pacientes_hoja_cacheada(hoja_seleccionada: str, sheet_id_objetivo: str, cache_buster: int = 0):
    """
    Carga los pacientes de una hoja específica utilizando su sheet_id correspondiente.
    El parámetro cache_buster permite invalidar la caché instantáneamente tras un guardado.
    """
    try:
        client = obtener_client_gspread_cacheado()
        spreadsheet = client.open_by_key(sheet_id_objetivo)
        worksheet_activa = spreadsheet.worksheet(hoja_seleccionada)
        all_values = worksheet_activa.get_all_values()

        pacientes_cargados = []
        if len(all_values) >= 14:
            for idx, row in enumerate(all_values[13:], start=14):
                if len(row) > 3 and row[1].strip() and row[2].strip():
                    ya_vacunado = any(str(row[i]).strip().upper() == "X" for i in range(32, min(43, len(row))))
                    pacientes_cargados.append({
                        "fila": idx,
                        "folio": row[1].strip(),
                        "paterno": row[2].strip() if sheet_id_objetivo != SHEET_ID_20_NOV else (row[13].strip() if len(row) > 13 else row[2].strip()),
                        "materno": (row[3].strip() if len(row) > 3 else "") if sheet_id_objetivo != SHEET_ID_20_NOV else (row[14].strip() if len(row) > 14 else ""),
                        "nombres": (row[4].strip() if len(row) > 4 else "") if sheet_id_objetivo != SHEET_ID_20_NOV else (row[12].strip() if len(row) > 12 else ""),
                        "ya_vacunado": ya_vacunado,
                    })

        return pacientes_cargados, all_values, datetime.datetime.now().strftime("%d/%m/%Y"), worksheet_activa

    except Exception as e:
        st.error(f"Error al leer la hoja {hoja_seleccionada}: {e}")
        return [], [], datetime.datetime.now().strftime("%d/%m/%Y"), None


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

if "reiniciar_busqueda" not in st.session_state:
    st.session_state.reiniciar_busqueda = False

# Control de versión de caché para forzar recargas limpias en cualquier unidad
if "cache_buster_val" not in st.session_state:
    st.session_state.cache_buster_val = 0

if st.session_state.reiniciar_busqueda:
    st.session_state.input_busqueda_lupa = ""
    st.session_state.reiniciar_busqueda = False


@st.dialog("🎉 ¡VACUNACIÓN REGISTRADA - COMPROBANTE OFICIAL!")
def mostrar_modal_comprobante_vacunacion():
    p = st.session_state.get("ultimo_comprobante_vacunacion")
    if p:
        nombre_val = p.get("nombre", "PACIENTE")
        folio_val = p.get("folio", "S/F")
        dosis_val = p.get("dosis_str", "N/A")
        lotes_val = p.get("lotes_str", "N/A")
        fecha_val = p.get("fecha_aplicacion", datetime.datetime.now().strftime("%d/%m/%Y"))
        correo_ax = p.get("correo_ax", "")

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
                position: relative; background-color: #ffffff; border: 3px solid #1e5b4f; 
                padding: 14px; border-radius: 10px; color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 10px; overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.90rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin-top: 0; margin-bottom: 6px; z-index: 2; position: relative; }}
            .cuerpo-ticket {{ display: flex; align-items: center; gap: 12px; z-index: 2; position: relative; }}
            .info-container {{ flex: 1; z-index: 2; position: relative; }}
            .qr-container {{ text-align: center; z-index: 2; position: relative; }}
            .qr-container img {{ width: 100px; height: 100px; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; }}
            .folio-grande {{ font-size: 1.05rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; }}
            .info-text {{ margin: 3px 0; font-size: 0.78rem; }}
            .watermark-overlay {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                display: flex; flex-direction: column; justify-content: space-evenly; align-items: center;
                pointer-events: none; z-index: 1; overflow: hidden;
            }}
            .watermark-row {{
                display: flex; gap: 30px; white-space: nowrap; font-size: 0.82rem; font-weight: 900;
                color: rgba(30, 91, 79, 0.08); text-transform: uppercase; letter-spacing: 2px; transform: rotate(-25deg);
            }}

            .btn-container {{ display: flex; gap: 8px; }}
            .btn-img {{ width: 100%; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="watermark-overlay">
                    <div class="watermark-row"><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span></div>
                    <div class="watermark-row"><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span></div>
                    <div class="watermark-row"><span>COMPROBANTE OFICIAL VIGILE</span><span>COMPROBANTE OFICIAL VIGILE</span></div>
                </div>
                <div class="titulo-ticket">COMPROBANTE DE VACUNACIÓN OFICIAL</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>Dosis:</b> {dosis_val}</p>
                        <p class="info-text"><b>Lotes:</b> {lotes_val}</p>
                        <p class="info-text"><b>Fecha de Aplicación:</b> {fecha_val}</p>
                    </div>
                    <div class="qr-container"><img src="{url_qr_api}" alt="QR Verificación"></div>
                </div>
                <div class="folio-grande">Folio: {folio_val}</div>
            </div>
            <div class="btn-container">
                <button class="btn-img" onclick="descargarCaptura()">📸 Descargar Comprobante</button>
            </div>
            <script>
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

        st.markdown("##### ✉️ Enviar Comprobante por Correo Electrónico")
        correo_destino_input = st.text_input("Correo electrónico del paciente:", value=correo_ax, placeholder="correo@ejemplo.com", key="input_correo_envio_modal")

        if st.button("🚀 Enviar Comprobante por Correo", use_container_width=True, key="btn_enviar_mail_modal"):
            if not correo_destino_input.strip():
                st.warning("⚠️ Ingrese un correo electrónico válido.")
            else:
                exito, mensaje = enviar_comprobante_correo(
                    destinatario_email=correo_destino_input.strip(),
                    nombre_paciente=nombre_val,
                    folio=folio_val,
                    dosis_str=dosis_val,
                    lotes_str=lotes_val,
                    fecha_val=fecha_val,
                    tipo="comprobante"
                )
                if exito:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Cerrar Comprobante", use_container_width=True):
            st.session_state.ultimo_comprobante_vacunacion = None
            st.session_state.reiniciar_busqueda = True
            st.session_state.cache_buster_val += 1
            st.rerun()


if st.session_state.get("ultimo_comprobante_vacunacion") is not None:
    mostrar_modal_comprobante_vacunacion()

if not st.session_state.get("autenticado_consulta", False):
    st.markdown('<p class="main-header">Acceso Restringido - Módulo Operativo CENSIA</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ingrese su correo electrónico y contraseña institucional</p>', unsafe_allow_html=True)

    with st.form("form_login_consulta"):
        correo_operador_input = st.text_input("📧 Correo Electrónico Institucional:", placeholder="ejemplo@issste.gob.mx")
        password = st.text_input("Contraseña:", type="password")
        btn_login = st.form_submit_button("Iniciar Sesión Operativa", use_container_width=True)

        if btn_login:
            correo_limpio = correo_operador_input.strip().lower()
            if not correo_limpio:
                st.error("⚠️ Debe ingresar su correo electrónico.")
            elif not password:
                st.error("⚠️ Debe ingresar su contraseña.")
            else:
                if (correo_limpio == "carlosju.med21@gmail.com" and password == "OtaniOrochi26") or (password == "OperativoInv26"):
                    st.session_state.autenticado_consulta = True
                    st.session_state.correo_operativo_asignado = correo_limpio
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas. Verifique su correo y contraseña.")
else:
    st.markdown('<p class="main-header">Módulo Operativo de Aplicación y Guía CENSIA</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Selección de jornada autorizada, evaluación clínica y registro de biológicos</p>', unsafe_allow_html=True)

    correo_sesion = st.session_state.get("correo_operativo_asignado", "").strip().lower()
    h_autorizadas = obtener_hojas_autorizadas_cacheadas(correo_sesion)

    if correo_sesion == "carlosju.med21@gmail.com":
        st.markdown(f'<div class="section-title">👑 Vista Administrador Universal: <code>{correo_sesion}</code></div>', unsafe_allow_html=True)
        opciones_select = [f"{item['titulo']}||{item['sheet_id']}" for item in h_autorizadas]
        seleccion_jornada = st.selectbox(
            "Seleccione la Hoja / Jornada a Operar:", 
            options=opciones_select, 
            format_func=lambda x: x.split("||")[0]
        ) if opciones_select else None
        
        if seleccion_jornada:
            partes_sel = seleccion_jornada.split("||")
            hoja_seleccionada = partes_sel[0]
            sheet_id_activo = partes_sel[1]
        else:
            hoja_seleccionada = None
            sheet_id_activo = GOOGLE_SHEET_ID
    else:
        st.markdown(f'<div class="section-title">1. Jornada Operativa Asignada a: <code>{correo_sesion}</code></div>', unsafe_allow_html=True)
        if not h_autorizadas:
            st.warning(f"⚠️ No se encontró ninguna hoja autorizada asociada al correo: **{correo_sesion}**.")
            hoja_seleccionada = None
            sheet_id_activo = GOOGLE_SHEET_ID
        else:
            hoja_seleccionada = h_autorizadas[0]["titulo"]
            sheet_id_activo = h_autorizadas[0]["sheet_id"]
            st.info(f"📋 Pestaña asignada automáticamente a tu cuenta: **{hoja_seleccionada}**")

    if correo_sesion != "carlosju.med21@gmail.com":
        params_url = st.query_params
        hoja_enlace = params_url.get("hoja_activa", "")
        if hoja_enlace:
            for item in h_autorizadas:
                if item["titulo"] == hoja_enlace:
                    hoja_seleccionada = item["titulo"]
                    sheet_id_activo = item["sheet_id"]
                    break

    if hoja_seleccionada:
        try:
            pacientes_cargados, todos_los_datos, fecha_aplicacion_hoja, worksheet_activa = cargar_pacientes_hoja_cacheada(
                hoja_seleccionada, sheet_id_activo, cache_buster=st.session_state.cache_buster_val
            )
        except Exception as e:
            pacientes_cargados = []
            todos_los_datos = []
            worksheet_activa = None
            st.error(f"Error al leer los datos de la hoja {hoja_seleccionada}: {e}")

        hoja_actual = hoja_seleccionada if hoja_seleccionada else ""
        url_externa = f"ver_tabla?hoja={urllib.parse.quote(hoja_actual)}&sheet_id={urllib.parse.quote(sheet_id_activo)}"

        st.markdown(
            f"""
            <div style="margin-top: 5px; margin-bottom: 20px;">
                <a href="{url_externa}" target="_blank" style="background-color: #1e5b4f; color: white; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;">
                    🪟 Abrir Censo en Ventana Externa (Pantalla Completa)
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title">2. Lupa de Búsqueda Rápida y Registro</div>', unsafe_allow_html=True)

        col_busq1, col_busq2 = st.columns([4, 1])
        with col_busq1:
            query_busqueda = st.text_input("🔍 Buscar por Folio, Apellido o Nombre:", placeholder="Escriba parte del folio, apellido o nombre...", key="input_busqueda_lupa")
        with col_busq2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar Lupa", use_container_width=True):
                st.session_state.cache_buster_val += 1
                st.rerun()

        if not pacientes_cargados:
            st.info("La jornada seleccionada aún no cuenta con pacientes registrados en el censo.")
        else:
            q_clean = query_busqueda.strip().upper()
            pacientes_filtrados = pacientes_cargados if not q_clean else [
                p for p in pacientes_cargados if q_clean in p["folio"].upper() or q_clean in p["paterno"].upper() or q_clean in p["materno"].upper() or q_clean in p["nombres"].upper()
            ]

            if not pacientes_filtrados:
                if q_clean:
                    st.warning("No se encontraron pacientes que coincidan con la búsqueda.")
                else:
                    st.info("ℹ️ Ingrese un criterio de búsqueda (Folio, Apellido o Nombre) para localizar y evaluar al paciente.")
            else:
                opciones_busqueda = [
                    f"{p['folio']} - {p['paterno']} {p['materno']}, {p['nombres']} {'(🟢 YA VACUNADO)' if p['ya_vacunado'] else ''}||{p['fila']}"
                    for p in pacientes_filtrados
                ]

                if not q_clean:
                    opciones_busqueda.insert(0, "Seleccione un paciente de la lista...||0")

                seleccion_paciente = st.selectbox("Seleccione del listado de coincidencias:", options=opciones_busqueda, format_func=lambda x: x.split("||")[0])

                if seleccion_paciente and not seleccion_paciente.startswith("Seleccione un paciente"):
                    fila_idx = int(seleccion_paciente.split("||")[1])
                    fila_datos = todos_los_datos[fila_idx - 1]

                    esta_vacunado_actual = any(str(fila_datos[i]).strip().upper() == "X" for i in range(32, min(43, len(fila_datos))))
                    if esta_vacunado_actual:
                        st.warning("⚠️ **AVISO:** Este paciente ya tiene registrada la aplicación de su vacuna en el censo.")

                    folio_p = fila_datos[1] if len(fila_datos) > 1 else ""
                    
                    if sheet_id_activo == SHEET_ID_20_NOV:
                        paterno_p = fila_datos[13] if len(fila_datos) > 13 else ""
                        materno_p = fila_datos[14] if len(fila_datos) > 14 else ""
                        nombres_p = fila_datos[12] if len(fila_datos) > 12 else ""
                    else:
                        paterno_p = fila_datos[2] if len(fila_datos) > 2 else ""
                        materno_p = fila_datos[3] if len(fila_datos) > 3 else ""
                        nombres_p = fila_datos[4] if len(fila_datos) > 4 else ""

                    correo_ax_val = ""
                    for idx_col in [49, 50, 48, len(fila_datos) - 1]:
                        if len(fila_datos) > idx_col and "@" in str(fila_datos[idx_col]):
                            correo_ax_val = str(fila_datos[idx_col]).strip()
                            break

                    dd_n = fila_datos[5] if len(fila_datos) > 5 else "01"
                    mm_n = fila_datos[6] if len(fila_datos) > 6 else "01"
                    yy_n = fila_datos[7] if len(fila_datos) > 7 else "2000"

                    try:
                        d_n_int = int(dd_n)
                        m_n_int = int(mm_n)
                        y_n_int = int(yy_n)
                        f_nac = datetime.date(y_n_int, m_n_int, d_n_int)
                        f_hoy = datetime.date.today()
                        edad_meses_calc = (f_hoy.year - f_nac.year) * 12 + (f_hoy.month - f_nac.month)
                        if f_hoy.day < f_nac.day:
                            edad_meses_calc -= 1
                    except:
                        edad_meses_calc = 372

                    sexo_p = fila_datos[10] if len(fila_datos) > 10 else "H"
                    curp_actual = todos_los_datos[fila_idx][2].strip() if len(todos_los_datos) > fila_idx and len(todos_los_datos[fila_idx]) > 2 else ""

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

                    comorb_map = {
                        17: "EMBARAZADAS",
                        18: "PERSONAL DE SALUD",
                        19: "VIH",
                        20: "DIABETES",
                        21: "OBESIDAD",
                        22: "CARDIOPATÍAS",
                        23: "ENFERMEDAD PULMONAR",
                        24: "CÁNCER",
                        25: "CONGÉNITAS",
                        26: "INSUFICIENCIA RENAL",
                        27: "INMUNOSUPRESIÓN",
                        28: "DISCAPACIDAD",
                        29: "FIBROSIS QUÍSTICA",
                        30: "HIPERTENSIÓN",
                    }
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

                    st.markdown(f"##### 📋 Datos Generales del Paciente (Folio: `{folio_p}` — Vacuna Solicitada: **{vacuna_registrada}** — Grupo: **{grupo_detallado_vista}**)")

                    habilitar_edicion = st.checkbox("🔓 Habilitar campos para edición en vivo", key=f"chk_edit_{fila_idx}")

                    c_ed1, c_ed2, c_ed3 = st.columns(3)
                    with c_ed1:
                        ed_paterno = st.text_input("Apellido Paterno:", value=paterno_p, disabled=not habilitar_edicion, key=f"ed_pat_{fila_idx}")
                    with c_ed2:
                        ed_materno = st.text_input("Apellido Materno:", value=materno_p, disabled=not habilitar_edicion, key=f"ed_mat_{fila_idx}")
                    with c_ed3:
                        ed_nombres = st.text_input("Nombres:", value=nombres_p, disabled=not habilitar_edicion, key=f"ed_nom_{fila_idx}")

                    c_ed4, c_ed5, c_ed6, c_ed7 = st.columns([1, 1, 1, 3])
                    with c_ed4:
                        ed_d = st.text_input("Día (Nac):", value=dd_n, disabled=not habilitar_edicion, key=f"ed_d_{fila_idx}")
                    with c_ed5:
                        ed_m = st.text_input("Mes (Nac):", value=mm_n, disabled=not habilitar_edicion, key=f"ed_m_{fila_idx}")
                    with c_ed6:
                        ed_y = st.text_input("Año (Nac):", value=yy_n, disabled=not habilitar_edicion, key=f"ed_y_{fila_idx}")
                    with c_ed7:
                        ed_sexo = st.selectbox("Sexo:", options=["H", "M"], index=0 if sexo_p == "H" else 1, disabled=not habilitar_edicion, key=f"ed_sex_{fila_idx}")

                    ed_curp = st.text_input("CURP:", value=curp_actual, max_chars=18, disabled=not habilitar_edicion, key=f"ed_curp_{fila_idx}")

                    st.markdown('<div class="section-title">3. Guía y Lineamientos CENSIA (Tarjetas de Grupos Prioritarios)</div>', unsafe_allow_html=True)

                    antecedente_vacunal = "NO"
                    matches_inf, matches_covid = obtener_recomendaciones_paciente(categoria_paciente, lista_riesgos_detectados, vacuna_registrada, edad_meses_calc, antecedente_vacunal)

                    mostrar_influenza = vacuna_registrada in ["INFLUENZA", "AMBAS"]
                    mostrar_covid = vacuna_registrada in ["COVID-19", "AMBAS"]

                    match_inf_prioritario = matches_inf[0] if matches_inf else None
                    match_cov_prioritario = matches_covid[0] if matches_covid else None

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
                            st.markdown(
                                f"""
                                <div style="background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; margin-bottom: 15px; min-height: 280px;">
                                    <h4 style="color: #611232; margin-top: 0;">🦠 COVID-19</h4>
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

                    st.markdown('<div class="section-title">4. Registro de Dosis Aplicadas, Lotes y Caducidad</div>', unsafe_allow_html=True)

                    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    meses_dict_num = {
                        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
                        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
                        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
                    }

                    st.markdown("##### 💉 INFLUENZA")
                    c_inf_d1, c_inf_d2, c_inf_d3 = st.columns(3)
                    with c_inf_d1:
                        inf_1ra = st.checkbox("1ra dosis", key=f"chk_inf_1ra_{fila_idx}")
                    with c_inf_d2:
                        inf_2da = st.checkbox("2da dosis", key=f"chk_inf_2da_{fila_idx}")
                    with c_inf_d3:
                        inf_anual = st.checkbox("Anual", key=f"chk_inf_anual_{fila_idx}")

                    tiene_dosis_influenza = inf_1ra or inf_2da or inf_anual

                    c_inf_l, c_inf_c = st.columns(2)
                    with c_inf_l:
                        lote_inf_input = st.text_input("Lote Influenza", value=st.session_state.lote_influenza_memoria, placeholder="Ej. A1234", key=f"lote_inf_{fila_idx}", disabled=not tiene_dosis_influenza)
                    with c_inf_c:
                        if tiene_dosis_influenza:
                            st.markdown("<p style='font-size:0.85rem; font-weight:bold; color:#1e5b4f; margin-bottom:2px;'>📅 Fecha Caducidad Influenza:</p>", unsafe_allow_html=True)
                            c_ci1, c_ci2, c_ci3 = st.columns(3)
                            with c_ci1:
                                cad_i_d = st.selectbox("Día Inf", options=[str(d).zfill(2) for d in range(1, 32)], key=f"cal_inf_d_{fila_idx}", label_visibility="collapsed")
                            with c_ci2:
                                cad_i_m_nombre = st.selectbox("Mes Inf", options=meses_nombres, key=f"cal_inf_m_{fila_idx}", label_visibility="collapsed")
                                cad_i_m = meses_dict_num[cad_i_m_nombre]
                            with c_ci3:
                                anio_actual = datetime.date.today().year
                                cad_i_y = st.selectbox("Año Inf", options=[str(a) for a in range(anio_actual, anio_actual + 6)], key=f"cal_inf_y_{fila_idx}", label_visibility="collapsed")
                            cad_inf_input = f"{cad_i_d}/{cad_i_m}/{cad_i_y}"
                        else:
                            cad_inf_input = st.text_input("Caducidad Influenza (DD/MM/AAAA)", value="", placeholder="DD/MM/AAAA", key=f"cad_inf_disabled_{fila_idx}", disabled=True)

                    if not tiene_dosis_influenza:
                        st.info("🔒 Marque al menos una casilla de Influenza para habilitar el lote y la fecha de caducidad.")

                    st.markdown("---")

                    st.markdown("##### 🦠 COVID-19")
                    c_cov_d1, c_cov_d2, c_cov_d3 = st.columns(3)
                    with c_cov_d1:
                        cov_1ra = st.checkbox("COVID 1ra", key=f"chk_cov_1ra_{fila_idx}")
                    with c_cov_d2:
                        cov_2da = st.checkbox("COVID 2da", key=f"chk_cov_2da_{fila_idx}")
                    with c_cov_d3:
                        cov_anual = st.checkbox("Anual", key=f"chk_cov_anual_{fila_idx}")

                    tiene_dosis_covid = cov_1ra or cov_2da or cov_anual

                    c_cov_l, c_cov_c = st.columns(2)
                    with c_cov_l:
                        lote_cov_input = st.text_input("Lote COVID-19", value=st.session_state.lote_covid_memoria, placeholder="Ej. C5678", key=f"lote_cov_{fila_idx}", disabled=not tiene_dosis_covid)
                    with c_cov_c:
                        if tiene_dosis_covid:
                            st.markdown("<p style='font-size:0.85rem; font-weight:bold; color:#611232; margin-bottom:2px;'>📅 Fecha Caducidad COVID-19:</p>", unsafe_allow_html=True)
                            c_cc1, c_cc2, c_cc3 = st.columns(3)
                            with c_cc1:
                                cad_c_d = st.selectbox("Día Cov", options=[str(d).zfill(2) for d in range(1, 32)], key=f"cal_cov_d_{fila_idx}", label_visibility="collapsed")
                            with c_cc2:
                                cad_c_m_nombre = st.selectbox("Mes Cov", options=meses_nombres, key=f"cal_cov_m_{fila_idx}", label_visibility="collapsed")
                                cad_c_m = meses_dict_num[cad_c_m_nombre]
                            with c_cc3:
                                anio_actual = datetime.date.today().year
                                cad_c_y = st.selectbox("Año Cov", options=[str(a) for a in range(anio_actual, anio_actual + 6)], key=f"cal_cov_y_{fila_idx}", label_visibility="collapsed")
                            cad_cov_input = f"{cad_c_d}/{cad_c_m}/{cad_c_y}"
                        else:
                            cad_cov_input = st.text_input("Caducidad COVID (DD/MM/AAAA)", value="", placeholder="DD/MM/AAAA", key=f"cad_cov_disabled_{fila_idx}", disabled=True)

                    if not tiene_dosis_covid:
                        st.info("🔒 Marque al menos una casilla de COVID-19 para habilitar el lote y la fecha de caducidad.")

                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                    biologico_covid_elegido = "COVID-19"

                    if st.button("💾 Guardar Aplicación y Actualizar Hoja Sheets", use_container_width=True, key=f"btn_guardar_{fila_idx}"):
                        if "ultimo_comprobante_vacunacion" in st.session_state and st.session_state.ultimo_comprobante_vacunacion:
                            st.session_state.ultimo_comprobante_vacunacion["correo_ax"] = correo_ax_val

                        exito = procesar_guardado_aplicacion(
                            worksheet_activa=worksheet_activa,
                            fila_idx=fila_idx,
                            todos_los_datos=todos_los_datos,
                            inf_1ra=inf_1ra, inf_2da=inf_2da, inf_anual=inf_anual,
                            cov_1ra=cov_1ra, cov_2da=cov_2da, cov_anual=cov_anual,
                            lote_inf_input=lote_inf_input, cad_inf_input=cad_inf_input,
                            lote_cov_input=lote_cov_input, cad_cov_input=cad_cov_input,
                            biologico_covid_elegido=biologico_covid_elegido,
                            habilitar_edicion=habilitar_edicion,
                            ed_paterno=ed_paterno, ed_materno=ed_materno, ed_nombres=ed_nombres,
                            ed_d=ed_d, ed_m=ed_m, ed_y=ed_y, ed_sexo=ed_sexo, ed_curp=ed_curp,
                            paterno_p=paterno_p, materno_p=materno_p, nombres_p=nombres_p,
                            fecha_aplicacion_hoja=fecha_aplicacion_hoja,
                            sheet_id_objetivo=sheet_id_activo
                        )

                        if exito:
                            comprobante_actual = st.session_state.get("ultimo_comprobante_vacunacion", {})
                            
                            if correo_ax_val and "@" in correo_ax_val:
                                enviado_ok, msg_correo = enviar_comprobante_correo(
                                    destinatario_email=correo_ax_val.strip(),
                                    nombre_paciente=comprobante_actual.get("nombre", f"{paterno_p} {materno_p}, {nombres_p}"),
                                    folio=comprobante_actual.get("folio", folio_p),
                                    dosis_str=comprobante_actual.get("dosis_str", "Vacunación Aplicada"),
                                    lotes_str=comprobante_actual.get("lotes_str", "N/A"),
                                    fecha_val=comprobante_actual.get("fecha_aplicacion", fecha_aplicacion_hoja),
                                    tipo="comprobante"
                                )
                                if enviado_ok:
                                    st.success(f"📧 Comprobante oficial enviado exitosamente a: {correo_ax_val}")
                                else:
                                    st.error(f"❌ Error al enviar el correo automático: {msg_correo}")
                            else:
                                st.warning("⚠️ El paciente no cuenta con un correo electrónico registrado en la columna AX para el envío automático.")

                            if st.session_state.get("ultimo_comprobante_vacunacion"):
                                st.session_state.ultimo_comprobante_vacunacion["correo_ax"] = correo_ax_val
                            
                            # Incrementamos el cache buster para forzar lectura limpia en cualquier unidad
                            st.session_state.cache_buster_val += 1
                            st.rerun()
