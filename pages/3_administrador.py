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
        "Avenida Félix Cuevas 540, Del Valle Sur, Benito Juárez, 03100 Ciudad de"
        " México, CDMX"
    )
if "jornada_autorizada" not in st.session_state:
    st.session_state.jornada_autorizada = False
if "hojas_creadas_recientes" not in st.session_state:
    st.session_state.hojas_creadas_recientes = []

if not st.session_state.autenticado_admin:
    st.markdown(
        '<p class="main-header">Acceso Restringido - Panel de Administración</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Seleccione usuario autorizado e ingrese su'
        " contraseña</p>",
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

    st.markdown(
        '<div class="section-title" style="font-size: 1.4rem; font-weight: 800;'
        ' color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem;'
        ' border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">1.'
        " Configuración de Operación y Unidad</div>",
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
            "⚠ Por favor seleccione una Unidad Médica y un Tipo de Jornada válidos"
            " para habilitar la configuración."
        )
    else:
        st.markdown("---")
        jornadas_simultaneas = st.toggle(
            "⚡ Activar Jornadas Simultáneas (Múltiples equipos o células en"
            " operación)",
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
            '<div class="section-title" style="font-size: 1.4rem; font-weight: 800;'
            ' color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem;'
            ' border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">2.'
            " Parámetros Independientes por Cédula / Brigada</div>",
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
                "responsable": resp_unico.upper() if
