from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ScrapeJob(db.Model):
    __tablename__ = 'scrape_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False)
    keyword = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')
    total_found = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    businesses = db.relationship('Business', backref='job', lazy=True)

class Business(db.Model):
    __tablename__ = 'businesses'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), db.ForeignKey('scrape_jobs.job_id'), nullable=False)
    name = db.Column(db.String(200))
    rating = db.Column(db.Float)
    review_count = db.Column(db.Integer, default=0)
    business_type = db.Column(db.String(200))
    address = db.Column(db.Text)
    phone = db.Column(db.String(50))
    website = db.Column(db.String(500))
    hours = db.Column(db.Text)
    status = db.Column(db.String(50))
    price_level = db.Column(db.String(10))
    place_id = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    maps_url = db.Column(db.Text)
    is_claimed = db.Column(db.Boolean, default=False)
    thumbnail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rating': self.rating,
            'review_count': self.review_count,
            'type': self.business_type,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'hours': self.hours,
            'status': self.status,
            'price_level': self.price_level,
            'place_id': self.place_id,
            'lat': self.latitude,
            'lng': self.longitude,
            'maps_url': self.maps_url,
            'is_claimed': self.is_claimed,
            'thumbnail': self.thumbnail
        }
