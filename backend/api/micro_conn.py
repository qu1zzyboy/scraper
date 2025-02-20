import requests
import json
import socket
import dotenv
from config import Config
def send_ip_to_microservice():
    config=Config()
    service_id=config.SERVICE_ID
    server_URL=config.MICR_SERVER_URL
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    finally:
        s.close()
    url = f'{server_URL}/register-heartbeat'
    data = {
        "ip_or_domain": ip_address,
        "service_id": service_id
        
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            print(response.text)
            print("IP address has successfully sent to microservice")
        else:
            print(f"Failed，status code: {response.status_code}, response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to request: {e}")