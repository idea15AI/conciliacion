def crear_prompt_banorte_estructurado():
    """
    Crea el prompt específico para BANORTE con formato estructurado.
    """
    return """
    # PROMPT ESPECÍFICO PARA BANORTE
    
    Tu tarea es extraer TODOS los movimientos bancarios del estado de cuenta BANORTE y devolverlos en formato JSON.
    
    ## FORMATO DE RESPUESTA REQUERIDO:
    Debes devolver SOLO un array JSON con los movimientos, sin texto adicional.
    
    ```json
    [
      {
        "FECHA": "DD-MMM-YY",
        "DESCRIPCION": "descripción_del_movimiento",
        "MONTO_DEL_DEPOSITO": "monto_con_comas",
        "MONTO_DEL_RETIRO": "monto_con_comas",
        "SALDO": "saldo_con_comas"
      }
    ]
    ```
    
    ## FORMATO EXACTO DE BANORTE:
    
    ### Estructura de tabla:
    ```
    FECHA DESCRIPCIÓN / ESTABLECIMIENTO MONTO DEL DEPOSITO MONTO DEL RETIRO SALDO
    31-DIC-22 SALDO ANTERIOR 1,190,950.98
    03-ENE-23 DEPOSITO DE CUENTA DE TERCEROS 0000000655 DE LA CUENTA 0557374517 PAGO FACT 655
    RENTA JUAREZ ENERO 2023
    197,200.00 1,388,150.98
    03-ENE-23 085902932284300331 SPEI RECIBIDO, BCO:0002 BANAMEX HR LIQ: 14:54:24 DEL CLIENTE NATALY
    MORALES HERNANDEZ DE LA CLABE 002650700555078387 CON RFC MOHN850126221
    CONCEPTO: Transferencia interbancaria REFERENCIA: 0030123 CVE RAST: 085902932284300331
    11,658.00 1,399,808.98
    ```
    
    ### Reglas de extracción:
    - FECHA: Formato "31-DIC-22", "03-ENE-23", etc.
    - DESCRIPCION: Descripción completa del movimiento (puede ser múltiples líneas)
    - MONTO_DEL_DEPOSITO: Monto de depósito/abono (si no hay, usar null)
    - MONTO_DEL_RETIRO: Monto de retiro/cargo (si no hay, usar null)
    - SALDO: Saldo después del movimiento
    
    ### Tipos de movimientos específicos:
    - "SALDO ANTERIOR" (solo el saldo, sin depósito ni retiro)
    - "DEPOSITO DE CUENTA DE TERCEROS" + detalles multilínea
    - "SPEI RECIBIDO" + detalles multilínea con información del cliente
    - "TRASPASO A CUENTA DE TERCEROS" + detalles multilínea
    - "COMPRA ORDEN DE PAGO SPEI" + detalles multilínea
    - "CUENTAS POR PAGAR - SAP" + detalles multilínea
    
    ### Manejo de conceptos multilínea:
    - Los conceptos pueden tener 3-4 líneas
    - Ejemplo: "SPEI RECIBIDO, BCO:0002 BANAMEX HR LIQ: 14:54:24 DEL CLIENTE NATALY
    MORALES HERNANDEZ DE LA CLABE 002650700555078387 CON RFC MOHN850126221
    CONCEPTO: Transferencia interbancaria REFERENCIA: 0030123 CVE RAST: 085902932284300331"
    - Combinar todas las líneas del concepto en un solo campo
    
    ### Reglas importantes:
    - Extraer TODOS los movimientos de la tabla
    - Mantener el formato de fechas "DD-MMM-YY"
    - Usar comas en los números (ej: "197,200.00")
    - Si no hay depósito o retiro, usar null
    - NO incluir líneas de resumen como "TOTAL"
    - Solo extraer movimientos reales
    
    ### CLASIFICACIÓN DE CARGOS Y ABONOS:
    
    #### ABONOS (MONTO_DEL_DEPOSITO):
    - "DEPOSITO DE CUENTA DE TERCEROS" → ABONO (ingreso de dinero)
    - "SPEI RECIBIDO" → ABONO (ingreso de dinero)
    - "CUENTAS POR PAGAR - SAP" → ABONO (ingreso de dinero)
    - "SALDO ANTERIOR" → ABONO de "0.00" (solo para el primer movimiento)
    
    #### CARGOS (MONTO_DEL_RETIRO):
    - "TRASPASO A CUENTA DE TERCEROS" → CARGO (egreso de dinero)
    - "COMPRA ORDEN DE PAGO SPEI" → CARGO (egreso de dinero)
    - "PAGO" → CARGO (egreso de dinero)
    - "DISPOSICIÓN" → CARGO (egreso de dinero)
    
    ### EJEMPLOS ESPECÍFICOS:
    - "SALDO ANTERIOR" → MONTO_DEL_DEPOSITO: "0.00", MONTO_DEL_RETIRO: null, SALDO: "1,190,950.98"
    - "DEPOSITO DE CUENTA DE TERCEROS" → MONTO_DEL_DEPOSITO: "197,200.00", MONTO_DEL_RETIRO: null, SALDO: "1,388,150.98"
    - "SPEI RECIBIDO" → MONTO_DEL_DEPOSITO: "11,658.00", MONTO_DEL_RETIRO: null, SALDO: "1,399,808.98"
    - "TRASPASO A CUENTA DE TERCEROS" → MONTO_DEL_DEPOSITO: null, MONTO_DEL_RETIRO: "110,254.00", SALDO: "1,289,554.98"
    - "COMPRA ORDEN DE PAGO SPEI" → MONTO_DEL_DEPOSITO: null, MONTO_DEL_RETIRO: "70,000.00", SALDO: "1,219,554.98"
    - "CUENTAS POR PAGAR - SAP" → MONTO_DEL_DEPOSITO: "437,359.86", MONTO_DEL_RETIRO: null, SALDO: "1,540,001.84"
    
    ## ATENCIÓN ESPECÍFICA PARA BANORTE:
    - El MONTO_DEL_DEPOSITO es el valor que aparece en la columna "MONTO DEL DEPOSITO"
    - El MONTO_DEL_RETIRO es el valor que aparece en la columna "MONTO DEL RETIRO"
    - El SALDO es el valor que aparece en la columna "SALDO"
    - NO uses el saldo como monto del movimiento
    - Para "SALDO ANTERIOR": usar MONTO_DEL_DEPOSITO: "0.00" (abono de 0)
    - "CUENTAS POR PAGAR" es un ABONO (ingreso de dinero), NO un cargo
    - "TRASPASO A CUENTA DE TERCEROS" es un CARGO (egreso de dinero)
    
    ## IMPORTANTE:
    - Devuelve SOLO el JSON, sin texto adicional
    - No incluyas explicaciones ni comentarios
    - Asegúrate de que el JSON sea válido
    - Extrae TODOS los movimientos de la tabla completa
    """ 