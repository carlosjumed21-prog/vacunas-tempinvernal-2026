# utils/sheets_esquemas.py
import streamlit as st

def obtener_recomendaciones_paciente(categoria_paciente, lista_riesgos_detectados, vacuna_registrada, edad_meses_calc, antecedente_vacunal):
    """
    Evalúa los criterios CENSIA y retorna las recomendaciones o tarjetas 
    tanto para Influenza como para COVID-19 según el perfil del paciente.
    """
    matches_inf = []
    matches_covid = []

    # Configuración de recomendación base para Influenza Estacional
    if vacuna_registrada in ["INFLUENZA", "AMBAS"]:
        matches_inf.append({
            "categoria": categoria_paciente,
            "grupos_blancos": ", ".join(lista_riesgos_detectados) if lista_riesgos_detectados else "Población General / Objetivo",
            "esquema": "Dosis Anual Estacional",
            "dosis": "0.5 mL (según grupo etario)",
            "intervalo": "Anual",
            "recomendacion": "Aplicar vacuna contra Influenza Estacional conforme a lineamientos CENSIA vigentes."
        })

    # Configuración de recomendación base para COVID-19
    if vacuna_registrada in ["COVID-19", "AMBAS"]:
        matches_covid.append({
            "categoria": categoria_paciente,
            "grupos_blancos": ", ".join(lista_riesgos_detectados) if lista_riesgos_detectados else "Población General / Objetivo",
            "esquema": "Dosis de Refuerzo / Campaña Invernal",
            "dosis": "Dosis única autorizada",
            "intervalo": "Anual / Según campaña",
            "recomendacion": "Aplicar biológico COVID-19 de temporada conforme a disponibilidad y comorbilidades."
        })

    return matches_inf, matches_covid
