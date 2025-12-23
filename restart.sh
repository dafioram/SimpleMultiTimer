#!/bin/bash
set -e

SERVICE="timer-app.service"
TEMPLATE="timer-app.service.template"

echo "--- Restarting Timer App ---"

# 1. Check if Service is Installed
if [ ! -f /etc/systemd/system/$SERVICE ]; then
    echo "Error: Service is not installed. Run ./up.sh first."
    exit 1
fi

# 2. Dynamic Port Extraction (Matches up.sh logic)
if [ -f .env ]; then
    # Extracts the value after 'PORT=' robustly
    APP_PORT=$(grep -E '^PORT=[0-9]+' .env | cut -d '=' -f2)
    if [ -z "$APP_PORT" ]; then
        echo "Error: .env found but PORT is not defined correctly."
        exit 1
    fi
else
    echo "Error: .env file missing. Cannot determine port."
    exit 1
fi

# 3. Update Configuration if needed
if [ -f "$TEMPLATE" ]; then
    WORKING_DIR=$(pwd)
    CURRENT_USER=$USER
    
    # Generate temporary service file with current variables
    sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
        -e "s|{{USER}}|$CURRENT_USER|g" \
        -e "s|{{PORT}}|$APP_PORT|g" \
        "$TEMPLATE" > timer-app.service.tmp

    # Only apply if the configuration actually changed
    if ! diff -q timer-app.service.tmp /etc/systemd/system/$SERVICE > /dev/null; then
        echo "Updating systemd config (Port changed to $APP_PORT)..."
        sudo mv timer-app.service.tmp /etc/systemd/system/$SERVICE
        sudo systemctl daemon-reload
    else
        rm timer-app.service.tmp
    fi
fi

# 4. Restart and Verify
sudo systemctl restart $SERVICE
sleep 2

if systemctl is-active --quiet $SERVICE; then
    echo "Success: App restarted on port $APP_PORT"
else
    echo "Error: App failed to start. Check error.log or ./logs.sh"
    exit 1
fi