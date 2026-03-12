from database import db

class Programmvariable(db.Model):
    __tablename__ = "programmvariablen"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    bezeichnung = db.Column(db.String, nullable=True)
    wert = db.Column(db.String, nullable=True)
    sort = db.Column(db.Integer, nullable=True)
    checkbox = db.Column(db.Boolean, nullable=True, default=False)