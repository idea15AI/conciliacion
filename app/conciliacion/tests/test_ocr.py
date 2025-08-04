"""
Tests unitarios para el procesador OCR

Tests específicos para el procesamiento OCR de estados de cuenta bancarios
usando mocks de OpenAI API y PyMuPDF.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import io
import base64
from datetime import datetime
from decimal import Decimal
from PIL import Image

from app.conciliacion.ocr_processor import OCRProcessor
from app.conciliacion.models import TipoBanco, TipoMovimiento
from app.conciliacion.exceptions import (
    OCRError, PDFProcessingError, BancoNoReconocidoError,
    FormatoBancarioInvalidoError, ExternalServiceError
)


# === FIXTURES ===

@pytest.fixture
def mock_openai_client():
    """Mock del cliente OpenAI"""
    client = Mock()
    
    # Mock response para detección de banco
    mock_response_banco = Mock()
    mock_response_banco.choices = [Mock()]
    mock_response_banco.choices[0].message.content = "bbva"
    
    # Mock response para metadatos  
    mock_response_metadatos = Mock()
    mock_response_metadatos.choices = [Mock()]
    mock_response_metadatos.choices[0].message.content = '''
    {
        "periodo_inicio": "2024-01-01",
        "periodo_fin": "2024-01-31", 
        "numero_cuenta": "1234",
        "saldo_inicial": "5000.00",
        "saldo_final": "4500.00",
        "nombre_titular": "EMPRESA TEST SA",
        "sucursal": "001",
        "tipo_cuenta": "CORRIENTE"
    }
    '''
    
    # Mock response para movimientos
    mock_response_movimientos = Mock()
    mock_response_movimientos.choices = [Mock()]
    mock_response_movimientos.choices[0].message.content = '''
    [
        {
            "fecha": "15/01/2024",
            "concepto": "PAGO FACTURA A1234 EMPRESA XYZ",
            "monto": "1250.50",
            "tipo": "cargo",
            "referencia": "REF123456",
            "saldo": "4500.00"
        }
    ]
    '''
    
    client.chat.completions.create.side_effect = [
        mock_response_banco,      # Primera llamada: detección banco
        mock_response_metadatos,  # Segunda llamada: metadatos
        mock_response_movimientos # Tercera llamada: movimientos
    ]
    
    return client


@pytest.fixture
def mock_pdf_bytes():
    """Bytes de PDF de prueba"""
    return b'%PDF-1.4\n%test pdf content...'


@pytest.fixture
def mock_pil_image():
    """Imagen PIL de prueba"""
    # Crear imagen simple de 100x100 píxeles
    image = Image.new('RGB', (100, 100), color='white')
    return image


@pytest.fixture
def ocr_processor(mock_openai_client):
    """Procesador OCR configurado para tests"""
    with patch('app.conciliacion.ocr_processor.OpenAI') as mock_openai:
        mock_openai.return_value = mock_openai_client
        processor = OCRProcessor("test-api-key")
        processor.client = mock_openai_client
        return processor


# === TESTS DE INICIALIZACIÓN ===

class TestOCRProcessorInit:
    """Tests de inicialización del procesador OCR"""
    
    @patch('app.conciliacion.ocr_processor.OpenAI')
    def test_init_con_api_key(self, mock_openai):
        """Test inicialización con API key"""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        processor = OCRProcessor("test-key")
        
        mock_openai.assert_called_once_with(api_key="test-key")
        assert processor.client == mock_client
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'})
    @patch('app.conciliacion.ocr_processor.OpenAI')
    def test_init_con_env_var(self, mock_openai):
        """Test inicialización con variable de entorno"""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        processor = OCRProcessor()
        
        mock_openai.assert_called_once_with(api_key="env-key")
    
    def test_init_sin_api_key(self):
        """Test error sin API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OCRProcessor()
            
            assert "OPENAI_API_KEY es requerida" in str(exc_info.value)


# === TESTS DE CONVERSIÓN PDF ===

