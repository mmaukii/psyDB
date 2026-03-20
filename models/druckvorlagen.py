from database import db


from datetime import datetime

class Druckvorlage(db.Model):
    __tablename__ = "druckvorlagen"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    pfad = db.Column(db.String)
    kuerzel = db.Column(db.String)
    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)