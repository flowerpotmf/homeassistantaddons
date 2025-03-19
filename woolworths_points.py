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

def process_offers():
    """Main function to process and boost Woolworths offers"""
    logger.info("Starting Woolworths Loyalty Points boost process")
    
    # Get credentials from environment variables
    client_id = os.environ.get('client_id')
    hashcrn = os.environ.get('hashcrn')
    
    if not client_id:
        error_msg = "Error: 'client_id' not found in environment variables"
        logger.error(error_msg)
        send_notification(error_msg)
        return
    
    # Set up headers for the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'client_id': client_id,
        'hashcrn': hashcrn or "",
        'content-type': 'application/json'
    }
    
    # Make GET request to fetch offers
    offers_url = "https://prod.api-wr.com/wx/v1/csl/customers/offers"
    try:
        logger.info("Fetching offers from Woolworths API")
        response = requests.get(offers_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching offers: {e}"
        logger.error(error_msg)
        send_notification(error_msg)
        return
    
    # Process the response data
    try:
        data = response.json()
        offers = data.get('offers', [])
        logger.info(f"Total offers found: {len(offers)}")
        
        # Filter offers with "NotActivated" status
        not_activated_offers = [offer for offer in offers if offer.get('status') == "NotActivated"]
        logger.info(f"Not activated offers: {len(not_activated_offers)}")
        
        # Boost each not activated offer
        boost_url = "https://prod.api-wr.com/wx/vl/csl/customers/offers/boost"
        boosted_count = 0
        
        for offer in not_activated_offers:
            offer_id = offer.get('id')
            if not offer_id:
                continue
                
            # Prepare the POST data
            post_data = {'offerIds': [offer_id]}
            
            try:
                logger.info(f"Attempting to boost offer ID: {offer_id}")
                boost_response = requests.post(
                    boost_url,
                    headers=headers,
                    data=json.dumps(post_data)
                )
                boost_response.raise_for_status()
                
                # Check if boost was successful
                if boost_response.status_code == 200:
                    boosted_count += 1
                    logger.info(f"Successfully boosted offer ID: {offer_id}")
                    
                # Small delay to avoid API rate limiting
                time.sleep(1)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error boosting offer {offer_id}: {e}")
        
        result_msg = f"Successfully boosted {boosted_count} offers out of {len(not_activated_offers)} not activated offers"
        logger.info(result_msg)
        send_notification(result_msg)
        
    except json.JSONDecodeError:
        error_msg = "Error: Could not parse JSON response"
        logger.error(error_msg)
        send_notification(error_msg)
    except KeyError as e:
        error_msg = f"Error: Missing expected key in response data: {e}"
        logger.error(error_msg)
        send_notification(error_msg)

def main():
    """Initialize and run the scheduler"""
    run_time = os.environ.get('run_time', '09:00')
    
    logger.info(f"Woolworths Loyalty Points Add-on started")
    logger.info(f"Scheduled to run daily at {run_time}")
    
    # Schedule the job
    schedule.every().day.at(run_time).do(process_offers)
    
    # Also run once at startup if needed
    # process_offers()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()