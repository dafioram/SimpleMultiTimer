#!/bin/bash
sudo systemctl stop timer-app.service
sudo systemctl disable timer-app.service
sudo rm /etc/systemd/system/timer-app.service
sudo systemctl daemon-reload

# Cleanup local files
rm -f timer-app.service
rm -f app.log error.log
rm -rf venv

echo "App, environment, and logs have been removed."