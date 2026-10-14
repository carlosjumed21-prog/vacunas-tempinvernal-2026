def guardar_registro_censal_20_nov(datos_paciente):
    """Guarda el registro censal específico del CMN '20 de Noviembre'
    en la hoja nominal duplicada y realiza la migración dual automática
    hacia la hoja maestra 'CENSO' general respetando el mapeo exacto de columnas (B a AH).
    """
    try:
        client = obtener_cliente_gspread()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
        tipo_jornada = datos_paciente.get("tipo_jornada", "I")
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        
        siglas_unidad = st.session_state.get("siglas_unidad", "20N")
        sufijo_js = st.session_state.get("sufijo_js", "")
        nombre_hoja_nominal = f"{siglas_unidad}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}_NOMINAL"

        # --- 1. ESCRITURA EN LA HOJA NOMINAL DINÁMICA (JORNADA) ---
        try:
            ws_nominal = spreadsheet.worksheet(nombre_hoja_nominal)
        except:
            try:
                plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
            except:
                plantilla_1 = spreadsheet.worksheet("CENSO")
            ws_nominal = spreadsheet.duplicate_sheet(
                plantilla_1.id, 
                insert_sheet_index=len(spreadsheet.worksheets()), 
                new_sheet_name=nombre_hoja_nominal
            )

        col_b_nom = ws_nominal.col_values(2)
        fila_nom = 14
        idx_n = 13
        while idx_n < len(col_b_nom):
            val_a = str(col_b_nom[idx_n]).strip()
            if val_a == "" or "POR ASIGNAR" in val_a.upper():
                fila_nom = idx_n + 1
                break
            idx_n += 2
        else:
            fila_nom = max(14, len(col_b_nom) + 1)
            if (fila_nom - 14) % 2 != 0:
                fila_nom += 1

        num_nom = ((fila_nom - 14) // 2) + 1
        aammmdd = val_fecha_app.strftime("%y%m%d")
        sigla_url = siglas_unidad
        folio_asignado = f"{aammmdd}-{tipo_jornada}{sigla_url}-{str(num_nom).zfill(3)}"

        comorb = datos_paciente.get("comorbilidades", {})
        ant_inf_val = datos_paciente.get("antecedente_influenza", "")
        ant_cov_val = datos_paciente.get("antecedente_covid", "")
        vacuna_int = datos_paciente.get("vacuna_interes", "").upper()

        updates_hoja1 = [
            {"range": "D7", "values": [["CDMX"]]},
            {"range": "M7", "values": [["ISSSTE"]]},
            {"range": "T7", "values": [["Delegación Sur"]]},
            {"range": "AB7", "values": [["CDMX"]]},
            {"range": "D8", "values": [["CDMX"]]},
            {"range": "D9", "values": [[st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE")]]},
            {"range": "AB9", "values": [[val_fecha_app.strftime("%d/%m/%Y")]]},
            {"range": f"B{fila_nom}:B{fila_nom+1}", "values": [[folio_asignado], [folio_asignado]]},
            {"range": f"C{fila_nom}", "values": [[datos_paciente['paterno'].upper()]]},
            {"range": f"D{fila_nom}", "values": [[datos_paciente['materno'].upper() if datos_paciente.get('materno') else ""]]},
            {"range": f"E{fila_nom}", "values": [[datos_paciente['nombres'].upper()]]},
            {"range": f"F{fila_nom}:F{fila_nom+1}", "values": [[datos_paciente['fn_dia']], [datos_paciente['fn_dia']]]},
            {"range": f"G{fila_nom}:G{fila_nom+1}", "values": [[datos_paciente['fn_mes']], [datos_paciente['fn_mes']]]},
            {"range": f"H{fila_nom}:H{fila_nom+1}", "values": [[datos_paciente['fn_ano']], [datos_paciente['fn_ano']]]},
            {"range": f"I{fila_nom}:I{fila_nom+1}", "values": [[str(datos_paciente['anos'])], [str(datos_paciente['anos'])]]},
            {"range": f"J{fila_nom}:J{fila_nom+1}", "values": [[str(datos_paciente['meses'])], [str(datos_paciente['meses'])]]},
            {"range": f"K{fila_nom}:K{fila_nom+1}", "values": [["H" if datos_paciente['sexo']=="HOMBRE" else "M"], ["H" if datos_paciente['sexo']=="HOMBRE" else "M"]]},
            {"range": f"L{fila_nom}:L{fila_nom+1}", "values": [[val_fecha_app.strftime("%d/%m/%Y")], [val_fecha_app.strftime("%d/%m/%Y")]]},
            {"range": f"M{fila_nom}:M{fila_nom+1}", "values": [[datos_paciente.get('calle','').upper()], [datos_paciente.get('calle','').upper()]]},
            {"range": f"N{fila_nom}:N{fila_nom+1}", "values": [[datos_paciente.get('numero','').upper()], [datos_paciente.get('numero','').upper()]]},
            {"range": f"O{fila_nom}:O{fila_nom+1}", "values": [[datos_paciente.get('colonia','').upper()], [datos_paciente.get('colonia','').upper()]]},
            {"range": f"C{fila_nom+1}", "values": [[datos_paciente.get('curp_con_nacimiento','')]]},
            
            {"range": f"AQ{fila_nom}:AQ{fila_nom+1}", "values": [[datos_paciente.get('cuenta_derechohabiencia', 'SÍ')], [datos_paciente.get('cuenta_derechohabiencia', 'SÍ')]]},
            {"range": f"AR{fila_nom}:AR{fila_nom+1}", "values": [[ant_inf_val], [ant_inf_val]]},
            {"range": f"AS{fila_nom}:AS{fila_nom+1}", "values": [[ant_cov_val], [ant_cov_val]]},
            {"range": f"AW{fila_nom}:AW{fila_nom+1}", "values": [[datetime.date.today().strftime("%d/%m/%Y")], [datetime.date.today().strftime("%d/%m/%Y")]]},
            {"range": f"AX{fila_nom}:AX{fila_nom+1}", "values": [[datos_paciente.get('correo_paciente', '')], [datos_paciente.get('correo_paciente', '')]]},
        ]
        
        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_hoja1.append({"range": f"AT{fila_nom}:AT{fila_nom+1}", "values": [["X"], ["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_hoja1.append({"range": f"AU{fila_nom}:AU{fila_nom+1}", "values": [["X"], ["X"]]})
        if vacuna_int == "AMBAS":
            updates_hoja1.append({"range": f"AV{fila_nom}:AV{fila_nom+1}", "values": [["X"], ["X"]]})

        if int(datos_paciente['anos']) < 5:
            updates_hoja1.append({"range": f"P{fila_nom}:P{fila_nom+1}", "values": [["X"], ["X"]]})
        elif int(datos_paciente['anos']) >= 60:
            updates_hoja1.append({"range": f"Q{fila_nom}:Q{fila_nom+1}", "values": [["X"], ["X"]]})

        if datos_paciente.get('embarazo') == "SÍ":
            updates_hoja1.append({"range": f"R{fila_nom}:R{fila_nom+1}", "values": [["X"], ["X"]]})
        if datos_paciente.get('personal_salud') == "SÍ":
            updates_hoja1.append({"range": f"S{fila_nom}:S{fila_nom+1}", "values": [["X"], ["X"]]})

        map_comorb_h1 = {
            "vih": "T", "diabetes": "U", "obesidad": "V", "cardiopatias": "W",
            "enfermedad_pulmonar": "X", "cancer": "Y", "cardiacas_congenitas": "Z",
            "insuficiencia_renal": "AA", "inmunosupresion": "AB", "discapacidades": "AC",
            "fibrosis_quistica": "AD", "hipertension": "AE"
        }
        for k_c, col_c in map_comorb_h1.items():
            if comorb.get(k_c, False):
                updates_hoja1.append({"range": f"{col_c}{fila_nom}:{col_c}{fila_nom+1}", "values": [["X"], ["X"]]})

        ws_nominal.batch_update(updates_hoja1)

        # --- 2. ESCRITURA EN LA HOJA MAESTRA GENERAL "CENSO" (RESPETANDO TU MAPEO B-AH) ---
        try:
            ws_censo_general = spreadsheet.worksheet("CENSO")
        except:
            ws_censo_general = ws_nominal # Fallback por seguridad

        col_b_censo = ws_censo_general.col_values(2)
        fila_censo = 14
        idx_c = 13
        while idx_c < len(col_b_censo):
            val_c = str(col_b_censo[idx_c]).strip()
            if val_c == "" or "POR ASIGNAR" in val_c.upper() or val_c.isdigit() == False:
                fila_censo = idx_c + 1
                break
            idx_c += 1
        else:
            fila_censo = max(14, len(col_b_censo) + 1)

        consecutivo_censo = fila_censo - 13

        ps_val = "SÍ" if datos_paciente.get("personal_salud") == "SÍ" else "NO"
        emb_val = "SÍ" if datos_paciente.get("embarazo") == "SÍ" else "NO"

        # Mapeo exacto según tus indicaciones para la hoja CENSO:
        # B: Folio, C: RFC, D: Cuenta DH, E: Tipo DH, F: Trabaja CMN, G: Num Trabajador, H: Personal Salud
        # I: Categoria, J: Servicio, K: Coordinacion, L: Turno, M: Nombres, N: Paterno, O: Materno
        # P: Edo Nac, Q: Muni Nac, R: Dia Nac, S: Mes Nac, T: Ano Nac, U: Anios, V: Meses, W: Sexo, X: Embarazo
        updates_censo = [
            {"range": f"B{fila_censo}", "values": [[folio_asignado]]},
            {"range": f"C{fila_censo}", "values": [[datos_paciente.get("rfc", "")]]},
            {"range": f"D{fila_censo}", "values": [[datos_paciente.get("cuenta_derechohabiencia", "SÍ")]]},
            {"range": f"E{fila_censo}", "values": [[datos_paciente.get("tipo_dh", "TRABAJADOR ACTIVO")]]},
            {"range": f"F{fila_censo}", "values": [[datos_paciente.get("trabaja_cmn", "SÍ")]]},
            {"range": f"G{fila_censo}", "values": [[datos_paciente.get("num_trabajador", "")]]},
            {"range": f"H{fila_censo}", "values": [[ps_val]]},
            {"range": f"I{fila_censo}", "values": [[datos_paciente.get("categoria", "")]]},
            {"range": f"J{fila_censo}", "values": [[datos_paciente.get("servicio", "")]]},
            {"range": f"K{fila_censo}", "values": [[datos_paciente.get("coordinacion", "")]]},
            {"range": f"L{fila_censo}", "values": [[datos_paciente.get("turno", "")]]},
            {"range": f"M{fila_censo}", "values": [[datos_paciente["nombres"].upper()]]},
            {"range": f"N{fila_censo}", "values": [[datos_paciente["paterno"].upper()]]},
            {"range": f"O{fila_censo}", "values": [[datos_paciente["materno"].upper() if datos_paciente.get("materno") else ""]] },
            {"range": f"P{fila_censo}", "values": [[datos_paciente.get("edo_nac", "CDMX")]]},
            {"range": f"Q{fila_censo}", "values": [[datos_paciente.get("muni_nac", "")]]},
            {"range": f"R{fila_censo}", "values": [[datos_paciente["fn_dia"]]]},
            {"range": f"S{fila_censo}", "values": [[datos_paciente["fn_mes"]]]},
            {"range": f"T{fila_censo}", "values": [[datos_paciente["fn_ano"]]]},
            {"range": f"U{fila_censo}", "values": [[str(datos_paciente["anos"])]]},
            {"range": f"V{fila_censo}", "values": [[str(datos_paciente["meses"])]]},
            {"range": f"W{fila_censo}", "values": [[datos_paciente["sexo"]]]},
            {"range": f"X{fila_censo}", "values": [[emb_val]]},
        ]

        # Mapeo de vacunas de interés en la hoja CENSO general:
        # Y: Influenza 1ra dosis, Z: Influenza 2da dosis, AA: Influenza Dosis anual
        # AD: COVID 1ra dosis, AE: COVID 2da dosis, AF: COVID Dosis anual
        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_censo.append({"range": f"Y{fila_censo}", "values": [["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_censo.append({"range": f"AD{fila_censo}", "values": [["X"]]})

        ws_censo_general.batch_update(updates_censo)
        return folio_asignado

    except Exception as e:
        raise e
