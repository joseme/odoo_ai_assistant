# Odoo AI Assistant

Asistente de IA integrado en Odoo con chat flotante, reconocimiento de voz local y respuesta hablada. Compatible con Odoo 17, 18 y 19.

## Características

### Chat con IA
- Respuestas inteligentes sobre el uso de Odoo usando **OpenRouter** (modelo configurable)
- Historial de conversaciones persistente
- Formato Markdown en las respuestas (código, listas, encabezados, negritas, etc.)
- Botón flotante (FAB) accesible desde cualquier pantalla de Odoo
- Integración en la barra de systray de Odoo

### Input de Voz (Vosk)
- **Reconocimiento de voz 100% local** con Vosk - no se envía audio a servicios externos
- Soporte para español (modelo vosk-model-small-es-0.42)
- Fallback automático a Web Speech API del navegador si Vosk no está disponible
- Indicador visual de grabación en tiempo real
- Auto-detención después de 60 segundos

### Respuesta Hablada (edge-tts)
- **Voces neuronales de Microsoft Edge** - gratis y de alta calidad
- Voces disponibles en múltiples idiomas (español, inglés, francés, portugués, etc.)
- Voz por defecto: es-MX-JorgeNeural
- Reproducción de audio directamente en el chat
- Configuración de voz e idioma desde Ajustes

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
pip install duckduckgo-search edge-tts vosk nest-asyncio
```

2. **Descargar modelo de Vosk (para reconocimiento de voz local):**

```bash
sudo mkdir -p /opt/vosk-models
cd /opt/vosk-models
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip
rm vosk-model-small-es-0.42.zip
```

Modelos disponibles: https://alphacephei.com/vosk/models

3. **Copiar el módulo a la carpeta de addons de Odoo:**

```bash
cp -r odoo_ai_assistant /ruta/de/addons/de/odoo/
```

4. **Reiniciar Odoo y actualizar la lista de addons:**

```bash
# Reiniciar servicio
sudo systemctl restart odoo

# O actualizar manualmente
python3 /opt/odoo/odoo-bin -u odoo_ai_assistant -d tu_base_de_datos
```

5. **Instalar el módulo desde la interfaz de Odoo:**
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
| Reconocimiento de voz | Habilitar/deshabilitar voz | Habilitado |
| Modelo Vosk | Modelo para reconocimiento de voz | vosk-model-small-es-0.42 |
| Respuesta hablada (TTS) | Habilitar/deshabilitar TTS | Habilitado |
| Voz TTS | Nombre de la voz edge-tts | es-MX-JorgeNeural |
| Idioma TTS | Código de idioma para filtrar voces | es |
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

### Voces TTS Recomendadas

| Idioma | Voz | Código |
|--------|-----|--------|
| Español (México) | Jorge | es-MX-JorgeNeural |
| Español (España) | Álvaro | es-ES-AlvaroNeural |
| Español (España) | Elvira | es-ES-ElviraNeural |
| Inglés (EE.UU.) | Guy | en-US-GuyNeural |
| Portugués (Brasil) | Antonio | pt-BR-AntonioNeural |
| Francés (Francia) | Henri | fr-FR-HenriNeural |

## Uso

1. **Abrir el chat**: Haz clic en el botón flotante púrpura en la esquina inferior derecha o en el ícono de robot en la barra de systray
2. **Escribir mensaje**: Escribe tu pregunta en el campo de texto y presiona Enter o el botón de enviar
3. **Usar voz**: Haz clic en el ícono de micrófono para activar el reconocimiento de voz
4. **Escuchar respuesta**: Haz clic en el ícono de altavoz junto a la respuesta para escucharla
5. **Ver fuentes**: Haz clic en "Fuentes" para ver los artículos de Knowledge y resultados web utilizados
6. **Historial**: Usa el botón de historial para ver conversaciones anteriores
7. **Nueva conversación**: Usa el botón "+" para iniciar una nueva conversación

## Estructura del Módulo

```
odoo_ai_assistant/
├── __init__.py                    # Inicialización del módulo
├── __manifest__.py                # Manifiesto del módulo (metadata)
├── install.sh                     # Script de instalación
├── controllers/
│   ├── __init__.py
│   └── ai_chat.py                 # Controladores API (chat, voz, TTS, contexto)
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
│       │   ├── ai_assistant.js    # Componente principal del chat
│       │   ├── voice_input.js     # Componente de reconocimiento de voz
│       │   └── systray.js         # Botón en barra de systray
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
| `/ai_assistant/audio/<attachment_id>` | GET (HTTP) | Obtiene el archivo de audio TTS |
| `/ai_assistant/transcribe` | POST (JSON) | Transcribe audio con Vosk |
| `/ai_assistant/tts` | POST (JSON) | Genera audio TTS desde texto |
| `/ai_assistant/tts_voices` | GET (JSON) | Lista voces TTS disponibles |
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
- `edge-tts` >= 6.1.0 - Text-to-Speech con voces de Microsoft Edge
- `vosk` >= 0.3.44 - Reconocimiento de voz offline
- `nest-asyncio` >= 1.5.0 - Soporte async anidado en Odoo

### Modelos Vosk (opcionales)
- `vosk-model-small-es-0.42` - Español (pequeño, ~40MB)
- `vosk-model-es-0.42` - Español (grande, ~1.3GB, mayor precisión)
- `vosk-model-small-en-us-0.15` - Inglés (pequeño)

### Odoo
- Módulo `base` (requerido)
- Módulo `web` (requerido)
- Módulo `knowledge` (opcional, para búsqueda en base de conocimiento)

## Resolución de Problemas

### Error: "No se ha configurado la API Key de OpenRouter"
- Ve a Configuración > Ajustes > AI Assistant
- Ingresa tu API Key de OpenRouter
- Obtén una en: https://openrouter.ai/keys

### Error: "Modelo Vosk no encontrado"
- Descarga el modelo de Vosk desde https://alphacephei.com/vosk/models
- Colócalo en `/opt/vosk-models/`
- O configura otra ruta en Ajustes > Modelo Vosk

### El reconocimiento de voz no funciona
- Verifica que Vosk esté instalado: `pip show vosk`
- Verifica que el modelo esté descargado en `/opt/vosk-models/`
- El navegador requiere permisos de micrófono (HTTPS o localhost)
- Si Vosk no está disponible, se usa automáticamente Web Speech API (requiere Chrome/Edge)

### El TTS no genera audio
- Verifica que edge-tts esté instalado: `pip show edge-tts`
- Verifica que TTS esté habilitado en Ajustes
- Revisa los logs de Odoo para errores: `tail -f /var/log/odoo/odoo-server.log`

### El chat no aparece
- Verifica que el módulo esté instalado correctamente
- Limpia la caché del navegador
- Verifica los errores en la consola del navegador (F12)

## Licencia

LGPL-3
