import os
import requests
import json
import time
import paho.mqtt.client as mqtt

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
    except Exception as e:
        print(f"Failed to send notification: {e}")

def main():
    # Get credentials from environment variables
    client_id = os.environ.get('client_id')
    hashcrn = os.environ.get('hashcrn')
    
    if not client_id:
        print("Error: 'client_id' not found in environment variables")
        send_notification("Error: Missing client_id configuration")
        return
    
    # Set up headers for the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'client_id': client_id,
        'hashcrn': hashcrn or "",
        'content-type': 'application/json'
    }
    
    # Make GET request to fetch offers
    offers_url = "https://prod.api-wr.com/wx/vl/csl/customers/offers"
    try:
        response = requests.get(offers_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching offers: {e}"
        print(error_msg)
        send_notification(error_msg)
        return
    
    # Process the response data
    try:
        data = response.json()
        offers = data.get('offers', [])
        print(f"Total offers found: {len(offers)}")
        
        # Filter offers with "NotActivated" status
        not_activated_offers = [offer for offer in offers if offer.get('status') == "NotActivated"]
        print(f"Not activated offers: {len(not_activated_offers)}")
        
        # Boost each not activated offer
        boost_url = "https://prod.api-wr.com/wx/vl/csl/customers/offers/boost"
        boosted_count = 0
        
        for offer in not_activated_offers:
            offer_id = offer.get('id')
            if not offer_id:
                continue
                
            # Prepare the POST data
            post_data = {'offerlds': [offer_id]}
            
            try:
                boost_response = requests.post(
                    boost_url,
                    headers=headers,
                    data=json.dumps(post_data)
                )
                boost_response.raise_for_status()
                
                # Check if boost was successful
                if boost_response.status_code == 200:
                    boosted_count += 1
                    print(f"Successfully boosted offer ID: {offer_id}")
                    
                # Small delay to avoid API rate limiting
                time.sleep(1)
                    
            except requests.exceptions.RequestException as e:
                print(f"Error boosting offer {offer_id}: {e}")
        
        result_msg = f"Successfully boosted {boosted_count} offers out of {len(not_activated_offers)} not activated offers"
        print(result_msg)
        send_notification(result_msg)
        
    except json.JSONDecodeError:
        error_msg = "Error: Could not parse JSON response"
        print(error_msg)
        send_notification(error_msg)
    except KeyError as e:
        error_msg = f"Error: Missing expected key in response data: {e}"
        print(error_msg)
        send_notification(error_msg)

if __name__ == "__main__":
    main()
