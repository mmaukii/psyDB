from database import db

class TermineRechnung(db.Model):
    __tablename__ = "termine_rechnungen"

    id = db.Column(db.Integer, primary_key=True)
    rechnung_id = db.Column(db.Integer, db.ForeignKey("rechnungen.id"), nullable=False)
    termin_id = db.Column(db.Integer, db.ForeignKey("termine.id"), nullable=False)  # <-- korrekt
