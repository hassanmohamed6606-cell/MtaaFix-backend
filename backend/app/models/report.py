from datetime import datetime, timezone
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    location_name = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    image_url = db.Column(db.String(700))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    author = db.relationship("User", back_populates="reports")

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "category": self.category, "status": self.status,
            "location_name": self.location_name, "latitude": self.latitude,
            "longitude": self.longitude, "image_url": self.image_url,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "user": {"id": self.author.id, "name": self.author.name} if self.author else None,
        }