class TestPDFConversion:
    """Tests de conversión de PDF a imágenes"""
    
    @patch('app.conciliacion.ocr_processor.fitz')
    def test_convertir_pdf_exitoso(self, mock_fitz, ocr_processor, mock_pdf_bytes):
        """Test conversión exitosa de PDF"""
        # Configurar mock de PyMuPDF
        mock_doc = Mock()
        mock_page = Mock()
        mock_pixmap = Mock()
        
        mock_fitz.open.return_value = mock_doc
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_pixmap.tobytes.return_value = b'fake-png-data'
        
        # Mock PIL Image.open
        with patch('app.conciliacion.ocr_processor.Image.open') as mock_image_open:
            mock_image = Mock(spec=Image.Image)
            mock_image_open.return_value = mock_image
            
            imagenes = ocr_processor._convertir_pdf_a_imagenes(mock_pdf_bytes)
            
            assert len(imagenes) == 1
            assert imagenes[0] == mock_image
            mock_doc.close.assert_called_once()
    
    @patch('app.conciliacion.ocr_processor.fitz')
    def test_convertir_pdf_error(self, mock_fitz, ocr_processor, mock_pdf_bytes):
        """Test error en conversión de PDF"""
        mock_fitz.open.side_effect = Exception("Error PyMuPDF")
        
        with pytest.raises(PDFProcessingError) as exc_info:
            ocr_processor._convertir_pdf_a_imagenes(mock_pdf_bytes)
        
        assert "Error convirtiendo PDF" in str(exc_info.value)
    
    @patch('app.conciliacion.ocr_processor.fitz')
    def test_pdf_sin_paginas(self, mock_fitz, ocr_processor, mock_pdf_bytes):
        """Test PDF sin páginas extraíbles"""
        mock_doc = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.side_effect = Exception("Error página")
        
        with pytest.raises(PDFProcessingError) as exc_info:
            ocr_processor._convertir_pdf_a_imagenes(mock_pdf_bytes)
        
        assert "No se pudieron extraer páginas" in str(exc_info.value)


# === TESTS DE DETECCIÓN DE BANCO ===

class TestDeteccionBanco:
    """Tests de detección automática de banco"""
    
    def test_detectar_banco_bbva(self, ocr_processor, mock_pil_image):
        """Test detección de BBVA"""
        # El mock ya está configurado para retornar "bbva"
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            banco = ocr_processor._detectar_banco(mock_pil_image)
            
            assert banco == TipoBanco.BBVA
    
    def test_detectar_banco_no_reconocido(self, ocr_processor, mock_pil_image):
        """Test banco no reconocido"""
        # Configurar respuesta con banco inválido
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "banco_inexistente"
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            with pytest.raises(BancoNoReconocidoError):
                ocr_processor._detectar_banco(mock_pil_image)
    
    def test_detectar_banco_mapeo_nombres(self, ocr_processor, mock_pil_image):
        """Test mapeo de nombres alternativos"""
        # Configurar respuesta con nombre alternativo
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "bancomer"  # Nombre alternativo para BBVA
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            banco = ocr_processor._detectar_banco(mock_pil_image)
            
            assert banco == TipoBanco.BBVA
    
    def test_detectar_banco_error_openai(self, ocr_processor, mock_pil_image):
        """Test error de OpenAI en detección"""
        ocr_processor.client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            with pytest.raises(ExternalServiceError):
                ocr_processor._detectar_banco(mock_pil_image)


# === TESTS DE EXTRACCIÓN DE METADATOS ===

