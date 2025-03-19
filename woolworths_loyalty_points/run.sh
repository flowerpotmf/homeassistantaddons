#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

# Get configuration
CLIENT_ID=$(jq --raw-output '.client_id' $CONFIG_PATH)
HASHCRN=$(jq --raw-output '.hashcrn' $CONFIG_PATH)
RUN_TIME=$(jq --raw-output '.run_time' $CONFIG_PATH)
NOTIFICATION=$(jq --raw-output '.notification' $CONFIG_PATH)

# Create environment variables for the Python script
export client_id=$CLIENT_ID
export hashcrn=$HASHCRN
export notification=$NOTIFICATION

echo "Woolworths Loyalty Points Add-on started"
echo "Scheduled to run daily at $RUN_TIME"

# Extract hours and minutes from RUN_TIME (format: HH:MM)
HOUR=${RUN_TIME%:*}
MINUTE=${RUN_TIME#*:}

# Remove leading zeros from hour and minute
HOUR=${HOUR#0}
MINUTE=${MINUTE#0}

# Schedule the cron job
(crontab -l 2>/dev/null || echo "") | \
    { cat; echo "$MINUTE $HOUR * * * /usr/local/bin/python /app/woolworths_points.py"; } | \
    crontab -

# Start cron
crond -f -d 8
