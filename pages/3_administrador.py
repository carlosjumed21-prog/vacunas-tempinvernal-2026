import datetime
import streamlit as st
from config import UNIDADES_ISSSTE, aplicar_configuracion_global
from utils.admin_utils import (
    autenticar_administrador,
    verificar_hojas_existentes,
    autorizar_y_crear_jornadas,
    sincronizar_historial_universal,
    generar_imagen_qr
)
from utils.admin_20_nov import autorizar_y_crear_jornadas_20_nov

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

# Sincronizar automáticamente el estado de administrador si ya se autenticó en app.py
if st.session_state.get("es_admin", False) and not st.session_state.get("autenticado_admin", False):
    st.session_state.autenticado_admin = True
    st.session_state.usuario_admin_actual = "Administrador Principal"

col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("🚪 Cerrar Sesión de Administrador", use_container_width=True):
        st.session_state.autenticado_admin = False
        st.session_state.es_admin = False
        st.session_state.usuario_admin_actual = ""
        st.session_state.jornada_autorizada = False
        st.session_state.hojas_creadas_recientes = []
        st.rerun()
with col_nav2:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

# Inicialización de variables de sesión
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

# --- VISTA DE LOGIN (Respaldo por acceso directo a la página) ---
if not st.session_state.autenticado_admin:
    st.markdown('<p class="main-header">Acceso Restringido - Panel de Administración</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ingrese su correo electrónico y contraseña de administrador</p>', unsafe_allow_html=True)

    with st.form("form_login_admin"):
        correo_admin_input = st.text_input("📧 Correo Electrónico Administrador:", placeholder="carlosju.med21@gmail.com")
        password_admin = st.text_input("Contraseña:", type="password")
        btn_login_admin = st.form_submit_button("Ingresar al Panel", use_container_width=True)

        if btn_login_admin:
            if not correo_admin_input.strip():
                st.error("⚠️ Debe ingresar su correo electrónico.")
            elif not password_admin:
                st.error("⚠️ Debe ingresar su contraseña.")
            else:
                exito, usuario = autenticar_administrador(correo_admin_input, password_admin)
                if exito:
                    st.session_state.autenticado_admin = True
                    st.session_state.es_admin = True
                    st.session_state.usuario_admin_actual = usuario
                    st.rerun()
                else:
                    st.error("❌ Correo o contraseña de administrador incorrectos.")
