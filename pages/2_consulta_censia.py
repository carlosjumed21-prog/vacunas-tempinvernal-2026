import streamlit as st

st.set_page_config(
    page_title="Guía CENSIA y Consulta",
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
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="main-header">Módulo de Búsqueda y Guía Clínica CENSIA</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Evaluación automatizada de esquemas y registro de dosis aplicada</p>', unsafe_allow_html=True)

if "registros_censales" not in st.session_state or not st.session_state.registros_censales:
    st.info("No hay pacientes registrados en la sesión actual. Registre al menos un paciente en el formulario principal.")
else:
    lista_folios_nombres = [f"{p['folio']} - {p['nombre_completo']}" for p in st.session_state.registros_censales]
    seleccion_busqueda = st.selectbox("Seleccione o busque un paciente registrado:", options=lista_folios_nombres)

    if seleccion_busqueda:
        folio_seleccionado = seleccion_busqueda.split(" - ")[0]
        paciente = next(p for p in st.session_state.registros_censales if p["folio"] == folio_seleccionado)

        st.markdown('<div class="section-title">Datos Generales del Paciente</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Folio:** {paciente['folio']}")
            st.markdown(f"**Nombre:** {paciente['nombre_completo']}")
        with col2:
            st.markdown(f"**Nacimiento:** {paciente['fecha_nacimiento'].strftime('%d/%m/%Y')}")
            st.markdown(f"**Edad:** {paciente['edad_anos']} AÑOS, {paciente['edad_meses']} MESES")
        with col3:
            st.markdown(f"**Sexo:** {paciente['sexo']}")
            st.markdown(f"**Grupo Objetivo:** {paciente['grupo_objetivo']}")

        # Lógica de Recomendaciones CENSIA
        edad_m = paciente["edad_total_meses"]
        anos = paciente["edad_anos"]
        es_embarazada = paciente["embarazo"]
        es_personal_salud = paciente["personal_salud"]
        comorb = paciente["tiene_comorbilidades"]
        ant_inf = paciente["antecedente_influenza"]
        ant_cov = paciente["antecedente_covid"]

        # Influenza
        if 6 <= edad_m <= 59:
            inf_dosis = "1 dosis anual de 0.5 mL." if ant_inf == "SÍ" else "2 dosis de 0.5 mL (intervalo de 4 semanas)."
            inf_via = "Intramuscular en muslo izquierdo (menores de 18m) o deltoides izquierdo (a partir de 18m)."
        elif anos >= 60 or es_embarazada or es_personal_salud or comorb:
            inf_dosis = "1 dosis anual de 0.5 mL."
            inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
        else:
            inf_dosis = "Población fuera de grupo prioritario estricto."
            inf_via = "Valorar disponibilidad."

        # COVID-19
        if 5 <= anos <= 11 and comorb:
            cov_dosis = "Dosis única de 0.25 mL de **Spikevax LP.8.1**, vía intramuscular en deltoides derecho."
        elif 12 <= anos <= 59 and (comorb or es_personal_salud or es_embarazada):
            cov_dosis = "Refuerzo con Opción A (**Spikevax LP.8.1**: 0.5 mL IM) o B (**Comirnaty LP.8.1**: 0.3 mL IM)."
        elif anos >= 60:
            cov_dosis = "Dosis única de refuerzo (Spikevax o Comirnaty según disponibilidad) vía intramuscular."
        else:
            cov_dosis = "Población general sin comorbilidades de alto riesgo para refuerzo estacional actual."

        st.markdown(
            f"""
            <div class="card-recomendacion">
                <h4>💉 1. Recomendación para Influenza Estacional</h4>
                <p><b>Antecedente reportado:</b> {ant_inf}</p>
                <p><b>Esquema / Dosis:</b> {inf_dosis}</p>
                <p><b>Vía y Sitio:</b> {inf_via}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="card-recomendacion">
                <h4>🦠 2. Recomendación para COVID-19 (LP.8.1)</h4>
                <p><b>Antecedente reportado:</b> {ant_cov}</p>
                <p><b>Esquema / Dosis:</b> {cov_dosis}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Registro de aplicación
        st.markdown('<div class="section-title">Registro de Lotes y Dosis Administradas (Día)</div>', unsafe_allow_html=True)
        with st.form("form_aplicacion"):
            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                lote_inf = st.text_input("No. de Lote - Influenza")
            with col_inf2:
                lote_cov = st.text_input("No. de Lote - COVID-19")

            biologico = st.radio("¿Qué biológico(s) se aplicó?", ["Ninguno", "Solo Influenza", "Solo COVID-19", "Ambos (Simultáneos)"])
            btn_conf = st.form_submit_button("Confirmar aplicación del día", use_container_width=True)

            if btn_conf:
                if biologico != "Ninguno":
                    st.success(f"¡Aplicación registrada con éxito para {paciente['nombre_completo']} ({biologico})!")
                else:
                    st.warning("Se guardó la evaluación sin aplicación.")
