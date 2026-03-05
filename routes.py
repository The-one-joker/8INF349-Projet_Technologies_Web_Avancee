from flask import Blueprint, jsonify, request
from models import Product, Order
import requests 

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

def calculate_total_with_shipping(order):

    product = Product.get_by_id(order.product_id)
    
    total_price = product.price * order.quantity
    
    tax_rate = TAX_RATES.get(order.province, 0)
    total_taxed = total_price * (1 + tax_rate)
    
    total_weight = product.weight * order.quantity
    shipping = calculate_shipping(total_weight)
    
    return round(total_taxed + shipping, 2)

def get_tax_rate(province):
    rates = {"QC": 0.15, "ON": 0.13, "AB": 0.05, "BC": 0.12, "NS": 0.14}
    return rates.get(province, 0)

def format_order(order):
    product = Product.get_by_id(order.product_id)
    
    # 1. Calculs obligatoires
    total_price = product.price * order.quantity
    
    tax_rate = TAX_RATES.get(order.province, 0)
    total_price_tax = round(total_price * (1 + tax_rate), 2)
    
    total_weight = product.weight * order.quantity
    shipping_price = calculate_shipping(total_weight)

    # 2. Construction de l'objet shipping_information 
    shipping_info = {}
    if order.address:
        shipping_info = {
            "country": order.country,
            "address": order.address,
            "postal_code": order.postal_code,
            "city": order.city,
            "province": order.province
        }

    # 3. Construction des objets de paiement (vides par défaut) 
    credit_card_info = {}
    transaction_info = {}
    
    if order.paid:
        credit_card_info = {
            "name": order.cc_name,
            "first_digits": order.cc_first_digits,
            "last_digits": order.cc_last_digits,
            "expiration_year": order.cc_exp_year,
            "expiration_month": order.cc_exp_month
        }
        transaction_info = {
            "id": order.transaction_id,
            "success": True,
            "amount_charged": order.amount_charged
        }

    return {
        "order": {
            "shipping_information": shipping_info,
            "credit_card": credit_card_info,
            "email": order.email,
            "total_price": total_price,
            "total_price_tax": total_price_tax,
            "transaction": transaction_info,
            "paid": order.paid,
            "product": {
                "id": order.product_id,
                "quantity": order.quantity
            },
            "shipping_price": shipping_price,
            "id": order.id
        }
    }

@api_bp.route('/', methods=['GET'])
def list_products():
    
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

    return jsonify(format_order(order)), 200

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


@api_bp.route('/order/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    try:
        order = Order.get_by_id(order_id)
    except Order.DoesNotExist:
        return jsonify({"errors": {"order": {"code": "not-found", "name": "La commande n'existe pas"}}}), 404 

    data = request.get_json()
    
    # --- SCÉNARIO A: Mise à jour des informations client ---
    if 'order' in data:
        order_data = data['order']
        required = ['email', 'shipping_information']
        ship_req = ['country', 'address', 'postal_code', 'city', 'province']
        
        if not all(k in order_data for k in required) or \
           not all(k in order_data.get('shipping_information', {}) for k in ship_req):
            return jsonify({"errors": {"order": {"code": "missing-fields", "name": "Champs obligatoires manquants"}}}), 422 

        order.email = order_data['email']
        ship = order_data['shipping_information']
        order.country, order.address = ship['country'], ship['address']
        order.postal_code, order.city, order.province = ship['postal_code'], ship['city'], ship['province']
        order.save()
        return jsonify(format_order(order)), 200


    # --- SCÉNARIO B: Paiement par carte de crédit ---
    elif 'credit_card' in data:
        if order.paid:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "already-paid", 
                        "name": "La commande a déjà été payée."
                    }
                }
            }), 422 


        if not order.email or not order.province:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "missing-fields", 
                        "name": "Les informations du client sont nécessaires avant d'appliquer une carte de crédit"
                    }
                }
            }), 422 

        payment_url = "http://dimprojetu.uqac.ca/~jgnault/shops/pay/"
        cc_data = data['credit_card']
        
        amount = calculate_total_with_shipping(order)
        
        payload = {
            "credit_card": {
                "name": cc_data.get("name"),
                "number": cc_data.get("number"),
                "expiration_year": cc_data.get("expiration_year"),
                "expiration_month": cc_data.get("expiration_month"),
                "cvv": str(cc_data.get("cvv")) 
            },
            "amount_charged": amount
        }

        try:
            response = requests.post(payment_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                res_data = response.json()
                
                order.paid = True
                
                order.transaction_id = res_data['transaction']['id']
                order.amount_charged = res_data['transaction']['amount_charged']
                
                order.cc_name = res_data['credit_card']['name']
                order.cc_first_digits = res_data['credit_card']['first_digits']
                order.cc_last_digits = res_data['credit_card']['last_digits']
                order.cc_exp_year = res_data['credit_card']['expiration_year']
                order.cc_exp_month = res_data['credit_card']['expiration_month']
                
                order.save()
                
                return jsonify(format_order(order)), 200
            
            else:
                try:
                    return jsonify(response.json()), 422
                except:
                    return jsonify({
                        "errors": {
                            "credit_card": {
                                "code": "card-declined", 
                                "name": "La carte de crédit a été déclinée."
                            }
                        }
                    }), 422
                    
        except requests.exceptions.RequestException:
            return jsonify({
                "errors": {
                    "payment": {
                        "code": "timeout", 
                        "name": "Le service de paiement est indisponible"
                    }
                }
            }), 503