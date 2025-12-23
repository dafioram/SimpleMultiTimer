#!/bin/bash
# 1. Check if Service Exists
if [ ! -f /etc/systemd/system/timer-app.service ]; then
    echo "Note: timer-app service is not registered. Skipping service removal."
else
    echo "Stopping and removing service..."
    sudo systemctl stop timer-app.service
    sudo systemctl disable timer-app.service
    sudo rm /etc/systemd/system/timer-app.service
    sudo systemctl daemon-reload
fi

# 2. Clean Up Local Files
if [ -d "venv" ]; then
    echo "Removing virtual environment..."
    rm -rf venv
fi

rm -f timer-app.service app.log error.log
echo "Cleanup complete. App is fully uninstalled."