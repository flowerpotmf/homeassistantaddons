#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

# ------------------------------  read options.json  ---------------------------
CLIENT_ID=$(jq -r '.client_id'               "$CONFIG_PATH")
HASHCRN=$(jq  -r '.hashcrn'                  "$CONFIG_PATH")
RUN_TIME=$(jq -r '.run_time'                 "$CONFIG_PATH")
NOTIFICATION=$(jq -r '.notification'         "$CONFIG_PATH")
X_API_KEY=$(jq -r '.x_api_key'               "$CONFIG_PATH")
X_WOOLIESX_API_KEY=$(jq -r '.x_wooliesx_api_key' "$CONFIG_PATH")
ACCOUNT_NAME=$(jq -r '.account_name'         "$CONFIG_PATH")

export client_id="$CLIENT_ID"
export hashcrn="$HASHCRN"
export notification="$NOTIFICATION"
export run_time="$RUN_TIME"
export x_api_key="$X_API_KEY"
export x_wooliesx_api_key="$X_WOOLIESX_API_KEY"
export account_name="$ACCOUNT_NAME"

# Optional MQTT overrides
export MQTT_HOST=${MQTT_HOST:-core-mosquitto}
export MQTT_PORT=${MQTT_PORT:-1883}

echo "▶ Woolworths Loyalty Points add‑on started – next run at ${RUN_TIME}"
exec python3 /app/woolworths_points.py
``` :contentReference[oaicite:0]{index=0}&#8203;:contentReference[oaicite:1]{index=1}

---
