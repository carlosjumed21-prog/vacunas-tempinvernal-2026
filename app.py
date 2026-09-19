import datetime
import urllib.parse
import unicodedata
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# Leer los parámetros de la URL para ver si el usuario entró mediante el código QR (modo operativo)
params = st.query_params
es_modo_qr = params.get("modo", "").lower() == "registro"

# Estilos CSS institucionales y de tarjetas dinámicas
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
            .card-comprobante { background-color: #ffffff; border: 3px solid #1e5b4f; padding: 25px; border-radius: 12px; color: #161a1d; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .folio-grande { font-size: 2rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 10px; border-radius: 6px; border: 2px dashed #a57f2c; margin: 15px 0; }
            
            /* Forzar color guinda en la barra lateral (sidebar) y sus textos */
            [data-testid="stSidebar"] { background-color: #611232 !important; }
            [data-testid="stSidebar"] * { color: #ffffff !important; }

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
            
            /* Forzar color guinda en la barra lateral (sidebar) y sus textos */
            [data-testid="stSidebar"] { background-color: #611232 !important; }
            [data-testid="stSidebar"] * { color: #ffffff !important; }

            .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
            .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
            .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
            label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
            .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
            .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
            .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
            .card-comprobante { background-color: #ffffff; border: 3px solid #1e5b4f; padding: 25px; border-radius: 12px; color: #161a1d; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .folio-grande { font-size: 2rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 10px; border-radius: 6px; border: 2px dashed #a57f2c; margin: 15px 0; }
            
            .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
            .stButton>button:hover { background-color: #002f2a !important; color: white !important; }
            input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )

# Inicializar variables de estado compartido si no existen
if "registros_censales" not in st.session_state:
    st.session_state.registros_censales = []
if "contador_consecutivo" not in st.session_state:
    st.session_state.contador_consecutivo = 1
if "fecha_ultimo_consecutivo" not in st.session_state:
    st.session_state.fecha_ultimo_consecutivo = datetime.date.today()
if "tipo_jornada" not in st.session_state:
    st.session_state.tipo_jornada = "I"
if "siglas_unidad" not in st.session_state:
    st.session_state.siglas_unidad = "ERM"
if "nombre_unidad" not in st.session_state:
    st.session_state.nombre_unidad = "ERMITA"
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

# --- VENTANA EMERGENTE / MODAL DE COMPROBANTE SI ACABA DE REGISTRARSE ---
if st.session_state.ultimo_paciente_registrado is not None:
  p = st.session_state.ultimo_paciente_registrado
  st.markdown("---")
  st.markdown(
      '<div style="background-color: #e8f0ec; padding: 10px; border-radius:'
      ' 6px; text-align: center; font-weight: bold; color: #1e5b4f; font-size:'
      ' 1.2rem; margin-bottom: 15px;">🎉 ¡REGISTRO EXITOSO! COMPROBANTE'
      " DIGITAL</div>",
      unsafe_allow_html=True,
  )

  texto_comprobante = f"""
    <div class="card-comprobante">
        <h3 style="color: #1e5b4f; text-align: center; margin-top: 0;">COMPROBANTE DE REGISTRO - CAMPAÑA INVERNAL</h3>
        <p><b>Unidad Médica:</b> {st.session_state.nombre_unidad}</p>
        <p><b>Nombre del Paciente:</b> {p['nombre_completo']}</p>
        <p><b>CURP:</b> {p['curp_algoritmica']}</p>
        <p><b>Grupo Objetivo:</b> {p['grupo_objetivo']}</p>
        <div class="folio-grande">FOLIO: {p['folio']}</div>
        <hr style="border: 1px solid #e6d194;">
        <p>📅 <b>Fecha de Aplicación:</b> {p['fecha_aplicacion'].strftime('%d/%m/%Y')}</p>
        <p>⏰ <b>Horario de Atención:</b> Lunes a Viernes de 08:00 a 14:00 hrs (Módulo de Vacunación)</p>
        <p style="font-size: 0.9rem; color: #666; text-align: center; margin-top: 15px;">Conserve este comprobante para su validación en el módulo.</p>
    </div>
    """
  st.markdown(texto_comprobante, unsafe_allow_html=True)

  # Botones de acción: Descargar y Compartir por WhatsApp
  col_btn1, col_btn2, col_btn3 = st.columns(3)

  with col_btn1:
    # Botón para descargar como archivo de texto plano con los datos del comprobante
    contenido_txt = f"""SISTEMA VIGILE - COMPROBANTE DE VACUNACION
Unidad: {st.session_state.nombre_unidad}
Folio: {p['folio']}
Paciente: {p['nombre_completo']}
CURP: {p['curp_algoritmica']}
Grupo: {p['grupo_objetivo']}
Fecha Aplicacion: {p['fecha_aplicacion'].strftime('%d/%m/%Y')}
"""
    st.download_button(
        label="📥 Descargar",
        data=contenido_txt,
        file_name=f"Comprobante_{p['folio']}.txt",
        mime="text/plain",
        use_container_width=True,
    )

  with col_btn2:
    # Mensaje codificado para WhatsApp
    msg_wa = (
        f"💉 *COMPROBANTE DE VACUNACIÓN - VIGILE*\n"
        f"Unidad: {st.session_state.nombre_unidad}\n"
        f"Folio: *{p['folio']}*\n"
        f"Paciente: {p['nombre_completo']}\n"
        f"CURP: {p['curp_algoritmica']}\n"
        f"Fecha: {p['fecha_aplicacion'].strftime('%d/%m/%Y')}\n"
        f"¡Preséntese en el módulo con este comprobante!"
    )
    url_whatsapp = f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
    st.markdown(
        f'<a href="{url_whatsapp}" target="_blank"><button'
        ' style="background-color: #25D366; color: white; border: none; padding:'
        ' 0.6rem 1rem; font-size: 1.1rem; font-weight: bold; border-radius: 6px;'
        ' width: 100%; text-align: center; cursor: pointer;">💬'
        " WhatsApp</button></a>",
        unsafe_allow_html=True,
    )

  with col_btn3:
    if st.button("➕ Nuevo Registro", use_container_width=True):
      st.session_state.ultimo_paciente_registrado = None
      st.rerun()

  st.markdown("---")

# --- BLOQUE 1: DATOS GENERALES Y FECHAS ---
st.markdown(
    '<div class="section-title">1. Datos Generales y Fechas</div>',
    unsafe_allow_html=True,
)
col_g1, col_g2, col_g3 = st.columns(3)
with col_g1:
  fecha_registro = st.date_input(
      "Fecha de Registro", value=datetime.date.today(), format="DD/MM/YYYY"
  )
with col_g2:
  fecha_aplicacion = st.date_input(
      "Fecha de Aplicación", value=datetime.date.today(), format="DD/MM/YYYY"
  )

hoy_actual = fecha_registro
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
  paterno = st.text_input("Apellido Paterno *")
with col_n2:
  materno = st.text_input("Apellido Materno *")
with col_n3:
  nombres = st.text_input("Nombre(s) *")

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1:
  fecha_nacimiento = st.date_input(
      "Fecha de Nacimiento *",
      value=None,
      min_value=datetime.date(1900, 1, 1),
      max_value=datetime.date.today(),
      format="DD/MM/YYYY",
  )
with col_fn2:
  sexo = st.selectbox(
      "Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"]
  )
with col_fn3:
    estado_nacimiento = st.selectbox(
        "Estado de Nacimiento *", options=estados_mexico, key="est_nac_block2"
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
    "Homoclave y Dígito Verificador (Opcional - 2 últimos caracteres de tu CURP"
    " oficial)",
    max_chars=2,
    placeholder="Ej. A1",
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
with col_info2:
  st.markdown(
      f'<div class="card-curp">🆔 CURP Resultante: <br><span'
      f' style="color: #611232; font-family:'
      f' monospace;">{curp_algoritmica}</span></div>',
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
    key="est_res",
)

col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
with col_dom1:
  calle = st.text_input("Calle *")
with col_dom2:
  numero = st.text_input("No. (Ext / Int) *")
with col_dom3:
  colonia = st.text_input("Colonia *")

cuenta_derechohabiencia = st.selectbox(
    "¿Cuenta con derechohabiencia? *",
    options=["SELECCIONE UNA OPCIÓN", "NO", "SÍ"],
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
)

# --- BLOQUE 5: GRUPOS DE RIESGO Y COMORBILIDADES ---
st.markdown(
    '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
    unsafe_allow_html=True,
)
col_r1, col_r2 = st.columns(2)

with col_r1:
  vih = st.checkbox("VIH / SIDA")
  diabetes = st.checkbox("DIABETES MELLITUS")
  obesidad = st.checkbox("OBESIDAD MÓRBIDA")
  cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS")
  epoc = st.checkbox("ENFERMEDAD PULMONAR CRÓNICA (EPOC / ASMA)")

with col_r2:
  cancer = st.checkbox("CÁNCER")
  congenitas = st.checkbox(
      "ENFERMEDADES CARDIACAS/PULMONARES CONGÉNITAS U OTROS"
  )
  insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL")
  inmunosupresion = st.checkbox("INMUNOSUPRESIÓN ADQUIRIDA (EXCEPTO VIH)")
  hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL ESENCIAL")
  discapacidades = st.checkbox(
      "DISCAPACIDADES (PARÁLISIS, NEURODESARROLLO, ETC.)"
  )

# --- LÓGICA DE CONDICIONES PARA AUTODETECCIÓN DE GRUPO OBJETIVO ---
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
    grupo_sugerido = "PERSONAS GESTANTES"
  elif ocupacion == "PERSONAL DE SALUD":
    grupo_sugerido = "PERSONAL DE SALUD"
  elif vih:
    grupo_sugerido = "PERSONAS QUE VIVEN CON VIH/SIDA"
  elif diabetes:
    grupo_sugerido = "PERSONAS QUE VIVEN CON DIABETES MELLITUS"
  elif obesidad:
    grupo_sugerido = "PERSONAS QUE VIVEN CON OBESIDAD MÓRBIDA"
  elif cardiopatias:
    grupo_sugerido = "PERSONAS QUE VIVEN CON CARDIOPATÍAS AGUDAS O CRÓNICAS"
  elif epoc:
    grupo_sugerido = (
        "PERSONAS QUE VIVEN CON ENFERMEDAD PULMONAR CRÓNICA (EPOC / ASMA)"
    )
  elif cancer:
    grupo_sugerido = "PERSONAS QUE VIVEN CON CÁNCER"
  elif congenitas:
    grupo_sugerido = "ENFERMEDADES CARDIACAS/PULMONARES CONGÉNITAS U OTROS"
  elif insuficiencia_renal:
    grupo_sugerido = "PERSONAS QUE VIVEN CON INSUFICIENCIA RENAL"
  elif inmunosupresion:
    grupo_sugerido = "INMUNOSUPRESIÓN ADQUIRIDA"
  elif hipertension:
    grupo_sugerido = "HIPERTENSIÓN ARTERIAL ESENCIAL"
  elif discapacidades:
    grupo_sugerido = "DISCAPACIDADES"
  else:
    grupo_sugerido = "POBLACIÓN GENERAL / OTRO"

st.markdown(
    '<div class="section-title">6. Grupo Objetivo (Detectado'
    " Automáticamente)</div>",
    unsafe_allow_html=True,
)
if grupo_sugerido == "":
  st.markdown(
      '<div class="card-grupo" style="background-color: #fbf9f4; border: 2px'
      ' dashed #a57f2c; color: #611232;">POR DESIGNAR</div>',
      unsafe_allow_html=True,
  )
else:
  st.markdown(
      f'<div class="card-grupo">🎯 {grupo_sugerido}</div>',
      unsafe_allow_html=True,
  )

# --- FORMULARIO PARA ANTECEDENTE VACUNAL Y BOTÓN DE GUARDADO ---
with st.form("form_censo_vacunacion_guardar"):
  # --- ANTECEDENTE VACUNAL ---
  st.markdown(
      '<div class="section-title">7. Antecedente Vacunal</div>',
      unsafe_allow_html=True,
  )
  col_av1, col_av2 = st.columns(2)
  with col_av1:
    antecedente_covid = st.radio(
        "¿Cuenta con alguna dosis previa de COVID-19?",
        options=["SÍ", "NO", "LO DESCONOCE"],
        horizontal=True,
    )
  with col_av2:
    antecedente_influenza = st.radio(
        "¿Cuenta con alguna dosis previa de Influenza?",
        options=["SÍ", "NO", "LO DESCONOCE"],
        horizontal=True,
    )

  st.markdown("---")
  submitted = st.form_submit_button(
      "Guardar Paciente en el Censo Nominal", use_container_width=True
  )

  if submitted:
    if not fecha_nacimiento:
      st.error("Por favor seleccione la Fecha de Nacimiento.")
    elif grupo_sugerido == "":
      st.error(
          "Por favor complete la fecha de nacimiento para determinar el grupo"
          " objetivo."
      )
    elif (
        not paterno
        or not nombres
        or estado_nacimiento == "SELECCIONE UN ESTADO"
        or estado_residencia == "SELECCIONE UN ESTADO"
        or cuenta_derechohabiencia == "SELECCIONE UNA OPCIÓN"
        or not calle
        or not numero
        or not colonia
        or ocupacion == "SELECCIONE UNA OPCIÓN"
    ):
      st.error(
          "Por favor complete los campos obligatorios y seleccione una opción"
          " válida en los menús desplegables (*)."
      )
    else:
      nuevo_paciente = {
          "folio": folio_automatico,
          "curp_algoritmica": curp_algoritmica,
          "nombre_completo": (
              f"{paterno.upper()} {materno.upper()}, {nombres.upper()}"
          ),
          "paterno": paterno.upper(),
          "materno": materno.upper(),
          "nombres": nombres.upper(),
          "fecha_nacimiento": fecha_nacimiento,
          "estado_nacimiento": estado_nacimiento,
          "edad_anos": calc_anos,
          "edad_meses": calc_meses,
          "edad_dias": calc_dias,
          "edad_total_meses": edad_total_meses,
          "sexo": sexo,
          "embarazo": (planes_o_embarazo == "SÍ"),
          "ocupacion": ocupacion,
          "personal_salud": (ocupacion == "PERSONAL DE SALUD"),
          "derechohabiencia": cuenta_derechohabiencia,
          "tiene_comorbilidades": tiene_comorb,
          "grupo_objetivo": grupo_sugerido,
          "antecedente_covid": antecedente_covid,
          "antecedente_influenza": antecedente_influenza,
          "fecha_registro": fecha_registro,
          "fecha_aplicacion": fecha_aplicacion,
      }
      st.session_state.registros_censales.append(nuevo_paciente)
      st.session_state.ultimo_paciente_registrado = nuevo_paciente
      st.session_state.contador_consecutivo += 1
      st.rerun()
