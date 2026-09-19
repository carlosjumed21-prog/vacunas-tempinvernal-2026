import datetime
import io
import urllib.parse
import qrcode
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Panel de Administración - Censo Nominal",
    page_icon="⚙️",
    layout="centered",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        [data-testid="stSidebar"] { background-color: #611232 !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #ffffff !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# Control de sesión para autenticación
if "autenticado_admin" not in st.session_state:
  st.session_state.autenticado_admin = False

# Variables de configuración global en session_state si no existen
if "config_fecha_aplicacion" not in st.session_state:
  st.session_state.config_fecha_aplicacion = datetime.date.today()
if "config_hora_inicio" not in st.session_state:
  st.session_state.config_hora_inicio = datetime.time(8, 0)
if "config_hora_fin" not in st.session_state:
  st.session_state.config_hora_fin = datetime.time(14, 0)
if "config_ubicacion_maps" not in st.session_state:
  st.session_state.config_ubicacion_maps = (
      "Centro Medico Nacional 20 de Noviembre, Ciudad de Mexico"
  )

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
      '<p class="sub-header">Configuración de Jornada, Unidad Médica, Fechas,'
      " Horarios, Ubicación Autónoma y Códigos QR</p>",
      unsafe_allow_html=True,
  )

  unidades_issste = {
      "20 DE NOVIEMBRE": "NOV",
      "CHURUBUSCO": "CHU",
      "ERMITA": "ERM",
      "ZARAGOZA": "ZAR",
      "GÓMEZ FARÍAS": "GFAR",
  }

  st.markdown(
      '<div class="section-title">1. Configuración de Operación y'
      " Unidad</div>",
      unsafe_allow_html=True,
  )

  col_c1, col_c2 = st.columns(2)
  with col_c1:
    unidad_sel = st.selectbox(
        "Unidad Médica ISSSTE:", options=list(unidades_issste.keys())
    )
    siglas_unidad = unidades_issste[unidad_sel]

  with col_c2:
    jornada_sel = st.selectbox(
        "Tipo de Jornada:",
        options=["Intramuros (I)", "Extramuros (E)"],
        format_func=lambda x: "Intramuros (I)" if "I" in x else "Extramuros (E)",
    )
    tipo_jornada_letra = "I" if "I" in jornada_sel else "E"

  st.markdown(
      '<div class="section-title">2. Configuración de Fecha y Horario de'
      " Atención</div>",
      unsafe_allow_html=True,
  )
  col_f1, col_f2, col_f3 = st.columns(3)
  with col_f1:
    fecha_admin = st.date_input(
        "Fecha de Aplicación:",
        value=st.session_state.config_fecha_aplicacion,
        format="DD/MM/YYYY",
    )
    st.session_state.config_fecha_aplicacion = fecha_admin
  with col_f2:
    hora_ini = st.time_input(
        "Hora de Inicio:", value=st.session_state.config_hora_inicio
    )
    st.session_state.config_hora_inicio = hora_ini
  with col_f3:
    hora_fin = st.time_input(
        "Hora de Cierre:", value=st.session_state.config_hora_fin
    )
    st.session_state.config_hora_fin = hora_fin

  st.markdown(
      '<div class="section-title">3. Búsqueda y Autocompletado de Dirección'
      " (Google Maps)</div>",
      unsafe_allow_html=True,
  )

  # Campo de texto estándar en Streamlit donde el administrador ingresa o refina la dirección
  ubicacion_input = st.text_input(
      "Dirección exacta de la clínica o módulo (Sugerida):",
      value=st.session_state.config_ubicacion_maps,
      placeholder=(
          "Ej. Centro Médico Nacional 20 de Noviembre, Ciudad de México"
      ),
  )
  st.session_state.config_ubicacion_maps = ubicacion_input

  # Widget interactivo dinámico de Google Maps con la dirección en tiempo real
  if ubicacion_input:
    query_mapa = urllib.parse.quote(ubicacion_input)
    url_embed_maps = (
        f"https://www.google.com/maps?q={query_mapa}&output=embed"
    )
    st.components.v1.iframe(url_embed_maps, height=320)

  st.markdown(
      '<div class="section-title">4. Generador de Enlaces y Códigos QR</div>',
      unsafe_allow_html=True,
  )

  base_url = "https://vacunas-invernal.streamlit.app/"
  link_generado = f"{base_url}?modo=registro&unidad={siglas_unidad}&jornada={tipo_jornada_letra}"

  st.info(
      "Enlace operativo listo para compartir con brigadas o imprimir en QR:"
  )
  st.code(link_generado, language="text")

  # Generación de Código QR en color Guinda institucional (#611232)
  qr = qrcode.QRCode(version=1, box_size=10, border=4)
  qr.add_data(link_generado)
  qr.make(fit=True)
  img = qr.make_image(fill_color="#611232", back_color="#ffffff")

  buf = io.BytesIO()
  img.save(buf, format="PNG")
  byte_im = buf.getvalue()

  col_qr1, col_qr2 = st.columns([1, 2])
  with col_qr1:
    st.image(
        byte_im, caption="Código QR (Guinda Institucional)", width=200
    )
  with col_qr2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Descargar Imagen QR (PNG)",
        data=byte_im,
        file_name=f"QR_Vacunacion_{siglas_unidad}_{tipo_jornada_letra}.png",
        mime="image/png",
        use_container_width=True,
    )

  st.markdown("---")
  if st.button("Cerrar Sesión de Administrador", use_container_width=True):
    st.session_state.autenticado_admin = False
    st.rerun()
