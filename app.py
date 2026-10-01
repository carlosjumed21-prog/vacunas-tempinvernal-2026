import streamlit as st

# Configuración de la página del menú principal
st.set_page_config(
    page_title="Menú Principal - Censo Nominal",
    page_icon="💉",
    layout="centered",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        .main-header { font-size: 2.3rem !important; font-weight: 800 !important; color: #1e5b4f !important; text-align: center; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; text-align: center; margin-bottom: 2rem; font-weight: 700 !important; }
        .card-menu { background-color: #ffffff; border: 2px solid #1e5b4f; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">Sistema de Vacunación e Invernal</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">CMN "20 de Noviembre" | Panel de Acceso</p>',
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# Diseño de botones personalizados en columnas centrales
col1, col2 = st.columns(2)

with col1:
  st.markdown(
      '<div class="card-menu"><h3 style="color: #1e5b4f;">📝 Cuestionario</h3><p>Registro nominal de pacientes y captura de datos.</p></div>',
      unsafe_allow_html=True,
  )
  # Como Streamlit lee automáticamente la carpeta pages, puedes usar enlaces de páginas o botones con st.switch_page
  if st.button("Ir al Cuestionario", use_container_width=True):
    st.switch_page("pages/1_formulario.py")

with col2:
  st.markdown(
      '<div class="card-menu"><h3 style="color: #611232;">📋 CENSIA / Consulta</h3><p>Módulo operativo y aplicación de dosis.</p></div>',
      unsafe_allow_html=True,
  )
  if st.button("Ir a Consulta CENSIA", use_container_width=True):
    st.switch_page("pages/2_consulta_censia.py")

st.markdown("<br>", unsafe_allow_html=True)

# Botón inferior para administración
col_admin1, col_admin2, col_admin3 = st.columns([1, 2, 1])
with col_admin2:
  st.markdown(
      '<div class="card-menu" style="padding: 15px;"><h4 style="color: #1e5b4f; margin:0;">⚙️ Panel de Administración</h4></div>',
      unsafe_allow_html=True,
  )
  if st.button("Abrir Administración", use_container_width=True):
    st.switch_page("pages/3_administrador.py")
