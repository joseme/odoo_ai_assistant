#!/bin/bash
# ============================================================
#  Script de instalación - Odoo AI Assistant
#  Compatible con Odoo 17, 18 y 19
# ============================================================

set -e

echo "============================================"
echo "  Instalación de Odoo AI Assistant"
echo "============================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar permisos de root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Nota: Se recomienda ejecutar como root para instalar dependencias del sistema${NC}"
fi

# ---------------------------------------------------------- #
# 1. Instalar dependencias de Python
# ---------------------------------------------------------- #
echo -e "${GREEN}[1/5] Instalando dependencias de Python...${NC}"

pip3 install duckduckgo-search edge-tts vosk nest-asyncio 2>/dev/null || {
    echo -e "${YELLOW}Intentando con pip...${NC}"
    pip install duckduckgo-search edge-tts vosk nest-asyncio
}

echo -e "${GREEN}  ✓ Dependencias de Python instaladas${NC}"

# ---------------------------------------------------------- #
# 2. Descargar modelo de Vosk para reconocimiento de voz
# ---------------------------------------------------------- #
echo -e "${GREEN}[2/5] Descargando modelo de Vosk para reconocimiento de voz...${NC}"

VOSK_MODELS_DIR="/opt/vosk-models"
VOSK_MODEL="vosk-model-small-es-0.42"
VOSK_URL="https://alphacephei.com/vosk/models/${VOSK_MODEL}.zip"

mkdir -p "${VOSK_MODELS_DIR}"

if [ -d "${VOSK_MODELS_DIR}/${VOSK_MODEL}" ]; then
    echo -e "${YELLOW}  Modelo Vosk ya existe, omitiendo descarga${NC}"
else
    echo "  Descargando ${VOSK_MODEL}..."
    TEMP_DIR=$(mktemp -d)
    wget -q "${VOSK_URL}" -O "${TEMP_DIR}/model.zip" || curl -sL "${VOSK_URL}" -o "${TEMP_DIR}/model.zip"
    unzip -q "${TEMP_DIR}/model.zip" -d "${VOSK_MODELS_DIR}"
    rm -rf "${TEMP_DIR}"
    echo -e "${GREEN}  ✓ Modelo Vosk descargado en ${VOSK_MODELS_DIR}/${VOSK_MODEL}${NC}"
fi

# ---------------------------------------------------------- #
# 3. Instalar el módulo en Odoo
# ---------------------------------------------------------- #
echo -e "${GREEN}[3/5] Instalando módulo en Odoo...${NC}"

# Detectar ruta de addons de Odoo
ODOO_ADDONS_PATHS=(
    "/opt/odoo/addons"
    "/opt/odoo/custom/addons"
    "/var/lib/odoo/addons"
    "/mnt/extra-addons"
    "/opt/odoo17/addons"
    "/opt/odoo18/addons"
    "/opt/odoo19/addons"
)

MODULE_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_NAME="odoo_ai_assistant"

INSTALLED=false
for ADDONS_PATH in "${ODOO_ADDONS_PATHS[@]}"; do
    if [ -d "${ADDONS_PATH}" ]; then
        echo "  Instalando en ${ADDONS_PATH}..."
        cp -r "${MODULE_SRC}" "${ADDONS_PATH}/${MODULE_NAME}"
        INSTALLED=true
        echo -e "${GREEN}  ✓ Módulo copiado a ${ADDONS_PATH}/${MODULE_NAME}${NC}"
        break
    fi
done

if [ "$INSTALLED" = false ]; then
    echo -e "${YELLOW}  No se encontró la ruta de addons de Odoo automáticamente.${NC}"
    echo -e "${YELLOW}  Por favor, copia manualmente la carpeta '${MODULE_NAME}' a tu directorio de addons.${NC}"
    echo "  Ejemplo: cp -r ${MODULE_SRC} /tu/ruta/de/addons/${MODULE_NAME}"
    echo ""
    read -p "  Ruta de addons de Odoo: " CUSTOM_ADDONS_PATH
    if [ -d "${CUSTOM_ADDONS_PATH}" ]; then
        cp -r "${MODULE_SRC}" "${CUSTOM_ADDONS_PATH}/${MODULE_NAME}"
        echo -e "${GREEN}  ✓ Módulo copiado a ${CUSTOM_ADDONS_PATH}/${MODULE_NAME}${NC}"
    else
        echo -e "${RED}  La ruta no existe. Instalación manual requerida.${NC}"
    fi
fi

# ---------------------------------------------------------- #
# 4. Actualizar lista de addons
# ---------------------------------------------------------- #
echo -e "${GREEN}[4/5] Actualizando lista de addons de Odoo...${NC}"

echo -e "${YELLOW}  Nota: Necesitas reiniciar Odoo con el flag -u para actualizar la lista de addons.${NC}"
echo "  Ejemplo: systemctl restart odoo"
echo "  O: python3 /opt/odoo/odoo-bin -u odoo_ai_assistant -d TU_BASE_DE_DATOS"

# ---------------------------------------------------------- #
# 5. Verificación
# ---------------------------------------------------------- #
echo -e "${GREEN}[5/5] Verificando instalación...${NC}"

ERRORS=0

# Verificar Python
python3 -c "import requests" 2>/dev/null && echo -e "  ✓ requests" || { echo -e "  ${RED}✗ requests${NC}"; ERRORS=$((ERRORS+1)); }
python3 -c "from duckduckgo_search import DDGS" 2>/dev/null && echo -e "  ✓ duckduckgo-search" || { echo -e "  ${RED}✗ duckduckgo-search${NC}"; ERRORS=$((ERRORS+1)); }
python3 -c "import edge_tts" 2>/dev/null && echo -e "  ✓ edge-tts" || { echo -e "  ${RED}✗ edge-tts${NC}"; ERRORS=$((ERRORS+1)); }
python3 -c "import vosk" 2>/dev/null && echo -e "  ✓ vosk" || { echo -e "  ${RED}✗ vosk${NC}"; ERRORS=$((ERRORS+1)); }

# Verificar modelo Vosk
[ -d "${VOSK_MODELS_DIR}/${VOSK_MODEL}" ] && echo -e "  ✓ Modelo Vosk" || { echo -e "  ${YELLOW}⚠ Modelo Vosk no encontrado${NC}"; }

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}¡Instalación completada exitosamente!${NC}"
else
    echo -e "${YELLOW}Instalación completada con ${ERRORS} advertencia(s)${NC}"
    echo "  Algunas dependencias no se instalaron correctamente."
    echo "  El módulo funcionará con funcionalidad reducida."
fi
echo ""
echo "Pasos siguientes:"
echo "  1. Reinicia Odoo: systemctl restart odoo"
echo "  2. Ve a Aplicaciones e instala 'AI Assistant'"
echo "  3. Configura la API Key de OpenRouter en Ajustes > AI Assistant"
echo "  4. ¡Usa el botón del asistente en la barra superior!"
echo "============================================"
