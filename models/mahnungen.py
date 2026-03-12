from database import db

class Mahnung(db.Model):
    __tablename__ = "mahnungen"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rechnung_id = db.Column(db.Integer, db.ForeignKey("rechnungen.id"), nullable=True)
    datum = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.Text, nullable=True)
    kommentar = db.Column(db.Text, nullable=True)
    mahnungsnr = db.Column(db.Integer, nullable=True)   
    verzugszinsenProz = db.Column(db.Float, nullable=True)
    zahlungsziel_tage = db.Column(db.Integer, nullable=True)
    verzugszinsen = db.Column(db.Float, default=0.0)
    mahnspesen = db.Column(db.Float, default=0.0)
    
    # Optional: Beziehung zu Rechnung, falls du darauf zugreifen willst
    rechnung = db.relationship("Rechnung", backref="mahnungen", lazy=True)

    def __repr__(self):
        return f"<Mahnung id={self.id}, rechnung_id={self.rechnung_id}, datum={self.datum}>"
