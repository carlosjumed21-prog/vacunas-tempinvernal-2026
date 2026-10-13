# --- ACCIÓN DE ELIMINACIÓN: BORRADO INSTANTÁNEO Y DINÁMICO ---
if btn_eliminar:
    indices_marcados = df_editado[df_editado["SELECCIONAR"] == True].index.tolist()
    pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}

    if not pacientes_a_eliminar:
        st.warning("⚠️ No ha seleccionado ningún paciente para eliminar.")
    else:
        try:
            pacientes_sorted = sorted(pacientes_a_eliminar, reverse=True)
            filas_actualizadas = list(filas_tabla)
            filas_gs_a_borrar = []
            
            for paciente_idx in pacientes_sorted:
                if paciente_idx < len(mapeo_indices_pares):
                    idx_par_real = mapeo_indices_pares[paciente_idx]
                    filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])
                    del filas_actualizadas[idx_par_real:idx_par_real + 2]

            # 1. Actualizamos la sesión de inmediato
            st.session_state[key_estado_filas] = filas_actualizadas

            # 2. Sincronización optimizada con Google Sheets en bloque rápido
            client = obtener_cliente_gspread()
            spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
            ws = spreadsheet.worksheet(hoja_activa_tabla)

            # Borrar filas de manera optimizada agrupando peticiones si es posible o de forma directa rápida
            filas_gs_a_borrar = sorted(set(filas_gs_a_borrar), reverse=True)
            
            # Ejecución rápida de borrado en Google Sheets
            for fila_gs in filas_gs_a_borrar:
                try:
                    ws.delete_rows(fila_gs)
                except Exception:
                    pass

            # Recálculo rápido de folios por lotes (batch_update) para evitar lentitud
            datos_actualizados = ws.get_all_values()
            if len(datos_actualizados) >= 14:
                filas_actuales = datos_actualizados[13:]
                contador = 1
                updates = []
                for i in range(0, len(filas_actuales), 2):
                    row = filas_actuales[i]
                    if len(row) > 0 and row[0].strip() != "":
                        a1 = gspread.utils.rowcol_to_a1(i + 14, 1)
                        updates.append({"range": a1, "values": [[str(contador)]]})
                        contador += 1
                if updates:
                    try:
                        ws.batch_update(updates)
                    except Exception:
                        pass

            # 3. Refresco dinámico instantáneo
            st.rerun()

        except Exception as e:
            st.error(f"❌ Ocurrió un error al intentar eliminar: {e}")
