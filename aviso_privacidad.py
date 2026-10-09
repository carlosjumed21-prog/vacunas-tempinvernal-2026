
import streamlit as st

def mostrar_aviso_privacidad_si_necesario():
    # Verificar si el usuario ya aceptó el aviso en esta sesión
    if "aviso_aceptado" not in st.session_state:
        st.session_state.aviso_aceptado = False

    if not st.session_state.aviso_aceptado:
        # Usamos un contenedor principal o modal para bloquear el acceso hasta aceptar
        st.markdown(
            """
            <div style="background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 25px; border-radius: 10px; margin-bottom: 20px;">
                <h2 style="color: #1e5b4f; margin-top: 0; text-align: center;">🛡️ Aviso de Privacidad</h2>
                <h4 style="color: #611232; text-align: center; margin-bottom: 20px;">Registro de Jornadas de Vacunación</h4>
                
                <p><b>Responsable del tratamiento:</b><br>
                Las instituciones del Sistema Nacional de Salud participantes en el programa de jornadas de vacunación son las responsables de recabar, tratar y proteger los datos personales proporcionados, los cuales serán resguardados bajo estrictas medidas de seguridad y confidencialidad.</p>
                
                <p><b>Finalidades del tratamiento de datos:</b><br>
                Los datos personales y clínicos recabados (identificación, datos sociodemográficos y antecedentes de salud para la inmunización) serán utilizados exclusivamente para:</p>
                <ul>
                    <li>El registro nominal de aplicación de biológicos y control operativo de la campaña.</li>
                    <li>Fines estadísticos, análisis epidemiológico, seguimiento de coberturas y evaluación de metas institucionales.</li>
                    <li>La notificación y vigilancia de Eventos Supuestamente Atribuibles a la Vacunación o Inmunización (ESAVI), en estricto cumplimiento con la normatividad vigente.</li>
                </ul>
                
                <p><b>Transferencia y confidencialidad estadística:</b><br>
                La información podrá ser integrada en informes estadísticos y sistemas oficiales de seguimiento (tales como plataformas institucionales de la Secretaría de Salud y CENSIA) garantizando en todo momento la disociación de los datos personales para proteger la identidad de los usuarios.</p>
                
                <p><b>Ejercicio de Derechos ARCO:</b><br>
                Puedes ejercer tus derechos de Acceso, Rectificación, Cancelación y Oposición directamente ante la unidad o instancia responsable del programa.</p>
                
                <p style="text-align: center; font-weight: bold; color: #1e5b4f; margin-top: 20px;">
                    Al hacer clic en "Acepto y continuar", confirmas que has leído este aviso y otorgas tu consentimiento para el tratamiento de tus datos bajo los fines descritos.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("❌ [ Rechazar / Salir ]", use_container_width=True):
                st.error("Has rechazado el aviso de privacidad. No es posible continuar con el registro.")
                st.stop()  # Detiene la ejecución de la página
                
        with col_btn2:
            if st.button("✅ [ Acepto y continuar ]", use_container_width=True):
                st.session_state.aviso_aceptado = True
                st.rerun()  # Recarga la página para mostrar el formulario principal

        st.stop()  # Detiene la renderización del resto del formulario hasta que acepte
