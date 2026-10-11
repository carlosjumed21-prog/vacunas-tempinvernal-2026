
import json
from google.oauth2 import service_account
import gspread
import streamlit as st
from config import GOOGLE_SCOPES


@st.cache_data(ttl=600)
def cargar_guias_censia():
    """Conecta con el documento CENSIA en la nube y extrae de forma limpia

    las guías de Influenza y COVID, propagando valores en celdas combinadas.
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
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            )
            for row in filas_inf[1:]:
                if len(row) >= 7:
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
                    if len(row) >= 8 and row[7].strip():
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
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            )
            for row in filas_cov[1:]:
                if len(row) >= 7:
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
                    if len(row) >= 8 and row[7].strip():
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
    categoria_paciente, lista_riesgos_detectados, vacuna_registrada
):
    """Cruza los datos puros del paciente con las guías CENSIA para retornar

    las tarjetas correspondientes a Influenza y COVID (incluyendo todos los
    biológicos aplicables).
    """
    guia_inf, guia_cov = cargar_guias_censia()

    matches_inf = []
    matches_cov = []

    mostrar_influenza = vacuna_registrada in ["INFLUENZA", "AMBAS"]
    mostrar_covid = vacuna_registrada in ["COVID-19", "AMBAS"]

    # --- Filtrar Influenza ---
    if mostrar_influenza:
        for item in guia_inf:
            cat_b = item["categoria"].strip().upper()
            gb_c = item["grupos_blancos"].strip().upper()
            if "RIESGO" in cat_b:
                if any(
                    "SALUD" in gb_c and "SALUD" in r.upper()
                    for r in lista_riesgos_detectados
                ) or any(
                    (
                        "COMORBILIDADES" in gb_c
                        or "VIH" in gb_c
                        or "DIABETES" in gb_c
                        or "OBESIDAD" in gb_c
                    )
                    and r.upper()
                    in [
                        "VIH",
                        "DIABETES",
                        "OBESIDAD",
                        "CARDIOPATÍAS",
                        "ENFERMEDAD PULMONAR",
                        "CÁNCER",
                        "RENAL",
                        "INMUNOSUPRESIÓN",
                        "HIPERTENSIÓN",
                    ]
                    for r in lista_riesgos_detectados
                ):
                    if item not in matches_inf:
                        matches_inf.append(item)
        if not matches_inf and guia_inf:
            matches_inf.append(guia_inf[0])

    # --- Filtrar COVID (Moderna, Pfizer, etc.) ---
    if mostrar_covid:
        for item in guia_cov:
            cat_b = item["categoria"].strip().upper()
            gb_c = item["grupos_blancos"].strip().upper()
            if "RIESGO" in cat_b:
                if any(
                    "SALUD" in gb_c and "SALUD" in r.upper()
                    for r in lista_riesgos_detectados
                ) or any(
                    (
                        "COMORBILIDADES" in gb_c
                        or "VIH" in gb_c
                        or "DIABETES" in gb_c
                        or "OBESIDAD" in gb_c
                    )
                    and r.upper()
                    in [
                        "VIH",
                        "DIABETES",
                        "OBESIDAD",
                        "CARDIOPATÍAS",
                        "ENFERMEDAD PULMONAR",
                        "CÁNCER",
                        "RENAL",
                        "INMUNOSUPRESIÓN",
                        "HIPERTENSIÓN",
                    ]
                    for r in lista_riesgos_detectados
                ):
                    if item not in matches_cov:
                        matches_cov.append(item)
        if not matches_cov and guia_cov:
            matches_cov.append(guia_cov[0])

    return matches_inf, matches_cov
