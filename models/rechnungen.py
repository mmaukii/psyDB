from database import db

class Rechnung(db.Model):
    __tablename__ = "rechnungen"

    id = db.Column(db.Integer, primary_key=True)

    datum = db.Column(db.String)
    betrag = db.Column(db.Float)

    rechnungsnr = db.Column(db.Integer, unique=True)
    bezahlt = db.Column(db.Integer)

    rechnungTextOben = db.Column(db.String)
    rechnungTextUnten = db.Column(db.String)
    kommentar = db.Column(db.String)

    timestamp = db.Column(db.Integer)
    changestamp = db.Column(db.Integer)

    zahlungsziel_tage = db.Column(db.Integer, nullable=True)

    termine_rechnungen = db.relationship(
        "TermineRechnung",
        backref="rechnung",
        cascade="all, delete-orphan"
    )
