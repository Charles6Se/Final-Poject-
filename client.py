import os
import requests


def lookup():
    """Look up quote for symbol."""

    # Contact API
    try:
        # api_key = os.environ.get("API_KEY")
        # url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        
        # Don't need API Key for this
        url = f"https://api.openopus.org/composer/list/search/bruc.json"

        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    resource = response.json()
    print(resource['composers'][0]['name'])
    return
    # Parse response
    try:
        quote = response.json()
        return {

            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


lookup()