import datetime
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# Estilo visual limpio y profesional
st.markdown(
    """
    <style>
        .main-header { font-size: 1.8rem; font-weight: 700; color: #1e3d59; margin-bottom: 0.2rem; }
        .sub-header { font-size: 1rem; color: #576574; margin-bottom: 1.5rem; }
        .section-title { font-size: 1.2rem; font-weight: 600; color: #17b978; margin-top: 1.2rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3rem; }
        .card-recomendacion { background-color: #f8fafc; border-left: 5px solid #17b978; padding: 15px; border-radius: 5px; margin-bottom: 15px; }
        .card-alerta { background-color: #fff5f5; border-left: 5px solid #e53e3e; padding: 15px; border-radius: 5px; margin-bottom: 15px; }
    </style>
""",
    unsafe_allow_html=True,
)


def calcular_edad_detallada(fecha_nac, fecha_ref):
    """Calcula la diferencia exacta en años, meses y días entre dos fechas."""
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


# Inicializar la base de datos temporal en memoria (Session State) para almacenar los registros
if "registros_censales" not in st.session_state:
    st.session_state.registros_censales = []

if "navegacion" not in st.session_state:
    st.session_state.navegacion = "Registro"  # Opciones: "Registro" o "Consulta"

estados_mexico = [
    "",
    "Aguascalientes",
    "Baja California",
    "Baja California Sur",
    "Campeche",
    "Chiapas",
    "Chihuahua",
    "Ciudad de México",
    "Coahuila",
    "Colima",
    "Durango",
    "Estado de México",
    "Guanajuato",
    "Guerrero",
    "Hidalgo",
    "Jalisco",
    "Michoacán",
    "Morelos",
    "Nayarit",
    "Nuevo León",
    "Oaxaca",
    "Puebla",
    "Querétaro",
    "Quintana Roo",
    "San Luis Potosí",
    "Sinaloa",
    "Sonora",
    "Tabasco",
    "Tamaulipas",
    "Tlaxcala",
    "Veracruz",
    "Yucatán",
    "Zacatecas",
]

# --- BARRA LATERAL DE NAVEGACIÓN ---
st.sidebar.title("Navegación del Sistema")
opcion_nav = st.sidebar.radio(
    "Seleccione el módulo:",
    ["1. Formulario de Censo Nominal", "2. Módulo de Consulta y Guía CENSIA"],
)

if "1. Formulario" in opcion_nav:
    st.session_state.navegacion = "Registro"
else:
    st.session_state.navegacion = "Consulta"

