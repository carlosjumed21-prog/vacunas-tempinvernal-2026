import datetime
import json
import unicodedata
import urllib.parse
from config import (
    GOOGLE_SCOPES,
    GOOGLE_SHEET_ID,
    MAPA_SIGLAS_INVERSO,
    aplicar_configuracion_global,
)
from google.oauth2 import service_account
import gspread
import streamlit as st
import streamlit.components.v1 as components

aplicar_configuracion_global("Censo Nominal - Registro", "💉")

params = st.query_params
# Capturamos la sigla directamente de la URL; si no existe, toma la primera disponible de forma segura
sigla_url = params.get("unidad", "").upper()
if not sigla_url or sigla_url not in MAPA_SIGLAS_INVERSO:
  sigla_url = "20N"  # Respaldo seguro solo si la URL viene completamente vacía

nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "20 DE NOVIEMBRE")
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

st.markdown(
    """
    <style>
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
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
    "SINALOA",¡Ya vi exactamente por qué pasa en la captura, Carlos! Fíjate en la URL que se está generando: `...unidad=COY...`, pero el título de arriba dice `Unidad: 20 DE NOVIEMBRE`. 

Esto pasa porque en **`pages/1_formulario.py`** se quedó un valor quemado por defecto (`sigla_url = params.get("unidad", "20N")`) o el diccionario inverso (`MAPA_SIGLAS_INVERSO`) no está mapeando correctamente las siglas cortas (`COY`, `CHU`, etc.) al nombre completo de la unidad, por lo que al leer `COY` no lo encuentra y cae en el default de `20 DE NOVIEMBRE`.

Para solucionarlo de forma definitiva y robusta, actualicemos el bloque inicial de **`pages/1_formulario.py`** donde se leen los parámetros de la URL para que traduzca dinámicamente cualquier sigla que le mandes.

Aquí tienes el archivo **`pages/1_formulario.py`** completo y corregido:

```python
import datetime
import json
import unicodedata
import urllib.parse
from config import (
    GOOGLE_SCOPES,
    GOOGLE_SHEET_ID,
    MAPA_SIGLAS_INVERSO,
    UNIDADES_ISSSTE,
    aplicar_configuracion_global,
)
from google.oauth2 import service_account
import gspread
import streamlit as st
import streamlit.components.v1 as components

aplicar_configuracion_global("Censo Nominal - Registro", "💉")

params = st.query_params
sigla_url = params.get("unidad", "20N").upper()

# Mapeo seguro y directo utilizando el diccionario global de config.py
nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "20 DE NOVIEMBRE")
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

st.markdown(
    """
    <style>
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important
