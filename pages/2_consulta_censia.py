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

# --- ESTILOS ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
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
# CLIENTE Y SPREADSHEET CACHEADOS (reduce overhead de auth/apertura)
# ============================================================
@st.cache_resource
def obtener_client_gspread_cacheado():
    """Cachea el cliente de gspread (evita re-autenticaciones frecuentes)."""
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    # gspread maneja internamente la sesión con service_account_from_dict
    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)


@st.cache_resource
def obtener_spreadsheet_cacheado():
    """Cachea el objeto Spreadsheet (open_by_key) para reutilizarlo sin reabrirlo."""
    client = obtener_client_gspread_cacheado()
    return client.open_by_key(GOOGLE_SHEET_ID)


def obtener_worksheet_activa(hoja_seleccionada: str):
    """Devuelve el worksheet activo usando el spreadsheet cacheado (no cacheado por Streamlit)."""
    spreadsheet = obtener_spreadsheet_cacheado()
    return spreadsheet.worksheet(hoja_seleccionada)


# ============================================================
# CARGA DE PACIENTES (cacheada, con rango limitado y versión controlada)
# ============================================================
# Ajusta este rango según cuántas columnas/filas use tu censo.
PACIENTES_RANGO = "A14:BK1000"  # lee desde fila 14 hasta BK (suficiente para muchas columnas)

@st.cache_data(ttl=120)
def cargar_pacientes_hoja_cacheada(hoja_seleccionada: str, cache_version: int = 0):
    """
    Carga pacientes devolviendo únicamente tipos serializables.
    cache_version forzará re-evaluación cuando se incremente al guardar.
    """
    try:
        spreadsheet = obtener_spreadsheet_cacheado()
        worksheet_activa = spreadsheet.worksheet(hoja_seleccionada)

        # Solicitamos solo un rango limitado para minimizar transferencia y latencia.
        # Devolveremos all_values como lista de listas (serializable).
        all_values = worksheet_activa.get(PACIENTES_RANGO)
        # Si la hoja es más corta, get() puede devolver menos filas; nos defendemos.
        pacientes_cargados = []
        if len(all_values) >= 1:
            # all_values corresponde a A14:BK...; mapear índices relativo a la fila 14
            for idx_rel, row in enumerate(all_values, start=14):
                if len(row) > 1 and row[1].strip() and row[2].strip():
                    # comprobamos columnas de vacunación en un rango seguro dentro del row
                    ya_vacunado = any(
                        str(row[i]).strip().upper() == "X"
                        for i in range(32, min(43, len(row)))
                    )
                    pacientes_cargados.append(
                        {
                            "fila": idx_rel,
                            "folio": row[1].strip(),
                            "paterno": row[2].strip(),
                            "materno": row[3].strip() if len(row) > 3 else "",
                            "nombres": row[4].strip() if len(row) > 4 else "",
                            "ya_vacunado": ya_vacunado,
                        }
                    )

        return pacientes_cargados, all_values, datetime.datetime.now().strftime("%d/%m/%Y")
    except Exception as e:
        st.error(f"Error al leer la hoja {hoja_seleccionada}: {e}")
        return [], [], datetime.datetime.now().strftime("%d/%m/%Y")


# ============================================================
# DIÁLOGOS Y UI (sin cambios lógicos, pero aprovechando cache_version)
# ============================================================
@st.dialog("⚠️ ¿ESTÁS SEGURO DE SALIR?")
def mostrar_dialogo_cerrar_sesion():
    st.markdown(
        "<b>Todos los datos, dosis y lotes registrados se han guardado automáticamente en Google Sheets.</b>",
        unsafe_allow_html=True,
    )
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

# Estado de sesión (inicializaciones)
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

if "cache_ver_pacientes" not in st.session_state:
    st.session_state.cache_ver_pacientes = 0

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
        <style>/* estilos ... iguales a los anteriores */</style>
        </head>
        <body>
            <div id="comprobante-captura">
                <div>COMPROBANTE DE VACUNACIÓN OFICIAL</div>
                <div>Paciente: {nombre_val}</div>
                <div>Dosis: {dosis_val}</div>
                <div>Lotes: {lotes_val}</div>
                <div>Fecha: {fecha_val}</div>
                <div><img src="{url_qr_api}" alt="QR"></div>
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
        correo_destino_input = st.text_input(
            "Correo electrónico del paciente:",
            value=correo_ax,
            placeholder="correo@ejemplo.com",
            key="input_correo_envio_modal",
        )

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
                    tipo="comprobante",
                )
                if exito:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Cerrar Comprobante", use_container_width=True):
            st.session_state.ultimo_comprobante_vacunacion = None
            st.session_state.reiniciar_busqueda = True
            st.rerun()


# Mostrar modal si existe comprobante en sesión
if st.session_state.get("ultimo_comprobante_vacunacion") is not None:
    mostrar_modal_comprobante_vacunacion()


