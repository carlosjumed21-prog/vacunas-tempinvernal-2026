import datetime
import io
import json
import urllib.parse
from config import (
    GOOGLE_SCOPES,
    GOOGLE_SHEET_ID,
    UNIDADES_ISSSTE,
    aplicar_configuracion_global,
)
from google.oauth2 import service_account
import gspread
import qrcode
import streamlit as st

aplicar_configuracion_global("Panel de Administración - Censo Nominal", "⚙️")

# --- OCULTAR LA BARRA SUPERIOR NATIVA DE STREAMLIT ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)

# --- ID DE LA CARPETA DE DRIVE PROPORCIONADA PARA ARCHIVOS AISLADOS ---
CARPETA_DESTINO_DRIVE_ID = "15gg0KzXi7nD5WaZ0nUPDb-vRPgJS_cZp"

col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("🚪 Cerrar Sesión de Administrador", use_container_width=True):
        st.session_state.autenticado_admin = False
        st.session_state.usuario_admin_actual = ""
        st.session_state.jornada_autorizada = False
        st.session_state.hojas_creadas_recientes = []
        st.rerun()
with col_nav2:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

if "autenticado_admin" not in st.session_state:
    st.session_state.autenticado_admin = False
if "usuario_admin_actual" not in st.session_state:
    st.session_state.usuario_admin_actual = ""
if "unidad_anterior" not in st.session_state:
    st.session_state.unidad_anterior = ""
if "config_direccion_base" not in st.session_state:
    st.session_state.config_direccion_base = (
        "Avenida Félix Cuevas 540, Del Valle Sur, Benito Juárez, 03100 Ciudad de México, CDMX"
    )
if "jornada_autorizada" not in st.session_state:
    st.session_state.jornada_autorizada = False
if "hojas_creadas_recientes" not in st.session_state:
    st.session_state.hojas_creadas_recientes = []

if "historial_jornadas" not in st.session_state:
    st.session_state.historial_jornadas = []

if not st.session_state.autenticado_admin:
    st.markdown(
        '<p class="main-header">Acceso Restringido - Panel de Administración</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Ingrese su correo electrónico y contraseña de administrador</p>',
        unsafe_allow_html=True,
    )

    with st.form("form_login_admin"):
        correo_admin_input = st.text_input(
            "📧 Correo Electrónico Administrador:",
            placeholder="carlosju.med21@gmail.com"
        )
        password_admin = st.text_input("Contraseña:", type="password")
        
        btn_login_admin = st.form_submit_button(
            "Ingresar al Panel", use_container_width=True
        )

        if btn_login_admin:
            correo_admin_limpio = correo_admin_input.strip().lower()
            if not correo_admin_limpio:
                st.error("⚠️ Debe ingresar su correo electrónico.")
            elif not password_admin:
                st.error("⚠️ Debe ingresar su contraseña.")
            else:
                if (correo_admin_limpio == "carlosju.med21@gmail.com" and password_admin == "OtaniOrochi26") or \
                   (correo_admin_limpio == "wendy@issste.gob.mx" and password_admin == "MedPrev26"):
                    st.session_state.autenticado_admin = True
                    st.session_state.usuario_admin_actual = correo_admin_limpio
                    st.rerun()
                else:
                    st.error("❌ Correo o contraseña de administrador incorrectos.")
