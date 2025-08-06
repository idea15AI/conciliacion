#!/usr/bin/env python3
"""
Script para limpiar archivos innecesarios del proyecto
"""

import os
import shutil
from pathlib import Path

def cleanup_unused_files():
    """Elimina archivos que ya no se necesitan."""
    
    # Archivos a eliminar (solo procesamiento, sin BD)
    files_to_remove = [
        # Procesadores complejos que no usamos
        "app/conciliacion/advanced_pdf_processor.py",
        "app/conciliacion/bank_statement_processor.py", 
        "app/conciliacion/hybrid_processor.py",
        "app/conciliacion/invoice_processor.py",
        "app/conciliacion/pdf_extractor.py",
        "app/conciliacion/pdf_processor.py",
        "app/conciliacion/pdf_upload_service.py",
        "app/conciliacion/ocr_processor.py",
        
        # Router complejo (reemplazado por simple_router)
        "app/conciliacion/router.py",
        
        # Archivos de frontend innecesarios
        "frontend/gemini_upload.html",
        "frontend/gemini_upload_local.html",
        "frontend/pdf_upload_minimal.html",
        "frontend/advanced_processor_test.html",
        
        # Scripts de test innecesarios
        "scripts/test_pdf_extractor.py",
        "scripts/test_real_pdf.py",
        "scripts/test_conceptos_dos_lineas.py",
        "scripts/test_advanced_processor.py",
        "scripts/test_duplicates_allowed.py",
        "scripts/test_routes_quick.py",
        "scripts/open_test_interface.py",
        "scripts/open_gemini_interface.py",
        "scripts/create_real_format_pdf.py",
        "scripts/create_test_bank_statement.py",
        "scripts/install_advanced_libraries.py",
        
        # Documentación innecesaria
        "docs/MEJORAS_AVANZADAS.md",
    ]
    
    # Directorios a eliminar
    dirs_to_remove = [
        "app/conciliacion/tests/",  # Tests complejos
    ]
    
    print("🧹 Limpiando archivos innecesarios...")
    print("=" * 50)
    
    # Eliminar archivos
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Eliminado: {file_path}")
            except Exception as e:
                print(f"❌ Error eliminando {file_path}: {e}")
        else:
            print(f"⚠️ No encontrado: {file_path}")
    
    # Eliminar directorios
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Eliminado directorio: {dir_path}")
            except Exception as e:
                print(f"❌ Error eliminando directorio {dir_path}: {e}")
        else:
            print(f"⚠️ Directorio no encontrado: {dir_path}")
    
    print("\n📋 Archivos esenciales que se mantienen:")
    print("- app/conciliacion/simple_router.py (router principal)")
    print("- app/conciliacion/gemini_processor.py (procesador Gemini)")
    print("- app/conciliacion/exceptions.py (excepciones)")
    print("- app/conciliacion/models.py (modelos de BD)")
    print("- app/conciliacion/schemas.py (esquemas)")
    print("- app/conciliacion/utils.py (utilidades)")
    print("- frontend/simple_pdf_processor.html (interfaz principal)")
    print("- scripts/test_gemini_processor.py (test del procesador)")
    print("- scripts/install_gemini.py (instalación de Gemini)")
    
    print("\n🎉 Limpieza completada!")
    print("El sistema ahora está enfocado solo en:")
    print("- Extracción de PDFs con Gemini")
    print("- Visualización de resultados")
    print("- Sin persistencia en BD")

if __name__ == "__main__":
    cleanup_unused_files() 