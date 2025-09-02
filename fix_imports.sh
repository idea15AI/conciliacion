#!/usr/bin/env bash
set -e

# Lista de archivos que contienen el import viejo
FILES=(
  "app/core/main.py"
  "app/conciliacion/routes/procesar_pdf_unificado.py"
  "app/conciliacion/gemini_processor.py"
  "app/utils/performance_monitor.py"
)

for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    echo "🔧 Corrigiendo imports en $f"
    sed -i \
      -e 's/from app\.core\.config import settings/from app.core.settings import settings/g' \
      -e 's/import app\.core\.config as config/from app.core.settings import settings as config/g' \
      "$f"
  fi
done

echo "✅ Reemplazos terminados"
