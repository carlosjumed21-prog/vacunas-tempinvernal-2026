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
        /* Barra lateral habilitada y estilizada con tono guinda institucional */
        [data-testid="stSidebar"] { background-color: #611232 !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #ffffff !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        .card-simultanea { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 20px; border-radius: 8px; margin-bottom: 20px; color: #161a1d; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- BARRA LATERAL PARA NAVEGACIÓN ---
with st.sidebar:
  st.markdown("### 🧭 Menú de Navegación")
  if st.button("🏠 Volver al Menú Principal", use_container_width=True):
    st.switch_page("app.py")
  st.markdown("---")

# Control de sesión para autenticación
if "autenticado_admin" not in st.session_state:
  st.session_state.autenticado_admin = False

if "unidad_anterior" not in st.session_state:
  st.session_state.unidad_anterior = ""
if "config_direccion_base" not in st.session_state:
  st.session_state.config_direccion_base = (
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
      },
      "CHURUBUSCO": {
          "sigla": "CHU",
          "dir": (
              "Calzada de Tlalpan 4430, Toriello Guerra, Tlalpan, 14050 Ciudad"
              " de México, CDMX"
          ),
      },
      "CLIDDA": {
          "sigla": "CLI",
          "dir": (
              "San Fernando 15, Toriello Guerra, Tlalpan, 14050 Ciudad de"
              " México, CDMX"
          ),
      },
      "COYOACAN": {
          "sigla": "COY",
          "dir": (
              "Avenida Cuauhtémoc 330, Del Carmen, Coyoacán, 04100 Ciudad de"
              " México, CDMX"
          ),
      },
      "DEL VALLE": {
          "sigla": "DVA",
          "dir": (
              "Cacho 35, Del Valle Norte, Benito Juárez, 03103 Ciudad de México,"
              " CDMX"
          ),
      },
      "DIVISION DEL NORTE": {
          "sigla": "DVN",
          "dir": (
              "Avenida División del Norte 3233, Xoco, Benito Juárez, 03330"
              " Ciudad de México, CDMX"
          ),
      },
      "DR. DARIO FERNANDEZ FIERRO": {
          "sigla": "DFF",
          "dir": (
              "Avenida Revolución 1182, Tlacopac, Álvaro Obregón, 01049 Ciudad de"
              " México, CDMX"
          ),
      },
      "DR. IGNACIO CHAVEZ": {
          "sigla": "ICH",
          "dir": (
              "Eje 1 Poniente Av. Cuauhtémoc s/n, Doctores, Cuauhtémoc, 06720"
              " Ciudad de México, CDMX"
          ),
      },
      "ERMITA": {
          "sigla": "ERM",
          "dir": (
              "Ermita Iztapalapa 67, Ermita, Benito Juárez, 03590 Ciudad de"
              " México, CDMX"
          ),
      },
      "FUENTES BROTANTES": {
          "sigla": "FBR",
          "dir": (
              "Fuentes Brotantes s/n, Fuentes Brotantes, Tlalpan, 14410 Ciudad de"
              " México, CDMX"
          ),
      },
      "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA": {
          "sigla": "MPM",
          "dir": (
              "Avenida Tláhuac s/n, San Lorenzo Tezonco, Iztapalapa, 13266 Ciudad"
              " de México, CDMX"
          ),
      },
      "MILPA ALTA": {
          "sigla": "MIL",
          "dir": (
              "Prolongación Matamoros s/n, Villa Milpa Alta, Milpa Alta, 12000"
              " Ciudad de México, CDMX"
          ),
      },
      "NARVARTE": {
          "sigla": "NAR",
          "dir": (
              "Avenida Cuauhtémoc 625, Narvarte Poniente, Benito Juárez, 03020"
              " Ciudad de México, CDMX"
          ),
      },
      "TLALPAN": {
          "sigla": "TLA",
          "dir": (
              "Calzada de Tlalpan 4800, Toriello Guerra, Tlalpan, 14050 Ciudad de"
              " México, CDMX"
          ),
      },
      "VILLA ALVARO OBREGON": {
          "sigla": "VAO",
          "dir": (
              "Calle 10 s/n, Tolteca, Álvaro Obregón, 01150 Ciudad de México,"
              " CDMX"
          ),
      },
      "XOCHIMILCO": {
          "sigla": "XOC",
          "dir": (
              "Providencia s/n, Barrio San Marcos, Xochimilco, 16050 Ciudad de"
              " México, CDMX"
          ),
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
    st.session_state.config_direccion_base = unidades_issste_data[unidad_sel][
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
      '<div class="section-title">2. Parámetros Independientes por Cédula /'
      " Brigada</div>",
      unsafe_allow_html=True,
  )

  config_jornadas_activas = []

  if not jornadas_simultaneas:
    st.markdown('<div class="card-simultanea">', unsafe_allow_html=True)
    resp_unico = st.text_input(
        "👤 Nombre del responsable de vacunación:",
        placeholder="Escriba el nombre completo...",
    )
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
      f_app = st.date_input(
          "Fecha de Aplicación:",
          value=datetime.date.today(),
          format="DD/MM/YYYY",
          key="f_app_unica",
      )
    with col_f2:
      h_ini = st.time_input(
          "Hora Inicio:", value=datetime.time(8, 0), key="h_ini_unica"
      )
    with col_f3:
      h_fin = st.time_input(
          "Hora Cierre:", value=datetime.time(14, 0), key="h_fin_unica"
      )

    dir_oficial = st.text_area(
        "📍 Dirección Oficial de esta Jornada:",
        value=st.session_state.config_direccion_base,
        height=70,
        key="dir_unica",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    config_jornadas_activas.append({
        "sufijo_hoja": "",
        "sufijo_qr": "",
        "responsable": resp_unico.upper()
        if resp_unico
        else "PERSONAL AUTORIZADO",
        "fecha": f_app,
        "hora_inicio": h_ini,
        "hora_fin": h_fin,
        "direccion": dir_oficial,
    })
  else:
    st.info(
        f"Configurando {num_jornadas} equipos simultáneos con fechas, horarios"
        " y ubicaciones personalizadas:"
    )
    for i in range(1, num_jornadas + 1):
      st.markdown(
          f'<div class="card-simultanea"><h4 style="color: #1e5b4f; margin-top:0;">📋 Cédula / Brigada Simultánea # {i}</h4>',
          unsafe_allow_html=True,
      )
      resp_sim = st.text_input(
          f"👤 Responsable de Brigada #{i}:",
          placeholder=f"Nombre del responsable {i}...",
          key=f"resp_sim_{i}",
      )

      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        f_app_sim = st.date_input(
            f"Fecha de Aplicación #{i}:",
            value=datetime.date.today(),
            format="DD/MM/YYYY",
            key=f"f_app_sim_{i}",
        )
      with col_f2:
        h_ini_sim = st.time_input(
            f"Hora Inicio #{i}:",
            value=datetime.time(8, 0),
            key=f"h_ini_sim_{i}",
        )
      with col_f3:
        h_fin_sim = st.time_input(
            f"Hora Cierre #{i}:",
            value=datetime.time(14, 0),
            key=f"h_fin_sim_{i}",
        )

      dir_sim = st.text_area(
          f"📍 Dirección Oficial para Brigada #{i}:",
          value=st.session_state.config_direccion_base,
          height=70,
          key=f"dir_sim_{i}",
      )
      st.markdown("</div>", unsafe_allow_html=True)

      config_jornadas_activas.append({
          "sufijo_hoja": f"_JS{i}",
          "sufijo_qr": f"_JS{i}",
          "responsable": resp_sim.upper()
          if resp_sim
          else f"RESPONSABLE JS{i}",
          "fecha": f_app_sim,
          "hora_inicio": h_ini_sim,
          "hora_fin": h_fin_sim,
          "direccion": dir_sim,
      })

  st.markdown(
      '<div class="section-title">3. Generador de Enlaces y Códigos QR'
      " (Simultáneos)</div>",
      unsafe_allow_html=True,
  )

  base_url = "https://medprev-vacunas-invernal.streamlit.app/"

  for idx, j_conf in enumerate(config_jornadas_activas, start=1):
    fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
    resp_encoded = urllib.parse.quote(j_conf["responsable"])
    link_generado = f"{base_url}?modo=registro&unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}&js={j_conf['sufijo_qr']}"

    titulo_seccion_qr = (
        f"🔗 Enlace y QR para Cédula / Brigada {j_conf['sufijo_hoja']}"
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

      for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        nombre_prueba = (
            f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
        )
        if nombre_prueba in hojas_existentes:
          duplicadas_detectadas.append(nombre_prueba)

      if duplicadas_detectadas:
        st.error(
            "⚠️ ALERTA: Las siguientes hojas ya existen en Google Sheets:"
            f" {', '.join(duplicadas_detectadas)}"
        )
        st.warning(
            "Ya existe una jornada creada con esta misma nomenclatura y fecha."
            " Verifique los datos o cambie la fecha/sufijo."
        )
      else:
        hojas_creadas_exito = []
        for j_conf in config_jornadas_activas:
          fecha_str_hoja = j_conf["fecha"].strftime("%d%m%y")
          nombre_nueva_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_hoja}"

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

          fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")

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
