from database import db


from datetime import datetime

class Standort(db.Model):
    __tablename__ = "standorte"
    standard = db.Column(db.Integer, default=0)  # 0/1 als Boolean

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    adresse = db.Column(db.String)
    plz = db.Column(db.String)
    ort = db.Column(db.String)

    email = db.Column(db.String)
    kuerzel = db.Column(db.String, unique=True)

    bic = db.Column(db.String)
    iban = db.Column(db.String)
    kontoName = db.Column(db.String)
    bankname = db.Column(db.String)
    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)
