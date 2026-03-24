from database import db
from .encrypted_type import EncryptedString

class Gruppentermin(db.Model):
    __tablename__ = "gruppentermine"

    id = db.Column(db.Integer, primary_key=True)
    gruppe_id = db.Column(db.Integer, db.ForeignKey("gruppen.id"), nullable=False)

    datum = db.Column(db.String)
    startzeit = db.Column(db.String)
    endzeit = db.Column(db.String)
    beschreibung = db.Column(db.String)
    kommentar = db.Column(db.String)

    betrag = db.Column(db.Float, nullable=False)
    entfallen = db.Column(db.String)

    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)
    doku = db.Column(EncryptedString)
    caldav_uid = db.Column(db.String, unique=True, nullable=True)
    caldav_etag = db.Column(db.String, nullable=True)

    pers_doku = db.Column(EncryptedString)
    nur_offline_vorhanden = db.Column(db.Integer, default=0)
    nur_offline_geloescht = db.Column(db.Integer, default=0)

    gruppe = db.relationship(
        "Gruppe",
        back_populates="gruppentermine"
    )

 


