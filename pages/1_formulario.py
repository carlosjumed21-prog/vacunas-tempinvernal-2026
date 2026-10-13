# --- BOTÓN DE REGISTRO DIRECTO A UN SOLO CLIC ---
if st.button("Registrarme para la jornada", use_container_width=True, key="btn_registrar_jornada"):
    if not fecha_nacimiento:
        st.error("⚠️ Seleccione correctamente el Día, Mes y Año de Nacimiento.")
    elif not paterno.strip() or not materno.strip() or not nombres.strip():
        st.error("⚠️ Complete Apellido Paterno, Materno y Nombre(s).")
    elif not correo_paciente.strip():
        st.error("⚠️ Ingrese el correo electrónico para enviarle su comprobante de folio.")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("⚠️ Seleccione una opción en Sexo.")
    elif vacuna_interes is None:
        st.error("⚠️ Seleccione la vacuna de su interés.")
    else:
        # Usamos st.status o st.spinner para asegurar que Streamlit pinte el estado de carga
        with st.status("🚀 Procesando registro en el servidor...", expanded=True) as status:
            try:
                st.write("Verificando registros previos...")
                duplicado, folio_previo = verificar_curp_duplicada(
                    curp_con_nacimiento, sigla_url, sufijo_js, st.session_state.tipo_jornada, val_fecha_app
                )

                if duplicado:
                    status.update(label="⚠️ ¡Paciente ya registrado!", state="error", expanded=True)
                    st.session_state.paciente_duplicado_info = {
                        "nombre": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                        "folio": folio_previo
                    }
                    safe_rerun()
                else:
                    st.write("Guardando datos en Google Sheets...")
                    fecha_aplicacion_str = val_fecha_app.strftime("%d/%m/%Y")

                    comorbilidades_dict = {
                        "personas_embarazadas": personas_embarazadas, "personal_salud_riesgo": personal_salud_riesgo,
                        "vih": vih, "diabetes": diabetes, "obesidad": obesidad, "cardiopatias": cardiopatias,
                        "enfermedad_pulmonar": enfermedad_pulmonar, "cancer": cancer, "cardiacas_congenitas": cardiacas_congenitas,
                        "insuficiencia_renal": insuficiencia_renal, "inmunosupresion": inmunosupresion,
                        "discapacidades": discapacidades, "fibrosis_quistica": fibrosis_quistica,
                        "hipertension": hipertension, "otro": otro_riesgo, "texto_otro": texto_otro_riesgo.upper() if otro_riesgo else "",
                    }

                    datos_paciente = {
                        "paterno": paterno, "materno": materno, "nombres": nombres,
                        "fecha_nacimiento": fecha_nacimiento, "calc_anos": calc_anos, "calc_meses": calc_meses,
                        "sexo": sexo, "calle": calle, "numero": numero, "colonia": colonia,
                        "correo_paciente": correo_paciente.strip(),
                        "estado_nacimiento": estado_nacimiento if estado_nacimiento != "SELECCIONE UN ESTADO" else "CDMX",
                        "estado_residencia": estado_residencia if estado_residencia != "SELECCIONE UN ESTADO" else "CDMX",
                        "curp_con_nacimiento": curp_con_nacimiento, "cuenta_derechohabiencia": cuenta_derechohabiencia,
                        "vacuna_interes": vacuna_interes, "antecedente_covid": antecedente_covid,
                        "antecedente_influenza": antecedente_influenza, "grupo_sugerido": grupo_sugerido,
                        "ocupacion": ocupacion, "comorbilidades": comorbilidades_dict,
                        "modalidad": st.session_state.modalidad,
                    }

                    folio_asignado, is_duplicate, existing_folio = guardar_registro_censal(
                        sigla_url=sigla_url, sufijo_js=sufijo_js, tipo_jornada=st.session_state.tipo_jornada,
                        val_fecha_app=val_fecha_app, nombre_unidad_completo=st.session_state.nombre_unidad, datos_paciente=datos_paciente
                    )

                    status.update(label="✅ ¡Registro exitoso!", state="complete", expanded=False)
                    st.session_state.pop("submission_id", None)

                    if is_duplicate:
                        st.session_state.paciente_duplicado_info = {
                            "nombre": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                            "folio": existing_folio
                        }
                        safe_rerun()
                    else:
                        st.session_state.ultimo_paciente_registrado = {
                            "nombre_completo": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                            "curp_con_nacimiento": curp_con_nacimiento,
                            "vacuna_interes": vacuna_interes,
                            "grupo_objetivo": grupo_sugerido,
                            "folio": folio_asignado,
                            "correo_paciente": correo_paciente.strip(),
                            "fecha_aplicacion": fecha_aplicacion_str,
                        }
                        safe_rerun()

            except Exception as e:
                status.update(label="❌ Error en el proceso", state="error", expanded=True)
                st.session_state.pop("submission_id", None)
                st.error("⚠️ Error general al procesar el registro en Google Sheets:")
                st.exception(e)
