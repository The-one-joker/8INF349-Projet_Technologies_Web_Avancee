import requests
from models import Product

def fetch_products():
    url = "https://dimensweb.uqac.ca/~jgnault/shops/products/"
    response = requests.get(url)
    if response.status_code == 200:
        products_data = response.json().get('products', [])
        for p in products_data:
            # On utilise .replace() pour mettre à jour les données existantes
            # sans créer de doublons à chaque lancement [cite: 441, 443]
            Product.replace(
                id=p['id'], name=p['name'], description=p['description'],
                price=p['price'], in_stock=p['in_stock'], 
                weight=p['weight'], image=p['image']
            ).execute()