else:
    # --- PANEL DE CONTROL PRINCIPAL ---
    st.markdown('<p class="main-header">Panel de Control y Administración (Gestión de Pestañas Maestras)</p>', unsafe_allow_html=True)
    tab_creacion, tab_historial = st.tabs(["🚀 Creación de Jornadas", "📋 Historial y Estatus de Jornadas"])

    with tab_creacion:
        st.markdown(
            '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">1. Configuración de Operación y Unidad</div>',
            unsafe_allow_html=True,
        )

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            unidad_sel = st.selectbox("Unidad Médica ISSSTE:", options=list(UNIDADES_ISSSTE.keys()))
            siglas_unidad = UNIDADES_ISSSTE[unidad_sel]["sigla"] if unidad_sel in UNIDADES_ISSSTE else ""

        with col_c2:
            jornada_sel = st.selectbox("Tipo de Jornada:", options=["Seleccione tipo...", "Intramuros I", "Extramuros E"])
            tipo_jornada_letra = "I" if "Intramuros" in jornada_sel else ("E" if "Extramuros" in jornada_sel else "")
            tipo_jornada_texto = "INTRA" if tipo_jornada_letra == "I" else ("EXTRA" if tipo_jornada_letra == "E" else "")

        if unidad_sel != "Seleccione una unidad médica..." and st.session_state.unidad_anterior != unidad_sel:
            st.session_state.unidad_anterior = unidad_sel
            st.session_state.config_direccion_base = UNIDADES_ISSSTE[unidad_sel]["dir"]
            st.session_state.jornada_autorizada = False
            st.rerun()

        if unidad_sel == "Seleccione una unidad médica..." or jornada_sel == "Seleccione tipo...":
            st.warning("⚠️ Por favor seleccione una Unidad Médica y un Tipo de Jornada válidos para habilitar la configuración.")
        else:
            st.markdown("---")
            jornadas_simultaneas = st.toggle("⚡ Activar Jornadas Simultáneas (Múltiples equipos o células en operación)", value=False)

            num_jornadas = 1
            if jornadas_simultaneas:
                num_jornadas = st.number_input("Número de jornadas simultáneas a habilitar:", min_value=2, max_value=5, value=2, step=1)

            st.markdown(
                '<div class="section-title" style="font-size: 1.4rem; font-weight: 800; color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">2. Parámetros Independientes por Cédula / Brigada</div>',
                unsafe_allow_html=True,
            )

            config_jornadas_activas = []

            if not jornadas_simultaneas:
                st.markdown('<div class="card-simultanea">', unsafe_allow_html=True)
                resp_unico = st.text_input("👤 Nombre del responsable de vacunación:", placeholder="Escriba el nombre completo...")
                correo_resp_unico = st.text_input("📧 Correo electrónico del responsable:", placeholder="ejemplo@issste.gob.mx", key="correo_resp_unico")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    f_app = st.date_input("Fecha de Aplicación:", value=datetime.date.today(), format="DD/MM/YYYY", key="f_app_unica")
                with col_f2:
                    h_ini = st.time_input("Hora Inicio:", value=datetime.time(8, 0), key="h_ini_unica")
                with col_f3:
                    h_fin = st.time_input("Hora Cierre:", value=datetime.time(14, 0), key="h_fin_unica")

                dir_oficial = st.text_area("📍 Dirección Oficial de esta Jornada:", value=st.session_state.config_direccion_base, height=70, key="dir_unica")
                st.markdown("</div>", unsafe_allow_html=True)

                config_jornadas_activas.append({
                    "sufijo_hoja": "",
                    "sufijo_qr": "",
                    "tipo_texto": tipo_jornada_texto,
                    "responsable": resp_unico.upper() if resp_unico else "PERSONAL",
                    "correo": correo_resp_unico.strip().lower(),
                    "fecha": f_app,
                    "hora_inicio": h_ini,
                    "hora_fin": h_fin,
                    "direccion": dir_oficial,
                })
            else:
                st.info(f"Configurando {num_jornadas} equipos simultáneos con fechas, horarios y ubicaciones personalizadas:")
                for i in range(1, num_jornadas + 1):
                    st.markdown(f'<div class="card-simultanea"><h4 style="color: #1e5b4f; margin-top:0;">📋 Cédula / Brigada Simultánea # {i}</h4>', unsafe_allow_html=True)
                    resp_sim = st.text_input(f"👤 Responsable de Brigada #{i}:", placeholder=f"Nombre del responsable {i}...", key=f"resp_sim_{i}")
                    correo_sim = st.text_input(f"📧 Correo electrónico de Brigada #{i}:", placeholder=f"correo_brigada_{i}@issste.gob.mx", key=f"correo_sim_{i}")

                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        f_app_sim = st.date_input(f"Fecha de Aplicación #{i}:", value=datetime.date.today(), format="DD/MM/YYYY", key=f"f_app_sim_{i}")
                    with col_f2:
                        h_ini_sim = st.time_input(f"Hora Inicio #{i}:", value=datetime.time(8, 0), key=f"h_ini_sim_{i}")
                    with col_f3:
                        h_fin_sim = st.time_input(f"Hora Cierre #{i}:", value=datetime.time(14, 0), key=f"h_fin_sim_{i}")

                    dir_sim = st.text_area(f"📍 Dirección Oficial para Brigada #{i}:", value=st.session_state.config_direccion_base, height=70, key=f"dir_sim_{i}")
                    st.markdown("</div>", unsafe_allow_html=True)

                    config_jornadas_activas.append({
                        "sufijo_hoja": f"_JS{i}",
                        "sufijo_qr": f"_JS{i}",
                        "tipo_texto": tipo_jornada_texto,
                        "responsable": resp_sim.upper() if resp_sim else f"RESPONSABLE JS{i}",
                        "correo": correo_sim.strip().lower(),
                        "fecha": f_app_sim,
                        "hora_inicio": h_ini_sim,
                        "hora_fin": h_fin_sim,
                        "direccion": dir_sim,
                    })

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 Autorizar Jornada(s) y Generar Pestaña en Google Sheets", use_container_width=True):
                duplicadas, error_verif = verificar_hojas_existentes(siglas_unidad, config_jornadas_activas)
                if error_verif:
                    st.error(f"Error al verificar hojas existentes: {error_verif}")
                elif duplicadas:
                    st.error(f"⚠️ ALERTA: Las siguientes hojas ya existen en Google Sheets maestro: {', '.join(duplicadas)}. Por favor cambie la fecha o el tipo de jornada.")
                else:
                    if siglas_unidad == "20N":
                        hojas_creadas_exito, error_creacion = autorizar_y_crear_jornadas_20_nov(
                            siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas
                        )
                    else:
                        hojas_creadas_exito, error_creacion = autorizar_y_crear_jornadas(
                            siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas
                        )

                    if error_creacion:
                        st.error(f"Error al configurar Google Sheets. Detalle: {error_creacion}")
                    else:
                        st.session_state.jornada_autorizada = True
                        st.session_state.hojas_creadas_recientes = hojas_creadas_exito
                        for h_info in hojas_creadas_exito:
                            if not any(h["nombre"] == h_info["nombre"] for h in st.session_state.historial_jornadas):
                                st.session_state.historial_jornadas.append(h_info)
                        st.success("¡Jornada(s) autorizada(s) y pestaña generada con éxito en Google Sheets maestro!")

            if st.session_state.jornada_autorizada and st.session_state.hojas_creadas_recientes:
                st.markdown("<br>", unsafe_allow_html=True)
                enlaces_html = ""
                for h_info in st.session_state.hojas_creadas_recientes:
                    url_sheet_directa = f"https://docs.google.com/spreadsheets/d/{h_info['sheet_id']}/edit?usp=sharing#gid={h_info['gid']}"
                    enlaces_html += f"""
                    <div style="margin-bottom: 8px;">
                        <a href="{url_sheet_directa}" target="_blank" style="background-color: #1e5b4f; color: white; padding: 8px 16px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block; font-size: 1rem;">
                            🔗 Ver Pestaña: {h_info['nombre']}
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

                for idx, j_conf in enumerate(config_jornadas_activas, start=1):
                    fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
                    nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL" if siglas_unidad == "20N" else f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"

                    base_url = "https://medprev-vacunas-invernal.streamlit.app"
                    fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
                    import urllib.parse
                    resp_encoded = urllib.parse.quote(j_conf["responsable"]) if "urllib" in globals() else j_conf["responsable"]
                    js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
                    
                    ruta_formulario = "registro_20_noviembre" if siglas_unidad == "20N" else "formulario"

                    link_paciente = f"{base_url}/{ruta_formulario}?unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
                    link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_objetivo)}"
                    link_prueba_simulacion = link_paciente + "&test=true"

                    titulo_seccion_qr = f"🔗 Enlaces para Cédula / Brigada {j_conf['sufijo_hoja']}" if j_conf["sufijo_hoja"] else "🔗 Enlaces Operativos y Públicos"

                    st.markdown(f"<h4 style='color: #1e5b4f; margin-top: 1.2rem;'>{titulo_seccion_qr}</h4>", unsafe_allow_html=True)
                    st.markdown("🔹 **Enlace Público para Registro de Pacientes (QR):**")
                    st.code(link_paciente, language="text")
                    st.markdown("🔹 **Enlace de Prueba (Autocompleta formulario con datos simulados):**")
                    st.code(link_prueba_simulacion, language="text")
                    st.markdown("🔹 **Enlace Directo para el Personal Operativo:**")
                    st.code(link_operativo, language="text")

                    byte_im = generar_imagen_qr(link_paciente)

                    col_qr1, col_qr2 = st.columns([1, 2])
                    with col_qr1:
                        st.image(byte_im, caption=f"QR de Registro {j_conf['sufijo_hoja']}", width=180)
                    with col_qr2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.download_button(
                            label=f"📥 Descargar QR Paciente ({j_conf['sufijo_hoja'] if j_conf['sufijo_hoja'] else 'Principal'})",
                            data=byte_im,
                            file_name=f"QR_Vacunacion_{siglas_unidad}_{tipo_jornada_letra}{j_conf['sufijo_hoja']}.png",
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
                hojas_encontradas, error_sync = sincronizar_historial_universal()
                if error_sync:
                    st.error(f"Error al sincronizar con Google Sheets: {error_sync}")
                elif hojas_encontradas:
                    st.session_state.historial_jornadas = hojas_encontradas
                    st.success(f"✅ ¡Historial universal sincronizado! Se detectaron {len(hojas_encontradas)} hojas activas.")
                    st.rerun()
                else:
                    st.warning("⚠️ No se encontraron hojas activas en Google Sheets.")

        st.markdown("<br>", unsafe_allow_html=True)
        if not st.session_state.historial_jornadas:
            st.info("ℹ️ Haga clic en **'🔄 Actualizar Historial Universal'** para escanear y visualizar todas las pestañas existentes en Google Sheets con sus respectivos enlaces y QR.")
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
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                col_h1, col_h2 = st.columns([1.2, 0.8])
                with col_h1:
                    url_sheet_universal = f"https://docs.google.com/spreadsheets/d/{h_item['sheet_id']}/edit?usp=sharing"
                    st.markdown(f"📊 **Libro Maestro:** [Abrir Google Sheets]({url_sheet_universal})")
                    
                    link_form_val = h_item.get("link_formulario", base_url)
                    st.markdown("🔹 **Enlace Formulario Público:**")
                    st.code(link_form_val, language="text")

                    import urllib.parse
                    link_op_val = h_item.get("link_operativo", f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(h_item['nombre'])}")
                    st.markdown("🔹 **Enlace Operativo Personalizado:**")
                    st.code(link_op_val, language="text")
                
                with col_h2:
                    link_qr_generar = h_item.get("link_formulario", base_url)
                    byte_im_h = generar_imagen_qr(link_qr_generar)

                    st.image(byte_im_h, caption=f"QR de Registro ({h_item['nombre']})", width=160)
                    st.download_button(
                        label=f"📥 Descargar QR ({h_item['nombre']})",
                        data=byte_im_h,
                        file_name=f"QR_{h_item['nombre']}.png",
                        mime="image/png",
                        key=f"hist_qr_{i}",
                        use_container_width=True
                    )
                st.markdown("---")
