import datetime
import json
import urllib.parse
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID, aplicar_configuracion_global
from google.oauth2 import service_account
import gspread
import streamlit as st
import streamlit.components.v1 as components

aplicar_configuracion_global("Guía CENSIA y Consulta Operativa", "📋")

# --- BOTÓN DE RETORNO AL MENÚ PRINCIPAL ---
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav1:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

if "lote_influenza_memoria" not in st.session_state:
    st.session_state.lote_influenza_memoria = ""
if "lote_covid_memoria" not in st.session_state:
    st.session_state.lote_covid_memoria = ""

if "autenticado_consulta" not in st.session_state:
    st.session_state.autenticado_consulta = False

if "ultimo_comprobante_vacunacion" not in st.session_state:
    st.session_state.ultimo_comprobante_vacunacion = None


@st.dialog("🎉 ¡VACUNACIÓN REGISTRADA - COMPROBANTE OFICIAL!")
def mostrar_modal_comprobante_vacunacion():
    p = st.session_state.ultimo_comprobante_vacunacion
    if p:
        nombre_val = p.get("nombre", "PACIENTE")
        folio_val = p.get("folio", "S/F")
        dosis_val = p.get("dosis_str", "N/A")
        lotes_val = p.get("lotes_str", "N/A")
        fecha_val = p.get("fecha_hora", datetime.datetime.now().strftime("%d/%m/%Y")).split()[0]

        html_comprobante_component = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .card-comprobante {{ 
                position: relative; 
                background-color: #ffffff; 
                border: 3px solid #1e5b4f; 
                padding: 15px; 
                border-radius: 10px; 
                color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                margin-bottom: 10px; 
                overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.95rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin-top: 0; margin-bottom: 8px; z-index: 2; position: relative; }}
            .folio-grande {{ font-size: 1.10rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 6px; border-radius: 6px; border: 2px dashed #a57f2c; margin: 8px 0 4px 0; z-index: 2; position: relative; }}
            .info-text {{ margin: 4px 0; font-size: 0.82rem; z-index: 2; position: relative; }}
            
            .watermark-overlay {{
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                transform: rotate(-25deg);
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                align-items: center;
                pointer-events: none;
                z-index: 0;
                overflow: hidden;
            }}
            .watermark-row {{
                display: flex;
                gap: 40px;
                white-space: nowrap;
                font-size: 1.05rem;
                font-weight: 900;
                color: transparent;
                -webkit-text-stroke: 1px rgba(30, 91, 79, 0.12);
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            .watermark-row:nth-child(even) {{
                transform: translateX(-40px);
            }}
            
            .btn-container {{ display: flex; gap: 8px; }}
            .btn {{ flex: 1; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; box-sizing: border-box; }}
            .btn-wa {{ background-color: #25D366; color: white; }}
            .btn-img {{ background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="watermark-overlay">
                    <div class="watermark-row">
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                        <span>COMPROBANTE DE VACUNACION OFICIAL</span>
                    </div>
                </div>
                <div class="titulo-ticket">COMPROBANTE DE VACUNACIÓN - VIGILE</div>
                <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                <p class="info-text"><b>Dosis Aplicadas:</b> {dosis_val}</p>
                <p class="info-text"><b>Lotes Registrados:</b> {lotes_val}</p>
                <p class="info-text"><b>Fecha de Aplicación:</b> {fecha_val}</p>
                <div class="folio-grande">Folio: {folio_val}</div>
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
                        const file = new File([blob], 'Comprobante_Vacunacion_{folio_val}.png', {{ type: 'image/png' }});
                        const textoMensaje = `💉 *COMPROBANTE DE VACUNACIÓN - VIGILE*\\nPaciente: {nombre_val}\\nFolio: *{folio_val}*\\nDosis: {dosis_val}\\nLotes: {lotes_val}\\nFecha: {fecha_val}\\n✅ Aplicación registrada con éxito.`;
                        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                            navigator.share({{ files: [file], title: 'Comprobante de Vacunación', text: textoMensaje }}).catch(error => console.log('Error', error));
                        }} else {{
                            const enlace = document.createElement('a');
                            enlace.download = 'Comprobante_Vacunacion_{folio_val}.png';
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
                    enlace.download = 'Comprobante_Vacunacion_{folio_val}.png';
                    enlace.href = canvas.toDataURL('image/png');
                    enlace.click();
                }});
            }}
            </script>
        </body>
        </html>
        """

        components.html(html_comprobante_component, height=310)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Cerrar Comprobante", use_container_width=True):
            st.session_state.ultimo_comprobante_vacunacion = None
            st.rerun()


if st.session_state.ultimo_comprobante_vacunacion is not None:
    mostrar_modal_comprobante_vacunacion()

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

        todas_las_hojas = spreadsheet.worksheets()
        h_autorizadas = [
            h.title for h in todas_las_hojas if h.title != "CENSO NOMINAL"
        ]

    except Exception as e:
        h_autorizadas = []
        st.error(f"Error al conectar con Google Sheets para listar jornadas: {e}")

    # --- CARGAR GUÍA CENSIA DESDE EL GOOGLE SHEETS DE REFERENCIA ---
    guia_covid_dict = {}
    guia_influenza_dict = {}
    try:
        sheet_censia_id = "1IevzrgHyvixoPfH0c1OWExekc1pSHYB7FcK5SIe5SqU"
        doc_censia = client.open_by_key(sheet_censia_id)

        ws_covid = doc_censia.worksheet("COVID")
        datos_covid = ws_covid.get_all_values()
        for row in datos_covid[1:]:
            if len(row) >= 3:
                cat_b = row[1].strip().upper()
                desc_c = row[2].strip()
                if cat_b:
                    guia_covid_dict[cat_b] = desc_c

        ws_influenza = doc_censia.worksheet("INFLUENZA")
        datos_influenza = ws_influenza.get_all_values()
        for row in datos_influenza[1:]:
            if len(row) >= 3:
                cat_b = row[1].strip().upper()
                desc_c = row[2].strip()
                if cat_b:
                    guia_influenza_dict[cat_b] = desc_c
    except Exception as e:
        pass

    st.markdown(
        '<div class="section-title">1. Jornada Operativa Activa</div>',
        unsafe_allow_html=True,
    )

    params_url = st.query_params
    hoja_enlace = params_url.get("hoja_activa", "")

    if hoja_enlace:
        hoja_seleccionada = hoja_enlace
        st.success(
            f"🔒 Jornada asignada y bloqueada por enlace institucional: "
            f"<b>{hoja_seleccionada}</b>",
            icon="🔒",
        )
    else:
        if not h_autorizadas:
            st.warning(
                "⚠️ No hay jornadas autorizadas activas en Google Sheets. Solicite al"
                " administrador que genere una hoja desde el Panel de Control."
            )
            hoja_seleccionada = None
        else:
            hoja_sel_manual = st.selectbox(
                "Seleccione la Hoja / Jornada Autorizada:",
                options=["Seleccione una jornada..."] + h_autorizadas,
            )
            hoja_seleccionada = (
                hoja_sel_manual
                if hoja_sel_manual != "Seleccione una jornada..."
                else None
            )

    if hoja_seleccionada:
        try:
            try:
                worksheet_activa = spreadsheet.worksheet(hoja_seleccionada)
            except:
                worksheet_activa = spreadsheet.worksheet("CENSO NOMINAL")

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
            query_busqueda = st.text_input(
                "🔍 Buscar por Folio, Apellido o Nombre:",
                placeholder="Escriba parte del folio, apellido o nombre...",
                key="input_busqueda_lupa",
            )

            if not query_busqueda.strip():
                st.info(
                    "ℹ️ Escriba en la lupa de búsqueda para localizar rápidamente a un"
                    " paciente."
                )
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

                if not pacientes_filtrados:
                    st.warning(
                        "No se encontraron pacientes que coincidan con la búsqueda."
                    )
                else:
                    opciones_busqueda = [
                        f"{p['folio']} - {p['paterno']} {p['materno']}, {p['nombres']}||{p['fila']}"
                        for p in pacientes_filtrados
                    ]

                    seleccion_paciente = st.selectbox(
                        "Seleccione del listado de coincidencias:",
                        options=opciones_busqueda,
                        format_func=lambda x: x.split("||")[0],
                    )

                    if seleccion_paciente:
                        fila_idx = int(seleccion_paciente.split("||")[1])
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
                            "S": "PERSONAS GESTANTES",
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
                            st.markdown(f"**Registro Base:** Activo")

                        st.markdown(
                            '<div class="section-title">3. Guía y Lineamientos'
                            " CENSIA</div>",
                            unsafe_allow_html=True,
                        )

                        desc_covid_censia = "Lineamiento no especificado en plantilla."
                        desc_influenza_censia = "Lineamiento no especificado en plantilla."

                        g_upper = grupo_detectado.upper()
                        for k, v in guia_covid_dict.items():
                            if (
                                g_upper in k
                                or k in g_upper
                                or ("6 A 59" in g_upper and "6 A 59" in k)
                                or ("60" in g_upper and "60" in k)
                                or ("GESTANTES" in g_upper and "GESTANTES" in k)
                                or ("SALUD" in g_upper and "SALUD" in k)
                            ):
                                desc_covid_censia = v
                                break

                        for k, v in guia_influenza_dict.items():
                            if (
                                g_upper in k
                                or k in g_upper
                                or ("6 A 59" in g_upper and "59 MESES" in k)
                                or ("60" in g_upper and "60" in k)
                                or ("GESTANTES" in g_upper and "GESTANTES" in k)
                                or ("SALUD" in g_upper and "SALUD" in k)
                            ):
                                desc_influenza_censia = v
                                break

                        st.markdown(
                            f"""
                            <div class="card-recomendacion" style="background-color: #f7f4eb; border-left: 5px solid #1e5b4f; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                                <h4 style="color: #1e5b4f; margin-top: 0;">💉 Guía para Influenza Estacional</h4>
                                <p><b>Grupo:</b> {grupo_detectado}</p>
                                <p><b>Lineamiento CENSIA:</b> {desc_influenza_censia}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"""
                            <div class="card-recomendacion" style="background-color: #f7f4eb; border-left: 5px solid #611232; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                                <h4 style="color: #611232; margin-top: 0;">🦠 Guía para COVID-19</h4>
                                <p><b>Grupo:</b> {grupo_detectado}</p>
                                <p><b>Lineamiento CENSIA:</b> {desc_covid_censia}</p>
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
                            c_cov1, c_cov2, c_cov3, c_cov4 = st.columns(4)
                            with c_cov1:
                                cov_1ra = st.checkbox("COVID 1ra dosis")
                            with c_cov2:
                                cov_2da = st.checkbox("COVID 2da dosis")
                            with c_cov3:
                                cov_anual = st.checkbox("COVID Dosis anual")
                            with c_cov4:
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
                                        st.session_state.lote_covid_memoria = (
                                            lote_cov_input.upper()
                                        )

                                    f_actual = fila_idx
                                    f_siguiente = fila_idx + 1

                                    dosis_aplicadas_lista = []

                                    # --- INFLUENZA ---
                                    if inf_1ra:
                                        worksheet_activa.update(f"AG{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AG{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("Influenza (1ra Dosis)")
                                    if inf_2da:
                                        worksheet_activa.update(f"AH{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AH{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("Influenza (2da Dosis)")
                                    if inf_anual:
                                        worksheet_activa.update(f"AI{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AI{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("Influenza (Dosis Anual)")

                                    # --- COVID ---
                                    if cov_1ra:
                                        worksheet_activa.update(f"AJ{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AJ{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("COVID-19 (1ra Dosis)")
                                    if cov_2da:
                                        worksheet_activa.update(f"AK{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AK{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("COVID-19 (2da Dosis)")
                                    if cov_anual:
                                        worksheet_activa.update(f"AL{f_actual}", [["X"]])
                                        worksheet_activa.update(f"AL{f_siguiente}", [["X"]])
                                        dosis_aplicadas_lista.append("COVID-19 (Dosis Anual)")

                                    # --- LOTES ---
                                    lote_final_str = ""
                                    if lote_inf_input and lote_cov_input:
                                        lote_final_str = f"{lote_inf_input.upper()} / {lote_cov_input.upper()}"
                                    elif lote_inf_input:
                                        lote_final_str = lote_inf_input.upper()
                                    elif lote_cov_input:
                                        lote_final_str = lote_cov_input.upper()

                                    if lote_final_str:
                                        worksheet_activa.update(f"AM{f_actual}", [[lote_final_str]])
                                        worksheet_activa.update(f"AM{f_siguiente}", [[lote_final_str]])

                                    dosis_str = ", ".join(dosis_aplicadas_lista) if dosis_aplicadas_lista else "Ninguna seleccionada"
                                    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")

                                    st.session_state.ultimo_comprobante_vacunacion = {
                                        "nombre": nombre_completo,
                                        "folio": folio_p,
                                        "dosis_str": dosis_str,
                                        "lotes_str": lote_final_str if lote_final_str else "N/A",
                                        "fecha_hora": fecha_actual
                                    }
                                    st.rerun()

                                except Exception as e:
                                    st.error(
                                        "Error al actualizar la base de datos en Google"
                                        f" Sheets: {e}"
                                    )
