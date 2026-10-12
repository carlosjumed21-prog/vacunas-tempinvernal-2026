import json
from google.oauth2 import service_account
import gspread
import streamlit as st
from config import GOOGLE_SCOPES


@st.cache_data(ttl=300)
def cargar_guias_censia():
    """Conecta con el documento CENSIA en la nube y extrae de forma limpia

    las guías de Influenza y COVID, propagando valores en celdas combinadas (Columnas A a H).
    """
    guia_influenza_registros = []
    guia_covid_registros = []
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

        sheet_censia_id = "1jiJhSq4RQytqax7Gh1B9k8ZSglmsLroAvrCv54lEZ_k"
        doc_censia = client.open_by_key(sheet_censia_id)

        # --- Hoja 1: Influenza ---
        try:
            ws_inf = doc_censia.worksheet("Influenza")
            filas_inf = ws_inf.get_all_values()
            v_vac, v_cat, v_esq, v_dos, v_int, v_rec, v_sim = (
                "", "", "", "", "", "", ""
            )
            for row in filas_inf[1:]:
                if len(row) >= 8:
                    if row[0].strip():
                        v_vac = row[0].strip()
                    if row[1].strip():
                        v_cat = row[1].strip()
                    if row[3].strip():
                        v_esq = row[3].strip()
                    if row[4].strip():
                        v_dos = row[4].strip()
                    if row[5].strip():
                        v_int = row[5].strip()
                    if row[6].strip():
                        v_rec = row[6].strip()
                    if row[7].strip():
                        v_sim = row[7].strip()

                    guia_influenza_registros.append({
                        "vacuna": v_vac,
                        "categoria": v_cat,
                        "grupos_blancos": row[2].strip(),
                        "esquema": v_esq,
                        "dosis": v_dos,
                        "intervalo": v_int,
                        "recomendacion": v_rec,
                        "aplicacion_simultanea": v_sim,
                    })
        except Exception:
            pass

        # --- Hoja 2: COVID ---
        try:
            ws_cov = doc_censia.worksheet("COVID")
            filas_cov = ws_cov.get_all_values()
            c_vac, c_cat, c_esq, c_dos, c_int, c_rec, c_sim = (
                "", "", "", "", "", "", ""
            )
            for row in filas_cov[1:]:
                if len(row) >= 8:
                    if row[0].strip():
                        c_vac = row[0].strip()
                    if row[1].strip():
                        c_cat = row[1].strip()
                    if row[3].strip():
                        c_esq = row[3].strip()
                    if row[4].strip():
                        c_dos = row[4].strip()
                    if row[5].strip():
                        c_int = row[5].strip()
                    if row[6].strip():
                        c_rec = row[6].strip()
                    if row[7].strip():
                        c_sim = row[7].strip()

                    guia_covid_registros.append({
                        "tipo_vacuna": c_vac,
                        "categoria": c_cat,
                        "grupos_blancos": row[2].strip(),
                        "esquema": c_esq,
                        "dosis": c_dos,
                        "intervalo": c_int,
                        "recomendacion": c_rec,
                        "aplicacion_simultanea": c_sim,
                    })
        except Exception:
            pass

    except Exception as e:
        st.error(f"Error al conectar con las guías CENSIA: {e}")

    return guia_influenza_registros, guia_covid_registros


