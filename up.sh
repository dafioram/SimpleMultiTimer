#!/bin/bash
# 1. Setup Environment
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Prepare the Service file from template
# We use 'sed' to replace placeholders with actual values
WORKING_DIR=$(pwd)
CURRENT_USER=$USER

sed -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    timer-app.service.template > timer-app.service

# 3. Move to system folder and Register
sudo mv timer-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable timer-app.service
sudo systemctl start timer-app.service

echo "App is UP at http://$(hostname -I | awk '{print $1}'):5051"