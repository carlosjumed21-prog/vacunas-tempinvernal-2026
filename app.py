import streamlit as st

# Configuración de la página del menú principal
st.set_page_config(
    page_title="Menú Principal - Censo Nominal",
    page_icon="💉",
    layout="centered",
)

# --- ENRUTADOR AUTOMÁTICO PARA ENLACES INDIVIDUALES ---
params = st.query_params

# Si el enlace individual trae el parámetro de registro o QR, redirige directo al formulario
if params.get("modo", "").lower() == "registro" or "unidad" in params:
  st.switch_page("pages/1_formulario.py")

# Si el enlace individual trae el parámetro para el operativo, redirige directo a CENSIA
if "hoja_activa" in params:
  st.switch_page("pages/2_consulta_censia.py")

# --- DISEÑO DEL MENÚ PRINCIPAL ---
st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        /* Ocultar barra lateral por completo */
        [data-testid="stSidebar"] { display: none !important; }
        
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; text-align: center; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; text-align: center; margin-bottom: 2rem; font-weight: 700 !important; }
        
        /* Estilo uniforme para nivelar las tarjetas de las columnas */
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">Sistema de Gestión de Jornadas de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Delegación Zona Sur - ISSSTE | Panel de Acceso</p>',
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# Diseño de botones personalizados en columnas simétricas y niveladas
col1, col2 = st.columns(2)

with col1:
  st.markdown(
      '<div class="card-menu"><h3 style="color: #1e5b4f; margin-top:0;">📝'
      ' Cuestionario</h3><p style="margin-bottom:0;">Registro nominal de'
      " pacientes y captura de datos.</p></div>",
      unsafe_allow_html=True,
  )
  if st.button("Ir al Cuestionario", use_container_width=True):
    st.switch_page("pages/1_formulario.py")

with col2:
  st.markdown(
      '<div class="card-menu"><h3 style="color: #611232; margin-top:0;">📋'
      ' CENSIA / Consulta</h3><p style="margin-bottom:0;">Módulo operativo y'
      " application de dosis.</p></div>",
      unsafe_allow_html=True,
  )
  if st.button("Ir a Consulta CENSIA", use_container_width=True):
    st.switch_page("pages/2_consulta_censia.py")

st.markdown("<br>", unsafe_allow_html=True)

# Botón inferior para administración centrado
col_admin1, col_admin2, col_admin3 = st.columns([1, 2, 1])
with col_admin2:
  st.markdown(
      '<div class="card-menu" style="height: auto; padding: 15px;"><h4'
      ' style="color: #1e5b4f; margin:0;">⚙️ Panel de'
      " Administración</h4></div>",
      unsafe_allow_html=True,
  )
  if st.button("Abrir Administración", use_container_width=True):
    st.switch_page("pages/3_administrador.py")
