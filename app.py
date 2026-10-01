import streamlit as st
from config import aplicar_configuracion_global

# Aplicar configuración global y ocultar la barra lateral de inmediato
aplicar_configuracion_global("Menú Principal - Censo Nominal", "💉")

params = st.query_params

# Interceptación inmediata de enlaces personalizados (evita renderizar la página principal)
if params.get("modo", "").lower() == "registro" or "unidad" in params:
    st.switch_page("pages/1_formulario.py")

if params.get("vista", "").lower() == "operativo" or "hoja_activa" in params:
    st.switch_page("pages/2_consulta_censia.py")

# --- DISEÑO DEL MENÚ PRINCIPAL (Visible únicamente al entrar de forma directa) ---
st.markdown("""
    <style>
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; text-align: center; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; text-align: center; margin-bottom: 2rem; font-weight: 700 !important; }
        .card-menu { 
            background-color: #ffffff; 
            border: 2px solid #1e5b4f; 
            padding: 25px; 
            border-radius: 12px; 
            text-align: center; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
            height: 160px; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
            margin-bottom: 15px; 
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Sistema de Gestión de Jornadas de Vacunación</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Delegación Zona Sur - ISSSTE | Panel de Acceso</p>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card-menu"><h3 style="color: #1e5b4f; margin-top:0;">📝 Cuestionario</h3><p style="margin-bottom:0;">Registro nominal de pacientes y captura de datos.</p></div>', unsafe_allow_html=True)
    if st.button("Ir al Cuestionario", use_container_width=True):
        st.switch_page("pages/1_formulario.py")

with col2:
    st.markdown('<div class="card-menu"><h3 style="color: #611232; margin-top:0;">📋 CENSIA / Consulta</h3><p style="margin-bottom:0;">Módulo operativo y aplicación de dosis.</p></div>', unsafe_allow_html=True)
    if st.button("Ir a Consulta CENSIA", use_container_width=True):
        st.switch_page("pages/2_consulta_censia.py")

st.markdown("<br>", unsafe_allow_html=True)
col_admin1, col_admin2, col_admin3 = st.columns([1, 2, 1])
with col_admin2:
    st.markdown('<div class="card-menu" style="height: auto; padding: 15px;"><h4 style="color: #1e5b4f; margin:0;">⚙️ Panel de Administración</h4></div>', unsafe_allow_html=True)
    if st.button("Abrir Administración", use_container_width=True):
        st.switch_page("pages/3_administrador.py")
