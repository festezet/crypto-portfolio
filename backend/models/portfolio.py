"""
Modèle PortfolioSnapshot - Sauvegarde l'état du portefeuille à un instant T
"""
from datetime import datetime
import json
from .database import db


class PortfolioSnapshot(db.Model):
    """Modèle pour les snapshots du portefeuille"""
    __tablename__ = 'portfolio_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, index=True, default=datetime.utcnow)

    # Valeurs globales en EUR
    total_value = db.Column(db.Float, nullable=False, default=0.0)
    total_invested = db.Column(db.Float, nullable=False, default=0.0)
    total_pnl = db.Column(db.Float, nullable=False, default=0.0)
    total_pnl_pct = db.Column(db.Float, nullable=False, default=0.0)

    # Détails par crypto (JSON)
    _details = db.Column('details', db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def details(self):
        """Parse le JSON des détails"""
        if self._details:
            return json.loads(self._details)
        return {}

    @details.setter
    def details(self, value):
        """Sérialise les détails en JSON"""
        self._details = json.dumps(value) if value else None

    def __repr__(self):
        return f'<PortfolioSnapshot {self.date} - {self.total_value}€>'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_value': self.total_value,
            'total_invested': self.total_invested,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'details': self.details
        }

    @classmethod
    def create_snapshot(cls, total_value, total_invested, details=None):
        """Crée un nouveau snapshot du portefeuille"""
        pnl = total_value - total_invested
        pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0

        snapshot = cls(
            date=datetime.utcnow(),
            total_value=total_value,
            total_invested=total_invested,
            total_pnl=pnl,
            total_pnl_pct=pnl_pct
        )
        snapshot.details = details

        db.session.add(snapshot)
        db.session.commit()

        return snapshot
