#!/bin/bash
SERVICE="timer-app.service"

if ! systemctl is-active --quiet $SERVICE; then
    echo "App is currently: DOWN"
    exit 0
fi

echo "--- App Status ---"
echo "Status: ACTIVE"
# Get uptime
systemctl status $SERVICE | grep "Active:" | awk '{print "Uptime: " $3 " " $4}'

# Get RAM usage of the Python process
PID=$(systemctl show -p MainPID --value $SERVICE)
if [ "$PID" != "0" ]; then
    RAM=$(ps -p $PID -o rss= | awk '{printf "%.2f MB\n", $1/1024}')
    echo "RAM Usage: $RAM"
fi

# Show the port it's listening on
PORT_CHECK=$(sudo ss -tulpn | grep python | grep -oP '(?<=:)\d+(?=\s)')
echo "Running on Port: ${PORT_CHECK:-Unknown}"