# ==========================================
# VISTA 1: FORMULARIO DE CAPTURA NOMINAL
# ==========================================
if st.session_state.navegacion == "Registro":
    st.markdown(
        '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Captura de cédula diaria para campañas de inmunización</p>',
        unsafe_allow_html=True,
    )

    with st.form("form_censo_vacunacion"):

        # --- BLOQUE 1: DATOS GENERALES ---
        st.markdown(
            '<div class="section-title">1. Datos Generales y Fechas</div>',
            unsafe_allow_html=True,
        )
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            fecha_registro = st.date_input(
                "Fecha de Registro [DD/MM/AAAA]",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
            )
        with col_g2:
            fecha_aplicacion = st.date_input(
                "Fecha de Aplicación [DD/MM/AAAA]",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
            )
        with col_g3:
            folio_reg = st.text_input(
                "No. de Registro / Censo",
                value=f"CENSO-{datetime.datetime.now().strftime('%H%M%S')}",
            )

        # --- BLOQUE 2: IDENTIFICACIÓN DEL PACIENTE ---
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

        col_fn1, col_fn2 = st.columns(2)
        with col_fn1:
            fecha_nacimiento = st.date_input(
                "Fecha de Nacimiento [DD/MM/AAAA] *",
                value=datetime.date(1990, 1, 1),
                min_value=datetime.date(1900, 1, 1),
                max_value=datetime.date.today(),
                format="DD/MM/YYYY",
            )
        with col_fn2:
            sexo = st.selectbox("Sexo *", options=["", "Hombre", "Mujer"])

        planes_o_embarazo = "No"
        if sexo == "Mujer":
            st.markdown(
                "<div style='background-color: #f0f4f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>",
                unsafe_allow_html=True,
            )
            planes_o_embarazo = st.radio(
                "¿Está embarazada o tiene planes de embarazo?",
                options=["No", "Sí"],
                horizontal=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        calc_anos, calc_meses, calc_dias = calcular_edad_detallada(
            fecha_nacimiento, fecha_aplicacion
        )

        st.markdown(
            '<div class="section-title">Edades Calculadas / Ajustables</div>',
            unsafe_allow_html=True,
        )
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            edad_anos = st.number_input(
                "Años", min_value=0, max_value=120, value=calc_anos
            )
        with col_e2:
            edad_meses = st.number_input(
                "Meses (adicionales / menores de 1 año)",
                min_value=0,
                max_value=11,
                value=calc_meses,
            )
        with col_e3:
            edad_dias = st.number_input(
                "Días (adicionales / recién nacidos)",
                min_value=0,
                max_value=30,
                value=calc_dias,
            )

        # --- BLOQUE 3: DOMICILIO Y AFILIACIÓN ---
        st.markdown(
            '<div class="section-title">3. Domicilio, Estados y Afiliación</div>',
            unsafe_allow_html=True,
        )
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            estado_nacimiento = st.selectbox(
                "Estado de Nacimiento *", options=estados_mexico, key="est_nac"
            )
        with col_d2:
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

        derechohabiencia = st.selectbox(
            "Derechohabiencia *",
            options=[
                "",
                "IMSS",
                "ISSSTE",
                "IMSS-BIENESTAR",
                "PEMEX",
                "SEDENA",
                "SEMAR",
                "ISSFAM",
                "IMSS / IMSS-BIENESTAR",
                "NINGUNA / INSABI / IMSS BIENESTAR (Población Abierta)",
                "OTRA",
            ],
        )

        # --- BLOQUE 4: OCUPACIÓN ---
        st.markdown(
            '<div class="section-title">4. Ocupación</div>',
            unsafe_allow_html=True,
        )
        ocupacion = st.selectbox(
            "Seleccione su Ocupación *",
            options=[
                "",
                "Personal de salud",
                "Jubilado/a",
                "Maestro/a",
                "Administrativo/a",
                "Trabajo en guardería",
                "Otras profesiones",
            ],
        )

        # --- BLOQUE 5: GRUPOS DE RIESGO Y COMORBILIDADES ---
        st.markdown(
            '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
            unsafe_allow_html=True,
        )
        col_r1, col_r2 = st.columns(2)

        with col_r1:
            emb = st.checkbox(
                "Embarazadas",
                value=(True if planes_o_embarazo == "Sí" else False),
            )
            personal_salud_riesgo = st.checkbox(
                "Personal de Salud",
                value=(True if ocupacion == "Personal de salud" else False),
            )
            vih = st.checkbox("VIH / Sida")
            diabetes = st.checkbox("Diabetes Mellitus")
            obesidad = st.checkbox("Obesidad Mórbida")
            cardiopatias = st.checkbox("Cardiopatías Agudas o Crónicas")

        with col_r2:
            epoc = st.checkbox("Enfermedad Pulmonar Crónica (EPOC / Asma)")
            cancer = st.checkbox("Cáncer")
            congenitas = st.checkbox(
                "Enfermedades cardíacas/pulmonares congénitas u otros (salicilatos)"
            )
            insuficiencia_renal = st.checkbox("Insuficiencia Renal")
            inmunosupresion = st.checkbox(
                "Inmunosupresión adquirida (excepto VIH)"
            )
            hipertension = st.checkbox("Hipertensión Arterial Esencial")

        # Autodetección de Grupo Objetivo
        edad_total_meses = (edad_anos * 12) + edad_meses
        grupo_sugerido = ""
        if 6 <= edad_total_meses <= 59:
            grupo_sugerido = "6 a 59 meses"
        elif edad_anos >= 60:
            grupo_sugerido = "60 y más"
        elif 5 <= edad_anos <= 11:
            grupo_sugerido = "5 a 11 años (Dosis única COVID-19)"
        elif emb or planes_o_embarazo == "Sí":
            grupo_sugerido = "Embarazadas"
        elif personal_salud_riesgo or ocupacion == "Personal de salud":
            grupo_sugerido = "Personal de Salud"
        else:
            grupo_sugerido = "Población general / Otro"

        st.markdown(
            '<div class="section-title">6. Grupo Objetivo (Detectado Automáticamente)</div>',
            unsafe_allow_html=True,
        )
        lista_grupos = [
            "",
            "6 a 59 meses",
            "60 y más",
            "5 a 11 años (Dosis única COVID-19)",
            "Embarazadas",
            "Personal de Salud",
            "Población general / Otro",
        ]
        indice_default = (
            lista_grupos.index(grupo_sugerido)
            if grupo_sugerido in lista_grupos
            else 0
        )
        grupo_objetivo = st.selectbox(
            "Grupo Objetivo (Autocalculado por edad/riesgo, editable)",
            options=lista_grupos,
            index=indice_default,
        )

        # --- BLOQUE 7: ESQUEMA DE VACUNACIÓN APLICADO ---
        st.markdown(
            '<div class="section-title">7. Biológicos Administrados y Lotes</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Anti Influenza Estacional**")
        col_inf1, col_inf2 = st.columns(2)
        with col_inf1:
            esquema_influenza = st.selectbox(
                "Tipo de Dosis / Esquema Influenza",
                options=["", "Dosis Anual", "Dosis Única", "1a Dosis", "2a Dosis"],
            )
        with col_inf2:
            lote_influenza = st.text_input("No. de Lote - Influenza")

        st.markdown("**Contra la COVID-19**")
        col_cov1, col_cov2 = st.columns(2)
        with col_cov1:
            esquema_covid = st.selectbox(
                "Tipo de Dosis / Esquema COVID-19",
                options=["", "1a Dosis", "2a Dosis", "Refuerzo", "Dosis Única"],
            )
        with col_cov2:
            lote_covid = st.text_input("No. de Lote - COVID-19")

        st.markdown("---")
        submitted = st.form_submit_button(
            "Guardar y Enviar al Módulo de Consulta", use_container_width=True
        )

        if submitted:
            if (
                not paterno
                or not nombres
                or not estado_nacimiento
                or not estado_residencia
                or not calle
                or not numero
                or not colonia
                or not derechohabiencia
                or not ocupacion
            ):
                st.error(
                    "Por favor complete los campos obligatorios marcados con (*)."
                )
            else:
                # Diccionario con los datos del paciente para migrar al state
                nuevo_paciente = {
                    "folio": folio_reg,
                    "nombre_completo": f"{paterno} {materno}, {nombres}",
                    "paterno": paterno,
                    "materno": materno,
                    "nombres": nombres,
                    "fecha_nacimiento": fecha_nacimiento,
                    "edad_anos": edad_anos,
                    "edad_meses": edad_meses,
                    "edad_dias": edad_dias,
                    "edad_total_meses": edad_total_meses,
                    "sexo": sexo,
                    "embarazo": emb or (planes_o_embarazo == "Sí"),
                    "ocupacion": ocupacion,
                    "personal_salud": personal_salud_riesgo
                    or (ocupacion == "Personal de salud"),
                    "tiene_comorbilidades": any(
                        [
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
                        ]
                    ),
                    "grupo_objetivo": grupo_objetivo,
                    "fecha_registro": fecha_registro,
                }
                st.session_state.registros_censales.append(nuevo_paciente)
                st.success(
                "¡Paciente registrado y migrado exitosamente! Seleccione en la barra lateral el **'Módulo de Consulta y Guía CENSIA'** para buscarlo y ver sus esquemas recomendados."
            )

# ==========================================
# VISTA 2: MÓDULO DE CONSULTA Y RECOMENDACIÓN CENSIA
# ==========================================
elif st.session_state.navegacion == "Consulta":
    st.markdown(
        '<p class="main-header">Módulo de Búsqueda y Guía Clínica CENSIA</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Evaluación automatizada de esquemas para Influenza y COVID-19 (Temporada Invernal)</p>',
        unsafe_allow_html=True,
    )

    if not st.session_state.registros_censales:
        st.info(
            "No hay pacientes registrados en la sesión actual. Por favor, registre al menos un paciente en el formulario de la barra lateral."
        )
    else:
        # Buscador por Folio o Nombre
        lista_folios_nombres = [
            f"{p['folio']} - {p['nombre_completo']}"
            for p in st.session_state.registros_censales
        ]
        seleccion_busqueda = st.selectbox(
            "Buscar paciente por Folio y Nombre:", options=lista_folios_nombres
        )

        if seleccion_busqueda:
            folio_seleccionado = seleccion_busqueda.split(" - ")[0]
            paciente = next(
                p
                for p in st.session_state.registros_censales
                if p["folio"] == folio_seleccionado
            )

            # Tarjeta de Datos Generales (Sección 2 requerida)
            st.markdown(
                '<div class="section-title">Datos Generales del Paciente (Identificación)</div>',
                unsafe_allow_html=True,
            )
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"**Folio:** {paciente['folio']}")
                st.markdown(f"**Nombre:** {paciente['nombre_completo']}")
            with col_info2:
                st.markdown(
                    f"**Nacimiento:** {paciente['fecha_nacimiento'].strftime('%d/%m/%Y')}"
                )
                st.markdown(
                    f"**Edad:** {paciente['edad_anos']} años, {paciente['edad_meses']} meses"
                )
            with col_info3:
                st.markdown(f"**Sexo:** {paciente['sexo']}")
                st.markdown(f"**Ocupación:** {paciente['ocupacion']}")

            st.markdown("---")
            st.markdown(
                '<div class="section-title">Evaluación de Lineamientos CENSIA (Esquemas Recomendados)</div>',
                unsafe_allow_html=True,
            )

            # --- MOTOR DE LÓGICA CLÍNICA BASADO EN CENSIA ---
            edad_m = paciente["edad_total_meses"]
            anos = paciente["edad_anos"]
            es_embarazada = paciente["embarazo"]
            es_personal_salud = paciente["personal_salud"]
            comorb = paciente["tiene_comorbilidades"]

            # LÓGICA INFLUENZA
            inf_dosis = ""
            inf_via = ""
            if 6 <= edad_m <= 59:
                inf_dosis = (
                    "2 dosis de 0.5 mL (intervalo de 4 semanas) si es su primer año de esquema; "
                    "o 1 dosis anual de 0.5 mL si ya cuenta con esquema completo previo."
                )
                inf_via = "Intramuscular; en tercio medio de la cara anterolateral externa del muslo izquierdo (menores de 18 meses) o región deltoidea del brazo izquierdo (a partir de 18 meses)."
            elif 5 <= anos <= 8 and comorb:
                inf_dosis = (
                    "2 dosis de 0.5 mL (intervalo de 4 semanas) si no tiene esquema primario previo, o 1 dosis anual si ya lo tiene."
                )
                inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
            elif (anos == 9 and comorb) or (10 <= anos <= 59 and comorb):
                inf_dosis = "1 dosis única anual de 0.5 mL."
                inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
            elif es_embarazada:
                inf_dosis = (
                    "1 dosis de 0.5 mL (aplicable en cualquier trimestre del embarazo o lactancia exclusiva)."
                )
                inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
            elif es_personal_salud:
                inf_dosis = "1 dosis anual de 0.5 mL."
                inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
            elif anos >= 60:
                inf_dosis = (
                    "1 dosis anual de 0.5 mL (dar prioridad al inicio de campaña)."
                )
                inf_via = "Intramuscular en región deltoidea del brazo izquierdo."
            else:
                inf_dosis = (
                    "Fuera de grupo prioritario estricto institucional (Valorar disponibilidad o factores de riesgo clínico)."
                )
                inf_via = "Intramuscular en región deltoidea."

            # LÓGICA COVID-19 (Vacunas Spikevax LP.8.1 o Comirnaty LP.8.1)
            cov_dosis = ""
            if 6 <= edad_m <= 18 and comorb:
                cov_dosis = (
                    "Dosis única de 0.25 mL de **Spikevax LP.8.1**, vía intramuscular en tercio medio de la cara anterolateral externa del muslo izquierdo."
                )
            elif 19 <= edad_m <= 59 and comorb:
                cov_dosis = (
                    "Dosis única de 0.25 mL de **Spikevax LP.8.1**, vía intramuscular en región deltoidea del brazo derecho (o a 2.5 cm si es simultánea)."
                )
            elif 5 <= anos <= 11 and comorb:
                cov_dosis = (
                    "Dosis única de 0.25 mL de **Spikevax LP.8.1**, vía intramuscular en región deltoidea del brazo derecho."
                )
            elif 12 <= anos <= 59 and (comorb or es_personal_salud or es_embarazada):
                cov_dosis = (
                    "Refuerzo con Opción A (**Spikevax LP.8.1**: 0.5 mL IM) o Opción B (**Comirnaty LP.8.1**: 0.3 mL IM). Mínimo 6 meses después de su dosis más reciente. *(Nota: Aplicar solo una opción, nunca ambas).* "
                )
            elif anos >= 60:
                cov_dosis = (
                    "Dosis única de refuerzo (0.5 mL de Spikevax o 0.3 mL de Comirnaty según disponibilidad) vía intramuscular en región deltoidea."
                )
            else:
                cov_dosis = (
                    "Población general sin comorbilidades de alto riesgo reportadas en lineamiento de refuerzo estacional actual."
                )

            # --- VISUALIZACIÓN DE ESCENARIOS ---
            st.markdown(
                f"""
                <div class="card-recomendacion">
                    <h4>💉 1. Recomendación para Influenza Estacional</h4>
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
                    <p><b>Esquema / Dosis:</b> {cov_dosis}</p>
                </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="section-title">Selección de Aplicación y Escenarios de Cierre</div>',
                unsafe_allow_html=True,
            )
            eleccion_biologico = st.radio(
                "¿Qué biológico(s) se decidió aplicar al paciente en esta visita?",
                [
                    "Ninguno (Solo evaluación)",
                    "Solo Influenza Estacional",
                    "Solo COVID-19",
                    "Ambos (Influenza y COVID-19 de forma simultánea)",
                ],
            )

            if eleccion_biologico != "Ninguno (Solo evaluación)":
                st.info(
                    f"Escenario seleccionado: **{eleccion_biologico}**. Recuerde que si se aplican ambos biológicos de manera simultánea en extremidades superiores, debe respetarse una separación mínima de 2.5 cm en la región deltoidea."
                )
                if st.button("Confirmar aplicación y finalizar registro"):
                    st.success(
                        "¡Aplicación registrada correctamente en el censo nominal del día!"
                    )
