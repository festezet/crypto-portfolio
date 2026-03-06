"""
Modèles pour les stratégies de sortie et alertes
"""
from datetime import datetime
import json
from .database import db


class ExitStrategy(db.Model):
    """Modèle pour les stratégies de sortie"""
    __tablename__ = 'exit_strategies'

    id = db.Column(db.Integer, primary_key=True)
    crypto_id = db.Column(db.Integer, db.ForeignKey('cryptos.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    mode = db.Column(db.String(20), default='alert')  # alert, semi-auto, auto

    # Configuration des seuils (JSON)
    _thresholds = db.Column('thresholds', db.Text, nullable=True)

    # Seuils déjà exécutés (JSON)
    _executed_thresholds = db.Column('executed_thresholds', db.Text, nullable=True)

    # Récupération du capital
    capital_recovery_enabled = db.Column(db.Boolean, default=True)
    capital_recovery_at_pct = db.Column(db.Float, default=100.0)  # À quel % de profit
    capital_recovery_amount_pct = db.Column(db.Float, default=100.0)  # Récupérer quel % du capital
    capital_recovered = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    alerts = db.relationship('StrategyAlert', backref='strategy', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def thresholds(self):
        """Parse le JSON des seuils"""
        if self._thresholds:
            return json.loads(self._thresholds)
        return []

    @thresholds.setter
    def thresholds(self, value):
        """Sérialise les seuils en JSON"""
        self._thresholds = json.dumps(value) if value else None

    @property
    def executed_thresholds(self):
        """Parse le JSON des seuils exécutés"""
        if self._executed_thresholds:
            return json.loads(self._executed_thresholds)
        return []

    @executed_thresholds.setter
    def executed_thresholds(self, value):
        """Sérialise les seuils exécutés en JSON"""
        self._executed_thresholds = json.dumps(value) if value else None

    def __repr__(self):
        return f'<ExitStrategy {self.crypto.symbol if self.crypto else "?"} - {"Active" if self.enabled else "Inactive"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'crypto_id': self.crypto_id,
            'crypto_symbol': self.crypto.symbol if self.crypto else None,
            'enabled': self.enabled,
            'mode': self.mode,
            'thresholds': self.thresholds,
            'executed_thresholds': self.executed_thresholds,
            'capital_recovery': {
                'enabled': self.capital_recovery_enabled,
                'at_profit_pct': self.capital_recovery_at_pct,
                'recover_pct': self.capital_recovery_amount_pct,
                'recovered': self.capital_recovered
            }
        }

    def get_next_threshold(self, current_profit_pct):
        """Retourne le prochain seuil à atteindre"""
        executed = set(self.executed_thresholds)
        for threshold in sorted(self.thresholds, key=lambda x: x['profit_pct']):
            if threshold['profit_pct'] not in executed:
                if current_profit_pct < threshold['profit_pct']:
                    return threshold
        return None

    def get_triggered_thresholds(self, current_profit_pct):
        """Retourne les seuils déclenchés mais non exécutés"""
        executed = set(self.executed_thresholds)
        triggered = []
        for threshold in self.thresholds:
            if (threshold['profit_pct'] not in executed and
                    current_profit_pct >= threshold['profit_pct']):
                triggered.append(threshold)
        return triggered

    def mark_threshold_executed(self, profit_pct):
        """Marque un seuil comme exécuté"""
        executed = self.executed_thresholds or []
        if profit_pct not in executed:
            executed.append(profit_pct)
            self.executed_thresholds = executed
            db.session.commit()


class StrategyAlert(db.Model):
    """Modèle pour les alertes de stratégie"""
    __tablename__ = 'strategy_alerts'

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('exit_strategies.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Détails de l'alerte
    threshold_pct = db.Column(db.Float, nullable=False)
    sell_pct = db.Column(db.Float, nullable=False)
    current_profit_pct = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)

    # Volume à vendre
    volume_to_sell = db.Column(db.Float, nullable=False)
    estimated_value = db.Column(db.Float, nullable=False)

    # Statut
    status = db.Column(db.String(20), default='pending')  # pending, executed, dismissed
    executed_at = db.Column(db.DateTime, nullable=True)
    executed_price = db.Column(db.Float, nullable=True)
    executed_volume = db.Column(db.Float, nullable=True)

    # Type d'alerte
    alert_type = db.Column(db.String(20), default='threshold')  # threshold, capital_recovery

    # Notes
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<StrategyAlert {self.threshold_pct}% - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'crypto_symbol': self.strategy.crypto.symbol if self.strategy and self.strategy.crypto else None,
            'date': self.date.isoformat() if self.date else None,
            'threshold_pct': self.threshold_pct,
            'sell_pct': self.sell_pct,
            'current_profit_pct': self.current_profit_pct,
            'current_price': self.current_price,
            'volume_to_sell': self.volume_to_sell,
            'estimated_value': self.estimated_value,
            'status': self.status,
            'alert_type': self.alert_type,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'executed_price': self.executed_price,
            'executed_volume': self.executed_volume
        }

    def execute(self, price=None, volume=None):
        """Marque l'alerte comme exécutée"""
        self.status = 'executed'
        self.executed_at = datetime.utcnow()
        self.executed_price = price or self.current_price
        self.executed_volume = volume or self.volume_to_sell

        # Marquer le seuil comme exécuté dans la stratégie
        if self.strategy:
            self.strategy.mark_threshold_executed(self.threshold_pct)

        db.session.commit()

    def dismiss(self, notes=None):
        """Ignore l'alerte"""
        self.status = 'dismissed'
        if notes:
            self.notes = notes
        db.session.commit()