class TestExtraccionMetadatos:
    """Tests de extracción de metadatos"""
    
    def test_extraer_metadatos_exitoso(self, ocr_processor, mock_pil_image):
        """Test extracción exitosa de metadatos"""
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            metadatos = ocr_processor._extraer_metadatos(mock_pil_image, TipoBanco.BBVA)
            
            assert metadatos["periodo_inicio"] == datetime(2024, 1, 1)
            assert metadatos["periodo_fin"] == datetime(2024, 1, 31)
            assert metadatos["numero_cuenta"] == "1234"
            assert metadatos["saldo_inicial"] == Decimal('5000.00')
            assert metadatos["saldo_final"] == Decimal('4500.00')
    
    def test_extraer_metadatos_json_invalido(self, ocr_processor, mock_pil_image):
        """Test JSON inválido en metadatos"""
        # Configurar respuesta con JSON inválido
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "json inválido"
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            metadatos = ocr_processor._extraer_metadatos(mock_pil_image, TipoBanco.BBVA)
            
            # Debería retornar metadatos vacíos
            assert metadatos["periodo_inicio"] is None
            assert metadatos["numero_cuenta"] is None
    
    def test_extraer_metadatos_con_markdown(self, ocr_processor, mock_pil_image):
        """Test respuesta con formato markdown"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
        {
            "periodo_inicio": "2024-01-01",
            "periodo_fin": "2024-01-31",
            "numero_cuenta": "1234",
            "saldo_inicial": null,
            "saldo_final": null,
            "nombre_titular": null,
            "sucursal": null,
            "tipo_cuenta": null
        }
        ```'''
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            metadatos = ocr_processor._extraer_metadatos(mock_pil_image, TipoBanco.BBVA)
            
            assert metadatos["periodo_inicio"] == datetime(2024, 1, 1)
            assert metadatos["numero_cuenta"] == "1234"


# === TESTS DE PROCESAMIENTO DE MOVIMIENTOS ===

class TestProcesamientoMovimientos:
    """Tests de procesamiento de movimientos"""
    
    def test_procesar_pagina_movimientos_exitoso(self, ocr_processor, mock_pil_image):
        """Test procesamiento exitoso de movimientos"""
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            movimientos = ocr_processor._procesar_pagina_movimientos(
                mock_pil_image, TipoBanco.BBVA, 1
            )
            
            assert len(movimientos) == 1
            mov = movimientos[0]
            assert mov["fecha"] == "15/01/2024"
            assert mov["concepto"] == "PAGO FACTURA A1234 EMPRESA XYZ"
            assert mov["monto"] == "1250.50"
            assert mov["tipo"] == "cargo"
            assert mov["pagina_origen"] == 1
    
    def test_procesar_pagina_sin_movimientos(self, ocr_processor, mock_pil_image):
        """Test página sin movimientos"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "[]"
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            movimientos = ocr_processor._procesar_pagina_movimientos(
                mock_pil_image, TipoBanco.BBVA, 1
            )
            
            assert len(movimientos) == 0
    
    def test_procesar_pagina_respuesta_invalida(self, ocr_processor, mock_pil_image):
        """Test respuesta inválida (no es lista)"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"error": "no es lista"}'
        ocr_processor.client.chat.completions.create.return_value = mock_response
        
        with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
            movimientos = ocr_processor._procesar_pagina_movimientos(
                mock_pil_image, TipoBanco.BBVA, 1
            )
            
            assert len(movimientos) == 0


# === TESTS DE VALIDACIÓN Y LIMPIEZA ===

class TestValidacionLimpieza:
    """Tests de validación y limpieza de datos"""
    
    def test_validar_y_limpiar_movimientos_exitoso(self, ocr_processor):
        """Test validación exitosa"""
        movimientos_raw = [
            {
                "fecha": "15/01/2024",
                "concepto": "PAGO FACTURA TEST",
                "monto": "1250.50",
                "tipo": "cargo",
                "referencia": "REF123",
                "saldo": "4500.00",
                "pagina_origen": 1
            }
        ]
        
        movimientos_limpios = ocr_processor._validar_y_limpiar_movimientos(movimientos_raw)
        
        assert len(movimientos_limpios) == 1
        mov = movimientos_limpios[0]
        assert isinstance(mov["fecha"], datetime)
        assert mov["monto"] == Decimal('1250.50')
        assert mov["tipo"] == TipoMovimiento.CARGO
    
    def test_filtrar_movimientos_invalidos(self, ocr_processor):
        """Test filtrado de movimientos inválidos"""
        movimientos_raw = [
            {
                "fecha": "fecha_invalida",
                "concepto": "CONCEPTO VÁLIDO",
                "monto": "1250.50",
                "tipo": "cargo"
            },
            {
                "fecha": "15/01/2024",
                "concepto": "",  # Concepto vacío
                "monto": "1250.50",
                "tipo": "cargo"
            },
            {
                "fecha": "15/01/2024",
                "concepto": "CONCEPTO VÁLIDO",
                "monto": "monto_invalido",  # Monto inválido
                "tipo": "cargo"
            },
            {
                "fecha": "15/01/2024",
                "concepto": "CONCEPTO VÁLIDO",
                "monto": "1250.50",
                "tipo": "tipo_invalido"  # Tipo inválido
            }
        ]
        
        movimientos_limpios = ocr_processor._validar_y_limpiar_movimientos(movimientos_raw)
        
        # Todos deberían ser filtrados por ser inválidos
        assert len(movimientos_limpios) == 0
    
    def test_limpiar_fecha_formatos(self, ocr_processor):
        """Test limpieza de diferentes formatos de fecha"""
        assert ocr_processor._limpiar_fecha("15/01/2024") == datetime(2024, 1, 15)
        assert ocr_processor._limpiar_fecha("15-01-2024") == datetime(2024, 1, 15)
        assert ocr_processor._limpiar_fecha("2024-01-15") == datetime(2024, 1, 15)
        assert ocr_processor._limpiar_fecha("15/01/24") == datetime(2024, 1, 15)
        assert ocr_processor._limpiar_fecha("fecha_invalida") is None
    
    def test_limpiar_monto_formatos(self, ocr_processor):
        """Test limpieza de diferentes formatos de monto"""
        assert ocr_processor._limpiar_monto("1250.50") == Decimal('1250.50')
        assert ocr_processor._limpiar_monto("$1,250.50") == Decimal('1250.50')
        assert ocr_processor._limpiar_monto("(100.50)") == Decimal('-100.50')  # Negativo
        assert ocr_processor._limpiar_monto("monto_invalido") is None
    
    def test_limpiar_tipo_movimiento(self, ocr_processor):
        """Test limpieza de tipos de movimiento"""
        assert ocr_processor._limpiar_tipo("cargo") == TipoMovimiento.CARGO
        assert ocr_processor._limpiar_tipo("ABONO") == TipoMovimiento.ABONO
        assert ocr_processor._limpiar_tipo("débito") == TipoMovimiento.CARGO
        assert ocr_processor._limpiar_tipo("crédito") == TipoMovimiento.ABONO
        assert ocr_processor._limpiar_tipo("tipo_invalido") is None


# === TESTS DE ELIMINACIÓN DE DUPLICADOS ===

class TestEliminacionDuplicados:
    """Tests de eliminación de duplicados"""
    
    def test_eliminar_duplicados_exactos(self, ocr_processor):
        """Test eliminación de duplicados exactos"""
        fecha = datetime(2024, 1, 15)
        movimientos = [
            {
                "fecha": fecha,
                "concepto": "PAGO DUPLICADO",
                "monto": Decimal('1000.00')
            },
            {
                "fecha": fecha,
                "concepto": "PAGO DUPLICADO",
                "monto": Decimal('1000.00')
            }
        ]
        
        unicos = ocr_processor._eliminar_duplicados(movimientos)
        
        assert len(unicos) == 1
    
    def test_no_eliminar_similares_pero_diferentes(self, ocr_processor):
        """Test no eliminar movimientos similares pero diferentes"""
        fecha = datetime(2024, 1, 15)
        movimientos = [
            {
                "fecha": fecha,
                "concepto": "PAGO EMPRESA A",
                "monto": Decimal('1000.00')
            },
            {
                "fecha": fecha,
                "concepto": "PAGO EMPRESA B",  # Concepto diferente
                "monto": Decimal('1000.00')
            }
        ]
        
        unicos = ocr_processor._eliminar_duplicados(movimientos)
        
        assert len(unicos) == 2


# === TESTS DE INTEGRACIÓN COMPLETA ===

class TestIntegracionOCR:
    """Tests de integración del procesamiento completo"""
    
    @patch('app.conciliacion.ocr_processor.fitz')
    def test_procesar_estado_cuenta_completo(self, mock_fitz, ocr_processor, mock_pdf_bytes):
        """Test del flujo completo de procesamiento"""
        # Configurar mocks para PDF
        mock_doc = Mock()
        mock_page = Mock()
        mock_pixmap = Mock()
        
        mock_fitz.open.return_value = mock_doc
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_pixmap.tobytes.return_value = b'fake-png-data'
        
        # Mock PIL Image
        with patch('app.conciliacion.ocr_processor.Image.open') as mock_image_open:
            mock_image = Mock(spec=Image.Image)
            mock_image_open.return_value = mock_image
            
            with patch.object(ocr_processor, '_imagen_a_base64', return_value="fake-base64"):
                resultado = ocr_processor.procesar_estado_cuenta(mock_pdf_bytes, 1)
                
                assert resultado["exito"] is True
                assert resultado["banco_detectado"] == TipoBanco.BBVA
                assert resultado["total_movimientos"] == 1
                assert "hash_archivo" in resultado
                assert "metadatos" in resultado
                assert "tiempo_procesamiento" in resultado
    
    def test_procesar_estado_cuenta_error_pdf(self, ocr_processor):
        """Test error en procesamiento de PDF"""
        pdf_invalido = b"no es un pdf"
        
        with patch.object(ocr_processor, '_convertir_pdf_a_imagenes', 
                         side_effect=PDFProcessingError("Error PDF", "test.pdf")):
            with pytest.raises(PDFProcessingError):
                ocr_processor.procesar_estado_cuenta(pdf_invalido, 1)


# === TESTS DE CONFIGURACIÓN ===

class TestConfiguracion:
    """Tests de configuración específica por banco"""
    
    def test_configuraciones_banco(self, ocr_processor):
        """Test configuraciones específicas por banco"""
        config_bbva = ocr_processor.configuraciones_banco[TipoBanco.BBVA.value]
        
        assert "formatos_fecha" in config_bbva
        assert "patrones_referencia" in config_bbva
        assert "columnas_esperadas" in config_bbva
        
        # Verificar que tiene configuraciones diferentes para distintos bancos
        config_santander = ocr_processor.configuraciones_banco[TipoBanco.SANTANDER.value]
        assert config_bbva != config_santander


# === CONFIGURACIÓN DE PYTEST ===

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mocks entre tests"""
    yield
    # Cleanup si es necesario


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 