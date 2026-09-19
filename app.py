import datetime
import json
import urllib.parse
import gspread
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# Leer los parámetros de la URL para modo operativo por QR / Multi-unidad
params = st.query_params
es_modo_qr = params.get("modo", "").lower() == "registro"

if "unidad" in params:
  sigla_url = params.get("unidad")
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
      "NOV": "20 DE NOVIEMBRE",
      "ZAR": "ZARAGOZA",
      "GFAR": "GÓMEZ FARÍAS",
  }
  if sigla_url in mapa_siglas_inverso:
    st.session_state.nombre_unidad = mapa_siglas_inverso[sigla_url]
    st.session_state.siglas_unidad = sigla_url

if "jornada" in params:
  st.session_state.tipo_jornada = params.get("jornada", "I")

if "fecha" in params:
  st.session_state.fecha_jornada_url = params.get("fecha")

if "resp" in params:
  st.session_state.resp_jornada_url = params.get("resp")

# Estilos CSS institucionales
if es_modo_qr:
  st.markdown(
      """
        <style>
            .stApp { background-color: #fbf9f4; }
            [data-testid="stSidebar"] { display: none !important; }
            .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
            .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
            .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
            label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
            .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
            .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
            .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
            .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
            .stButton>button:hover { background-color: #002f2a !important; color: white !important; }
            input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
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
            [data-testid="stSidebar"] * { color: #ffffff !important; }
            .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
            .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
            .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
            label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
            .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
            .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
            .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
            .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
            .stButton>button:hover { background-color: #002f2a !important; color: white !important; }
            input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
        </style>
    """,
      unsafe_allow_html=True,
  )

# Inicializar variables de estado
if "registros_censales" not in st.session_state:
  st.session_state.registros_censales = []
if "contador_consecutivo" not in st.session_state:
  st.session_state.contador_consecutivo = 1
if "fecha_ultimo_consecutivo" not in st.session_state:
  st.session_state.fecha_ultimo_consecutivo = datetime.date.today()
if "tipo_jornada" not in st.session_state:
  st.session_state.tipo_jornada = "I"
if "siglas_unidad" not in st.session_state:
  st.session_state.siglas_unidad = "20N"
if "nombre_unidad" not in st.session_state:
  st.session_state.nombre_unidad = "20 DE NOVIEMBRE"
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
  vocales = "AEIOU"
  for letra in palabra[1:]:
    if letra in vocales:
      return letra
  return "X"


def obtener_primera_consonante_interna(palabra):
  consonantes = "BCDFGHJKLMNPQRSTVWXYZ"
  for letra in palabra[1:]:
    if letra in consonantes:
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
  if len(extra_limpio) >= 2:
    sufijo = extra_limpio[:2]
  else:
    sufijo = "00"

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
    "SINALOA",
    "SONORA",
    "TABASCO",
    "TAMAULIPAS",
    "TLAXCALA",
    "VERACRUZ",
    "YUCATÁN",
    "ZACATECAS",
]


