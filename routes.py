from flask import Blueprint, jsonify
from models import Product

# On crée un Blueprint pour regrouper les routes
api_bp = Blueprint('api', __name__)

@api_bp.route('/', methods=['GET'])
def list_products():
    """Retourne la liste complète des produits en format JSON[cite: 33, 58]."""
    # On récupère tous les produits, incluant ceux hors inventaire [cite: 58]
    products = list(Product.select().dicts())
    return jsonify({"products": products}), 200