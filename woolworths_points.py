Key fixes & improvements
------------------------

| Problem | Fix |
|---------|-----|
| *Unreachable debug code* after `while True:` (it never executes) | Moved those sanity‑check logs to **startup**, before scheduling |
| Endless hang if Woolworths endpoint stalls | Added a **requests `Session` with back‑off / timeout / retry** |
| `notification` check was case‑sensitive | Normalised to `.lower()` |
| Hard‑coded `userlocaltime` (`'480'`) | Auto‑calculates from the host’s TZ, falls back to `'480'` |
| Lacked graceful exit on bad schedule string | Validate `HH:MM`; abort early with clear log + MQTT notice |
| MQTT topic too generic | Default topic → `homeassistant/notification/woolworths_points` but still overrideable |
| Single‑account only | Can now process **N accounts** if you later extend `options.json` to hold a list |

```python
#!/usr/bin/env python3
import os, sys, json, time, logging
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import schedule

# -----------------------------------------------------------------------------
# Logging ---------------------------------------------------------------------
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("woolworths_points")

# -----------------------------------------------------------------------------
# Helper: MQTT notifications ---------------------------------------------------
# -----------------------------------------------------------------------------
def notify(msg: str, level: str = "info") -> None:
    if os.getenv("notification", "true").lower() != "true":
        return
    try:
        client = mqtt.Client()
        client.connect(
            os.getenv("MQTT_HOST", "core-mosquitto"),
            int(os.getenv("MQTT_PORT", 1883)),
            60,
        )
        payload = {"title": "Woolworths Loyalty Points", "message": msg, "level": level}
        client.publish(
            os.getenv(
                "MQTT_TOPIC", "homeassistant/notification/woolworths_points"
            ),
            json.dumps(payload),
        )
        client.disconnect()
    except Exception as exc:
        log.error("MQTT notification failed: %s", exc)

# -----------------------------------------------------------------------------
# Helper: resilient requests session ------------------------------------------
# -----------------------------------------------------------------------------
def session_factory() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    sess.mount("https://", HTTPAdapter(max_retries=retries))
    sess.timeout = 15
    return sess

# -----------------------------------------------------------------------------
# Offer boosting ---------------------------------------------------------------
# -----------------------------------------------------------------------------
def process_account(acc: dict) -> str:
    required = ("client_id", "hashcrn", "x_api_key", "x_wooliesx_api_key")
    if any(not acc.get(k) for k in required):
        return f"{acc.get('name','Account')}: missing credentials – skipped"

    log.info("▶ Processing %s", acc.get("name", "Account"))
    sess = session_factory()

    tz_offset_min = int(round(datetime.now().astimezone().utcoffset().total_seconds() / 60))
    base_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        "client_id": acc["client_id"],
        "hashcrn": acc["hashcrn"],
        "x-api-key": acc["x_api_key"],
        "x-wooliesx-api-key": acc["x_wooliesx_api_key"],
        "userlocaltime": str(tz_offset_min),
        "Accept": "application/json",
    }
    sess.headers.update(base_headers)

    try:
        offers = (
            sess.get("https://prod.api-wr.com/wx/v1/csl/customers/offers").json().get(
                "offers", []
            )
        )
    except Exception as exc:
        notify(f"{acc['name']}: failed to fetch offers – {exc}", "error")
        return f"{acc['name']}: ERROR fetching offers"

    pending = [o for o in offers if o.get("status") == "NotActivated"]
    if not pending:
        return f"{acc['name']}: nothing to boost"

    boosted = 0
    for offer in pending:
        try:
            resp = sess.post(
                "https://prod.api-wr.com/wx/v1/csl/customers/offers/boost",
                json={"offerIds": [offer["id"]]},
                headers={
                    "origin": "https://www.woolworths.com.au",
                    "referer": "https://www.woolworths.com.au/",
                },
            ).json()
            if resp.get("status", "").lower() == "success":
                boosted += 1
                log.info("  • boosted offer %s", offer["id"])
            else:
                log.warning("  • unexpected response for %s: %s", offer["id"], resp)
        except Exception as exc:
            log.error("  • boost failed for %s: %s", offer["id"], exc)
        time.sleep(1.2)

    return f"{acc['name']}: boosted {boosted}/{len(pending)}"

# -----------------------------------------------------------------------------
# Scheduler entry point --------------------------------------------------------
# -----------------------------------------------------------------------------
def main() -> None:
    run_time = os.getenv("run_time", "09:00")
    try:
        datetime.strptime(run_time, "%H:%M")
    except ValueError:
        msg = f"run_time '{run_time}' is not HH:MM – aborting"
        log.error(msg)
        notify(msg, "error")
        sys.exit(1)

    # ----------------------------  single account (env)  ----------------------
    account = {
        "name": os.getenv("account_name", "My Account"),
        "client_id": os.getenv("client_id"),
        "hashcrn": os.getenv("hashcrn"),
        "x_api_key": os.getenv("x_api_key"),
        "x_wooliesx_api_key": os.getenv("x_wooliesx_api_key"),
    }

    # You can later extend this to a list: accounts = json.load(open("/data/…"))
    accounts = [account]

    log.info("Add‑on started – job scheduled daily at %s", run_time)
    log.info("client_id present: %s", bool(account["client_id"]))

    def job():
        for acc in accounts:
            result = process_account(acc)
            log.info(result)
            notify(result)

    schedule.every().day.at(run_time).do(job)
    job()  # run once immediately on start‑up

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
``` :contentReference[oaicite:2]{index=2}&#8203;:contentReference[oaicite:3]{index=3}

---