@st.dialog("🎉 ¡REGISTRO EXITOSO - COMPROBANTE DIGITAL!")
def mostrar_modal_comprobante():
  p = st.session_state.ultimo_paciente_registrado
  if p:
    html_comprobante_component = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .card-comprobante {{ background-color: #ffffff; border: 3px solid #1e5b4f; padding: 12px; border-radius: 10px; color: #161a1d; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 10px; }}
            .folio-grande {{ font-size: 1.3rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 6px; border-radius: 6px; border: 2px dashed #a57f2c; margin: 5px 0; }}
            .btn-container {{ display: flex; gap: 8px; }}
            .btn {{ flex: 1; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; box-sizing: border-box; }}
            .btn-wa {{ background-color: #25D366; color: white; }}
            .btn-img {{ background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <h3 style="color: #1e5b4f; text-align: center; margin-top: 0; font-size: 0.95rem;">COMPROBANTE DE REGISTRO - VIGILE</h3>
                <p style="margin: 2px 0; font-size: 0.8rem;"><b>Unidad:</b> {unidad}</p>
                <p style="margin: 2px 0; font-size: 0.8rem;"><b>Paciente:</b> {nombre}</p>
                <p style="margin: 2px 0; font-size: 0.8rem;"><b>CURP:</b> {curp}</p>
                <p style="margin: 2px 0; font-size: 0.8rem;"><b>Grupo:</b> {grupo}</p>
                <div class="folio-grande">FOLIO: {folio}</div>
            </div>
            <div class="btn-container">
                <button class="btn btn-wa" onclick="compartirImagenWhatsApp()">💬 WhatsApp (Img)</button>
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar</button>
            </div>
            <script>
            function compartirImagenWhatsApp() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2 }}).then(canvas => {{
                    canvas.toBlob(blob => {{
                        const file = new File([blob], 'Comprobante_{folio}.png', {{ type: 'image/png' }});
                        const textoMensaje = `💉 *COMPROBANTE DE VACUNACIÓN - VIGILE*\\nUnidad: {unidad}\\nFolio: *{folio}*\\nPaciente: {nombre}\\nCURP: {curp}\\n¡Presente este comprobante en el módulo!`;
                        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                            navigator.share({{ files: [file], title: 'Comprobante', text: textoMensaje }}).catch(error => console.log('Error', error));
                        }} else {{
                            const enlace = document.createElement('a');
                            enlace.download = 'Comprobante_{folio}.png';
                            enlace.href = URL.createObjectURL(blob);
                            enlace.click();
                            window.open('https://wa.me/?text=' + encodeURIComponent(textoMensaje), '_blank');
                        }}
                    }}, 'image/png');
                }});
            }}
            function descargarCaptura() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2 }}).then(canvas => {{
                    const enlace = document.createElement('a');
                    enlace.download = 'Comprobante_{folio}.png';
                    enlace.href = canvas.toDataURL('image/png');
                    enlace.click();
                }});
            }}
            </script>
        </body>
        </html>
        """.format(
        unidad=st.session_state.nombre_unidad,
        nombre=p["nombre_completo"],
        curp=p["curp_con_entidad"],
        grupo=p["grupo_objetivo"],
        folio=p["folio"],
    )

    components.html(html_comprobante_component, height=270)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "➕ Nuevo Registro (Reiniciar Formulario)", use_container_width=True
    ):
      st.session_state.ultimo_paciente_registrado = None
      for key in [
          "input_paterno",
          "input_materno",
          "input_nombres",
          "input_fnac",
          "input_sexo",
          "input_estnac",
          "input_estres",
          "input_calle",
          "input_num",
          "input_col",
          "input_derecho",
          "input_ocupacion",
          "input_digitos",
      ]:
        if key in st.session_state:
          del st.session_state[key]
      st.rerun()


if st.session_state.ultimo_paciente_registrado is not None:
  mostrar_modal_comprobante()

st.markdown(
    '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> |'
    ' Modalidad: <b>'
    f'{"Extramuros" if st.session_state.tipo_jornada == "E" else "Intramuros"}</b></p>',
    unsafe_allow_html=True,
)

# --- BLOQUE 1: DATOS GENERALES Y FECHAS (BLOQUEADOS / AUTOMÁTICOS) ---
st.markdown(
    '<div class="section-title">1. Datos Generales y Fechas de Jornada</div>',
    unsafe_allow_html=True,
)
col_g1, col_g2, col_g3 = st.columns(3)

# Fecha de Registro fija con la fecha actual del sistema (bloqueada)
with col_g1:
  fecha_registro = st.date_input(
      "Fecha de Registro (Actual)",
      value=datetime.date.today(),
      format="DD/MM/YYYY",
      disabled=True,
  )

# Fecha de Aplicación leída desde la URL de la Pestaña 3 (bloqueada)
fecha_url_str = st.session_state.get("fecha_jornada_url", None)
if fecha_url_str:
  try:
    val_fecha_app = datetime.datetime.strptime(
        fecha_url_str, "%Y-%m-%d"
    ).date()
  except:
    val_fecha_app = datetime.date.today()
else:
  val_fecha_app = datetime.date.today()

with col_g2:
  fecha_aplicacion = st.date_input(
      "Fecha de Aplicación (Autorizada)",
      value=val_fecha_app,
      format="DD/MM/YYYY",
      disabled=True,
  )

hoy_actual = datetime.date.today()
if st.session_state.fecha_ultimo_consecutivo != hoy_actual:
  st.session_state.fecha_ultimo_consecutivo = hoy_actual
  st.session_state.contador_consecutivo = 1

aammmdd = hoy_actual.strftime("%y%m%d")
folio_automatico = f"{aammmdd}-{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}-{str(st.session_state.contador_consecutivo).zfill(3)}"

with col_g3:
  st.markdown(
      f"**Folio Generado (Auto)**<br>`{folio_automatico}`",
      unsafe_allow_html=True,
  )

# --- BLOQUE 2: IDENTIFICACIÓN DEL PACIENTE Y CURP ALGORÍTMICA ---
st.markdown(
    '<div class="section-title">2. Identificación del Paciente</div>',
    unsafe_allow_html=True,
)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1:
  paterno = st.text_input("Apellido Paterno *", key="input_paterno")
with col_n2:
  materno = st.text_input("Apellido Materno *", key="input_materno")
with col_n3:
  nombres = st.text_input("Nombre(s) *", key="input_nombres")

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1:
  fecha_nacimiento = st.date_input(
      "Fecha de Nacimiento *",
      value=None,
      min_value=datetime.date(1900, 1, 1),
      max_value=datetime.date.today(),
      format="DD/MM/YYYY",
      key="input_fnac",
  )
with col_fn2:
  sexo = st.selectbox(
      "Sexo *",
      options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"],
      key="input_sexo",
  )
with col_fn3:
  estado_nacimiento = st.selectbox(
      "Estado de Nacimiento *", options=estados_mexico, key="input_estnac"
  )

planes_o_embarazo = "NO"
if sexo == "MUJER":
  st.markdown(
      "<div style='background-color: #f7f4eb; border: 1px solid #a57f2c;"
      " padding: 12px; border-radius: 6px; margin-bottom: 10px;'>",
      unsafe_allow_html=True,
  )
  planes_o_embarazo = st.radio(
      "¿Está embarazada o tiene planes de embarazo?",
      options=["NO", "SÍ"],
      horizontal=True,
      key="input_embarazo",
  )
  st.markdown("</div>", unsafe_allow_html=True)

calc_anos, calc_meses, calc_dias = (
    calcular_edad_detallada(fecha_nacimiento, fecha_aplicacion)
    if fecha_nacimiento
    else (0, 0, 0)
)

col_info1, col_info2 = st.columns(2)
with col_info1:
  st.markdown(
      f'<div class="card-edad">📅 Edad: {calc_anos} A, {calc_meses} M,'
      f" {calc_dias} D</div>",
      unsafe_allow_html=True,
  )

digitos_faltantes = st.text_input(
    "Homoclave y Dígito Verificador (Opcional - 2 últimos caracteres)",
    max_chars=2,
    placeholder="Ej. A1",
    key="input_digitos",
)

curp_algoritmica = generar_curp_algoritmica(
    paterno,
    materno,
    nombres,
    fecha_nacimiento,
    sexo,
    estado_nacimiento,
    digitos_faltantes,
)
entidad_abr = estados_curp.get(estado_nacimiento, "NE")
curp_con_entidad = (
    f"{curp_algoritmica}/{entidad_abr}"
    if estado_nacimiento != "SELECCIONE UN ESTADO"
    else curp_algoritmica
)

with col_info2:
  st.markdown(
      f'<div class="card-curp">🆔 CURP / Entidad Resultante (14C): <br><span'
      f' style="color: #611232; font-family:'
      f' monospace;">{curp_con_entidad}</span></div>',
      unsafe_allow_html=True,
  )

# --- BLOQUE 3: DOMICILIO Y AFILIACIÓN ---
st.markdown(
    '<div class="section-title">3. Domicilio y Afiliación</div>',
    unsafe_allow_html=True,
)
estado_residencia = st.selectbox(
    "Estado de Residencia (Entidad Federativa) *",
    options=estados_mexico,
    key="input_estres",
)

col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
with col_dom1:
  calle = st.text_input("Calle *", key="input_calle")
with col_dom2:
  numero = st.text_input("No. (Ext / Int) *", key="input_num")
with col_dom3:
  colonia = st.text_input("Colonia *", key="input_col")

cuenta_derechohabiencia = st.selectbox(
    "¿Cuenta con derechohabiencia? *",
    options=["SELECCIONE UNA OPCIÓN", "NO", "SÍ"],
    key="input_derecho",
)

# --- BLOQUE 4: OCUPACIÓN ---
st.markdown(
    '<div class="section-title">4. Ocupación</div>', unsafe_allow_html=True
)
ocupacion = st.selectbox(
    "Seleccione su Ocupación *",
    options=[
        "SELECCIONE UNA OPCIÓN",
        "PERSONAL DE SALUD",
        "JUBILADO/A",
        "MAESTRO/A",
        "ADMINISTRATIVO/A",
        "TRABAJO EN GUARDERÍA",
        "OTRAS PROFESIONES",
    ],
    key="input_ocupacion",
)

# --- BLOQUE 5: GRUPOS DE RIESGO Y COMORBILIDADES ---
st.markdown(
    '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
    unsafe_allow_html=True,
)
col_r1, col_r2 = st.columns(2)

with col_r1:
  vih = st.checkbox("VIH / SIDA", key="com_vih")
  diabetes = st.checkbox("DIABETES MELLITUS", key="com_diab")
  obesidad = st.checkbox("OBESIDAD MÓRBIDA", key="com_obes")
  cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS", key="com_card")
  epoc = st.checkbox("ENFERMEDAD PULMONAR CRÓNICA (EPOC / ASMA)", key="com_epoc")

with col_r2:
  cancer = st.checkbox("CÁNCER", key="com_canc")
  congenitas = st.checkbox(
      "ENFERMEDADES CARDIACAS/PULMONARES CONGÉNITAS U OTROS", key="com_cong"
  )
  insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL", key="com_iren")
  inmunosupresion = st.checkbox(
      "INMUNOSUPRESIÓN ADQUIRIDA (EXCEPTO VIH)", key="com_inmu"
  )
  hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL ESENCIAL", key="com_hipt")
  discapacidades = st.checkbox(
      "DISCAPACIDADES (PARÁLISIS, NEURODESARROLLO, ETC.)", key="com_disc"
  )

otros_riesgos = st.text_input(
    "Otros grupos de riesgo / Observaciones clínicas (Mapeo AE):",
    placeholder="Especifique si aplica otro padecimiento...",
    key="input_otros_riesgos",
)

# --- LÓGICA DE GRUPO OBJETIVO ---
edad_total_meses = (calc_anos * 12) + calc_meses
tiene_comorb = any([
    vih,
    diabetes,
    obesidad,
    cardiopatias,
    epoc,
    cancer,
    congenitas,
    insuficiencia_renal,
    inmunosupresion,
    hipertension,
    discapacidades,
])

grupo_sugerido = ""
if fecha_nacimiento is not None:
  if 6 <= edad_total_meses <= 59:
    grupo_sugerido = "6 A 59 MESES"
  elif calc_anos >= 60:
    grupo_sugerido = "60 Y MÁS"
  elif planes_o_embarazo == "SÍ":
    grupo_sugerido = "EMBARAZADAS"
  elif ocupacion == "PERSONAL DE SALUD":
    grupo_sugerido = "PERSONAL DE SALUD"
  elif vih:
    grupo_sugerido = "VIH/sida"
  elif diabetes:
    grupo_sugerido = "DIABETES MELLITUS"
  elif obesidad:
    grupo_sugerido = "OBESIDAD MORBIDA"
  elif cardiopatias:
    grupo_sugerido = "CARDIOPATÍAS AGUDAS O CRÓNICAS"
  else:
    grupo_sugerido = "POBLACIÓN GENERAL"

st.markdown(
    '<div class="section-title">6. Grupo Objetivo (Detectado'
    " Automáticamente)</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="card-grupo">🎯 {grupo_sugerido}</div>', unsafe_allow_html=True
)

st.markdown("---")
if st.button(
    "Guardar Paciente y Migrar a Censo Nominal", use_container_width=True
):
  if not fecha_nacimiento:
    st.error("Por favor seleccione la Fecha de Nacimiento.")
  elif not paterno or not nombres:
    st.error("Complete Apellido Paterno y Nombre(s).")
  elif sexo == "SELECCIONE UNA OPCIÓN":
    st.error("Seleccione una opción en Sexo.")
  elif estado_nacimiento == "SELECCIONE UN ESTADO":
    st.error("Seleccione un Estado de Nacimiento válido.")
  elif estado_residencia == "SELECCIONE UN ESTADO":
    st.error("Seleccione un Estado de Residencia válido.")
  elif cuenta_derechohabiencia == "SELECCIONE UNA OPCIÓN":
    st.error("Por favor indique si cuenta con derechohabiencia.")
  elif not calle or not numero or not colonia:
    st.error("Complete los datos obligatorios del domicilio.")
  elif ocupacion == "SELECCIONE UNA OPCIÓN":
    st.error("Seleccione una Ocupación válida.")
  else:
    try:
      fecha_hoy_str = datetime.date.today().strftime("%d%m%y")
      siglas_actual = st.session_state.get("siglas_unidad", "20N")
      tipo_texto_jornada = (
          "INTRA" if st.session_state.tipo_jornada == "I" else "EXTRA"
      )
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

      try:
        worksheet = spreadsheet.worksheet(nombre_hoja_destino)
      except:
        worksheet = spreadsheet.worksheet("CENSO NOMINAL")

      valores_col_c = worksheet.col_values(3)
      siguiente_fila = max(13, len(valores_col_c) + 1)

      f_actual = siguiente_fila
      f_siguiente = siguiente_fila + 1

      worksheet.update(
          f"B{f_actual}:B{f_siguiente}",
          [[folio_automatico], [folio_automatico]],
      )
      worksheet.update_acell(f"C{f_actual}", paterno.upper())
      worksheet_acell_materno = (
          materno.upper() if materno else ""
      )  # Variable auxiliar limpia
      worksheet.update_acell(f"D{f_actual}", worksheet_acell_materno)
      worksheet.update_acell(f"E{f_actual}", nombres.upper())

      dd_nac = str(fecha_nacimiento.day).zfill(2)
      mm_nac = str(fecha_nacimiento.month).zfill(2)
      yyyy_nac = str(fecha_nacimiento.year)

      worksheet.update(f"F{f_actual}:F{f_siguiente}", [[dd_nac], [dd_nac]])
      worksheet.update(f"G{f_actual}:G{f_siguiente}", [[mm_nac], [mm_nac]])
      worksheet.update(f"H{f_actual}:H{f_siguiente}", [[yyyy_nac], [yyyy_nac]])

      worksheet.update(
          f"I{f_actual}:I{f_siguiente}", [[str(calc_anos)], [str(calc_anos)]]
      )
      worksheet.update(
          f"J{f_actual}:J{f_siguiente}", [[str(calc_meses)], [str(calc_meses)]]
      )

      sexo_letra = "H" if sexo == "HOMBRE" else "M"
      f_aplicacion_str = val_fecha_app.strftime("%d/%m/%Y")
      worksheet.update(
          f"K{f_actual}:K{f_siguiente}", [[sexo_letra], [sexo_letra]]
      )
      worksheet.update(
          f"L{f_actual}:L{f_siguiente}",
          [[f_aplicacion_str], [f_aplicacion_str]],
      )

      dir_calle = calle.upper()
      dir_num = numero.upper()
      dir_col = colonia.upper()
      worksheet.update(f"M{f_actual}:M{f_siguiente}", [[dir_calle], [dir_calle]])
      worksheet.update(f"N{f_actual}:N{f_siguiente}", [[dir_num], [dir_num]])
      worksheet.update(f"O{f_actual}:O{f_siguiente}", [[dir_col], [dir_col]])

      worksheet.update_acell(f"C{f_siguiente}", curp_con_entidad)

      col_grupo_map = {
          "6 A 59 MESES": "P",
          "60 Y MÁS": "Q",
          "EMBARAZADAS": "S",
          "PERSONAL DE SALUD": "T",
          "VIH/sida": "U",
          "DIABETES MELLITUS": "V",
          "OBESIDAD MORBIDA": "W",
          "CARDIOPATÍAS AGUDAS O CRÓNICAS": "X",
      }
      letra_col_grupo = col_grupo_map.get(grupo_sugerido, None)
      if letra_col_grupo:
        worksheet.update(
            f"{letra_col_grupo}{f_actual}:{letra_col_grupo}{f_siguiente}",
            [["X"], ["X"]],
        )

      for estado_activo, columna_letra in [
          (epoc, "Y"),
          (cancer, "Z"),
          (congenitas, "AA"),
          (insuficiencia_renal, "AB"),
          (inmunosupresion, "AC"),
          (hipertension, "AD"),
      ]:
        if estado_activo:
          worksheet.update(
              f"{columna_letra}{f_actual}:{columna_letra}{f_siguiente}",
              [["X"], ["X"]],
          )

      if otros_riesgos:
        worksheet.update(
            f"AE{f_actual}:AE{f_siguiente}",
            [[otros_riesgos.upper()], [otros_riesgos.upper()]],
        )

      worksheet.update(
          f"AM{f_actual}:AM{f_siguiente}",
          [[cuenta_derechohabiencia], [cuenta_derechohabiencia]],
      )

      nuevo_paciente = {
          "folio": folio_automatico,
          "curp_con_entidad": curp_con_entidad,
          "nombre_completo": (
              f"{paterno.upper()} {materno.upper()}, {nombres.upper()}"
          ),
          "grupo_objetivo": grupo_sugerido,
      }
      st.session_state.registros_censales.append(nuevo_paciente)
      st.session_state.ultimo_paciente_registrado = nuevo_paciente
      st.session_state.contador_consecutivo += 1
      st.rerun()

    except Exception as e:
      st.error(f"Error al conectar con Google Sheets para migrar el dato: {e}")
