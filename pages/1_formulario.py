import datetime
import json
import unicodedata
import urllib.parse
import gspread
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# --- CAPTURA PRECISA DE PARÁMETROS DE LA URL ---
params = st.query_params
es_modo_qr = params.get("modo", "").lower() == "registro" or "unidad" in params

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

sigla_url = params.get("unidad", "20N")
nombre_base_unidad = mapa_siglas_inverso.get(sigla_url, "20 DE NOVIEMBRE")
sufijo_js = params.get("js", "")

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = (
    f"{nombre_base_unidad} (Brigada {sufijo_js})"
    if sufijo_js
    else nombre_base_unidad
)
st.session_state.tipo_jornada = params.get("jornada", "I")

fecha_url_str = params.get("fecha", datetime.date.today().strftime("%Y-%m-%d"))
try:
  val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
  val_fecha_app = datetime.date.today()

# Ocultar barra lateral si viene por enlace o QR
css_sidebar_oculta = (
    """
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    """
    if es_modo_qr
    else ""
)

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: #fbf9f4; }}
        {css_sidebar_oculta}
        .main-header {{ font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }}
        .sub-header {{ font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }}
        .section-title {{ font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }}
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label {{ font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }}
        .card-edad {{ background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }}
        .card-curp {{ background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }}
        .card-grupo {{ background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }}
        .stButton>button {{ background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }}
        input[type="text"] {{ text-transform: uppercase !important; font-size: 1.1rem !important; }}
    </style>
