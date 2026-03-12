from database import db


class Druckvorlage(db.Model):
    __tablename__ = "druckvorlagen"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    pfad = db.Column(db.String)
    kuerzel = db.Column(db.String)
