FROM python:3.11-slim-bookworm

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0
ENV RESOLUTION=1280x800x24

# 1. Install system dependencies: X11 virtual display, Fluxbox WM, VNC, noVNC, Tkinter, fonts, supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    fluxbox \
    supervisor \
    python3-tk \
    fonts-dejavu-core \
    fonts-liberation \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt reportlab pillow pypdfium2

# 3. Copy application source code
COPY . /app

# 4. Copy custom configurations
COPY cloud_demo/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY cloud_demo/entrypoint.sh /entrypoint.sh
COPY cloud_demo/fluxbox_init /root/.fluxbox/init
COPY cloud_demo/index.html /usr/share/novnc/index.html

RUN chmod +x /entrypoint.sh

# 5. Expose HTTP port for the web browser
EXPOSE 8080

# 6. Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