""",
    unsafe_allow_html=True,
)

if "registros_censales" not in st.session_state:
  st.session_state.registros_censales = []
if "ultimo_paciente_registrado" not in st.session_state:
  st.session_state.ultimo_paciente_registrado = None


def calcular_edad_detallada(fecha_nac, fecha_ref):
  if not fecha_nac or not fecha_ref or fecha_nac > fecha_ref:
    return 0, 0, 0
  anos = fecha_ref.year - fecha_nac.year
  meses = fecha_ref.month - fecha_nac.month
  dias = fecha_ref.day - fecha_nac.day
  if dias < 0:
    meses -= 1
    mes_anterior = fecha_ref.month - 1 if fecha_ref.month > 1 else 12
    anio_anterior = (
        fecha_ref.year if fecha_ref.month > 1 else fecha_ref.year - 1
    )
    dias_mes_anterior = (
        datetime.date(anio_anterior, mes_anterior + 1, 1)
        - datetime.timedelta(days=1)
    ).day
    dias += dias_mes_anterior
  if meses < 0:
    anos -= 1
    meses += 12
  return max(0, anos), max(0, meses), max(0, dias)


def limpiar_texto(texto):
  if not texto:
    return ""
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()


def obtener_primera_vocal_interna(palabra):
  for letra in palabra[1:]:
    if letra in "AEIOU":
      return letra
  return "X"


def obtener_primera_consonante_interna(palabra):
  for letra in palabra[1:]:
    if letra in "BCDFGHJKLMNPQRSTVWXYZ":
      return letra
  return "X"


estados_curp = {
    "AGUASCALIENTES": "AS",
    "BAJA CALIFORNIA": "BC",
    "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC",
    "CHIAPAS": "CS",
    "CHIHUAHUA": "CH",
    "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL",
    "COLIMA": "CM",
    "DURANGO": "DG",
    "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT",
    "GUERRERO": "GR",
    "HIDALGO": "HG",
    "JALISCO": "JC",
    "MICHOACÁN": "MN",
    "MORELOS": "MS",
    "NAYARIT": "NT",
    "NUEVO LEÓN": "NL",
    "OAXACA": "OC",
    "PUEBLA": "PL",
    "QUERÉTARO": "QT",
    "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP",
    "SINALOA": "SL",
    "SONORA": "SR",
    "TABASCO": "TC",
    "TAMAULIPAS": "TS",
    "TLAXCALA": "TL",
    "VERACRUZ": "VZ",
    "YUCATÁN": "YN",
    "ZACATECAS": "ZS",
}


def generar_curp_algoritmica(
    paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""
):
  p = limpiar_texto(paterno)
  m = limpiar_texto(materno) if materno else ""
  n = limpiar_texto(nombres)
  if not p or not n or not fecha_nac:
    return "COMPLETA DATOS Y FECHA"
  nombres_lista = n.split()
  primer_nombre = nombres_lista[0] if nombres_lista else "X"
  if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
    primer_nombre = nombres_lista[1]
  c1 = p[0] if p else "X"
  c2 = obtener_primera_vocal_interna(p)
  c3 = m[0] if m else "X"
  c4 = primer_nombre[0] if primer_nombre else "X"
  yy = str(fecha_nac.year)[-2:]
  mm = str(fecha_nac.month).zfill(2)
  dd = str(fecha_nac.day).zfill(2)
  fec_part = f"{yy}{mm}{dd}"
  sexo_part = "H" if sexo == "HOMBRE" else ("M" if sexo == "MUJER" else "X")
  est_part = estados_curp.get(est_nac, "NE")
  c14 = obtener_primera_consonante_interna(p)
  c15 = obtener_primera_consonante_interna(m) if m else "X"
  c16 = obtener_primera_consonante_interna(primer_nombre)
  curp_16 = f"{c1}{c2}{c3}{c4}{fec_part}{sexo_part}{est_part}{c14}{c15}{c16}"
  extra_limpio = limpiar_texto(digitos_extra)
  sufijo = extra_limpio[:2] if len(extra_limpio) >= 2 else "00"
  return f"{curp_16}{sufijo}"


estados_mexico = [
    "SELECCIONE UN ESTADO",
    "AGUASCALIENTES",
    "BAJA CALIFORNIA",
    "BAJA CALIFORNIA SUR",
    "CAMPECHE",
    "CHIAPAS",
    "CHIHUAHUA",
    "CIUDAD DE MÉXICO",
    "COAHUILA",
    "COLIMA",
    "DURANGO",
    "ESTADO DE MÉXICO",
    "GUANAJUATO",
    "GUERRERO",
    "HIDALGO",
    "JALISCO",
    "MICHOACÁN",
    "MORELOS",
    "NAYARIT",
    "NUEVO LEÓN",
    "OAXACA",
    "PUEBLA",
    "QUERÉTARO",
    "QUINTANA ROO",
    "SAN LUIS POTOSÍ",
¡Te entiendo perfectamente, Carlos! Vamos a corregir esos tres puntos clave de inmediato:

1. **Formulario:** Ocultar por completo la barra lateral cuando se accede por enlace personalizado y eliminar la leyenda del responsable.
2. **Módulo Operativo:** Bloquear o fijar la hoja activa cuando se entra por enlace personalizado para que no se despliegue el menú de selección y los datos caigan directo en su hoja correspondiente.
3. **Panel de Administración:** Iniciar los menús desplegables (selectboxes) sin valores por defecto (obligando a elegir o mostrando una opción vacía inicial).

Aquí tienes los códigos limpios, completos y en español para cada uno de los archivos involucrados:

---

### 1. Archivo `pages/1_formulario.py` (Sin menú lateral y sin leyenda de responsable)

```python
import datetime
import json
import unicodedata
import urllib.parse
import gspread
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# --- CAPTURA PRECISA DE PARÁMETROS DE LA URL ---
params = st.query_params
es_modo_qr = (
    params.get("modo", "").lower() == "registro"
    or "unidad" in params
    or "js" in params
)

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

sigla_url = params.get("unidad", "20N")
nombre_base_unidad = mapa_siglas_inverso.get(sigla_url, "20 DE NOVIEMBRE")
sufijo_js = params.get("js", "")

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = (
    f"{nombre_base_unidad} (Brigada {sufijo_js})"
    if sufijo_js
    else nombre_base_unidad
)
st.session_state.tipo_jornada = params.get("jornada", "I")

fecha_url_str = params.get("fecha", datetime.date.today().strftime("%Y-%m-%d"))
try:
  val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
  val_fecha_app = datetime.date.today()

# Estilos CSS (Forzando la ocultación total de la barra lateral si es enlace personalizado)
css_sidebar_oculta = (
    """
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    """
    if es_modo_qr
    else ""
)

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: #fbf9f4; }}
        {css_sidebar_oculta}
        .main-header {{ font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }}
        .sub-header {{ font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }}
        .section-title {{ font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }}
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label {{ font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }}
        .card-edad {{ background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }}
        .card-curp {{ background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }}
        .card-grupo {{ background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }}
        .stButton>button {{ background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }}
        input[type="text"] {{ text-transform: uppercase !important; font-size: 1.1rem !important; }}
    </style>
""",
    unsafe_allow_html=True,
)

