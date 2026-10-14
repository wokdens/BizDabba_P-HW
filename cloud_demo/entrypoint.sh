#!/bin/bash
set -e

echo "=================================================="
echo "  ⚡ Starting BizDabba Online Cloud Demo Container"
echo "  Powered by Wokdens.com"
echo "=================================================="

# Ensure directories exist
mkdir -p /var/log/supervisor
mkdir -p /root/.fluxbox
mkdir -p /app/database

# Configure fluxbox
if [ -f /app/cloud_demo/fluxbox_init ]; then
    cp /app/cloud_demo/fluxbox_init /root/.fluxbox/init
fi

# Initialize clean demo database if not present
if [ ! -f /app/database/business.db ]; then
    echo "Initializing demo paints & hardware database..."
    cd /app && python3 -c "from database import create_tables, run_migrations; create_tables(); run_migrations()"
    if [ -f /app/scripts/convert_and_import_ods.py ]; then
        cd /app && python3 scripts/convert_and_import_ods.py || true
    fi
fi

# Pre-activate Demo License with 50 launches for frictionless instant online tryout
python3 -c "
from license_manager import activate_license
try:
    activate_license('7492-8160')
    print('Demo license 7492-8160 successfully activated for cloud demo!')
except Exception as e:
    print('License init note:', e)
" || true

echo "Starting Xvfb, Fluxbox, VNC, noVNC, and BizDabba via Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
