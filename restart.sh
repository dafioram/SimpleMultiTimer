#!/bin/bash
set -e

# 0. Root Privilege Check
if [ "$EUID" -ne 0 ]; then 
  echo "Error: This script must be run with sudo."
  exit 1
fi

SERVICE="timer-app.service"
TEMPLATE="timer-app.service.template"

echo "--- Restarting Timer App ---"

# 1. Check if Service is Installed
if [ ! -f /etc/systemd/system/$SERVICE ]; then
    echo "Error: Service is not installed. Run ./up.sh first."
    exit 1
fi

# 2. Dynamic Port Extraction
if [ -f .env ]; then
    APP_PORT=$(grep -E '^APP_PORT=[0-9]+' .env | cut -d '=' -f2)
    if [ -z "$APP_PORT" ]; then
        echo "Error: .env found but $APP_PORT is not defined correctly."
        exit 1
    fi
else
    echo "Error: .env file missing. Cannot determine port."
    exit 1
fi

# 3. Update Configuration if needed
if [ -f "$TEMPLATE" ]; then
    WORKING_DIR=$(pwd)

    # Get the original user even if running under sudo
	REAL_USER=${SUDO_USER:-$(id -un)}
    
    # Generate temporary service file
    sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
        -e "s|{{USER}}|$REAL_USER|g" \
        -e "s|{{PORT}}|$APP_PORT|g" \
        "$TEMPLATE" > timer-app.service.tmp

    # Only apply if the configuration actually changed
    if ! diff -q timer-app.service.tmp /etc/systemd/system/$SERVICE > /dev/null; then
        echo "Updating systemd config (Port changed to $APP_PORT)..."
        mv timer-app.service.tmp /etc/systemd/system/$SERVICE
        systemctl daemon-reload
    else
        rm timer-app.service.tmp
    fi
fi

# 4. Restart and Verify
systemctl restart $SERVICE
sleep 2

if systemctl is-active --quiet $SERVICE; then
    echo "Success: App restarted on port $APP_PORT"
else
    echo "Error: App failed to start. Check error.log or ./logs.sh"
    exit 1
fi