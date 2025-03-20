import os
import requests
import json
import time
import schedule
import datetime
import paho.mqtt.client as mqtt
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("woolworths_points")

def send_notification(message):
    """Send a notification to Home Assistant"""
    if os.environ.get('notification') != 'true':
        return
    
    try:
        # Connect to MQTT broker
        client = mqtt.Client()
        client.connect("core-mosquitto", 1883, 60)
        
        # Create notification payload
        payload = {
            "message": message,
            "title": "Woolworths Loyalty Points"
        }
        
        # Publish notification
        client.publish("homeassistant/notify", json.dumps(payload))
        client.disconnect()
        logger.info(f"Notification sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def process_account(account):
    """Process offers for a single account"""
    client_id = account.get('client_id')
    hashcrn = account.get('hashcrn')
    account_name = account.get('name', 'Unnamed Account')
    x_api_key = account.get('x_api_key')
    x_wooliesx_api_key = account.get('x_wooliesx_api_key')

    logger.info(f"Processing account: {account_name}")

    # Create a persistent session for cookies/headers
    session = requests.Session()

    # Set base headers (observed from network tab)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'client_id': client_id,
        'hashcrn': hashcrn,
        'x-api-key': x_api_key,
        'x-wooliesx-api-key': x_wooliesx_api_key,
        'userlocaltime': '480',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        'sec-ch-ua-platform': '"Windows"',
        'priority': 'u=1, i',
        'content-type': 'application/json'
    })

    try:
        # Fetch offers with session
        offers_url = "https://prod.api-wr.com/wx/v1/csl/customers/offers"
        response = session.get(offers_url)
        response.raise_for_status()

        # Process offers
        data = response.json()
        offers = data.get('offers', [])
        not_activated_offers = [offer for offer in offers if offer.get('status') == "NotActivated"]
        
        # Boost offers
        boost_url = "https://prod.api-wr.com/wx/v1/csl/customers/offers/boost"
        boosted_count = 0

        for offer in not_activated_offers:
            offer_id = offer.get('id')
            if not offer_id:
                continue

            try:
                # Add POST-specific headers (from network inspection)
                boost_headers = {
                    'origin': 'https://www.woolworths.com.au',
                    'referer': 'https://www.woolworths.com.au/'
                }
                
                boost_response = session.post(
                    boost_url,
                    json={'offerIds': [offer_id]},
                    headers=boost_headers
                )
                boost_response.raise_for_status()
                
                # Check for success in response body
                if boost_response.json().get('status') == 'Success':
                    boosted_count += 1
                    logger.info(f"Boosted offer {offer_id}")
                else:
                    logger.warning(f"Unexpected response for {offer_id}: {boost_response.text}")

                time.sleep(1.5)  # Safer delay

            except Exception as e:
                logger.error(f"Boost failed for offer_id: {offer_id}  Error: {str(e)}")
        logger.info(f"{account_name}: Boosted {boosted_count}/{len(not_activated_offers)} offers")
        return f"{account_name}: Boosted {boosted_count}/{len(not_activated_offers)} offers"

    except Exception as e:
        error_msg = f"Account processing failed: {str(e)}"
        logger.error(error_msg)
        send_notification(f"{account_name} error: {str(e)}")
        return error_msg

def main():
    """Initialize and run the scheduler"""
    run_time = os.environ.get('run_time', '09:00')
    
    logger.info(f"Woolworths Loyalty Points Add-on started")
    logger.info(f"Scheduled to run daily at {run_time}")

    # Get account details from environment variables and config
    account = {
        'client_id': os.environ.get('client_id'),
        'hashcrn': os.environ.get('hashcrn'),
        'name': os.environ.get('account_name', 'My Account'),
        'x_api_key': os.environ.get('x_api_key'), # added
        'x_wooliesx_api_key': os.environ.get('x_wooliesx_api_key') # added
    }

    if not account['client_id']:
        error_msg = "Error: 'client_id' not found in environment variables"
        logger.error(error_msg)
        send_notification(error_msg)
        return
    
    # Schedule the job
    def scheduled_job():
        logger.info("scheduled_job() is being called")
        result = process_account(account)
        send_notification(result)

    schedule.every().day.at(run_time).do(scheduled_job)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

    # 1. Verify Environment Variables:
    logger.info(f"client_id: {os.environ.get('client_id')}")
    logger.info(f"hashcrn: {os.environ.get('hashcrn')}")
    logger.info(f"x_api_key: {os.environ.get('x_api_key')}")
    logger.info(f"x_wooliesx_api_key: {os.environ.get('x_wooliesx_api_key')}")
    logger.info(f"run_time: {os.environ.get('run_time')}")
    logger.info(f"notification: {os.environ.get('notification')}")
    logger.info(f"account_name: {os.environ.get('account_name')}")

    # 4. Check Python Path:
    logger.info(f"Python executable: {sys.executable}")
    
if __name__ == "__main__":
    main()