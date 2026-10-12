
Error general al procesar el registro en Google Sheets:

Exception: Error al guardar el registro en Google Sheets: No se pudo parsear un diccionario válido con 'client_email' desde GOOGLE_CREDENTIALS.
Traceback:
File "/mount/src/vacunas-tempinvernal-2026/utils/sheets.py", line 70, in guardar_registro_censal
    client = obtener_cliente_gspread()
File "/mount/src/vacunas-tempinvernal-2026/utils/sheets.py", line 43, in obtener_cliente_gspread
    raise ValueError(
        "No se pudo parsear un diccionario válido con 'client_email' desde GOOGLE_CREDENTIALS."
    )
ValueError: No se pudo parsear un diccionario válido con 'client_email' desde GOOGLE_CREDENTIALS.
During handling of the above exception, another exception occurred:
File "/mount/src/vacunas-tempinvernal-2026/pages/1_formulario.py", line 773, in <module>
    guardar_registro_censal(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        sigla_url=sigla_url,
        ^^^^^^^^^^^^^^^^^^^^
    ...<4 lines>...
        datos_paciente=datos_paciente,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/mount/src/vacunas-tempinvernal-2026/utils/sheets.py", line 223, in guardar_registro_censal
    raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
