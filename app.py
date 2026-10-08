import streamlit as st
from config import aplicar_configuracion_global, UNIDADES_ISSSTE

# Aplicar configuración global (oculta la barra lateral si hay parámetros de URL)
aplicar_configuracion_global("Sistema Censo Nominal VIGILE", "💉")

st.markdown("""
    <style>
        /* Ocultar la barra superior y el menú de Streamlit Cloud */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        #MainMenu {
            visibility: hidden !important;
        }
        /* Ajustar el espacio superior para que el contenido suba de forma limpia */
        .block-container {
            padding-top: 1.5rem !important;
        }
        
        .main-header { font-size: 2.3rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; text-align: center; }
        .sub-header { font-size: 1.25rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; text-align: center; }
        .card-menu { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.1rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; width: 100%; }
        .btn-admin>button { background-color: #611232 !important; color: white !important; font-size: 0.95rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.4rem 0.8rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- ACCESO RÁPIDO A ADMINISTRACIÓN EN LA PARTE SUPERIOR ---
col_top1, col_top2, col_top3 = st.columns([2, 2, 1])
with col_top3:
    if st.button("🔐 Panel Admin", use_container_width=True, key="btn_top_admin"):
        st.switch_page("pages/3_administrador.py")

st.markdown('<p class="main-header">Sistema de Jornadas de Vacunación y Censo Nominal</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Módulo Principal de Acceso Institucional</p>', unsafe_allow_html=True)

# Verificación de parámetros URL institucionales
params = st.query_params
unidad_url = params.get("unidad", "").upper()
jornada_url = params.get("jornada", "").upper()

# --- LÓGICA DE ENRUTAMIENTO DINÁMICO ---
pagina_formulario = "pages/registro_20_noviembre.py" if unidad_url == "20N" else "pages/1_formulario.py"

if unidad_url:
    st.markdown(f"""
        <div style="background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
            <span style="font-weight: bold; color: #1e5b4f; font-size: 1.1rem;">🔗 Enlace Institucional Detectado</span><br>
            <span>Unidad clave: <b>{unidad_url}</b> | Jornada: <b>{'Extramuros' if jornada_url == 'E' else 'Intramuros'}</b></span><br>
            <span style="font-size: 0.85rem; color: #611232;">{'✨ Redirección especializada activada para CMN 20 de Noviembre.' if unidad_url == '20N' else ''}</span>
        </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="card-menu">
            <h3>📝 Registro Nominal</h3>
            <p>Acceso al formulario de captura para pacientes en jornadas de vacunación.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Ir al Formulario de Registro", use_container_width=True):
        st.switch_page(pagina_formulario)

with col2:
    st.markdown("""
        <div class="card-menu">
            <h3>📋 Operatividad</h3>
            <p>Captura de dosis aplicadas, lotes y comprobantes.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Ir a Consulta CENSIA", use_container_width=True):
        st.switch_page("pages/2_consulta_censia.py")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; color: #611232; font-weight: 600; font-size: 0.9rem;">
        Subdelegación Sur ISSSTE<br>
        Medicina Preventiva - Epidemiología<br>
        © 2026 Carlos Ju R2 Epidemiología. Proyecto de Captura de Jornadas de Vacunación.<br>
        Todos los derechos reservados. Prohibida su reproducción total o parcial sin autorización.
    </div>
""", unsafe_allow_html=True)
