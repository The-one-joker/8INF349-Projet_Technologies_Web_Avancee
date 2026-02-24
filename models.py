from peewee import SqliteDatabase, Model, CharField, IntegerField, FloatField, BooleanField

db = SqliteDatabase('inf349.db')

class BaseModel(Model):
    class Meta:
        database = db

class Product(BaseModel):
    id = IntegerField(primary_key=True) 
    name = CharField()
    description = CharField() 
    price = IntegerField() 
    in_stock = BooleanField() 
    weight = IntegerField()
    image = CharField() 

class Order(BaseModel):
    # Pour la remise 1, un seul produit par commande [cite: 68]
    product_id = IntegerField()
    quantity = IntegerField()
    shipping_price = IntegerField(default=0) 
    total_price = IntegerField(default=0) 
    total_price_tax = FloatField(default=0.0) 
    email = CharField(null=True) 
    paid = BooleanField(default=False)
    # Informations de livraison [cite: 141-147]
    address = CharField(null=True)
    city = CharField(null=True)
    province = CharField(null=True)
    postal_code = CharField(null=True)
    country = CharField(null=True)