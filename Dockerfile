# Dockerfile para AI Assistant
# Usage: docker build -t odoo:ai-assistant .
FROM odoo:17

# Create target dir as root, then install packages
USER root
RUN mkdir -p /opt/odoo-libs && \
    pip install --no-cache-dir --target=/opt/odoo-libs \
    'duckduckgo-search>=4.0.0' \
    'edge-tts>=6.1.0' \
    'nest-asyncio>=1.5.0' \
    'vosk>=0.3.44'
USER odoo

# Make packages visible to Odoo's Python
ENV PYTHONPATH="/opt/odoo-libs"

# Exponer puerto
EXPOSE 8069

# Comando por defecto
CMD ["odoo", "-w", "2"]