if "registros_censales" not in st.session_state:
  st.session_state.registros_censales = []
if "ultimo_paciente_registrado" not in st.session_state:
  st.session_state.ultimo_paciente_registrado = None


def calcular_edad_detallada(fecha_nac, fecha_ref):
  if not fecha_nac or not fecha_ref or fecha_nac > fecha_ref:
    return 0, 0, 0
  anos = fecha_ref.year - fecha_nac.year
  meses = fecha_ref.month - fecha_nac.month
  dias = fecha_ref.day - fecha_nac.day
  if dias < 0:
    meses -= 1
    mes_anterior = fecha_ref.month - 1 if fecha_ref.month > 1 else 12
    anio_anterior = (
        fecha_ref.year if fecha_ref.month > 1 else fecha_ref.year - 1
    )
    dias_mes_anterior = (
        datetime.date(anio_anterior, mes_anterior + 1, 1)
        - datetime.timedelta(days=1)
    ).day
    dias += dias_mes_anterior
  if meses < 0:
    anos -= 1
    meses += 12
  return max(0, anos), max(0, meses), max(0, dias)


def limpiar_texto(texto):
  if not texto:
    return ""
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()


def obtener_primera_vocal_interna(palabra):
  for letra in palabra[1:]:
    if letra in "AEIOU":
      return letra
  return "X"


def obtener_primera_consonante_interna(palabra):
  for letra in palabra[1:]:
    if letra in "BCDFGHJKLMNPQRSTVWXYZ":
      return letra
  return "X"


estados_curp = {
    "AGUASCALIENTES": "AS",
    "BAJA CALIFORNIA": "BC",
    "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC",
    "CHIAPAS": "CS",
    "CHIHUAHUA": "CH",
    "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL",
    "COLIMA": "CM",
    "DURANGO": "DG",
    "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT",
    "GUERRERO": "GR",
    "HIDALGO": "HG",
    "JALISCO": "JC",
    "MICHOACÁN": "MN",
    "MORELOS": "MS",
    "NAYARIT": "NT",
    "NUEVO LEÓN": "NL",
    "OAXACA": "OC",
    "PUEBLA": "PL",
    "QUERÉTARO": "QT",
    "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP",
    "SINALOA": "SL",
    "SONORA": "SR",
    "TABASCO": "TC",
    "TAMAULIPAS": "TS",
    "TLAXCALA": "TL",
    "VERACRUZ": "VZ",
    "YUCATÁN": "YN",
    "ZACATECAS": "ZS",
}


def generar_curp_algoritmica(
    paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""
):
  p = limpiar_texto(paterno)
  m = limpiar_texto(materno) if materno else ""
  n = limpiar_texto(nombres)
  if not p or not n or not fecha_nac:
    return "COMPLETA DATOS Y FECHA"
  nombres_lista = n.split()
  primer_nombre = nombres_lista[0] if nombres_lista else "X"
  if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
    primer_nombre = nombres_lista[1]
  c1 = p[0] if p else "X"
  c2 = obtener_primera_vocal_interna(p)
  c3 = m[0] if m else "X"
  c4 = primer_nombre[0] if primer_nombre else "X"
  yy = str(fecha_nac.year)[-2:]
  mm = str(fecha_nac.month).zfill(2)
  dd = str(fecha_nac.day).zfill(2)
  fec_part = f"{yy}{mm}{dd}"
  sexo_part = "H" if sexo == "HOMBRE" else ("M" if sexo == "MUJER" else "
