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

col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("🚪 Cerrar Sesión de Administrador", use_container_width=True):
        st.session_state.autenticado_admin = False
        st.session_state.jornada_autorizada = False
        st.session_state.hojas_creadas_recientes = []
        st.rerun()
with col_nav2:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

if "autenticado_admin" not in st.session_state:
    st.session_state.autenticado_admin = False
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

# Inicializar el historial general de jornadas en session_state
if "historial_jornadas" not in st.session_state:
    st.session_state.historial_jornadas = []

if not st.session_state.autenticado_admin:
    st.markdown(
        '<p class="main-header">Acceso Restringido - Panel de Administración</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Seleccione usuario autorizado e ingrese su contraseña</p>',
        unsafe_allow_html=True,
    )

    with st.form("form_login_admin"):
        usuario_admin = st.selectbox(
            "Seleccione Usuario:", options=["Seleccione...", "Admin", "EESP Wendy"]
        )
        password_admin = st.text_input("Contraseña:", type="password")
        btn_login_admin = st.form_submit_button(
            "Ingresar al Panel", use_container_width=True
        )

        if btn_login_admin:
            if (usuario_admin == "Admin" and password_admin == "OtaniOrochi26") or (
                usuario_admin == "EESP Wendy" and password_admin == "MedPrev26"
            ):
                st.session_state.autenticado_admin = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta o usuario no seleccionado.")
