from database import db

class GruppenKunde(db.Model):
    __tablename__ = "gruppen_kunden"

    gruppe_id = db.Column(db.Integer, db.ForeignKey("gruppen.id"), primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey("kunden.id"), primary_key=True)
    betrag = db.Column(db.Integer)
