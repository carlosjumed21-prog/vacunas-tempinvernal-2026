import datetime
import io
import json
import urllib.parse
import gspread
import qrcode
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Panel de Administración - Censo Nominal",
    page_icon="⚙️",
    layout="centered",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        [data-testid="stSidebar"] { display: none !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        .card-simultanea { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
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
if "unidad_anterior" not in st.session_state:
  st.session_state.unidad_anterior = ""
if "config_direccion_oficial" not in st.session_state:
  st.session_state.config_direccion_oficial = (
      "Avenida Félix Cuevas 540, Del Valle Sur, Benito Juárez, 03100 Ciudad de"
      " México, CDMX"
  )
if "jornada_autorizada" not in st.session_state:
  st.session_state.jornada_autorizada = False

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

  # Catálogo oficial completo de las 16 unidades del ISSSTE
  unidades_issste_data = {
      "20 DE NOVIEMBRE": {
          "sigla": "20N",
          "dir": (
              "Avenida Félix Cuevas 540, Del Valle Sur, Benito Juárez, 03100"
              " Ciudad de México, CDMX"
          ),
          "mapa": (
              "CMN 20 de Noviembre ISSSTE, Avenida Félix Cuevas, Ciudad de"
              " México"
          ),
      },
      "CHURUBUSCO": {
          "sigla": "CHU",
          "dir": (
              "Calzada de Tlalpan 4430, Toriello Guerra, Tlalpan, 14050 Ciudad"
              " de México, CDMX"
          ),
          "mapa": "Hospital Regional Churubusco ISSSTE, Ciudad de México",
      },
      "CLIDDA": {
          "sigla": "CLI",
          "dir": (
              "San Fernando 15, Toriello Guerra, Tlalpan, 14050 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "CLIDDA ISSSTE San Fernando Tlalpan, Ciudad de México",
      },
      "COYOACAN": {
          "sigla": "COY",
          "dir": (
              "Avenida Cuauhtémoc 330, Del Carmen, Coyoacán, 04100 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Coyoacán ISSSTE, CDMX",
      },
      "DEL VALLE": {
          "sigla": "DVA",
          "dir": (
              "Cacho 35, Del Valle Norte, Benito Juárez, 03103 Ciudad de México,"
              " CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Del Valle ISSSTE, CDMX",
      },
      "DIVISION DEL NORTE": {
          "sigla": "DVN",
          "dir": (
              "Avenida División del Norte 3233, Xoco, Benito Juárez, 03330"
              " Ciudad de México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar División del Norte ISSSTE",
      },
      "DR. DARIO FERNANDEZ FIERRO": {
          "sigla": "DFF",
          "dir": (
              "Avenida Revolución 1182, Tlacopac, Álvaro Obregón, 01049 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "Clínica Hospital Dr. Darío Fernández Fierro ISSSTE",
      },
      "DR. IGNACIO CHAVEZ": {
          "sigla": "ICH",
          "dir": (
              "Eje 1 Poniente Av. Cuauhtémoc s/n, Doctores, Cuauhtémoc, 06720"
              " Ciudad de México, CDMX"
          ),
          "mapa": "Clínica Hospital Dr. Ignacio Chávez ISSSTE",
      },
      "ERMITA": {
          "sigla": "ERM",
          "dir": (
              "Ermita Iztapalapa 67, Ermita, Benito Juárez, 03590 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "CMF Ermita ISSSTE, Ermita Iztapalapa, Ciudad de México",
      },
      "FUENTES BROTANTES": {
          "sigla": "FBR",
          "dir": (
              "Fuentes Brotantes s/n, Fuentes Brotantes, Tlalpan, 14410 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Fuentes Brotantes ISSSTE",
      },
      "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA": {
          "sigla": "MPM",
          "dir": (
              "Avenida Tláhuac s/n, San Lorenzo Tezonco, Iztapalapa, 13266 Ciudad"
              " de México, CDMX"
          ),
          "mapa": (
              "Hospital General Dra. Matilde Petra Montoya Lafragua ISSSTE"
          ),
      },
      "MILPA ALTA": {
          "sigla": "MIL",
          "dir": (
              "Prolongación Matamoros s/n, Villa Milpa Alta, Milpa Alta, 12000"
              " Ciudad de México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Milpa Alta ISSSTE",
      },
      "NARVARTE": {
          "sigla": "NAR",
          "dir": (
              "Avenida Cuauhtémoc 625, Narvarte Poniente, Benito Juárez, 03020"
              " Ciudad de México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Narvarte ISSSTE",
      },
      "TLALPAN": {
          "sigla": "TLA",
          "dir": (
              "Calzada de Tlalpan 4800, Toriello Guerra, Tlalpan, 14050 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Tlalpan ISSSTE",
      },
      "VILLA ALVARO OBREGON": {
          "sigla": "VAO",
          "dir": (
              "Calle 10 s/n, Tolteca, Álvaro Obregón, 01150 Ciudad de México,"
              " CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Villa Álvaro Obregón ISSSTE",
      },
      "XOCHIMILCO": {
          "sigla": "XOC",
          "dir": (
              "Providencia s/n, Barrio San Marcos, Xochimilco, 16050 Ciudad de"
              " México, CDMX"
          ),
          "mapa": "Clínica de Medicina Familiar Xochimilco ISSSTE",
      },
  }

  st.markdown(
      '<div class="section-title">1. Configuración de Operación y'
      " Unidad</div>",
      unsafe_allow_html=True,
  )

  col_c1, col_c2 = st.columns(2)
  with col_c1:
    unidad_sel = st.selectbox(
        "Unidad Médica ISSSTE:", options=list(unidades_issste_data.keys())
    )
    siglas_unidad = unidades_issste_data[unidad_sel]["sigla"]

  with col_c2:
    jornada_sel = st.selectbox(
        "Tipo de Jornada:",
        options=["Intramuros I", "Extramuros E"],
        format_func=lambda x: "Intramuros I" if "I" in x else "Extramuros E",
    )
    tipo_jornada_letra = "I" if "I" in jornada_sel else "E"
    tipo_jornada_texto = "INTRA" if tipo_jornada_letra == "I" else "EXTRA"

  if st.session_state.unidad_anterior != unidad_sel:
    st.session_state.unidad_anterior = unidad_sel
    st.session_state.config_direccion_oficial = unidades_issste_data[unidad_sel][
        "dir"
    ]
    st.rerun()

  # --- CONFIGURACIÓN DE JORNADAS SIMULTÁNEAS ---
  st.markdown("---")
  jornadas_simultaneas = st.toggle(
      "⚡ Activar Jornadas Simultáneas (Múltiples equipos o células en"
      " operación)",
      value=False,
  )

  num_jornadas = 1
  if jornadas_simultaneas:
    num_jornadas = st.number_input(
        "Número de jornadas simultáneas a habilitar:",
        min_value=2,
        max_value=5,
        value=2,
        step=1,
    )

  st.markdown(
      '<div class="section-title">2. Responsable(s) de la(s) Jornada(s) y'
      " Fechas</div>",
      unsafe_allow_html=True,
  )

  fecha_admin = st.date_input(
      "Fecha de Aplicación (Global para todas las simultáneas):",
      value=st.session_state.config_fecha_aplicacion,
      format="DD/MM/YYYY",
  )
  st.session_state.config_fecha_aplicacion = fecha_admin

  # Diccionario o lista para almacenar los datos de cada jornada simultánea
  config_jornadas_activas = []

  if not jornadas_simultaneas:
    resp_unico = st.text_input(
        "👤 Nombre del responsable de vacunación:",
        placeholder="Escriba el nombre completo...",
    )
    config_jornadas_activas.append({
        "sufijo_hoja": "",
        "sufijo_qr": "",
        "responsable": resp_unico.upper()
        if resp_unico
        else "PERSONAL AUTORIZADO",
    })
  else:
    st.info(
        f"Configurando {num_jornadas} equipos simultáneos (Se generarán"
        " sufijos JS1, JS2...)"
    )
    for i in range(1, num_jornadas + 1):
      st.markdown(
          f'<div class="card-simultanea"><b>Cédula / Brigada Simultánea #'
          f" {i}</b></div>",
          unsafe_allow_html=True,
      )
      resp_sim = st.text_input(
          f"👤 Responsable de Brigada #{i}:",
          placeholder=f"Nombre del responsable {i}...",
          key=f"resp_sim_{i}",
      )
      config_jornadas_activas.append({
          "sufijo_hoja": f"_JS{i}",
          "sufijo_qr": f"_JS{i}",
          "responsable": resp_sim.upper() if resp_sim else f"RESPONSABLE JS{i}",
      })

  col_f2, col_f3 = st.columns(2)
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
      '<div class="section-title">3. Ubicación y Mapa Interactivo</div>',
      unsafe_allow_html=True,
  )
  consulta_mapa = unidades_issste_data[unidad_sel]["mapa"]
  query_mapa = urllib.parse.quote(consulta_mapa)
  url_embed_maps = f"https://www.google.com/maps?q={query_mapa}&output=embed"
  st.components.v1.iframe(url_embed_maps, height=300)

  st.markdown("<br>", unsafe_allow_html=True)
  direccion_oficial_input = st.text_area(
      "📍 Dirección Oficial Principal:",
      value=st.session_state.config_direccion_oficial,
      height=80,
  )
  st.session_state.config_direccion_oficial = direccion_oficial_input

  st.markdown(
      '<div class="section-title">4. Generador de Enlaces y Códigos QR'
      " (Simultáneos)</div>",
      unsafe_allow_html=True,
  )

  base_url = "https://medprev-vacunas-invernal.streamlit.app/"
  fecha_url_str = st.session_state.config_fecha_aplicacion.strftime("%Y-%m-%d")

  # Iterar y mostrar enlaces/QRs para cada jornada configurada
  for idx, j_conf in enumerate(config_jornadas_activas, start=1):
    resp_encoded = urllib.parse.quote(j_conf["responsable"])
    link_generado = f"{base_url}?modo=registro&unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}&js={j_conf['sufijo_qr']}"

    titulo_seccion_qr = (
        f"🔗 Enlace y QR para Jornada {j_conf['sufijo_hoja']}"
        if j_conf["sufijo_hoja"]
        else "🔗 Enlace y QR Operativo"
    )
    st.markdown(f"**{titulo_seccion_qr}**")
    st.code(link_generado, language="text")

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
          byte_im,
          caption=f"QR Institucional {j_conf['sufijo_hoja']}",
          width=180,
      )
    with col_qr2:
      st.markdown("<br>", unsafe_allow_html=True)
      st.download_button(
          label=f"📥 Descargar QR PNG ({j_conf['sufijo_hoja'] if j_conf['sufijo_hoja'] else 'Principal'})",
          data=byte_im,
          file_name=(
              f"QR_Vacunacion_{siglas_unidad}_{tipo_jornada_letra}{j_conf['sufijo_hoja']}.png"
          ),
          mime="image/png",
          key=f"dl_qr_{idx}",
          use_container_width=True,
      )
    st.markdown("---")

  # --- BOTÓN DE AUTORIZACIÓN Y DUPLICACIÓN EN GOOGLE SHEETS ---
  if st.button(
      "🚀 Autorizar Jornada(s) y Generar Hoja(s) en Google Sheets",
      use_container_width=True,
  ):
    try:
      fecha_str = st.session_state.config_fecha_aplicacion.strftime("%d%m%y")

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

      hojas_existentes = [h.title for h in spreadsheet.worksheets()]
      duplicadas_detectadas = []

      # Verificar nombres de hojas que se intentan crear
      for j_conf in config_jornadas_activas:
        nombre_prueba = (
            f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str}"
        )
        if nombre_prueba in hojas_existentes:
          duplicadas_detectadas.append(nombre_prueba)

      # Validación de duplicados con alerta interactiva
      if duplicadas_detectadas:
        st.error(
            "⚠️ ALERTA: Las siguientes hojas ya existen en Google Sheets:"
            f" {', '.join(duplicadas_detectadas)}"
        )
        st.warning(
            "Si continúa, podría sobrescribir o interferir con registros"
            " existentes. Verifique los datos o cancele."
        )
      else:
        hojas_creadas_exito = []
        for j_conf in config_jornadas_activas:
          nombre_nueva_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str}"

          plantilla = spreadsheet.worksheet("CENSO NOMINAL")
          nueva_hoja = spreadsheet.duplicate_sheet(
              plantilla.id, new_sheet_name=nombre_nueva_hoja
          )
          spreadsheet.reorder_worksheets(
              [plantilla, nueva_hoja]
              + [
                  h
                  for h in spreadsheet.worksheets()
                  if h.title not in ["CENSO NOMINAL", nombre_nueva_hoja]
              ]
          )

          hoja_activa = spreadsheet.worksheet(nombre_nueva_hoja)

          # Inserción de metadatos institucionales
          fecha_formato_oficial = (
              st.session_state.config_fecha_aplicacion.strftime("%d/%m/%Y")
          )

          hoja_activa.update_acell("D6", "CDMX")
          hoja_activa.update_acell("M6", "ISSSTE")
          hoja_activa.update_acell("U6", "Delegación Sur")
          hoja_activa.update_acell("AC6", "CDMX")
          hoja_activa.update_acell("D7", "CDMX")
          hoja_activa.update_acell("D8", unidad_sel)
          hoja_activa.update_acell("AC8", fecha_formato_oficial)
          hoja_activa.update_acell("E9", j_conf["responsable"])

          hojas_creadas_exito.append(nombre_nueva_hoja)

        st.session_state.jornada_autorizada = True
        st.success(
            "¡Jornadas autorizadas y hojas generadas con éxito:"
            f" {', '.join(hojas_creadas_exito)}!"
        )
        st.rerun()

    except Exception as e:
      st.error(
          "Error al configurar Google Sheets. Asegúrate de que la hoja 'CENSO"
          " NOMINAL' exista y que el correo de servicio tenga permisos de"
          f" Editor. Detalle: {e}"
      )

  st.markdown("---")
  if st.button("🚪 Cerrar Sesión de Administrador", use_container_width=True):
    st.session_state.autenticado_admin = False
    st.rerun()
