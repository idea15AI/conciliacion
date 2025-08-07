def crear_prompt_bbva_estructurado():
    """
    Crea el prompt específico para BBVA con formato estructurado.
    """
    return """
    # PROMPT PARA EXTRAER MOVIMIENTOS BBVA
    
    Extrae movimientos BBVA en JSON. Formato:
    ```json
    [
      {
        "FECHA": "DD/MMM",
        "OPER": "código",
        "LIQ": "fecha_liquidación", 
        "COD": "código",
        "DESCRIPCION": "descripción",
        "REFERENCIA": "referencia",
        "CARGOS": "monto",
        "ABONOS": "monto",
        "SALDO": "saldo"
      }
    ]
    ```
    
    ## FORMATO  DE BBVA:
    
    ### Estructura de tabla:
    ```
    FECHA SALDO
    OPER LIQ COD. DESCRIPCIÓN REFERENCIA CARGOS ABONOS OPERACIÓN LIQUIDACIÓN
    00058650000012201888
    BNET01002506200029230973
    JOSE JAVIER RODRIGUEZ MOLINA
    20/JUN 20/JUN T17 SPEI ENVIADO BANREGIO 2,000.00
    0200625JAVIER ROD Ref. 0029231831 058
    00058650000012201888
    BNET01002506200029231831
    JOSE JAVIER RODRIGUEZ MOLINA
    20/JUN 20/JUN T20 SPEI RECIBIDOBANORTE 330.00
    0250620Sin informaci n Ref. 0133124123 072
    ```
    
    ## REGLAS:
    - FECHA: "20/JUN", "21/JUN"
    - OPER: "T17", "T20", "N06"
    - LIQ: "20/JUN"
    - COD: "BANREGIO", "BANORTE", "BANCOPPEL"
    - DESCRIPCION: Descripción completa
    - REFERENCIA: Extraer del concepto (ej: "Ref. 0029231831")
    - CARGOS: Monto o null
    - ABONOS: Monto o null
    - SALDO: Saldo final
    
    ## CLASIFICACIÓN DE CARGOS Y ABONOS:
    
    #### CARGOS (CARGOS):
    - "SPEI ENVIADO" → CARGO (egreso de dinero)
    - "PAGO CUENTA DE TERCERO" → CARGO (cuando hay un monto en la columna CARGOS)
    
    #### ABONOS (ABONOS):
    - "SPEI RECIBIDO" → ABONO (ingreso de dinero)
    - "PAGO CUENTA DE TERCERO" → ABONO (cuando hay un monto en la columna ABONOS)
    
    ## EJEMPLOS:
    - "SPEI ENVIADO BANREGIO" → CARGOS: "2000.00", ABONOS: null
    - "SPEI RECIBIDOBANORTE" → CARGOS: null, ABONOS: "330.00"
    - "PAGO CUENTA DE TERCERO" → CARGOS: null, ABONOS: "1049.36"
    
    ## ATENCIÓN:
    - "SPEI ENVIADO" = CARGO
    - "SPEI RECIBIDO" = ABONO
    - "PAGO CUENTA DE TERCERO" = según columna CARGOS/ABONOS
    - REFERENCIAS dentro del concepto
    - Extraer TODOS los movimientos
    - SOLO JSON, sin texto adicional
    """ 