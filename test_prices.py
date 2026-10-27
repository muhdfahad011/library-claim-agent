import os
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")
COUNTRY = "IN"

tests = [("1491", "Charles Mann"), ("Cobalt Red", "Siddharth Kara"), ("King Leopold's Ghost", "Adam Hochschild")]

for title, author in tests:
    for use_key in (False, True):
        params = {"q": f"intitle:{title} inauthor:{author}", "maxResults": 1,
                  "country": COUNTRY, "printType": "books"}
        if use_key:
            params["key"] = KEY
        r = requests.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=30)
        label = "with key" if use_key else "no key  "
        if r.status_code != 200:
            print(title[:22].ljust(22), label, "| HTTP", r.status_code)
            continue
        items = r.json().get("items") or []
        if not items:
            print(title[:22].ljust(22), label, "| no result")
            continue
        sale = items[0].get("saleInfo", {})
        print(title[:22].ljust(22), label, "|", sale.get("saleability"), "| list:", sale.get("listPrice"),
              "| retail:", sale.get("retailPrice"), "| buy:", (sale.get("buyLink") or "none")[:60])
