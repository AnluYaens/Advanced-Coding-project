import requests
import os
from dotenv import load_dotenv

load_dotenv ()

API_KEY = os.getenv("EXCHANGE_API_KEY")

def get_exchange_rate(base_currency, target_currency):
    """Get exchange rate between two currencies using free API"""
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch exchange rate")
    data = response.json()
    return data['conversion_rates'].get(target_currency)