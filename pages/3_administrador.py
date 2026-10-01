import datetime
import io
import json
import urllib.parse
from config import (
    GOOGLE_SCOPES,
    GOOGLE_SHEET_ID,
    UNIDADES_ISSSTE,
    aplicar_configuracion_global,
)
from google.oauth2 import service_account
import gspread
import qrcode
import streamlit as st

aplicar_configuracion_global("Panel de Administración - Censo Nominal", "⚙️")

col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
  if st.button("🚪 Cerrar Sesión de Administrador", use_container_width=True):
    st.session_state.autenticado_admin = False
    st.session_state.jornada_autorizada = False
    st.session_state.hojas_creadas_recientes = []
    st.rerun()
with col_nav2:
  if st.button("🏠 Volver al Menú Principal", use_container_width=True):
    st.switch_page("app.py")

st.markdown("---")

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
if "hojas_creadas_recientes" not in st.session_state:
  st.session_state.hojas_creadas_recientes = []

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
  # TÍTULO PRINCIPAL DESTACADO
  st.markdown(
      '<p class="main-header">Panel de Control y Administración</p>',
      unsafe_allow_html=True,
  )

  st.markdown(
      '<div class="section-title" style="font-size: 1.4rem; font-weight: 800;'
      ' color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem;'
      ' border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">1.'
      ' Configuración de Operación y Unidad</div>',
      unsafe_allow_html=True,
  )

  col_c1, col_c2 = st.columns(2)
  with col_c1:
    unidad_sel = st.selectbox(
        "Unidad Médica ISSSTE:", options=list(UNIDADES_ISSSTE.keys())
    )
    siglas_unidad = (
        UNIDADES_ISSSTE[unidad_sel]["sigla"]
        if unidad_sel in UNIDADES_ISSSTE
        else ""
    )

  with col_c2:
    jornada_sel = st.selectbox(
        "Tipo de Jornada:",
        options=["Seleccione tipo...", "Intramuros I", "Extramuros E"],
    )
    tipo_jornada_letra = (
        "I"
        if "Intramuros" in jornada_sel
        else ("E" if "Extramuros" in jornada_sel else "")
    )
    tipo_jornada_texto = (
        "INTRA"
        if tipo_jornada_letra == "I"
        else ("EXTRA" if tipo_jornada_letra == "E" else "")
    )

  if (
      unidad_sel != "Seleccione una unidad médica..."
      and st.session_state.unidad_anterior != unidad_sel
  ):
    st.session_state.unidad_anterior = unidad_sel
    st.session_state.config_direccion_base = UNIDADES_ISSSTE[unidad_sel]["dir"]
    st.rerun()

  if (
      unidad_sel == "Seleccione una unidad médica..."
      or jornada_sel == "Seleccione tipo..."
  ):
    st.warning(
        "⚠️ Por favor seleccione una Unidad Médica y un Tipo de Jornada válidos"
        " para habilitar la configuración."
    )
  else:
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
        '<div class="section-title" style="font-size: 1.4rem; font-weight: 800;'
        ' color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem;'
        ' border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">2.'
        " Parámetros Independientes por Cédula / Brigada</div>",
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
          "responsable": resp_unico.upper() if resp_unico else "PERSONAL",
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
            f'<div class="card-simultanea"><h4 style="color: #1e5b4f;'
            f' margin-top:0;">📋 Cédula / Brigada Simultánea # {i}</h4>',
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

    st.markdown("<br>", unsafe_allow_html=True)

    # --- BOTÓN DE AUTORIZACIÓN Y DUPLICACIÓN EN GOOGLE SHEETS (UBICADO ARRIBA) ---
    if st.button(
        "🚀 Autorizar Jornada(s) y Generar Hoja(s) en Google Sheets",
        use_container_width=True,
    ):
      try:
        scope = GOOGLE_SCOPES

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

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

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

            hojas_creadas_exito.append({
                "nombre": nombre_nueva_hoja,
                "gid": str(hoja_activa.id),
            })

          st.session_state.jornada_autorizada = True
          st.session_state.hojas_creadas_recientes = hojas_creadas_exito
          st.success(
              "¡Jornadas autorizadas y hojas generadas con éxito en Google"
              " Sheets!"
          )

      except Exception as e:
        st.error(
            "Error al configurar Google Sheets. Asegúrate de que la hoja 'CENSO"
            " NOMINAL' exista y que el correo de servicio tenga permisos de"
            f" Editor. Detalle: {e}"
        )

    # --- RECUADRO VERDE DE CONFIRMACIÓN PERMANENTE ---
    if (
        st.session_state.jornada_autorizada
        and st.session_state.hojas_creadas_recientes
    ):
      st.markdown("<br>", unsafe_allow_html=True)

      enlaces_html = ""
      for h_info in st.session_state.hojas_creadas_recientes:
        url_sheet_directa = f"https://docs.google.com/spreadsheets/d/1TH2KkQzNe4HwBcuJK_QR4gWfQ-wiyAyyczdTmLzn1Ds/edit#gid={h_info['gid']}"
        enlaces_html += f"""
          <div style="margin-bottom: 8px;">
              <a href="{url_sheet_directa}" target="_blank" style="background-color: #1e5b4f; color: white; padding: 8px 16px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block; font-size: 1rem;">
                  🔗 Ver Hoja: {h_info['nombre']}
              </a>
          </div>
        """

      st.markdown(
          f"""
          <div style="background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 18px; border-radius: 8px; margin-top: 15px; text-align: center;">
              <h3 style="color: #1e5b4f; margin-top: 0; margin-bottom: 8px;">🟢 JORNADAS AUTORIZADAS Y ACTIVAS</h3>
              <p style="font-size: 1.05rem; color: #161a1d; margin-bottom: 12px;">
                  Las hojas correspondientes han sido creadas con sus metadatos institucionales y están listas para recibir registros:
              </p>
              {enlaces_html}
          </div>
          """,
          unsafe_allow_html=True,
      )

    # SECCIÓN 3: GENERADOR DE ENLACES Y QR (VISIBLE SIEMPRE DESPUÉS DE SELECCIONAR UNIDAD)
    st.markdown(
        '<div class="section-title" style="font-size: 1.4rem; font-weight: 800;'
        ' color: #1e5b4f; margin-top: 1.5rem; margin-bottom: 0.8rem;'
        ' border-bottom: 2px solid #a57f2c; padding-bottom: 0.4rem;">3.'
        " Generador de Enlaces y Códigos QR (Públicos y Operativos)</div>",
        unsafe_allow_html=True,
    )

    base_url = "https://medprev-vacunas-invernal.streamlit.app/"

    for idx, j_conf in enumerate(config_jornadas_activas, start=1):
      fecha_str_hoja = j_conf["fecha"].strftime("%d%m%y")
      nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_hoja}"
      fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
      resp_encoded = urllib.parse.quote(j_conf["responsable"])

      js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
      link_paciente = f"{base_url}?modo=registro&unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
      link_operativo = f"{base_url}?vista=operativo&hoja_activa={urllib.parse.quote(nombre_hoja_objetivo)}"

      titulo_seccion_qr = (
          f"🔗 Enlaces para Cédula / Brigada {j_conf['sufijo_hoja']}"
          if j_conf["sufijo_hoja"]
          else "🔗 Enlaces Operativos"
      )

      st.markdown(
          f"<h4 style='color: #1e5b4f; margin-top:"
          f" 1.2rem;'>{titulo_seccion_qr}</h4>",
          unsafe_allow_html=True,
      )

      st.markdown("🔹 **Enlace Público para Registro de Pacientes (QR):**")
      st.code(link_paciente, language="text")

      st.markdown(
          "🔹 **Enlace Directo para el Personal Operativo (Abre directo en la"
          " hoja correspondiente):**"
      )
      st.code(link_operativo, language="text")

      qr = qrcode.QRCode(version=1, box_size=10, border=4)
      qr.add_data(link_paciente)
      qr.make(fit=True)
      img = qr.make_image(fill_color="#611232", back_color="#ffffff")

      buf = io.BytesIO()
      img.save(buf, format="PNG")
      byte_im = buf.getvalue()

      col_qr1, col_qr2 = st.columns([1, 2])
      with col_qr1:
        st.image(
            byte_im,
            caption=f"QR de Registro {j_conf['sufijo_hoja']}",
            width=180,
        )
      with col_qr2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label=f"📥 Descargar QR Paciente ({j_conf['sufijo_hoja'] if j_conf['sufijo_hoja'] else 'Principal'})",
            data=byte_im,
            file_name=(
                f"QR_Vacunacion_{siglas_unidad}_{tipo_jornada_letra}{j_conf['sufijo_hoja']}.png"
            ),
            mime="image/png",
            key=f"dl_qr_{idx}",
            use_container_width=True,
        )
      st.markdown("---")
