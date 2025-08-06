#!/usr/bin/env python3
"""
Script para probar el manejo de JSON malformado
"""

from app.conciliacion.gemini_processor import GeminiProcessor

def test_malformed_json():
    """Prueba el manejo de JSON malformado"""
    processor = GeminiProcessor()
    
    # Simular respuesta JSON malformada como la que vimos en los logs
    malformed_response = '''```json
{
  "banco_detectado": "INBURSA",
  "periodo_detectado": "Mayo 2025",
  "movimientos": [
    {
      "fecha": "01/05/2025",
      "referencia": null,
      "concepto": "BALANCE INICIAL",
      "monto": 44432.09,
      "tipo_movimiento": "abono",
      "saldo": 44432.09
    },
    {
      "fecha": "02/05/2025",
      "referencia": "3407784114",
      "concepto": "LIQUIDACION ADQUIRENTE CREDITO LIQUIDACION ADQ CREDITO-8993380",
      "monto": 165.00,
      "tipo_movimiento": "abono",
      "saldo": 44597.09
    }
  ]
}```'''
    
    print("🧪 Probando parsing de JSON malformado...")
    
    # Probar el parsing mejorado
    resultado = processor._parsear_respuesta_json(malformed_response)
    
    if resultado:
        print(f"✅ JSON parseado exitosamente")
        print(f"🏦 Banco: {resultado.get('banco_detectado')}")
        print(f"📊 Movimientos: {len(resultado.get('movimientos', []))}")
        for i, mov in enumerate(resultado.get('movimientos', [])[:3]):
            print(f"  {i+1}. {mov.get('fecha')} - {mov.get('concepto', '')[:50]}...")
    else:
        print("❌ No se pudo parsear el JSON malformado")
    
    # Probar extracción básica
    print("\n🧪 Probando extracción básica...")
    resultado_basico = processor._extraer_info_basica(malformed_response)
    
    print(f"🏦 Banco detectado: {resultado_basico.get('banco_detectado')}")
    print(f"📊 Movimientos extraídos: {len(resultado_basico.get('movimientos', []))}")

if __name__ == "__main__":
    test_malformed_json() 