# --- Login simple ---
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

    # Cargar hojas autorizadas (cacheada)
    h_autorizadas = cargar_hojas := None
    try:
        h_autorizadas = obtener_spreadsheet_cacheado().worksheets()
        # convert to titles excluding plantilla
        hojas_plantillas_excluir = {"CENSO NOMINAL", "CENSO", "Influenza", "COVID"}
        h_autorizadas = [h.title for h in h_autorizadas if h.title not in hojas_plantillas_excluir]
        # filtro por AU4 si no es administrador
        if correo_sesion != "carlosju.med21@gmail.com":
            hojas_permitidas = []
            for title in h_autorizadas:
                try:
                    w = obtener_worksheet_activa(title)
                    val_au4 = w.acell("AU4").value
                    if val_au4 and val_au4.strip().lower() == correo_sesion:
                        hojas_permitidas.append(title)
                except Exception:
                    pass
            h_autorizadas = hojas_permitidas
    except Exception as e:
        st.error(f"Error al listar hojas autorizadas: {e}")
        h_autorizadas = []

    if correo_sesion == "carlosju.med21@gmail.com":
        st.markdown(f'<div class="section-title">👑 Vista Administrador Universal: <code>{correo_sesion}</code></div>', unsafe_allow_html=True)
        hoja_seleccionada = st.selectbox("Seleccione la Hoja / Jornada a Operar:", options=h_autorizadas) if h_autorizadas else None
    else:
        st.markdown(f'<div class="section-title">1. Jornada Operativa Asignada a: <code>{correo_sesion}</code></div>', unsafe_allow_html=True)
        if not h_autorizadas:
            st.warning(f"⚠️ No se encontró ninguna hoja autorizada asociada al correo: **{correo_sesion}**.")
            hoja_seleccionada = None
        else:
            hoja_seleccionada = h_autorizadas[0]
            st.info(f"📋 Pestaña asignada automáticamente a tu cuenta: **{hoja_seleccionada}**")

    # Soporta override desde query params
    if correo_sesion != "carlosju.med21@gmail.com":
        params_url = st.query_params
        hoja_enlace = params_url.get("hoja_activa", "")
        if hoja_enlace and hoja_enlace in h_autorizadas:
            hoja_seleccionada = hoja_enlace

    # Si hay hoja elegida, cargamos pacientes (cacheada por versión)
    if hoja_seleccionada:
        try:
            cache_ver = st.session_state.get("cache_ver_pacientes", 0)
            pacientes_cargados, todos_los_datos, fecha_aplicacion_hoja = cargar_pacientes_hoja_cacheada(hoja_seleccionada, cache_ver)
            worksheet_activa = obtener_worksheet_activa(hoja_seleccionada)
        except Exception as e:
            pacientes_cargados = []
            todos_los_datos = []
            worksheet_activa = None
            st.error(f"Error al leer los datos de la hoja {hoja_seleccionada}: {e}")

        hoja_actual = hoja_seleccionada if hoja_seleccionada else ""
        url_externa = f"ver_tabla?hoja={urllib.parse.quote(hoja_actual)}"

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
                # incrementa versión para forzar recarga controlada
                st.session_state.cache_ver_pacientes = st.session_state.get("cache_ver_pacientes", 0) + 1
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
                    # Convertimos fila_idx en índice relativo dentro de todos_los_datos (que empezó en fila 14)
                    idx_rel = fila_idx - 14
                    fila_datos = todos_los_datos[idx_rel] if 0 <= idx_rel < len(todos_los_datos) else []

                    esta_vacunado_actual = any(str(fila_datos[i]).strip().upper() == "X" for i in range(32, min(43, len(fila_datos)))) if fila_datos else False
                    if esta_vacunado_actual:
                        st.warning("⚠️ **AVISO:** Este paciente ya tiene registrada la aplicación de su vacuna en el censo.")

                    folio_p = fila_datos[1] if len(fila_datos) > 1 else ""
                    paterno_p = fila_datos[2] if len(fila_datos) > 2 else ""
                    materno_p = fila_datos[3] if len(fila_datos) > 3 else ""
                    nombres_p = fila_datos[4] if len(fila_datos) > 4 else ""

                    correo_ax_val = fila_datos[49].strip() if len(fila_datos) > 49 else ""

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
                    except Exception:
                        edad_meses_calc = 372

                    sexo_p = fila_datos[10] if len(fila_datos) > 10 else "H"
                    curp_actual = fila_datos[2].strip() if len(fila_datos) > 2 else ""

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

                    # Lista de riesgos y lógica (igual que antes)
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

                    # ediciones, controles y bloques de dosis (idénticos al anterior) ...
                    # Para no alargar demasiado este snippet, mantén aquí el mismo bloque
                    # que tenías para los inputs de edición y registro de dosis/caducidades.
                    # IMPORTANTE: cuando llames a procesar_guardado_aplicacion, usa worksheet_activa
                    # que ya obtuviste anteriormente.

                    # --- EJEMPLO DE GUARDADO (usa tu función real tal cual) ---
                    # ... (mantén el bloque de inputs y el botón de guardado)
                    # en el handler de guardado, en lugar de st.cache_data.clear():
                    # st.session_state.cache_ver_pacientes = st.session_state.get("cache_ver_pacientes", 0) + 1
                    # st.rerun()

                    # (El resto del código UI y guardado se mantiene idéntico al original,
                    #  usando worksheet_activa para las operaciones de escritura.)
