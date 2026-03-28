from database import db
from .encrypted_type import EncryptedString

class Termin(db.Model):
    __tablename__ = "termine"

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey("kunden.id"), nullable=False)
    gruppentermin_id = db.Column(db.Integer, db.ForeignKey("gruppentermine.id"))

    datum = db.Column(db.String)
    utc_starttime = db.Column(db.String)
    utc_endtime = db.Column(db.String)

    beschreibung = db.Column(db.String)
    kommentar = db.Column(db.String)

    betrag = db.Column(db.Float, nullable=False)
    abgesagt = db.Column(db.String)

    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)
    doku = db.Column(EncryptedString)
    caldav_uid = db.Column(db.String, unique=True, nullable=True)
    caldav_etag = db.Column(db.String, nullable=True)
    therapieform = db.Column(db.Integer)  # 1=Einzeltherapie, 2=Gruppentherapie, 3=Supervision, 4=Gruppensupervision, 5=Coaching, 6=Gruppenselbsterfahrung, 7=Einzelselbsterfahrung, 8=Gruppenselbsterfahrung, 9=Coaching
    ust = db.Column(db.Integer)  

    kunde_id = db.Column(db.Integer, db.ForeignKey("kunden.id"), nullable=False)
    kunde = db.relationship("Kunde", backref="termine")

    pers_doku = db.Column(EncryptedString)
    nur_offline_vorhanden = db.Column(db.Integer, default=0)
    nur_offline_geloescht = db.Column(db.Integer, default=0)
