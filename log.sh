#!/bin/bash
# Check if logs exist yet
if [ ! -f app.log ]; then
    echo "No logs found. Is the app running? Start it with ./up.sh"
    exit 1
fi

echo "--- Showing live logs (Press Ctrl+C to stop) ---"
tail -f app.log