#!/bin/bash

while true; do
    echo "Starting ./scripts/prepdocs.sh..."
    ./scripts/prepdocs.sh

    echo "Command terminated. Restarting in 5 seconds..."
    sleep 5  # Optional: Adjust the delay before restarting
done
