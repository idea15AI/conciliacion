"""
Tests unitarios para el módulo de conciliación bancaria avanzada

Incluye tests para todas las estrategias de conciliación, validaciones,
y casos edge del sistema.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

# Imports del módulo
from app.conciliacion.conciliador import ConciliadorAvanzado
from app.conciliacion.models import (
    MovimientoBancario, EstadoConciliacion, MetodoConciliacion, TipoMovimiento
)
from app.conciliacion.schemas import EstadisticasConciliacion
from app.conciliacion.utils import (
    comparar_montos, calcular_similitud_texto, normalizar_texto,
    extraer_rfc_de_texto, validar_rfc, calcular_rango_fechas
)
from app.conciliacion.exceptions import (
    ConciliacionError, DatosInsuficientesError, EmpresaNoEncontradaError
)
from app.models.mysql_models import ComprobanteFiscal, EmpresaContribuyente


# === FIXTURES ===

@pytest.fixture
def mock_db():
    """Mock de sesión de base de datos"""
    db = Mock(spec=Session)
    db.query.return_value = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.flush = Mock()
    return db


@pytest.fixture
def empresa_test():
    """Empresa de prueba"""
    empresa = EmpresaContribuyente()
    empresa.id = 1
    empresa.rfc = "TST123456789"
    empresa.razon_social = "Empresa Test SA de CV"
    return empresa


@pytest.fixture
def movimiento_bancario_test():
    """Movimiento bancario de prueba"""
    movimiento = MovimientoBancario()
    movimiento.id = 1
    movimiento.empresa_id = 1
    movimiento.fecha = datetime(2024, 1, 15)
    movimiento.concepto = "PAGO FACTURA A1234 EMPRESA XYZ SA DE CV"
    movimiento.monto = Decimal('1250.50')
    movimiento.tipo = TipoMovimiento.CARGO
    movimiento.referencia = "REF123456"
    movimiento.estado = EstadoConciliacion.PENDIENTE
    return movimiento


@pytest.fixture
def cfdi_test():
    """CFDI de prueba"""
    cfdi = ComprobanteFiscal()
    cfdi.id = 1
    cfdi.uuid = "12345678-1234-1234-1234-123456789012"
    cfdi.empresa_id = 1
    cfdi.fecha = datetime(2024, 1, 15)
    cfdi.total = Decimal('1250.50')
    cfdi.nombre_emisor = "EMPRESA XYZ SA DE CV"
    cfdi.nombre_receptor = "EMPRESA TEST SA DE CV"
    cfdi.rfc_emisor = "EXY123456789"
    cfdi.rfc_receptor = "TST123456789"
    cfdi.tipo_comprobante = 'I'
    cfdi.estatus_sat = True
    return cfdi


@pytest.fixture
def conciliador(mock_db):
    """Conciliador configurado para tests"""
    return ConciliadorAvanzado(mock_db)


# === TESTS DE UTILIDADES ===

class TestUtils:
    """Tests para funciones auxiliares"""
    
    def test_normalizar_texto(self):
        """Test normalización de texto"""
        assert normalizar_texto("PAGO Factura Ñoño") == "pago factura nono"
        assert normalizar_texto("  Múltiples    espacios  ") == "multiples espacios"
        assert normalizar_texto("Caracteres-Especiales@#$") == "caracteres especiales"
    
    def test_comparar_montos_exacto(self):
        """Test comparación exacta de montos"""
        resultado = comparar_montos(Decimal('1250.50'), Decimal('1250.50'))
        assert resultado["exacto"] is True
        assert resultado["diferencia"] == Decimal('0.00')
        assert resultado["dentro_tolerancia"] is True
    
    def test_comparar_montos_tolerancia(self):
        """Test comparación con tolerancia"""
        resultado = comparar_montos(
            Decimal('1250.50'), 
            Decimal('1251.00'), 
            Decimal('1.00')
        )
        assert resultado["exacto"] is False
        assert resultado["aproximado"] is True
        assert resultado["dentro_tolerancia"] is True
        assert resultado["diferencia"] == Decimal('0.50')
    
    def test_comparar_montos_fuera_tolerancia(self):
        """Test montos fuera de tolerancia"""
        resultado = comparar_montos(
            Decimal('1250.00'), 
            Decimal('1260.00'), 
            Decimal('5.00')
        )
        assert resultado["dentro_tolerancia"] is False
    
    def test_calcular_similitud_texto(self):
        """Test cálculo de similitud entre textos"""
        similitud = calcular_similitud_texto(
            "PAGO FACTURA EMPRESA XYZ",
            "FACTURA EMPRESA XYZ SA DE CV"
        )
        assert 0.5 <= similitud <= 1.0
        
        # Textos idénticos
        assert calcular_similitud_texto("MISMO TEXTO", "MISMO TEXTO") == 1.0
        
        # Textos completamente diferentes
        similitud_baja = calcular_similitud_texto("ABC", "XYZ")
        assert similitud_baja < 0.3
    
    def test_extraer_rfc_de_texto(self):
        """Test extracción de RFCs de texto"""
        texto = "PAGO A RFC EMPRESA ABC123456789 CONCEPTO DEF987654321"
        rfcs = extraer_rfc_de_texto(texto)
        assert "ABC123456789" in rfcs
        assert "DEF987654321" in rfcs
        assert len(rfcs) == 2
    
    def test_validar_rfc(self):
        """Test validación de RFC"""
        # RFC persona moral válido
        assert validar_rfc("ABC123456789") is True
        
        # RFC persona física válido
        assert validar_rfc("ABCD123456789") is True
        
        # RFCs inválidos
        assert validar_rfc("ABC12345") is False
        assert validar_rfc("") is False
        assert validar_rfc("INVALID") is False
    
    def test_calcular_rango_fechas(self):
        """Test cálculo de rango de fechas"""
        inicio, fin = calcular_rango_fechas(3, 2024)  # Marzo 2024
        
        assert inicio.year == 2024
        assert inicio.month == 3
        assert inicio.day == 1
        assert inicio.hour == 0
        
        assert fin.year == 2024
        assert fin.month == 3
        assert fin.day == 31
        assert fin.hour == 23
    
    def test_calcular_rango_fechas_febrero(self):
        """Test rango de fechas para febrero año bisiesto"""
        inicio, fin = calcular_rango_fechas(2, 2024)  # Febrero 2024 (bisiesto)
        assert fin.day == 29
        
        # Año no bisiesto
        inicio, fin = calcular_rango_fechas(2, 2023)
        assert fin.day == 28


# === TESTS DEL CONCILIADOR ===

class TestConciliadorAvanzado:
    """Tests para el conciliador principal"""
    
    def test_init_conciliador(self, mock_db):
        """Test inicialización del conciliador"""
        conciliador = ConciliadorAvanzado(mock_db)
        assert conciliador.db == mock_db
        assert isinstance(conciliador.estadisticas, EstadisticasConciliacion)
        assert conciliador.config["tolerancia_monto_default"] == Decimal('1.00')
    
    @patch('app.conciliacion.conciliador.ConciliadorAvanzado._precargar_datos')
    @patch('app.conciliacion.conciliador.ConciliadorAvanzado._obtener_movimientos_pendientes')
    @patch('app.conciliacion.conciliador.ConciliadorAvanzado._obtener_cfdis_periodo')
    def test_conciliar_periodo_sin_datos(self, mock_cfdis, mock_movimientos, mock_precargar, conciliador):
        """Test conciliación sin datos disponibles"""
        # Mock sin movimientos
        mock_movimientos.return_value = []
        
        with pytest.raises(DatosInsuficientesError) as exc_info:
            conciliador.conciliar_periodo(
                empresa_id=1,
                fecha_inicio=datetime(2024, 1, 1),
                fecha_fin=datetime(2024, 1, 31)
            )
        
        assert "No hay movimientos bancarios pendientes" in str(exc_info.value)
    
    def test_estrategia_match_exacto(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test estrategia de match exacto"""
        # Configurar mocks
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        # Mock del método _conciliar_movimiento
        conciliador._conciliar_movimiento = Mock()
        
        # Ejecutar estrategia
        conciliador._estrategia_match_exacto(movimientos, cfdis)
        
        # Verificar que se llamó _conciliar_movimiento
        conciliador._conciliar_movimiento.assert_called_once_with(
            movimiento_bancario_test,
            cfdi_test,
            MetodoConciliacion.EXACTO,
            Decimal('0.95')
        )
        
        assert conciliador.estadisticas.conciliados_exacto == 1
    
    def test_estrategia_match_exacto_sin_coincidencia(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test estrategia match exacto sin coincidencia"""
        # Cambiar monto para que no coincida
        cfdi_test.total = Decimal('2000.00')
        
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        conciliador._conciliar_movimiento = Mock()
        conciliador._estrategia_match_exacto(movimientos, cfdis)
        
        # No debería haberse llamado
        conciliador._conciliar_movimiento.assert_not_called()
        assert conciliador.estadisticas.conciliados_exacto == 0
    
    def test_estrategia_match_referencia(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test estrategia match por referencia"""
        # Configurar referencia con UUID del CFDI
        movimiento_bancario_test.referencia = f"PAGO_{cfdi_test.uuid}_COMPLETO"
        
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        conciliador._conciliar_movimiento = Mock()
        conciliador._estrategia_match_referencia(movimientos, cfdis)
        
        # Debería encontrar el UUID en la referencia
        assert conciliador._conciliar_movimiento.called
        assert conciliador.estadisticas.conciliados_referencia >= 0
    
    def test_estrategia_match_aproximado(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test estrategia match aproximado"""
        # Configurar montos ligeramente diferentes pero dentro de tolerancia
        movimiento_bancario_test.monto = Decimal('1250.00')
        cfdi_test.total = Decimal('1250.50')  # Diferencia de 0.50
        
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        conciliador._conciliar_movimiento = Mock()
        conciliador._estrategia_match_aproximado(movimientos, cfdis)
        
        # Verificar llamada con nivel de confianza apropiado
        if conciliador._conciliar_movimiento.called:
            args = conciliador._conciliar_movimiento.call_args[0]
            assert args[2] == MetodoConciliacion.APROXIMADO
            assert args[3] <= Decimal('0.8')  # Confianza máxima para aproximado
    
    def test_validar_coherencia_tipo(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test validación de coherencia de tipos"""
        # Cargo con factura de ingreso - coherente
        movimiento_bancario_test.tipo = TipoMovimiento.CARGO
        cfdi_test.tipo_comprobante = 'I'
        
        assert conciliador._validar_coherencia_tipo(movimiento_bancario_test, cfdi_test) is True
        
        # Abono con factura de ingreso - coherente
        movimiento_bancario_test.tipo = TipoMovimiento.ABONO
        cfdi_test.tipo_comprobante = 'I'
        
        assert conciliador._validar_coherencia_tipo(movimiento_bancario_test, cfdi_test) is True
    
    def test_calcular_score_patron(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test cálculo de score por patrones"""
        # Configurar concepto con nombre del emisor
        movimiento_bancario_test.concepto = f"PAGO A {cfdi_test.nombre_emisor.lower()}"
        
        score = conciliador._calcular_score_patron(movimiento_bancario_test, cfdi_test)
        assert score > 0.0
        assert score <= 1.0
    
    def test_generar_sugerencias_inteligentes(self, conciliador, movimiento_bancario_test, cfdi_test):
        """Test generación de sugerencias"""
        # Movimiento similar pero no exacto
        movimiento_bancario_test.monto = Decimal('1200.00')  # Diferente al CFDI
        movimiento_bancario_test.estado = EstadoConciliacion.PENDIENTE
        
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        conciliador._calcular_score_sugerencia = Mock(return_value=0.6)
        conciliador._generar_razon_sugerencia = Mock(return_value="similitud general")
        
        conciliador._generar_sugerencias_inteligentes(movimientos, cfdis)
        
        assert len(conciliador.sugerencias) > 0
        sugerencia = conciliador.sugerencias[0]
        assert sugerencia.movimiento_id == movimiento_bancario_test.id
        assert sugerencia.cfdi_uuid == cfdi_test.uuid
    
    def test_detectar_alertas_criticas(self, conciliador, movimiento_bancario_test):
        """Test detección de alertas críticas"""
        # Movimiento grande sin conciliar
        movimiento_bancario_test.monto = Decimal('15000.00')
        movimiento_bancario_test.estado = EstadoConciliacion.PENDIENTE
        
        conciliador.estadisticas.total_movimientos_bancarios = 10
        conciliador.estadisticas.movimientos_conciliados = 5  # 50% conciliado
        
        movimientos = [movimiento_bancario_test]
        cfdis = []
        
        conciliador._detectar_alertas_criticas(movimientos, cfdis)
        
        # Debería haber alertas
        assert len(conciliador.alertas_criticas) > 0
        
        # Verificar alerta de movimiento grande
        alerta_grande = next(
            (a for a in conciliador.alertas_criticas if a.tipo == "MOVIMIENTO_GRANDE_PENDIENTE"),
            None
        )
        assert alerta_grande is not None
        assert alerta_grande.gravedad == "alto"


# === TESTS DE INTEGRACIÓN ===

class TestIntegracionConciliacion:
    """Tests de integración para el flujo completo"""
    
    @patch('app.conciliacion.conciliador.ConciliadorAvanzado._precargar_datos')
    def test_flujo_conciliacion_completo(self, mock_precargar, conciliador, movimiento_bancario_test, cfdi_test):
        """Test del flujo completo de conciliación"""
        # Configurar datos de prueba
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi_test]
        
        # Mock de métodos de base de datos
        conciliador.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = movimientos
        
        # Mock de métodos internos
        conciliador._obtener_movimientos_pendientes = Mock(return_value=movimientos)
        conciliador._obtener_cfdis_periodo = Mock(return_value=cfdis)
        conciliador._conciliar_movimiento = Mock()
        
        # Ejecutar conciliación
        resultado = conciliador.conciliar_periodo(
            empresa_id=1,
            fecha_inicio=datetime(2024, 1, 1),
            fecha_fin=datetime(2024, 1, 31)
        )
        
        # Verificaciones
        assert resultado["exito"] is True
        assert "estadisticas" in resultado
        assert "alertas_criticas" in resultado
        assert "sugerencias" in resultado
        assert resultado["tiempo_procesamiento_segundos"] >= 0
    
    def test_manejo_errores_conciliacion(self, conciliador):
        """Test manejo de errores durante conciliación"""
        # Simular error en precargar datos
        conciliador._precargar_datos = Mock(side_effect=Exception("Error DB"))
        
        resultado = conciliador.conciliar_periodo(
            empresa_id=1,
            fecha_inicio=datetime(2024, 1, 1),
            fecha_fin=datetime(2024, 1, 31)
        )
        
        assert resultado["exito"] is False
        assert "Error DB" in resultado["mensaje"]


# === TESTS DE CASOS EDGE ===

class TestCasosEdge:
    """Tests para casos límite y edge cases"""
    
    def test_movimiento_sin_referencia(self, conciliador, cfdi_test):
        """Test movimiento sin referencia bancaria"""
        movimiento = MovimientoBancario()
        movimiento.referencia = None
        movimiento.concepto = "PAGO SIN REFERENCIA"
        movimiento.estado = EstadoConciliacion.PENDIENTE
        
        movimientos = [movimiento]
        cfdis = [cfdi_test]
        
        # No debería fallar
        conciliador._estrategia_match_referencia(movimientos, cfdis)
        
        # Debería intentar usar el concepto para buscar patrones
        assert True  # Si llega aquí sin error, el test pasa
    
    def test_monto_cero(self, conciliador):
        """Test manejo de montos en cero"""
        resultado = comparar_montos(Decimal('0.00'), Decimal('0.00'))
        assert resultado["exacto"] is True
        
        # Monto negativo vs positivo
        resultado = comparar_montos(Decimal('-100.00'), Decimal('100.00'))
        assert resultado["diferencia"] == Decimal('200.00')
    
    def test_fechas_extremas(self, conciliador):
        """Test manejo de fechas extremas"""
        # Fechas muy distantes
        fecha1 = datetime(2024, 1, 1)
        fecha2 = datetime(2024, 12, 31)
        
        from app.conciliacion.utils import calcular_score_fecha, esta_en_rango_fechas
        
        score = calcular_score_fecha(fecha1, fecha2, 30)
        assert score == 0.0  # Muy distantes
        
        en_rango = esta_en_rango_fechas(fecha1, fecha2, 3)
        assert en_rango is False
    
    def test_concepto_muy_largo(self, conciliador):
        """Test manejo de conceptos muy largos"""
        concepto_largo = "A" * 2000  # 2000 caracteres
        concepto_normalizado = normalizar_texto(concepto_largo)
        
        # Debería procesar sin error
        assert len(concepto_normalizado) > 0
        assert concepto_normalizado == "a" * 2000
    
    def test_multiples_cfdis_mismo_monto(self, conciliador, movimiento_bancario_test):
        """Test múltiples CFDIs con el mismo monto"""
        # Crear múltiples CFDIs con mismo monto
        cfdi1 = ComprobanteFiscal()
        cfdi1.uuid = "11111111-1111-1111-1111-111111111111"
        cfdi1.total = Decimal('1250.50')
        cfdi1.fecha = datetime(2024, 1, 15)
        cfdi1.nombre_emisor = "EMPRESA A"
        
        cfdi2 = ComprobanteFiscal()
        cfdi2.uuid = "22222222-2222-2222-2222-222222222222"
        cfdi2.total = Decimal('1250.50')
        cfdi2.fecha = datetime(2024, 1, 16)
        cfdi2.nombre_emisor = "EMPRESA B"
        
        movimientos = [movimiento_bancario_test]
        cfdis = [cfdi1, cfdi2]
        
        conciliador._conciliar_movimiento = Mock()
        conciliador._estrategia_match_exacto(movimientos, cfdis)
        
        # Debería conciliar solo con uno (el primero que coincida)
        assert conciliador._conciliar_movimiento.call_count <= 1


# === TESTS DE PERFORMANCE ===

class TestPerformance:
    """Tests de rendimiento y escalabilidad"""
    
    def test_performance_muchos_movimientos(self, conciliador):
        """Test rendimiento con muchos movimientos"""
        import time
        
        # Crear muchos movimientos mock
        movimientos = []
        for i in range(1000):
            mov = Mock()
            mov.id = i
            mov.estado = EstadoConciliacion.PENDIENTE
            mov.monto = Decimal(f'{100 + i}.00')
            mov.fecha = datetime(2024, 1, 1) + timedelta(days=i % 30)
            movimientos.append(mov)
        
        # Crear algunos CFDIs mock
        cfdis = []
        for i in range(100):
            cfdi = Mock()
            cfdi.uuid = f"uuid-{i}"
            cfdi.total = Decimal(f'{100 + i}.00')
            cfdi.fecha = datetime(2024, 1, 1) + timedelta(days=i % 30)
            cfdis.append(cfdi)
        
        # Medir tiempo de ejecución
        inicio = time.time()
        conciliador._estrategia_match_exacto(movimientos, cfdis)
        tiempo_transcurrido = time.time() - inicio
        
        # Debería procesar en tiempo razonable (menos de 5 segundos)
        assert tiempo_transcurrido < 5.0


# === TESTS DE MOCKS ===

class TestMocks:
    """Tests que requieren mocking extensivo"""
    
    @patch('app.conciliacion.ocr_processor.OpenAI')
    def test_mock_openai_api(self, mock_openai):
        """Test con mock de OpenAI API"""
        from app.conciliacion.ocr_processor import OCRProcessor
        
        # Configurar mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "bbva"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Crear processor
        processor = OCRProcessor("fake-api-key")
        
        # Verificar que se configuró correctamente
        assert processor.client == mock_client
    
    def test_mock_database_queries(self, mock_db, conciliador):
        """Test con mock de queries de base de datos"""
        # Configurar mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = []
        
        # Ejecutar método que usa DB
        resultado = conciliador._obtener_movimientos_pendientes(1, datetime.now(), datetime.now())
        
        # Verificar que se llamaron los métodos correctos
        mock_db.query.assert_called()
        mock_query.filter.assert_called()
        assert resultado == []


# === CONFIGURACIÓN DE PYTEST ===

@pytest.fixture(autouse=True)
def setup_logging():
    """Configurar logging para tests"""
    import logging
    logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 