else:
    st.markdown(
        '<p class="main-header">Panel de Control y Administración</p>',
        unsafe_allow_html=True,
    )

    # Menú de pestañas para organizar la creación y el historial
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
                        "fecha": f_app_sim,
                        "hora_inicio": h_ini_sim,
                        "hora_fin": h_fin_sim,
                        "direccion": dir_sim,
                    })

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "🚀 Autorizar Jornada(s) y Generar Hoja(s) en Google Sheets",
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
                    spreadsheet = client.open_by_key(sheet_id_destino)

                    hojas_existentes = [h.title for h in spreadsheet.worksheets()]
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
                            "⚠️ ALERTA: Las siguientes hojas ya existen en Google Sheets:"
                            f" {', '.join(duplicadas_detectadas)}"
                        )
                    else:
                        hojas_creadas_exito = []
                        for j_conf in config_jornadas_activas:
                            fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
                            fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")

                            if siglas_unidad == "20N":
                                nombre_copia_1 = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
                                nombre_copia_2 = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_CENSO"

                                try:
                                    plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
                                    copia_1 = spreadsheet.duplicate_sheet(
                                        plantilla_1.id, 
                                        insert_sheet_index=len(spreadsheet.worksheets()), 
                                        new_sheet_name=nombre_copia_1
                                    )
                                except:
                                    copia_1 = spreadsheet.add_worksheet(title=nombre_copia_1, rows=1000, cols=30)

                                try:
                                    plantilla_2 = spreadsheet.worksheet("CENSO")
                                    spreadsheet.duplicate_sheet(
                                        plantilla_2.id, 
                                        insert_sheet_index=len(spreadsheet.worksheets()), 
                                        new_sheet_name=nombre_copia_2
                                    )
                                except:
                                    spreadsheet.add_worksheet(title=nombre_copia_2, rows=1000, cols=30)

                                hoja_activa = spreadsheet.worksheet(nombre_copia_1)
                                try:
                                    hoja_activa.update_acell("D7", "CDMX")
                                    hoja_activa.update_acell("M7", "ISSSTE")
                                    hoja_activa.update_acell("T7", "Delegación Sur")
                                    hoja_activa.update_acell("AB7", "CDMX")
                                    hoja_activa.update_acell("D8", "CDMX")
                                    hoja_activa.update_acell("D9", unidad_sel)
                                    hoja_activa.update_acell("M9", "")
                                    hoja_activa.update_acell("S9", "")
                                    hoja_activa.update_acell("AB9", fecha_formato_oficial)
                                    hoja_activa.update_acell("E10", j_conf["responsable"])
                                except:
                                    pass

                                hoja_info = {
                                    "nombre": nombre_copia_1,
                                    "gid": str(copia_1.id),
                                    "unidad": unidad_sel,
                                    "siglas_unidad": siglas_unidad,
                                    "tipo_jornada": jornada_sel,
                                    "tipo_jornada_letra": tipo_jornada_letra,
                                    "responsable": j_conf["responsable"],
                                    "fecha": j_conf["fecha"],
                                    "sheet_id": sheet_id_destino
                                }
                                hojas_creadas_exito.append(hoja_info)
                                st.session_state.historial_jornadas.append(hoja_info)

                            else:
                                nombre_nueva_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
                                try:
                                    plantilla = spreadsheet.worksheet("CENSO NOMINAL")
                                    nueva_hoja = spreadsheet.duplicate_sheet(
                                        plantilla.id, 
                                        insert_sheet_index=len(spreadsheet.worksheets()), 
                                        new_sheet_name=nombre_nueva_hoja
                                    )
                                except:
                                    nueva_hoja = spreadsheet.add_worksheet(title=nombre_nueva_hoja, rows=1000, cols=30)

                                hoja_activa = spreadsheet.worksheet(nombre_nueva_hoja)
                                try:
                                    # Mapeo actualizado para las otras unidades médicas en el administrador
                                    hoja_activa.update_acell("D6", "CDMX")                  # Entidad Federativa
                                    hoja_activa.update_acell("M6", "ISSSTE")                 # Institución
                                    hoja_activa.update_acell("U6", "Delegación Sur")         # Jurisdicción / Delegación
                                    hoja_activa.update_acell("AC6", "CDMX")                # Municipio
                                    hoja_activa.update_acell("D7", "CDMX")                   # Localidad
                                    hoja_activa.update_acell("D8", unidad_sel)               # Unidad de Salud
                                    hoja_activa.update_acell("AC8", fecha_formato_oficial)   # Fecha de aplicación
                                    hoja_activa.update_acell("E10", j_conf["responsable"])     # Responsable de vacunación
                                except:
                                    pass

                                hoja_info = {
                                    "nombre": nombre_nueva_hoja,
                                    "gid": str(nueva_hoja.id),
                                    "unidad": unidad_sel,
                                    "siglas_unidad": siglas_unidad,
                                    "tipo_jornada": jornada_sel,
                                    "tipo_jornada_letra": tipo_jornada_letra,
                                    "responsable": j_conf["responsable"],
                                    "fecha": j_conf["fecha"],
                                    "sheet_id": sheet_id_destino
                                }
                                hojas_creadas_exito.append(hoja_info)
                                st.session_state.historial_jornadas.append(hoja_info)

                        st.session_state.jornada_autorizada = True
                        st.session_state.hojas_creadas_recientes = hojas_creadas_exito
                        st.success(
                            "¡Jornadas autorizadas y hojas generadas con éxito en Google Sheets!"
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
                    url_sheet_directa = f"https://docs.google.com/spreadsheets/d/{h_info['sheet_id']}/edit?usp=sharing#gid={h_info['gid']}"
                    enlaces_html += f"""
                    <div style="margin-bottom: 8px;">
                        <a href="{url_sheet_directa}" target="_blank" style="background-color: #1e5b4f; color: white; padding: 8px 16px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block; font-size: 1rem;">
                            🔗 Ver Hoja: {h_info['nombre']}
                        </a>
                    </div>
                    """

                st.markdown(
                    f"""
                    <div style="background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 18px; border-radius: 8px; margin-top: 15px; text-align: center;">
                        <h3 style="color: #1e5b4f; margin-top: 0; margin-bottom: 8px;">🟢 JORNADAS AUTORIZADAS Y ACTIVAS</h3>
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

                    st.markdown("🔹 **Enlace de Prueba (Autocompleta formulario con datos simulados):**")
                    st.code(link_prueba_simulacion, language="text")

                    st.markdown("🔹 **Enlace Directo para el Personal Operativo (Abre el panel censal/operativo):**")
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
        st.markdown(
            '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">Historial General de Jornadas Autorizadas</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.historial_jornadas:
            st.info("ℹ️ No hay jornadas registradas en el historial de esta sesión todavía.")
        else:
            hoy = datetime.date.today()
            base_url = "https://medprev-vacunas-invernal.streamlit.app"

            for i, h_item in enumerate(st.session_state.historial_jornadas):
                fecha_jornada = h_item["fecha"]
                
                # Evaluación de estatus por fecha
                if fecha_jornada >= hoy:
                    estatus_badge = "🟢 **Activa**"
                    estado_color = "#e8f0ec"
                else:
                    estatus_badge = "🔴 **Finalizada / Vencida**"
                    estado_color = "#f9ecec"

                with st.container():
                    st.markdown(
                        f"""
                        <div style="background-color: {estado_color}; border: 1px solid #1e5b4f; padding: 15px; border-radius: 8px; margin-bottom: 12px;">
                            <h4 style="margin: 0; color: #1e5b4f;">📋 {h_item['nombre']}</h4>
                            <p style="margin: 4px 0;"><b>Unidad:</b> {h_item['unidad']} | <b>Tipo:</b> {h_item['tipo_jornada']}</p>
                            <p style="margin: 4px 0;"><b>Responsable:</b> {h_item['responsable']} | <b>Fecha Programada:</b> {fecha_jornada.strftime('%d/%m/%Y')}</p>
                            <p style="margin: 4px 0;"><b>Estatus:</b> {estatus_badge}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Si la jornada está activa, permitir ver y descargar el QR o acceder a sus enlaces directos
                    if fecha_jornada >= hoy:
                        col_h1, col_h2 = st.columns([1, 1])
                        with col_h1:
                            url_sheet = f"https://docs.google.com/spreadsheets/d/{h_item['sheet_id']}/edit?usp=sharing#gid={h_item['gid']}"
                            st.markdown(f"[🔗 Abrir Google Sheet]({url_sheet})", unsafe_allow_html=True)
                        
                        with col_h2:
                            # Generación dinámica del QR histórico activo
                            fecha_url_str = fecha_jornada.strftime("%Y-%m-%d")
                            resp_encoded = urllib.parse.quote(h_item["responsable"])
                            ruta_formulario = "registro_20_noviembre" if h_item["siglas_unidad"] == "20N" else "formulario"
                            link_paciente_hist = f"{base_url}/{ruta_formulario}?unidad={h_item['siglas_unidad']}&jornada={h_item['tipo_jornada_letra']}&fecha={fecha_url_str}&resp={resp_encoded}"

                            qr_h = qrcode.QRCode(version=1, box_size=10, border=4)
                            qr_h.add_data(link_paciente_hist)
                            qr_h.make(fit=True)
                            img_h = qr_h.make_image(fill_color="#611232", back_color="#ffffff")

                            buf_h = io.BytesIO()
                            img_h.save(buf_h, format="PNG")
                            byte_im_h = buf_h.getvalue()

                            st.download_button(
                                label=f"📥 Descargar QR Activo ({h_item['nombre']})",
                                data=byte_im_h,
                                file_name=f"QR_{h_item['nombre']}.png",
                                mime="image/png",
                                key=f"hist_qr_{i}"
                            )
                st.markdown("---")
