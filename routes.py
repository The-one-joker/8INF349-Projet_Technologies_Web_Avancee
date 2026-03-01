from flask import Blueprint, jsonify, request
from models import Product, Order

# On crée un Blueprint pour regrouper les routes
api_bp = Blueprint('api', __name__)

# On fait les calcules pour les taxes et les prix selon le poid

def calculate_shipping(weight):
    """Calcul frais d'expédition selon poids total en grammes"""
    if weight < 500:
        return 500      # 5$
    elif weight < 2000:
        return 1000     # 10$
    else:
        return 2500     # 25$

TAX_RATES = {
    "QC": 0.15,
    "ON": 0.13,
    "AB": 0.05,
    "BC": 0.12,
    "NS": 0.14,
}

def format_order(order):
    # Récupère le produit lié
    product = Product.get_by_id(order.product_id)
    
    total_price = product.price * order.quantity
    
    # Calcul taxes selon province (si shipping_information rempli)
    province = order.province if order.province else None
    tax_rate = TAX_RATES.get(province, 0)
    total_price_tax = round(total_price * (1 + tax_rate), 2)
    
    # Calcul shipping selon poids total
    shipping_price = calculate_shipping(product.weight * order.quantity)

    shipping_information = {}
    if order.address:
        shipping_information = {
            "country": order.country,
            "address": order.address,
            "postal_code": order.postal_code,
            "city": order.city,
            "province": order.province
        }
    return {
        "id": order.id,
        "product": {
            "id": order.product_id,
            "quantity": order.quantity
        },
        "total_price": total_price,
        "total_price_tax": total_price_tax,
        "shipping_price": shipping_price,
        "email": order.email,
        "credit_card":{},
        "transaction":{},
        "paid": False
    }


@api_bp.route('/', methods=['GET'])
def list_products():
    """Retourne la liste complète des produits en format JSON[cite: 33, 58]."""
    # On récupère tous les produits, incluant ceux hors inventaire [cite: 58]
    products = list(Product.select().dicts())
    return jsonify({"products": products}), 200

# On crée un blueprint pour envoyer une erreur 404 si la commande est inexistante

@api_bp.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):
    # 404 si commande inexistante
    try:
        order = Order.get_by_id(order_id)
    except Order.DoesNotExist:
        return jsonify({"errors": {"order": {"code": "not-found", "name": "La commande n'existe pas"}}}), 404

    return jsonify({"order": format_order(order)}), 200

@api_bp.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()

    # Vérifie que l'objet product existe
    if not data or 'product' not in data:
        return jsonify({"errors": {"product": {
            "code": "missing-fields",
            "name": "La création d'une commande nécessite un produit"
        }}}), 422

    product_data = data['product']

    # Vérifie id et quantity présents
    if 'id' not in product_data or 'quantity' not in product_data:
        return jsonify({"errors": {"product": {
            "code": "missing-fields",
            "name": "La création d'une commande nécessite un produit"
        }}}), 422

    # Vérifie quantity >= 1
    if product_data['quantity'] < 1:
        return jsonify({"errors": {"product": {
            "code": "missing-fields",
            "name": "La création d'une commande nécessite un produit"
        }}}), 422

    # Vérifie que le produit existe
    try:
        product = Product.get_by_id(product_data['id'])
    except Product.DoesNotExist:
        return jsonify({"errors": {"product": {
            "code": "missing-fields",
            "name": "La création d'une commande nécessite un produit"
        }}}), 422

    # Vérifie que le produit est en stock
    if not product.in_stock:
        return jsonify({"errors": {"product": {
            "code": "out-of-inventory",
            "name": "Le produit demandé n'est pas en inventaire"
        }}}), 422

    # Crée la commande
    order = Order.create(
        product_id=product.id,
        quantity=product_data['quantity'],
        paid=False
    )

    return '', 302, {'Location': f'/order/{order.id}'}
