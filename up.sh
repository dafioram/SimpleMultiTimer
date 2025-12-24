#!/bin/bash
set -e

# 1. Root Privilege Check
if [ "$EUID" -ne 0 ]; then 
  echo "Error: This script must be run with sudo."
  exit 1
fi

SERVICE="timer-app.service"

# 2. Dependency & Duplicate Checks
if ! command -v python3 &> /dev/null; then echo "Error: python3 missing"; exit 1; fi

if systemctl is-active --quiet $SERVICE || [ -f /etc/systemd/system/$SERVICE ]; then
    echo "Warning: Service already exists. Run ./down.sh first."
    exit 1
fi

# 3. Setup Env & Extract Port
echo "Setting Up Python env and install requirements"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 4. Generate & Register Service
WORKING_DIR=$(pwd)

# Get the original user even if running under sudo
REAL_USER=${SUDO_USER:-$(id -un)}

# 5. Extract Port from .env (Looking for APP_PORT)
if [ -f .env ]; then
    APP_PORT=$(grep -E '^APP_PORT=[0-9]+' .env | cut -d '=' -f2)
    if [ -z "$APP_PORT" ]; then
        echo "Error: APP_PORT not defined in .env."
        exit 1
    fi
else
    echo "Error: .env file missing."
    exit 1
fi

sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
    -e "s|{{USER}}|$REAL_USER|g" \
    -e "s|{{PORT}}|$APP_PORT|g" \
    timer-app.service.template > timer-app.service

mv timer-app.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE
systemctl start $SERVICE

echo "Success: App is UP at port $APP_PORT"