from database import db
from .encrypted_type import EncryptedString

class Kunde(db.Model):
    __tablename__ = "kunden"

    id = db.Column(db.Integer, primary_key=True)

    nachname = db.Column(EncryptedString, nullable=False)
    vorname = db.Column(EncryptedString)
    email = db.Column(EncryptedString)
    adresse = db.Column(EncryptedString)
    plz = db.Column(EncryptedString)
    ort = db.Column(EncryptedString)

    stundensatz = db.Column(db.Numeric)
    kuerzel = db.Column(db.String, unique=True, nullable=False)
    geschlecht = db.Column(db.String)
    gebdatum = db.Column(db.String)

    ust = db.Column(db.Integer, default=0)

    rechnungTextUntenVorgabe = db.Column(db.String)
    rechnungTextObenVorgabe = db.Column(db.String)
    doku = db.Column(EncryptedString)

    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)

    standort_id = db.Column(db.Integer, nullable=False)
    therapieform = db.Column(db.Integer)
    aktiv = db.Column(db.Integer, default=1)
    standort_id = db.Column(db.Integer, db.ForeignKey('standorte.id'), nullable=False)
    druckvorlage_id = db.Column(db.Integer, db.ForeignKey('druckvorlagen.id'), nullable=False)
    dauer_min = db.Column(db.Integer)

    # Relationship
    standort = db.relationship("Standort", backref="kunden")
    druckvorlage = db.relationship("Druckvorlage", backref="kunden")
    # Neue Felder
    svnr = db.Column(db.Integer)
    krankenkasse = db.Column(db.String)
    diagnose = db.Column(db.String)

    
