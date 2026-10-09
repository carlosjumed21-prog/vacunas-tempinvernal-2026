import streamlit as st

@st.dialog("🛡️ Aviso de Privacidad - Registro de Jornadas de Vacunación", width="large")
def mostrar_modal_aviso():
    st.markdown("**Responsable del tratamiento:**")
    st.markdown("Las instituciones del Sistema Nacional de Salud participantes en el programa de jornadas de vacunación son las responsables de recabar, tratar y proteger los datos personales proporcionados, los cuales serán resguardados bajo estrictas medidas de seguridad y confidencialidad.")
    
    st.markdown("**Finalidades del tratamiento de datos:**")
    st.markdown("Los datos personales y clínicos recabados (identificación, datos sociodemográficos y antecedentes de salud para la inmunización) serán utilizados exclusivamente para:")
    st.markdown("- El registro nominal de aplicación de biológicos y control operativo de la campaña.")
    st.markdown("- Fines estadísticos, análisis epidemiológico, seguimiento de coberturas y evaluación de metas institucionales.")
    st.markdown("- La notificación y vigilancia de Eventos Supuestamente Atribuibles a la Vacunación o Inmunización (ESAVI), en estricto cumplimiento con la normatividad vigente.")
    
    st.markdown("**Transferencia y confidencialidad estadística:**")
    st.markdown("La información podrá ser integrada en informes estadísticos y sistemas oficiales de seguimiento (tales como plataformas institucionales de la Secretaría de Salud y CENSIA) garantizando en todo momento la disociación de los datos personales para proteger la identidad de los usuarios.")
    
    st.markdown("**Ejercicio de Derechos ARCO:**")
    st.markdown("Puedes ejercer tus derechos de Acceso, Rectificación, Cancelación y Oposición directamente ante la unidad o instancia responsable del programa.")
    
    st.markdown("---")
    st.markdown("<p style='text-align: center; font-weight: bold; color: #1e5b4f;'>Al hacer clic en \"Acepto y continuar\", confirmas que has leído este aviso y otorgas tu consentimiento para el tratamiento de tus datos bajo los fines descritos.</p>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("❌ Rechazar / Salir", use_container_width=True):
            st.error("Has rechazado el aviso de privacidad.")
            st.stop()
    with col_m2:
        if st.button("✅ Acepto y continuar", use_container_width=True):
            st.session_state.aviso_aceptado = True
            st.rerun()

def mostrar_aviso_privacidad_si_necesario():
    if "aviso_aceptado" not in st.session_state:
        st.session_state.aviso_aceptado = False

    if not st.session_state.aviso_aceptado:
        mostrar_modal_aviso()
