#!/bin/bash
set -e

SERVICE="timer-app.service"
TEMPLATE="timer-app.service.template"

echo "--- Installing Timer App ---"

# 1. Dependency Check
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it and try again."
    exit 1
fi

# 2. File Presence Checks
if [ ! -f "$TEMPLATE" ]; then
    echo "Error: $TEMPLATE not found."
    exit 1
fi

# 3. Duplicate Service Check
if systemctl is-active --quiet $SERVICE || [ -f /etc/systemd/system/$SERVICE ]; then
    echo "Warning: $SERVICE is already installed. Run ./down.sh first."
    exit 1
fi

# 4. Extract Port from .env
if [ -f .env ]; then
    APP_PORT=$(grep -E '^PORT=[0-9]+' .env | cut -d '=' -f2)
    if [ -z "$APP_PORT" ]; then
        echo "Error: PORT not defined in .env."
        exit 1
    fi
else
    echo "Error: .env file missing."
    exit 1
fi

# 5. NEW: Port Conflict Check
# We check if anything is already listening on the target port
if ss -tulpn | grep -q ":$APP_PORT "; then
    CONFLICTING_PROCESS=$(ss -tulpn | grep ":$APP_PORT " | awk '{print $7}')
    echo "Error: Port $APP_PORT is already in use by: $CONFLICTING_PROCESS"
    echo "Please stop that process or change the PORT in .env before running up.sh."
    exit 1
fi

# 6. Setup Environment
echo "Creating virtual environment and installing dependencies..."
python3 -m venv venv || { echo "Failed to create venv"; exit 1; }
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 7. Generate Service File
WORKING_DIR=$(pwd)
CURRENT_USER=$USER
sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{PORT}}|$APP_PORT|g" \
    "$TEMPLATE" > timer-app.service

# 8. Move and Start
sudo mv timer-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE
sudo systemctl start $SERVICE

# 9. Verification
sleep 2
if systemctl is-active --quiet $SERVICE; then
    echo "------------------------------------------------"
    echo "Success: App is UP at http://$(hostname -I | awk '{print $1}'):$APP_PORT"
    echo "------------------------------------------------"
else
    echo "Error: App failed to start. Check ./logs.sh"
    exit 1
fi