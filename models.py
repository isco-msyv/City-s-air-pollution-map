from database import db
from sqlalchemy.dialects.postgresql import JSON


class CityGeometry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    geometry = db.Column(JSON)

    @staticmethod
    def add(city, geometry):
        new = CityGeometry(city=city, geometry=geometry)

        try:
            db.session.add(new)
            db.session.commit()
        except:
            return 'There was an issue adding your task'


class CityPolygonList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    pollygons_list = db.Column(JSON)

    @staticmethod
    def add(city, pollygons_list):
        new = CityPolygonList(city=city, pollygons_list=pollygons_list)

        try:
            db.session.add(new)
            db.session.commit()
        except:
            return 'There was an issue adding your task'


class CityPollutionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.String(40), nullable=False)
    pollution = db.Column(JSON)

    @staticmethod
    def add(city, pollution, timestamp):
        new = CityPollutionData(city=city, pollution=pollution, timestamp=timestamp)

        try:
            db.session.add(new)
            db.session.commit()
        except:
            return 'There was an issue adding your task'
