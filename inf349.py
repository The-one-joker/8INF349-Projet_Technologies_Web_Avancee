import click
import requests # Pour l'appel distant (ou urllib.request de la lib standard)
from flask import Flask, jsonify, request
from peewee import SqliteDatabase, Model, CharField, IntegerField, FloatField, BooleanField

app = Flask(__name__)
db = SqliteDatabase('inf349.db') # La base de données doit être un fichier local [cite: 476]

class BaseModel(Model):
    class Meta:
        database = db

class Product(BaseModel):
    # L'identifiant numérique unique du produit [cite: 470]
    id = IntegerField(primary_key=True)
    name = CharField()
    description = CharField()
    price = IntegerField() # Le prix en cents [cite: 470]
    in_stock = BooleanField()
    weight = IntegerField()
    image = CharField()

class Order(BaseModel):
    # Structure de base pour la première remise [cite: 100-114]
    total_price = FloatField(default=0.0)
    total_price_tax = FloatField(default=0.0)
    shipping_price = IntegerField(default=0)
    email = CharField(null=True)
    paid = BooleanField(default=False)
    # Pour la remise 1, une commande ne reçoit qu'un seul produit [cite: 68]
    product_id = IntegerField() 
    quantity = IntegerField()

@app.cli.command('init-db')
def init_db():
    """Initialise la base de données SQLite et crée les tables."""
    db.connect()
    db.create_tables([Product, Order]) # Crée les tables pour les modèles définis
    print("Base de données initialisée avec succès (fichier inf349.db).")