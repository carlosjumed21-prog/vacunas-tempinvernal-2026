import datetime
import json
import urllib.parse
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Censo Nominal - Vacunación",
    page_icon="💉",
    layout="centered",
)

# 1. LECTURA DE PARÁMETROS DE LA URL (MODO OPERATIVO / QR)
params = st.query_params
es_modo_qr = params.get("modo", "").lower() == "registro"

# Mapeo inverso de siglas a nombres oficiales de las unidades
mapa_siglas_inverso = {
    "20N": "20 DE NOVIEMBRE",
    "CHU": "CHURUBUSCO",
    "CLI": "CLIDDA",
    "COY": "COYOACAN",
    "DVA": "DEL VALLE",
    "DVN": "DIVISION DEL NORTE",
    "DFF": "DR. DARIO FERNANDEZ FIERRO",
    "ICH": "DR. IGNACIO CHAVEZ",
    "ERM": "ERMITA",
    "FBR": "FUENTES BROTANTES",
    "MPM": "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA",
    "MIL": "MILPA ALTA",
    "NAR": "NARVARTE",
    "TLA": "TLALPAN",
    "VAO": "VILLA ALVARO OBREGON",
    "XOC": "XOCHIMILCO",
}

if "unidad" in params:
  sigla_url = params.get("unidad")
  if sigla_url in mapa_siglas_inverso:
    st.session_state.nombre_unidad = mapa_siglas_inverso[sigla_url]
    st.session_state.siglas_unidad = sigla_url

if "jornada" in params:
  st.session_state.tipo_jornada = params.get("jornada", "I")

# 2. ESTILOS INSTITUCIONALES Y OCULTAR SIDEBAR EN MODO REGISTRO
if es_modo_qr:
  st.markdown(
      """
        <style>
            .stApp { background-color: #fbf9f4; }
            [data-testid="stSidebar"] { display: none !important; }
            .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
            .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
            .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
        </style>
    """,
      unsafe_allow_html=True,
  )
else:
  st.markdown(
      """
        <style>
            .stApp { background-color: #fbf9f4; }
            [data-testid="stSidebar"] { background-color: #611232 !important; }
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #ffffff !important; }
            .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
            .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
            .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
        </style>
    """,
      unsafe_allow_html=True,
  )

# Interfaz Principal de Captura
unidad_actual = st.session_state.get(
    "nombre_unidad", "Seleccione Unidad en el Panel"
)
siglas_actual = st.session_state.get("siglas_unidad", "GEN")
jornada_actual = st.session_state.get("tipo_jornada", "I")
tipo_texto_jornada = "INTRA" if jornada_actual == "I" else "EXTRA"

st.markdown(
    '<p class="main-header">Sistema VIGILE - Censo Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad Médica: <b>{unidad_actual}</b> ({siglas_actual})'
    f' | Modalidad: <b>{tipo_texto_jornada}</b></p>',
    unsafe_allow_html=True,
)

st.info(
    "💡 Formulario de registro activo. Los datos capturados se migrarán de"
    " forma automática a la hoja correspondiente de Google Sheets."
)

# Formulario de captura base
with st.form("form_captura_paciente"):
  st.subheader("Datos Generales del Paciente")
  col1, col2 = st.columns(2)
  with col1:
    curp = st.text_input("CURP:")
    nombre = st.text_input("Nombre(s):")
    apellido_p = st.text_input("Apellido Paterno:")
  with col2:
    apellido_m = st.text_input("Apellido Materno:")
    edad = st.number_input("Edad:", min_value=0, max_value=120, value=30)
    sexo = st.selectbox("Sexo:", options=["Masculino", "Femenino"])

  submitted = st.form_submit_button(
      "💾 Guardar y Registrar en Censo", use_container_width=True
  )

  if submitted:
    if not curp or not nombre:
      st.error("Por favor, complete al menos la CURP y el Nombre.")
    else:
      try:
        # Lógica de migración a Google Sheets
        fecha_hoy_str = datetime.date.today().strftime("%d%m%y")
        nombre_hoja_destino = (
            f"{siglas_actual}_{tipo_texto_jornada}_{fecha_hoy_str}"
        )

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
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

        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        sheet_id = "1TH2KkQzNe4HwBcuJK_QR4gWfQ-wiyAyyczdTmLzn1Ds"
        spreadsheet = client.open_by_key(sheet_id)

        # Intentar acceder a la hoja específica de la jornada
        try:
          worksheet = spreadsheet.worksheet(nombre_hoja_destino)
        except:
          # Si por alguna razón no existe, usa la plantilla base
          worksheet = spreadsheet.worksheet("CENSO NOMINAL")

        # Agregar fila de datos
        fila_datos = [
            str(datetime.datetime.now()),
            curp,
            nombre,
            apellido_p,
            apellido_m,
            str(edad),
            sexo,
            unidad_actual,
            tipo_texto_jornada,
        ]
        worksheet.append_row(fila_datos)
        st.success(
            f"✅ ¡Registro guardado con éxito en la hoja: {nombre_hoja_destino}!"
        )

      except Exception as e:
        st.error(f"Error al conectar con Google Sheets para migrar el dato: {e}")
