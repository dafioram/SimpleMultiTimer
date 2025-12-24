#!/bin/bash
# 1. Root Privilege Check
if [ "$EUID" -ne 0 ]; then 
  echo "Error: This script must be run with sudo."
  exit 1
fi

SERVICE="timer-app.service"

# 2. Check if the service file exists in the system directory
if [ -f /etc/systemd/system/$SERVICE ]; then
    echo "Stopping and unregistering $SERVICE..."
    systemctl stop $SERVICE
    systemctl disable $SERVICE
    rm /etc/systemd/system/$SERVICE
    systemctl daemon-reload
    echo "Service successfully removed."
else
    # Notify the user if the app wasn't there to begin with
    echo "Note: $SERVICE is not registered as a system service. Skipping service removal."
fi

# 3. Clean up local files regardless of service status
echo "Cleaning up local environment files..."
rm -rf venv timer-app.service app.log error.log
echo "Cleanup complete."