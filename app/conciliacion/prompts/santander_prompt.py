def crear_prompt_santander_estructurado():
    """
    Crea el prompt específico para SANTANDER con formato estructurado.
    """
    return """
    # PROMPT PARA SANTANDER
    
    Extrae movimientos bancarios SANTANDER en formato JSON.
    
    ```json
    [
      {
        "FECHA": "DD-MMM-YYYY",
        "FOLIO - REFERENCIA": "referencia",
        "DESCRIPCION": "descripción",
        "MONTO_DEL_DEPOSITO": "monto",
        "MONTO_DEL_RETIRO": "monto", 
        "SALDO": "saldo"
      }
    ]
    ```
    
    ## REGLAS IMPORTANTES:
    - FECHA: Formato "DD-MMM-YYYY" (ej: "31-DIC-2023", "04-ENE-2024", "25-ENE-2024")
    - FOLIO = Número de referencia (ej: "3407784114", "6975217", "0985291")
    - MONTO_DEL_DEPOSITO = ABONO (ingreso) - SOLO el monto del depósito
    - MONTO_DEL_RETIRO = CARGO (egreso) - SOLO el monto del retiro
    - SALDO = Saldo resultante después del movimiento
    - Si no hay valor, usar null
    - Usar comas en números: "94,762.02", "1,680.26", "400,000.00"
    
    ## VERIFICACIÓN POR COLUMNAS:
    - Busca en la columna "DEPOSITOS" para MONTO_DEL_DEPOSITO
    - Busca en la columna "RETIROS" para MONTO_DEL_RETIRO
    - Busca en la columna "SALDO" para el saldo resultante
    - NO confundas el saldo con el monto del movimiento
    
    ## EJEMPLOS ESPECÍFICOS:
    - "SALDO FINAL DEL PERIODO ANTERIOR" → MONTO_DEL_DEPOSITO: "0.00", MONTO_DEL_RETIRO: null, SALDO: "589,428.18"
    - "DEPOSITO EN EFECTIVO" → MONTO_DEL_DEPOSITO: "94,762.02", MONTO_DEL_RETIRO: null, SALDO: "684,190.20"
    - "CARGO PAGO NOMINA POR APLICAR PAGO DE NOMINA" → MONTO_DEL_DEPOSITO: null, MONTO_DEL_RETIRO: "1,680.26", SALDO: "682,509.94"
    - "PAGO TRANSFERENCIA SPEI HORA 14:41:36" → MONTO_DEL_DEPOSITO: null, MONTO_DEL_RETIRO: "400,000.00", SALDO: "279,324.92"
    - "COM MEMBRESIA CUENTA E PYME MEMBRESIA" → MONTO_DEL_DEPOSITO: null, MONTO_DEL_RETIRO: "699.00", SALDO: "277,121.16"
    
    ## ATENCIÓN:
    - El MONTO_DEL_DEPOSITO es el valor que aparece en la columna "DEPOSITOS"
    - El MONTO_DEL_RETIRO es el valor que aparece en la columna "RETIROS"
    - El SALDO es el valor que aparece en la columna "SALDO"
    - NO uses el saldo como monto del movimiento
    - Para "SALDO FINAL DEL PERIODO ANTERIOR": usar MONTO_DEL_DEPOSITO: "0.00" (abono de 0)
    - Las fechas están en formato "DD-MMM" (ej: "31-ENE", "04-ENE", "25-ENE", "26-ENE")
    - Los montos pueden tener comas como separadores de miles
    
    Devuelve SOLO el JSON.
    """ 