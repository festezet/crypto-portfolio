"""
Modèle Crypto - Représente une cryptomonnaie
"""
from datetime import datetime
from .database import db


class Crypto(db.Model):
    """Modèle pour les cryptomonnaies"""
    __tablename__ = 'cryptos'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    coingecko_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    transactions = db.relationship('Transaction', backref='crypto', lazy='dynamic')
    strategies = db.relationship('ExitStrategy', backref='crypto', lazy='dynamic')

    def __repr__(self):
        return f'<Crypto {self.symbol}>'

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'coingecko_id': self.coingecko_id
        }

    @classmethod
    def get_or_create(cls, symbol, name=None, coingecko_id=None):
        """Récupère ou crée une crypto par son symbole"""
        crypto = cls.query.filter_by(symbol=symbol.upper()).first()
        if crypto is None:
            from backend.config import CRYPTO_MAPPING
            crypto = cls(
                symbol=symbol.upper(),
                name=name or symbol.upper(),
                coingecko_id=coingecko_id or CRYPTO_MAPPING.get(symbol.upper())
            )
            db.session.add(crypto)
            db.session.commit()
        return crypto
