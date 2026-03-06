"""
Modèle Transaction - Représente un achat, vente ou transfert
"""
from datetime import datetime
from enum import Enum
from .database import db


class TransactionType(Enum):
    """Types de transactions"""
    BUY = "BUY"
    SELL = "SELL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    STAKING_REWARD = "STAKING_REWARD"
    AIRDROP = "AIRDROP"
    FEE = "FEE"


class Exchange(Enum):
    """Exchanges supportés"""
    BINANCE = "binance"
    KUCOIN = "kucoin"
    MANUAL = "manual"
    OTHER = "other"


class Transaction(db.Model):
    """Modèle pour les transactions"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # BUY, SELL, etc.
    exchange = db.Column(db.String(20), nullable=False, default='manual')

    # Relation avec crypto
    crypto_id = db.Column(db.Integer, db.ForeignKey('cryptos.id'), nullable=False)

    # Montants
    volume = db.Column(db.Float, nullable=False)  # Quantité de crypto
    price = db.Column(db.Float, nullable=False)   # Prix unitaire en devise de base
    total = db.Column(db.Float, nullable=False)   # Montant total
    fee = db.Column(db.Float, default=0.0)        # Frais
    fee_currency = db.Column(db.String(10), default='EUR')

    # Paire de trading (ex: BTC/USDT)
    pair = db.Column(db.String(20), nullable=True)
    quote_currency = db.Column(db.String(10), default='EUR')

    # Métadonnées
    notes = db.Column(db.Text, nullable=True)
    imported_from = db.Column(db.String(255), nullable=True)
    external_id = db.Column(db.String(100), nullable=True)  # ID de l'exchange

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.type} {self.volume} {self.crypto.symbol if self.crypto else "?"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'type': self.type,
            'exchange': self.exchange,
            'crypto_id': self.crypto_id,
            'crypto_symbol': self.crypto.symbol if self.crypto else None,
            'volume': self.volume,
            'price': self.price,
            'total': self.total,
            'fee': self.fee,
            'fee_currency': self.fee_currency,
            'pair': self.pair,
            'quote_currency': self.quote_currency,
            'notes': self.notes,
            'imported_from': self.imported_from,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_buy(cls, crypto_id, volume, price, date=None, exchange='manual',
                   fee=0.0, fee_currency='EUR', notes=None, pair=None):
        """Crée une transaction d'achat"""
        return cls(
            date=date or datetime.utcnow(),
            type=TransactionType.BUY.value,
            exchange=exchange,
            crypto_id=crypto_id,
            volume=volume,
            price=price,
            total=volume * price,
            fee=fee,
            fee_currency=fee_currency,
            notes=notes,
            pair=pair
        )

    @classmethod
    def create_sell(cls, crypto_id, volume, price, date=None, exchange='manual',
                    fee=0.0, fee_currency='EUR', notes=None, pair=None):
        """Crée une transaction de vente"""
        return cls(
            date=date or datetime.utcnow(),
            type=TransactionType.SELL.value,
            exchange=exchange,
            crypto_id=crypto_id,
            volume=volume,
            price=price,
            total=volume * price,
            fee=fee,
            fee_currency=fee_currency,
            notes=notes,
            pair=pair
        )

    @property
    def is_buy(self):
        return self.type in [TransactionType.BUY.value, TransactionType.TRANSFER_IN.value,
                             TransactionType.STAKING_REWARD.value, TransactionType.AIRDROP.value]

    @property
    def is_sell(self):
        return self.type in [TransactionType.SELL.value, TransactionType.TRANSFER_OUT.value]
