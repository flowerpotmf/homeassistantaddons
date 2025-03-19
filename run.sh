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
export run_time=$RUN_TIME

echo "Woolworths Loyalty Points Add-on started"
echo "Scheduled to run daily at $RUN_TIME"

# Install schedule library if not already installed
pip install schedule

# Run the Python script directly (no cron needed)
exec python /app/woolworths_points.py