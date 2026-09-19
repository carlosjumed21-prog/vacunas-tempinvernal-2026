import datetime
import json
import urllib.parse
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Guía CENSIA y Consulta Operativa",
    page_icon="📋",
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
        .card-recomendacion { background-color: #ffffff; border-left: 6px solid #1e5b4f; padding: 18px; border-radius: 6px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); font-size: 1.1rem !important; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
        input[type="text"] { text-transform: uppercase !important; }
    </style>
""",
    unsafe_allow_html=True,
)

if "lote_influenza_memoria" not in st.session_state:
  st.session_state.lote_influenza_memoria = ""
if "lote_covid_memoria" not in st.session_state:
  st.session_state.lote_covid_memoria = ""

if "autenticado_consulta" not in st.session_state:
  st.session_state.autenticado_consulta = False

if not st.session_state.autenticado_consulta:
  st.markdown(
      '<p class="main-header">Acceso Restringido - Módulo Operativo CENSIA</p>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<p class="sub-header">Ingrese sus credenciales operativas</p>',
      unsafe_allow_html=True,
  )

  with st.form("form_login_consulta"):
    usuario = st.selectbox(
        "Seleccione Usuario:", options=["Seleccione...", "Operativo"]
    )
    password = st.text_input("Contraseña:", type="password")
    btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)

    if btn_login:
      if usuario == "Operativo" and password == "Operativo":
        st.session_state.autenticado_consulta = True
        st.rerun()
      else:
        st.error("Credenciales incorrectas. Verifique usuario y contraseña.")
else:
  st.markdown(
      '<p class="main-header">Módulo Operativo de Aplicación y Guía CENSIA</p>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<p class="sub-header">Selección de jornada autorizada, evaluación'
      " clínica y registro de biológicos</p>",
      unsafe_allow_html=True,
  )

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

    todas_las_hojas = spreadsheet.worksheets()
    h_autorizadas = [
        h.title for h in todas_las_hojas if h.title != "CENSO NOMINAL"
    ]

  except Exception as e:
    h_autorizadas = []
    st.error(f"Error al conectar con Google Sheets para listar jornadas: {e}")

  if not h_autorizadas:
    st.warning(
        "⚠️ No hay jornadas autorizadas activas en Google Sheets. Solicite al"
        " administrador que genere una hoja desde el Panel de Control."
    )
  else:
    st.markdown(
        '<div class="section-title">1. Selección de Jornada Activa</div>',
        unsafe_allow_html=True,
    )
    hoja_seleccionada = st.selectbox(
        "Seleccione la Hoja / Jornada Autorizada:", options=h_autorizadas
    )

    if hoja_seleccionada:
      try:
        worksheet_activa = spreadsheet.worksheet(hoja_seleccionada)
        todos_los_datos = worksheet_activa.get_all_values()

        pacientes_cargados = []
        if len(todos_los_datos) >= 13:
          for idx, row in enumerate(todos_los_datos[12:], start=13):
            if len(row) > 3 and row[1].strip() and row[2].strip():
              pacientes_cargados.append({
                  "fila": idx,
                  "folio": row[1].strip(),
                  "paterno": row[2].strip(),
                  "materno": row[3].strip() if len(row) > 3 else "",
                  "nombres": row[4].strip() if len(row) > 4 else "",
              })

      except Exception as e:
        pacientes_cargados = []
        st.error(f"Error al leer los datos de la hoja {hoja_seleccionada}: {e}")

      st.markdown(
          '<div class="section-title">2. Lupa de Búsqueda Rápida</div>',
          unsafe_allow_html=True,
      )
      if not pacientes_cargados:
        st.info(
            "La jornada seleccionada aún no cuenta con pacientes registrados en"
            " el censo."
        )
      else:
        # Lupa interactiva que inicia vacía y sin mostrar resultados hasta que se escriba algo
        query_busqueda = st.text_input(
            "🔍 Buscar por Folio, Apellido o Nombre:",
            placeholder="Escriba parte del folio o apellido...",
        )

        if not query_busqueda.strip():
          st.info(
              "ℹ️ Ingrese un término en la lupa de búsqueda para localizar a"
              " un paciente."
          )
          pacientes_filtrados = []
        else:
          q_clean = query_busqueda.strip().upper()
          pacientes_filtrados = [
              p
              for p in pacientes_cargados
              if q_clean in p["folio"].upper()
              or q_clean in p["paterno"].upper()
              or q_clean in p["materno"].upper()
              or q_clean in p["nombres"].upper()
          ]

        if query_busqueda.strip() and not pacientes_filtrados:
          st.warning(
              "No se encontraron pacientes que coincidan con la búsqueda."
          )
        elif pacientes_filtrados:
          opciones_busqueda = [
              f"{p['folio']} - {p['paterno']} {p['materno']}, {p['nombres']} (Fila {p['fila']})"
              for p in pacientes_filtrados
          ]
          seleccion_paciente = st.selectbox(
              "Seleccione del listado de coincidencias:",
              options=opciones_busqueda,
          )

          if seleccion_paciente:
            fila_idx = int(
                seleccion_paciente.split("(Fila ")[1].replace(")", "")
            )
            fila_datos = todos_los_datos[fila_idx - 1]

            folio_p = fila_datos[1] if len(fila_datos) > 1 else ""
            paterno_p = fila_datos[2] if len(fila_datos) > 2 else ""
            materno_p = fila_datos[3] if len(fila_datos) > 3 else ""
            nombres_p = fila_datos[4] if len(fila_datos) > 4 else ""
            nombre_completo = f"{paterno_p} {materno_p}, {nombres_p}"

            dd_n = fila_datos[5] if len(fila_datos) > 5 else "01"
            mm_n = fila_datos[6] if len(fila_datos) > 6 else "01"
            yy_n = fila_datos[7] if len(fila_datos) > 7 else "2000"
            fecha_nac_str = f"{dd_n}/{mm_n}/{yy_n}"

            sexo_p = fila_datos[10] if len(fila_datos) > 10 else "H"
            sexo_texto = "HOMBRE" if sexo_p == "H" else "MUJER"

            grupos_letras = {
                "P": "6 A 59 MESES",
                "Q": "60 Y MÁS",
                "R": "5 A 11 AÑOS (COVID-19)",
                "S": "EMBARAZADAS",
                "T": "PERSONAL DE SALUD",
                "U": "VIH/sida",
                "V": "DIABETES MELLITUS",
                "W": "OBESIDAD MORBIDA",
                "X": "CARDIOPATÍAS AGUDAS O CRÓNICAS",
            }
            grupo_detectado = "POBLACIÓN GENERAL"
            col_indices = {
                "P": 15,
                "Q": 16,
                "R": 17,
                "S": 18,
                "T": 19,
                "U": 20,
                "V": 21,
                "W": 22,
                "X": 23,
            }
            for letra, idx_col in col_indices.items():
              if (
                  len(fila_datos) > idx_col
                  and fila_datos[idx_col].strip().upper() == "X"
              ):
                grupo_detectado = grupos_letras[letra]
                break

            st.markdown(
                '<div class="section-title">Vista Previa y Datos Generales'
                " del Paciente</div>",
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns(3)
            with col1:
              st.markdown(f"**Folio:** {folio_p}")
              st.markdown(f"**Nombre:** {nombre_completo}")
            with col2:
              st.markdown(f"**Nacimiento:** {fecha_nac_str}")
              st.markdown(f"**Sexo:** {sexo_texto}")
            with col3:
              st.markdown(f"**Grupo Objetivo:** {grupo_detectado}")
              st.markdown(f"**Fila en Sheets:** #{fila_idx}")

            st.markdown(
                '<div class="section-title">3. Guía y Lineamientos CENSIA</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="card-recomendacion">
                    <h4>💉 Guía para Influenza Estacional</h4>
                    <p><b>Esquema sugerido:</b> 1 dosis anual de 0.5 mL (Aplicación recomendada estacional).</p>
                    <p><b>Vía y Sitio:</b> Intramuscular en región deltoidea del brazo izquierdo.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="card-recomendacion">
                    <h4>🦠 Guía para COVID-19</h4>
                    <p><b>Esquema sugerido:</b> Refuerzo o dosis estacional actual según disponibilidad autorizada.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="section-title">4. Registro de Dosis Aplicadas y'
                " Lotes (Actualización en Base de Datos)</div>",
                unsafe_allow_html=True,
            )

            with st.form("form_aplicacion_lotes"):
              st.markdown("##### 💉 INFLUENZA")
              c_inf1, c_inf2, c_inf3, c_inf4 = st.columns(4)
              with c_inf1:
                inf_1ra = st.checkbox("1ra dosis")
              with c_inf2:
                inf_2da = st.checkbox("2da dosis")
              with c_inf3:
                inf_anual = st.checkbox("Dosis anual")
              with c_inf4:
                lote_inf_input = st.text_input(
                    "Lote Influenza",
                    value=st.session_state.lote_influenza_memoria,
                    placeholder="Ej. A1234",
                )

              st.markdown("##### 🦠 COVID-19")
              c_cov1, c_cov2, c_cov3 = st.columns(3)
              with c_cov1:
                cov_unica = st.checkbox("Dosis Única")
              with c_cov2:
                cov_refuerzo = st.checkbox("Refuerzo")
              with c_cov3:
                lote_cov_input = st.text_input(
                    "Lote COVID-19",
                    value=st.session_state.lote_covid_memoria,
                    placeholder="Ej. C5678",
                )

              btn_actualizar_dosis = st.form_submit_button(
                  "💾 Guardar Aplicación y Actualizar Hoja Sheets",
                  use_container_width=True,
              )

              if btn_actualizar_dosis:
                try:
                  if lote_inf_input:
                    st.session_state.lote_influenza_memoria = (
                        lote_inf_input.upper()
                    )
                  if lote_cov_input:
                    st.session_state.lote_covid_memoria = lote_cov_input.upper()

                  f_actual = fila_idx
                  f_siguiente = fila_idx + 1

                  if inf_1ra:
                    worksheet_activa.update(
                        f"AF{f_actual}:AF{f_siguiente}", [["X"], ["X"]]
                    )
                  if inf_2da:
                    worksheet_activa.update(
                        f"AG{f_actual}:AG{f_siguiente}", [["X"], ["X"]]
                    )
                  if inf_anual:
                    worksheet_activa.update(
                        f"AH{f_actual}:AH{f_siguiente}", [["X"], ["X"]]
                    )
                  if lote_inf_input:
                    worksheet_activa.update(
                        f"AI{f_actual}:AI{f_siguiente}",
                        [[lote_inf_input.upper()], [lote_inf_input.upper()]],
                    )

                  if cov_unica:
                    worksheet_activa.update(
                        f"AJ{f_actual}:AJ{f_siguiente}", [["X"], ["X"]]
                    )
                  if cov_refuerzo:
                    worksheet_activa.update(
                        f"AK{f_actual}:AK{f_siguiente}", [["X"], ["X"]]
                    )
                  if lote_cov_input:
                    worksheet_activa.update(
                        f"AL{f_actual}:AL{f_siguiente}",
                        [[lote_cov_input.upper()], [lote_cov_input.upper()]],
                    )

                  st.success(
                      f"✅ ¡Aplicación registrada y base actualizada con éxito"
                      f" para {nombre_completo} en la hoja"
                      f" {hoja_seleccionada}!"
                  )

                except Exception as e:
                  st.error(
                      "Error al actualizar la base de datos en Google Sheets:"
                      f" {e}"
                  )
