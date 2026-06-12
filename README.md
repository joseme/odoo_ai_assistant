# Odoo AI Assistant

Asistente de IA integrado en Odoo con chat flotante. Compatible con Odoo 17, 18 y 19.

## Características

### Chat con IA
- Respuestas inteligentes sobre el uso de Odoo usando **OpenRouter** (modelo configurable)
- Historial de conversaciones persistente
- Formato Markdown en las respuestas (código, listas, encabezados, negritas, etc.)
- Botón flotante (FAB) accesible desde cualquier pantalla de Odoo
- Integración en la barra de systray de Odoo

### Contexto Automático
- Detecta automáticamente el **módulo**, **modelo** y **registro** que el usuario está viendo
- Analiza el contenido de la página actual de Odoo para obtener información relevante
- Envía el contexto al LLM para respuestas más precisas y específicas
- Muestra badge de contexto en el chat para que el usuario sepa qué contexto se está usando

### Integración con Knowledge
- Busca artículos relevantes del módulo **Knowledge** de Odoo
- Solo se activa si el módulo Knowledge está instalado
- Los resultados se muestran como fuentes enlazadas en la respuesta

### Búsqueda Inteligente con DuckDuckGo
- Busca información relevante en la web para completar la respuesta
- Se puede habilitar/deshabilitar desde Ajustes
- Las fuentes web se muestran como enlaces en la respuesta

## Instalación

### Opción 1: Script automático

```bash
cd odoo_ai_assistant
sudo bash install.sh
```

### Opción 2: Instalación manual

1. **Instalar dependencias de Python:**

```bash
pip install duckduckgo-search nest-asyncio
```

2. **Copiar el módulo a la carpeta de addons de Odoo:**

```bash
cp -r odoo_ai_assistant /ruta/de/addons/de/odoo/
```

3. **Reiniciar Odoo y actualizar la lista de addons:**

```bash
# Reiniciar servicio
sudo systemctl restart odoo

# O actualizar manualmente
python3 /opt/odoo/odoo-bin -u odoo_ai_assistant -d tu_base_de_datos
```

4. **Instalar el módulo desde la interfaz de Odoo:**
   - Ir a Aplicaciones
   - Buscar "AI Assistant"
   - Hacer clic en Instalar

## Configuración

### API Key de OpenRouter

1. Ir a **Configuración > Ajustes > AI Assistant**
2. Ingresar tu API Key de OpenRouter
3. Obtener una API Key gratuita en: https://openrouter.ai/keys

### Opciones de Configuración

| Parámetro | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| OpenRouter API Key | Clave API de OpenRouter | (vacío) |
| Modelo de IA | Modelo de IA a utilizar | openai/gpt-4o-mini |
| Búsqueda web | Habilitar DuckDuckGo | Habilitado |
| Búsqueda en Knowledge | Buscar en Knowledge de Odoo | Habilitado |
| Mensaje de bienvenida | Mensaje al abrir el chat | "¡Hola! Soy tu asistente..." |
| Historial de mensajes | Máximo mensajes enviados al LLM | 20 |

### Modelos de IA Disponibles (OpenRouter)

OpenRouter soporta cientos de modelos. Algunos populares:

- **OpenAI GPT-4o Mini** (recomendado) - Rápido y eficiente
- **OpenAI GPT-4o** - Máxima calidad
- **Anthropic Claude Sonnet 4** - Excelente para razonamiento
- **Google Gemini 2.0 Flash** - Rápido y gratuito
- **Meta Llama 4 Scout** - Open source
- **DeepSeek V4 Flash** - Eficiente
- **Mistral Large** - Multilingüe

## Uso

1. **Abrir el chat**: Haz clic en el botón flotante púrpura en la esquina inferior derecha o en el ícono de robot en la barra de systray
2. **Escribir mensaje**: Escribe tu pregunta en el campo de texto y presiona Enter o el botón de enviar
3. **Ver fuentes**: Haz clic en "Fuentes" para ver los artículos de Knowledge y resultados web utilizados
4. **Historial**: Usa el botón de historial para ver conversaciones anteriores
5. **Nueva conversación**: Usa el botón "+" para iniciar una nueva conversación

## Estructura del Módulo

```
odoo_ai_assistant/
├── __init__.py                    # Inicialización del módulo
├── __manifest__.py                # Manifiesto del módulo (metadata)
├── install.sh                     # Script de instalación
├── controllers/
│   ├── __init__.py
│   └── ai_chat.py                 # Controladores API (chat, contexto)
├── models/
│   ├── __init__.py
│   ├── ai_chat.py                 # Modelos de datos y servicio de IA
│   └── res_config_settings.py     # Configuración en Ajustes de Odoo
├── views/
│   ├── ai_chat_views.xml          # Vistas del backend (lista, formulario)
│   └── res_config_settings_views.xml  # Vista de configuración
├── static/
│   └── src/
│       ├── css/
│       │   └── ai_chat.css        # Estilos del chat flotante
│       ├── js/
│   │   ├── ai_assistant.js    # Componente principal del chat
│   │   └── systray.js         # Botón en barra de systray
│       └── xml/
│           └── ai_chat.xml        # Templates OWL del chat
├── security/
│   ├── ir.model.access.csv        # Permisos de acceso
│   └── security.xml               # Grupos de seguridad
├── data/
│   └── default_data.xml           # Parámetros por defecto
└── i18n/
    └── (traducciones)
```

## API Endpoints

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/ai_assistant/chat` | POST (JSON) | Envía un mensaje y recibe respuesta de la IA |
| `/ai_assistant/conversations` | POST (JSON) | Obtiene la lista de conversaciones |
| `/ai_assistant/conversation/<id>` | GET (JSON) | Obtiene los mensajes de una conversación |
| `/ai_assistant/conversation/<id>/delete` | POST (JSON) | Elimina una conversación |
| `/ai_assistant/config` | GET (JSON) | Obtiene configuración del asistente |
| `/ai_assistant/context` | POST (JSON) | Obtiene contexto de la página actual |

## Compatibilidad

| Versión de Odoo | Estado |
|-----------------|--------|
| Odoo 17 | ✅ Compatible |
| Odoo 18 | ✅ Compatible |
| Odoo 19 | ✅ Compatible |

## Dependencias

### Python (requeridas)
- `requests` - Cliente HTTP para API de OpenRouter
- `duckduckgo-search` >= 4.0.0 - Búsqueda web con DuckDuckGo
- `nest-asyncio` >= 1.5.0 - Soporte async anidado en Odoo

### Odoo
- Módulo `base` (requerido)
- Módulo `web` (requerido)
- Módulo `knowledge` (opcional, para búsqueda en base de conocimiento)

## Resolución de Problemas

### Error: "No se ha configurado la API Key de OpenRouter"
- Ve a Configuración > Ajustes > AI Assistant
- Ingresa tu API Key de OpenRouter
- Obtén una en: https://openrouter.ai/keys

### El chat no aparece
- Verifica que el módulo esté instalado correctamente
- Limpia la caché del navegador
- Verifica los errores en la consola del navegador (F12)

## Licencia

LGPL-3