else:
    st.markdown(
        '<p class="main-header">Panel de Control y Administración (Espejo y Seguridad)</p>',
        unsafe_allow_html=True,
    )

    tab_creacion, tab_historial = st.tabs(["🚀 Creación de Jornadas", "📋 Historial y Estatus de Jornadas"])

    with tab_creacion:
        st.markdown(
            '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">1. Configuración de Operación y Unidad</div>',
            unsafe_allow_html=True,
        )

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            unidad_sel = st.selectbox(
                "Unidad Médica ISSSTE:", options=list(UNIDADES_ISSSTE.keys())
            )
            siglas_unidad = (
                UNIDADES_ISSSTE[unidad_sel]["sigla"]
                if unidad_sel in UNIDADES_ISSSTE
                else ""
            )

        with col_c2:
            jornada_sel = st.selectbox(
                "Tipo de Jornada:",
                options=["Seleccione tipo...", "Intramuros I", "Extramuros E"],
            )
            tipo_jornada_letra = (
                "I"
                if "Intramuros" in jornada_sel
                else ("E" if "Extramuros" in jornada_sel else "")
            )
            tipo_jornada_texto = (
                "INTRA"
                if tipo_jornada_letra == "I"
                else ("EXTRA" if tipo_jornada_letra == "E" else "")
            )

        if (
            unidad_sel != "Seleccione una unidad médica..."
            and st.session_state.unidad_anterior != unidad_sel
        ):
            st.session_state.unidad_anterior = unidad_sel
            st.session_state.config_direccion_base = UNIDADES_ISSSTE[unidad_sel]["dir"]
            st.session_state.jornada_autorizada = False
            st.rerun()

        if (
            unidad_sel == "Seleccione una unidad médica..."
            or jornada_sel == "Seleccione tipo..."
        ):
            st.warning(
                "⚠️ Por favor seleccione una Unidad Médica y un Tipo de Jornada válidos para habilitar la configuración."
            )
        else:
            st.markdown("---")
            jornadas_simultaneas = st.toggle(
                "⚡ Activar Jornadas Simultáneas (Múltiples equipos o células en operación)",
                value=False,
            )

            num_jornadas = 1
            if jornadas_simultaneas:
                num_jornadas = st.number_input(
                    "Número de jornadas simultáneas a habilitar:",
                    min_value=2,
                    max_value=5,
                    value=2,
                    step=1,
                )

            st.markdown(
                '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">2. Parámetros Independientes por Cédula / Brigada</div>',
                unsafe_allow_html=True,
            )

            config_jornadas_activas = []

            if not jornadas_simultaneas:
                st.markdown('<div class="card-simultanea">', unsafe_allow_html=True)
                resp_unico = st.text_input(
                    "👤 Nombre del responsable de vacunación:",
                    placeholder="Escriba el nombre completo...",
                )
                correo_resp_unico = st.text_input(
                    "📧 Correo electrónico del responsable (Dueño del archivo aislado):",
                    placeholder="ejemplo@issste.gob.mx",
                    key="correo_resp_unico"
                )
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    f_app = st.date_input(
                        "Fecha de Aplicación:",
                        value=datetime.date.today(),
                        format="DD/MM/YYYY",
                        key="f_app_unica",
                    )
                with col_f2:
                    h_ini = st.time_input(
                        "Hora Inicio:", value=datetime.time(8, 0), key="h_ini_unica"
                    )
                with col_f3:
                    h_fin = st.time_input(
                        "Hora Cierre:", value=datetime.time(14, 0), key="h_fin_unica"
                    )

                dir_oficial = st.text_area(
                    "📍 Dirección Oficial de esta Jornada:",
                    value=st.session_state.config_direccion_base,
                    height=70,
                    key="dir_unica",
                )
                st.markdown("</div>", unsafe_allow_html=True)

                config_jornadas_activas.append({
                    "sufijo_hoja": "",
                    "sufijo_qr": "",
                    "responsable": resp_unico.upper() if resp_unico else "PERSONAL",
                    "correo": correo_resp_unico.strip().lower(),
                    "fecha": f_app,
                    "hora_inicio": h_ini,
                    "hora_fin": h_fin,
                    "direccion": dir_oficial,
                })
            else:
                st.info(
                    f"Configurando {num_jornadas} equipos simultáneos con fechas, horarios y ubicaciones personalizadas:"
                )
                for i in range(1, num_jornadas + 1):
                    st.markdown(
                        f'<div class="card-simultanea"><h4 style="color: #1e5b4f; margin-top:0;">📋 Cédula / Brigada Simultánea # {i}</h4>',
                        unsafe_allow_html=True,
                    )
                    resp_sim = st.text_input(
                        f"👤 Responsable de Brigada #{i}:",
                        placeholder=f"Nombre del responsable {i}...",
                        key=f"resp_sim_{i}",
                    )
                    correo_sim = st.text_input(
                        f"📧 Correo electrónico de Brigada #{i}:",
                        placeholder=f"correo_brigada_{i}@issste.gob.mx",
                        key=f"correo_sim_{i}"
                    )

                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        f_app_sim = st.date_input(
                            f"Fecha de Aplicación #{i}:",
                            value=datetime.date.today(),
                            format="DD/MM/YYYY",
                            key=f"f_app_sim_{i}",
                        )
                    with col_f2:
                        h_ini_sim = st.time_input(
                            f"Hora Inicio #{i}:",
                            value=datetime.time(8, 0),
                            key=f"h_ini_sim_{i}",
                        )
                    with col_f3:
                        h_fin_sim = st.time_input(
                            f"Hora Cierre #{i}:",
                            value=datetime.time(14, 0),
                            key=f"h_fin_sim_{i}",
                        )

                    dir_sim = st.text_area(
                        f"📍 Dirección Oficial para Brigada #{i}:",
                        value=st.session_state.config_direccion_base,
                        height=70,
                        key=f"dir_sim_{i}",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                    config_jornadas_activas.append({
                        "sufijo_hoja": f"_JS{i}",
                        "sufijo_qr": f"_JS{i}",
                        "responsable": resp_sim.upper() if resp_sim else f"RESPONSABLE JS{i}",
                        "correo": correo_sim.strip().lower(),
                        "fecha": f_app_sim,
                        "hora_inicio": h_ini_sim,
                        "hora_fin": h_fin_sim,
                        "direccion": dir_sim,
                    })

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "🚀 Autorizar Jornada(s), Duplicar en Maestro y Crear Archivo Aislado",
                use_container_width=True,
            ):
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
                    
                    sheet_id_destino = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE" if siglas_unidad == "20N" else GOOGLE_SHEET_ID
                    spreadsheet_maestro = client.open_by_key(sheet_id_destino)

                    hojas_existentes = [h.title for h in spreadsheet_maestro.worksheets()]
                    duplicadas_detectadas = []

                    for j_conf in config_jornadas_activas:
                        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
                        if siglas_unidad == "20N":
                            nombre_prueba = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
                        else:
                            nombre_prueba = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"

                        if nombre_prueba in hojas_existentes:
                            duplicadas_detectadas.append(nombre_prueba)

                    if duplicadas_detectadas:
                        st.error(
                            "⚠️ ALERTA: Las siguientes hojas ya existen en Google Sheets maestro:"
                            f" {', '.join(duplicadas_detectadas)}. Por favor cambie la fecha o el tipo de jornada."
                        )
                    else:
                        hojas_creadas_exito = []
                        base_url = "https://medprev-vacunas-invernal.streamlit.app"

                        for j_conf in config_jornadas_activas:
                            fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
                            fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")

                            fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
                            resp_encoded = urllib.parse.quote(j_conf["responsable"])
                            js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
                            ruta_formulario = "registro_20_noviembre" if siglas_unidad == "20N" else "formulario"
                            link_paciente = f"{base_url}/{ruta_formulario}?unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"

                            nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL" if siglas_unidad == "20N" else f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
                            link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_objetivo)}"

                            url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_paciente)}"
                            formula_imagen_qr = f'=IMAGE("{url_qr_api}")'

                            # 1. Creamos la hoja en el Google Sheets MAESTRO
                            if siglas_unidad == "20N":
                                nombre_copia_1 = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
                                plantilla_1 = spreadsheet_maestro.worksheet("CENSO NOMINAL")
                                copia_1 = spreadsheet_maestro.duplicate_sheet(
                                    plantilla_1.id, 
                                    insert_sheet_index=len(spreadsheet_maestro.worksheets()), 
                                    new_sheet_name=nombre_copia_1
                                )
                                hoja_activa_maestro = spreadsheet_maestro.worksheet(nombre_copia_1)
                            else:
                                nombre_nueva_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
                                plantilla = spreadsheet_maestro.worksheet("CENSO NOMINAL")
                                nueva_hoja = spreadsheet_maestro.duplicate_sheet(
                                    plantilla.id, 
                                    insert_sheet_index=len(spreadsheet_maestro.worksheets()), 
                                    new_sheet_name=nombre_nueva_hoja
                                )
                                hoja_activa_maestro = spreadsheet_maestro.worksheet(nombre_nueva_hoja)
                                nombre_copia_1 = nombre_nueva_hoja
                                copia_1 = nueva_hoja

                            # Llenamos datos en el maestro
                            hoja_activa_maestro.update_acell("D7", "CDMX")
                            hoja_activa_maestro.update_acell("M7", "ISSSTE")
                            hoja_activa_maestro.update_acell("T7", "Delegación Sur")
                            hoja_activa_maestro.update_acell("AB7", "CDMX")
                            hoja_activa_maestro.update_acell("D8", "CDMX")
                            hoja_activa_maestro.update_acell("D9", unidad_sel)
                            hoja_activa_maestro.update_acell("AB9", fecha_formato_oficial)
                            hoja_activa_maestro.update_acell("E10", j_conf["responsable"])
                            hoja_activa_maestro.update(values=[[j_conf["correo"]]], range_name="AU4")
                            hoja_activa_maestro.update(values=[[link_paciente]], range_name="AU6")
                            hoja_activa_maestro.update(values=[[link_operativo]], range_name="AU7")
                            hoja_activa_maestro.update(values=[[formula_imagen_qr]], range_name="AU8", value_input_option='USER_ENTERED')

                            # 2. CREAR UN ARCHIVO AISLADO EN LA CARPETA DE DRIVE
                            spreadsheet_aislado = client.copy(sheet_id_destino, title=f"JORNADA_{nombre_copia_1}")
                            id_archivo_aislado = spreadsheet_aislado.id

                            if j_conf["correo"]:
                                try:
                                    spreadsheet_aislado.share(j_conf["correo"], perm_type='user', role='editor')
                                except Exception as share_err:
                                    print(f"Aviso de permisos: {share_err}")

                            hoja_info = {
                                "nombre": nombre_copia_1,
                                "gid": str(copia_1.id),
                                "unidad": unidad_sel,
                                "siglas_unidad": siglas_unidad,
                                "tipo_jornada": jornada_sel,
                                "tipo_jornada_letra": tipo_jornada_letra,
                                "responsable": j_conf["responsable"],
                                "correo": j_conf["correo"],
                                "fecha": j_conf["fecha"],
                                "sheet_id": sheet_id_destino,
                                "sheet_aislado_id": id_archivo_aislado
                            }
                            hojas_creadas_exito.append(hoja_info)
                            if not any(h["nombre"] == nombre_copia_1 for h in st.session_state.historial_jornadas):
                                st.session_state.historial_jornadas.append(hoja_info)

                        st.session_state.jornada_autorizada = True
                        st.session_state.hojas_creadas_recientes = hojas_creadas_exito
                        st.success(
                            "¡Jornada(s) autorizada(s) en el maestro y archivo aislado creado con éxito!"
                        )

                except Exception as e:
                    st.error(
                        "Error al configurar Google Sheets. Detalle: " + str(e)
                    )

            if (
                st.session_state.jornada_autorizada
                and st.session_state.hojas_creadas_recientes
            ):
                st.markdown("<br>", unsafe_allow_html=True)

                enlaces_html = ""
                for h_info in st.session_state.hojas_creadas_recientes:
                    url_archivo_aislado = f"https://docs.google.com/spreadsheets/d/{h_info['sheet_aislado_id']}/edit?usp=sharing"
                    enlaces_html += f"""
                    <div style="margin-bottom: 12px; background: #fff; padding: 10px; border-radius: 6px; border: 1px solid #1e5b4f;">
                        <b>Responsable:</b> {h_info['responsable']} ({h_info['correo']})<br>
                        <a href="{url_archivo_aislado}" target="_blank" style="background-color: #1e5b4f; color: white; padding: 6px 12px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block; margin-top: 5px; font-size: 0.9rem;">
                            📁 Abrir Archivo Exclusivo del Operativo
                        </a>
                    </div>
                    """

                st.markdown(
                    f"""
                    <div style="background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 18px; border-radius: 8px; margin-top: 15px;">
                        <h3 style="color: #1e5b4f; margin-top: 0; margin-bottom: 12px; text-align: center;">🟢 ARCHIVOS AISLADOS CREADOS</h3>
                        {enlaces_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">3. Generador de Enlaces y Códigos QR (Públicos y Operativos)</div>',
                    unsafe_allow_html=True,
                )

                base_url = "https://medprev-vacunas-invernal.streamlit.app"

                for idx, j_conf in enumerate(config_jornadas_activas, start=1):
                    fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
                    if siglas_unidad == "20N":
                        nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
                    else:
                        nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"

                    fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
                    resp_encoded = urllib.parse.quote(j_conf["responsable"])

                    js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
                    ruta_formulario = "registro_20_noviembre" if siglas_unidad == "20N" else "formulario"

                    link_paciente = f"{base_url}/{ruta_formulario}?unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
                    link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_objetivo)}"
                    link_prueba_simulacion = link_paciente + "&test=true"

                    titulo_seccion_qr = (
                        f"🔗 Enlaces para Cédula / Brigada {j_conf['sufijo_hoja']}"
                        if j_conf["sufijo_hoja"]
                        else "🔗 Enlaces Operativos y Públicos"
                    )

                    st.markdown(
                        f"<h4 style='color: #1e5b4f; margin-top: 1.2rem;'>{titulo_seccion_qr}</h4>",
                        unsafe_allow_html=True,
                    )

                    st.markdown("🔹 **Enlace Público para Registro de Pacientes (QR):**")
                    st.code(link_paciente, language="text")

                    st.markdown("🔹 **Enlace Directo para el Personal Operativo:**")
                    st.code(link_operativo, language="text")

                    qr = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr.add_data(link_paciente)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="#611232", back_color="#ffffff")

                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    byte_im = buf.getvalue()

                    col_qr1, col_qr2 = st.columns([1, 2])
                    with col_qr1:
                        st.image(
                            byte_im,
                            caption=f"QR de Registro {j_conf['sufijo_hoja']}",
                            width=180,
                        )
                    with col_qr2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.download_button(
                            label=f"📥 Descargar QR Paciente ({j_conf['sufijo_hoja'] if j_conf['sufijo_hoja'] else 'Principal'})",
                            data=byte_im,
                            file_name=(
                                f"QR_Vacunacion_{siglas_unidad}_{tipo_jornada_letra}{j_conf['sufijo_hoja']}.png"
                            ),
                            mime="image/png",
                            key=f"dl_qr_{idx}",
                            use_container_width=True,
                        )
                    st.markdown("---")
            else:
                st.info("ℹ️ Configure los parámetros y autorice la jornada para generar los códigos QR.")

    with tab_historial:
        col_hist_tit, col_hist_btn = st.columns([3, 1])
        with col_hist_tit:
            st.markdown(
                '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">Historial General y Acceso Universal</div>',
                unsafe_allow_html=True,
            )
        with col_hist_btn:
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar Historial Universal", use_container_width=True, help="Escanear y mostrar todas las hojas existentes en Google Sheets"):
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
                    
                    ids_a_revisar = [GOOGLE_SHEET_ID, "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"]
                    hojas_encontradas = []

                    for sheet_id_item in ids_a_revisar:
                        try:
                            sp_item = client.open_by_key(sheet_id_item)
                            for ws in sp_item.worksheets():
                                titulo_w = ws.title
                                if titulo_w not in ["CENSO NOMINAL", "CENSO", "Influenza", "COVID"]:
                                    try:
                                        val_au4 = ""
                                        try:
                                            val_au4 = ws.acell("AU4").value
                                        except:
                                            pass

                                        siglas_h = "20N" if "20N_" in titulo_w or sheet_id_item == "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE" else "GEN"
                                        tipo_letra_h = "I" if "INTRA" in titulo_w else "E"
                                        
                                        hojas_encontradas.append({
                                            "nombre": titulo_w,
                                            "gid": str(ws.id),
                                            "unidad": "CMN 20 DE NOVIEMBRE" if siglas_h == "20N" else "Unidad Médica",
                                            "siglas_unidad": siglas_h,
                                            "tipo_jornada": "Intramuros I" if tipo_letra_h == "I" else "Extramuros E",
                                            "tipo_jornada_letra": tipo_letra_h,
                                            "responsable": "PERSONAL OPERATIVO",
                                            "correo": val_au4.strip().lower() if val_au4 else "No asignado",
                                            "fecha": datetime.date.today(),
                                            "sheet_id": sheet_id_item,
                                            "link_formulario": f"https://medprev-vacunas-invernal.streamlit.app/consulta_censia?hoja_activa={urllib.parse.quote(titulo_w)}"
                                        })
                                    except:
                                        pass
                        except:
                            pass
                    
                    if hojas_encontradas:
                        st.session_state.historial_jornadas = hojas_encontradas
                        st.success(f"✅ ¡Historial universal sincronizado! Se detectaron {len(hojas_encontradas)} hojas activas.")
                        st.rerun()
                    else:
                        st.warning("⚠️ No se encontraron hojas activas en Google Sheets.")
                except Exception as e:
                    st.error(f"Error al sincronizar con Google Sheets: {e}")

        # --- VISTA UNIVERSAL PARA EL ADMINISTRADOR ---
        st.markdown("<br>", unsafe_allow_html=True)
        if not st.session_state.historial_jornadas:
            st.info("ℹ️ Haga clic en **'🔄 Actualizar Historial Universal'** para escanear y visualizar todas las pestañas existentes en Google Sheets.")
        else:
            st.success(f"👑 Panel de Administración Universal: Mostrando todas las pestañas creadas ({len(st.session_state.historial_jornadas)} en total).")
            base_url = "https://medprev-vacunas-invernal.streamlit.app"

            for i, h_item in enumerate(st.session_state.historial_jornadas):
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background-color: #e8f0ec; border: 1px solid #1e5b4f; padding: 15px; border-radius: 8px; margin-bottom: 12px;">
                            <h4 style="margin: 0; color: #1e5b4f;">📋 {h_item['nombre']}</h4>
                            <p style="margin: 4px 0;"><b>Unidad:</b> {h_item['unidad']} | <b>Tipo:</b> {h_item['tipo_jornada']}</p>
                            <p style="margin: 4px 0;"><b>Correo Responsable (AU4):</b> <code>{h_item['correo']}</code></p>
                            <p style="margin: 4px 0;"><b>Estatus:</b> 🟢 <b>Visible en Vista Universal de Administrador</b></p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                col_h1, col_h2 = st.columns([1, 1])
                with col_h1:
                    url_sheet_universal = f"https://docs.google.com/spreadsheets/d/{h_item['sheet_id']}/edit?usp=sharing"
                    st.markdown(f"[🔗 Abrir Libro Maestro Completo en Google Sheets]({url_sheet_universal})", unsafe_allow_html=True)
                    
                    if h_item.get("link_formulario") and h_item["link_formulario"] != "#":
                        st.markdown(f"🔹 **Formulario Público:** [Abrir enlace]({h_item['link_formulario']})")
                
                with col_h2:
                    link_qr_generar = h_item.get("link_formulario", base_url)
                    qr_h = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr_h.add_data(link_qr_generar)
                    qr_h.make(fit=True)
                    img_h = qr_h.make_image(fill_color="#611232", back_color="#ffffff")

                    buf_h = io.BytesIO()
                    img_h.save(buf_h, format="PNG")
                    byte_im_h = buf_h.getvalue()

                    st.image(byte_im_h, caption=f"QR ({h_item['nombre']})", width=140)
                    st.download_button(
                        label=f"📥 Descargar QR ({h_item['nombre']})",
                        data=byte_im_h,
                        file_name=f"QR_{h_item['nombre']}.png",
                        mime="image/png",
                        key=f"hist_qr_{i}"
                    )
                st.markdown("---")
