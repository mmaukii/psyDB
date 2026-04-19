from database import db
from .encrypted_type import EncryptedString
class Gruppe(db.Model):
    __tablename__ = "gruppen"

    id = db.Column(db.Integer, primary_key=True)

    gruppenname = db.Column(db.String, nullable=False)
    standardbetrag = db.Column(db.Float)
    dauer_min = db.Column(db.Integer)
    gruppenkuerzel = db.Column(db.String, nullable=False)
    rechnungstext = db.Column(db.String)
    doku = db.Column(EncryptedString)
    aktiv = db.Column(db.Integer, nullable=False, default=1)
    timestamp = db.Column(db.String)
    changestamp = db.Column(db.String)
    therapieform = db.Column(db.Integer, nullable=False)  # 4=Gruppentherapie, 6=Gruppensupervision, 8=Gruppenselbsterfahrung
    ust = db.Column(db.Integer, nullable=False, default=0)
    
    # ✅ FEHLTE
    gruppentermine = db.relationship(
        "Gruppentermin",
        back_populates="gruppe",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "gruppenname": self.gruppenname,
            "standardbetrag": self.standardbetrag,
            "dauer_min": self.dauer_min,
            "gruppenkuerzel": self.gruppenkuerzel,
            "rechnungstext": self.rechnungstext,
            "doku": self.doku,
            "aktiv": self.aktiv,
            "therapieform": self.therapieform,
            "ust": self.ust,
        }