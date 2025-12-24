#!/bin/bash

# 0. Root Privilege Check
if [ "$EUID" -ne 0 ]; then 
  echo "Error: This script must be run with sudo."
  exit 1
fi

SERVICE="timer-app.service"

# 1. Check if service exists
if [ ! -f /etc/systemd/system/$SERVICE ]; then
    echo "App is currently: NOT INSTALLED"
    exit 0
fi

# 2. Check if active
if ! systemctl is-active --quiet $SERVICE; then
    echo "--- App Status ---"
    echo "Status: DOWN (Inactive)"
    exit 0
fi

echo "--- App Status ---"
echo "Status: ACTIVE"

# 3. Uptime
UPTIME=$(systemctl status $SERVICE | grep "Active:" | sed 's/.*since //')
echo "Uptime: Started $UPTIME"

# 4. RAM and PID
PID=$(systemctl show -p MainPID --value $SERVICE)
if [ "$PID" != "0" ] && [ ! -z "$PID" ]; then
    RAM=$(ps -p $PID -o rss= | awk '{printf "%.2f MB\n", $1/1024}')
    echo "Memory Usage: $RAM"
    echo "Process ID: $PID"
fi

# 5. Show the port it's listening on
# Broadened grep to catch 'python', 'python3', or 'python3.11'
PORT_CHECK=$(ss -tulpn | grep -E "python|python3" | grep -oP '(?<=:)\d+(?=\s)' | head -n 1)
echo "Running on Port: ${PORT_CHECK:-Unknown}"

# 6. Check .env (Looking for APP_PORT)
if [ -f .env ]; then
    # Changed from PORT to APP_PORT to match your config
    ENV_PORT=$(grep -E '^APP_PORT=[0-9]+' .env | cut -d '=' -f2)
    echo "Configured Port (.env): ${ENV_PORT:-Not set in .env}"
    
    if [ "$ENV_PORT" != "$PORT_CHECK" ] && [ ! -z "$PORT_CHECK" ]; then
        echo "Warning: .env expects $ENV_PORT but app is live on $PORT_CHECK"
    fi
fi