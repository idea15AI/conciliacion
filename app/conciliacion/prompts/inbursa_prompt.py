def crear_prompt_inbursa_estructurado():
    """
    Crea el prompt específico para INBURSA con formato estructurado.
    """
    return """
    # PROMPT PARA INBURSA
    
    Extrae movimientos bancarios INBURSA en formato JSON.
    
    ```json
    [
      {
        "FECHA": "MMM. DD",
        "REFERENCIA": "número",
        "CONCEPTO": "descripción",
        "CARGOS": "monto",
        "ABONOS": "monto",
        "SALDO": "saldo"
      }
    ]
    ```
    
    ## FORMATO EXACTO DE INBURSA:
    
    ### Estructura de tabla:
    ```
    FECHA REFERENCIA CONCEPTO CARGOS ABONOS SALDO
    MAY. 01 MAY. 02 3407784114 BALANCE INICIAL LIQUIDACION ADQUIRENTE CREDITO
    165.00 44,432.09
    44,597.09
    LIQUIDACION ADQ CREDITO-8993380
    ```
    
    ### Reglas de extracción:
    - FECHA: Formato "MAY. 01", "MAY. 02", etc.
    - REFERENCIA: Número de referencia (ej: "3407784114")
    - CONCEPTO: Descripción completa del movimiento (puede ser múltiples líneas)
    - CARGOS: Monto de cargos (si no hay, usar null)
    - ABONOS: Monto de abonos (si no hay, usar null)
    - SALDO: Saldo después del movimiento
    
    ### Tipos de movimientos específicos:
    - "BALANCE INICIAL" + "LIQUIDACION ADQUIRENTE CREDITO" → ABONOS: 165.00
    - "TASA DE DESCTO CREDITO" + "APLICACION DE TASAS DE DESCUENTO-CREDITO-8993380" → CARGOS: 4.60
    - "IVA TASA DE DESCTO CREDITO" + "Tasa IVA 16.0 %" → CARGOS: 0.74
    - "LIQUIDACION ADQUIRENTE DEBITO" + "LIQUIDACION ADQ DEBITO-8993380" → ABONOS: 1,050.00
    - "TASA DE DESCTO DEBITO" + "APLICACION DE TASAS DE DESCUENTO-DEBITO-8993380" → CARGOS: 22.48
    - "IVA TASA DE DESCTO DEBITO" + "Tasa IVA 16.0 %" → CARGOS: 3.60
    - "DEPOSITO TEF" + "OPERADORA PAYPAL DE MEXICO S DE RL" → ABONOS: 472.46
    
    ### Manejo de conceptos multilínea:
    - Los conceptos pueden tener 2-3 líneas
    - Ejemplo: "LIQUIDACION ADQUIRENTE CREDITO" + "LIQUIDACION ADQ CREDITO-8993380"
    - Combinar todas las líneas del concepto en un solo campo
    
    ### Reglas importantes:
    - Extraer TODOS los movimientos de la tabla
    - Mantener el formato de fechas "MMM. DD"
    - Usar comas en los números (ej: "44,432.09")
    - Si no hay cargos o abonos, usar null
    - NO incluir líneas de resumen como "TOTAL"
    
    ## IMPORTANTE:
    - Devuelve SOLO el JSON, sin texto adicional
    - No incluyas explicaciones ni comentarios
    - Asegúrate de que el JSON sea válido
    - Extrae TODOS los movimientos de la tabla completa
    """ 