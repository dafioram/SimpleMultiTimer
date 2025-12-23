#!/bin/bash
# 1. Dependency Check
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it and try again."
    exit 1
fi

# 2. Duplicate Check
if systemctl is-active --quiet timer-app.service || [ -f /etc/systemd/system/timer-app.service ]; then
    echo "Warning: timer-app service is already installed or running."
    echo "Run ./down.sh first if you want to perform a clean reinstall."
    exit 1
fi

# 3. Setup Environment
python3 -m venv venv || { echo "Failed to create venv"; exit 1; }
./venv/bin/pip install -r requirements.txt

# 4. Generate Service File from Template
WORKING_DIR=$(pwd)
CURRENT_USER=$USER
sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    timer-app.service.template > timer-app.service

# 5. Move and Start
sudo mv timer-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable timer-app.service
sudo systemctl start timer-app.service

echo "Success: App is UP at http://$(hostname -I | awk '{print $1}'):5051"