def obtener_recomendaciones_paciente(
    edad_meses, antecedente_vacunal, lista_riesgos_detectados, vacuna_registrada
):
    """Cruza los datos del paciente con las guías CENSIA evaluando con precisión

    el riesgo específico detectado (VIH, comorbilidades, personal de salud, embarazo)
    y evitando cruces erróneos de filas.
    """
    try:
        guia_inf, guia_cov = cargar_guias_censia()

        matches_inf = []
        matches_cov = []

        mostrar_influenza = vacuna_registrada in ["INFLUENZA", "AMBAS"]
        mostrar_covid = vacuna_registrada in ["COVID-19", "AMBAS"]

        # Identificamos los riesgos reales del paciente de forma limpia
        riesgos_up = [r.upper() for r in lista_riesgos_detectados]
        es_embarazada = any("EMBARAZ" in r for r in riesgos_up)
        es_personal_salud = any("SALUD" in r for r in riesgos_up)
        tiene_vih = any("VIH" in r for r in riesgos_up)
        tiene_comorbilidades = len(riesgos_up) > 0

        # ==========================================
        # 1. FILTRADO INFLUENZA
        # ==========================================
        if mostrar_influenza:
            for item in guia_inf:
                cat = item["categoria"].strip().upper()
                gb = item["grupos_blancos"].strip().upper()
                dosis = item["dosis"].strip().upper()
                
                es_match = False

                if "POBLACIÓN OBJETIVO" in cat:
                    if 6 <= edad_meses <= 18 and "6 A 18 MESES" in gb:
                        if antecedente_vacunal == "NO" and "PRIMERA" in dosis:
                            es_match = True
                        elif antecedente_vacunal == "SI" and "ANUAL" in dosis:
                            es_match = True
                    elif 19 <= edad_meses <= 59 and "19 A 59 MESES" in gb:
                        if antecedente_vacunal == "NO" and "PRIMERA" in dosis:
                            es_match = True
                        elif antecedente_vacunal == "SI" and "ANUAL" in dosis:
                            es_match = True
                    elif edad_meses >= 720 and "60 AÑOS Y MAS" in gb:
                        es_match = True

                elif "POBLACIÓN DE RIESGO" in cat:
                    if es_embarazada and "GESTANTES" in gb:
                        es_match = True
                    elif es_personal_salud and "PERSONAL DE SALUD" in gb:
                        es_match = True
                    elif tiene_comorbilidades or tiene_vih:
                        if (9 <= edad_meses < 720) and "9 A 59 AÑOS" in gb:
                            es_match = True
                        elif (5 <= edad_meses < 9) and "5 A 8 AÑOS" in gb:
                            es_match = True

                if es_match and item not in matches_inf:
                    matches_inf.append(item)

        # ==========================================
        # 2. FILTRADO COVID-19 (Moderna y Pfizer)
        # ==========================================
        if mostrar_covid:
            for item in guia_cov:
                vac_tipo = item["tipo_vacuna"].strip().upper()
                cat = item["categoria"].strip().upper()
                gb = item["grupos_blancos"].strip().upper()

                es_match = False

                # Restricción estricta de Pfizer para < 12 años (144 meses)
                if "PFIZER" in vac_tipo and edad_meses < 144:
                    continue

                if "POBLACIÓN OBJETIVO" in cat:
                    if "MODERNA" in vac_tipo:
                        if 6 <= edad_meses <= 18 and "6 A 18 MESES" in gb:
                            es_match = True
                        elif 19 <= edad_meses <= 59 and "19 A 59 MESES" in gb:
                            es_match = True
                        elif 60 <= edad_meses <= 131 and "5 A 11 AÑOS" in gb:
                            es_match = True
                        elif edad_meses >= 144 and "12 AÑOS" in gb:
                            es_match = True
                    elif "PFIZER" in vac_tipo:
                        if edad_meses >= 144 and "12 AÑOS" in gb:
                            es_match = True

                elif "POBLACIÓN DE RIESGO" in cat:
                    if es_embarazada and "GESTANTES" in gb:
                        es_match = True
                    elif es_personal_salud and "PERSONAL DE SALUD" in gb:
                        es_match = True
                    elif edad_meses >= 720 and "60 AÑOS O MÁS" in gb:
                        es_match = True
                    elif (tiene_comorbilidades or tiene_vih) and "COMORBILIDADES" in gb:
                        if 6 <= edad_meses < 720:
                            es_match = True

                if es_match and item not in matches_cov:
                    matches_cov.append(item)

        return matches_inf, matches_cov

    except Exception as e:
        st.error(f"Error al procesar recomendaciones: {e}")
        return [], []
