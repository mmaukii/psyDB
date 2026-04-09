from database import db


class Leistung(db.Model):
    __tablename__ = 'leistungen'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)
    bezeichnung = db.Column(db.Text)
    dauer_min = db.Column(db.Integer)
    betrag = db.Column(db.Integer)
    gruppe = db.Column(db.Integer)  # Neue Spalte für Gruppenzuordnung
