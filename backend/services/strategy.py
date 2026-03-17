"""
Service de gestion des stratégies de sortie
Surveillance des seuils et génération d'alertes
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.models import db, Crypto, ExitStrategy, StrategyAlert, Transaction
from backend.services.price import price_service
from backend.services.portfolio import portfolio_service
from backend.config import DEFAULT_EXIT_STRATEGY


class StrategyService:
    """Service pour la gestion des stratégies de sortie"""

    def get_strategies(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les stratégies avec leur état actuel

        Returns:
            Liste des stratégies avec calculs de P&L
        """
        strategies = ExitStrategy.query.all()
        holdings = {h['symbol']: h for h in portfolio_service.get_holdings()}

        result = []
        for strategy in strategies:
            symbol = strategy.crypto.symbol
            holding = holdings.get(symbol)

            if not holding:
                continue

            current_profit_pct = holding['pnl_pct']
            next_threshold = strategy.get_next_threshold(current_profit_pct)
            triggered = strategy.get_triggered_thresholds(current_profit_pct)

            result.append({
                **strategy.to_dict(),
                'holding': holding,
                'current_profit_pct': current_profit_pct,
                'next_threshold': next_threshold,
                'triggered_thresholds': triggered,
                'pending_alerts': StrategyAlert.query.filter_by(
                    strategy_id=strategy.id,
                    status='pending'
                ).count()
            })

        return result

    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une stratégie par son ID"""
        strategy = ExitStrategy.query.get(strategy_id)
        if not strategy:
            return None

        holdings = {h['symbol']: h for h in portfolio_service.get_holdings()}
        symbol = strategy.crypto.symbol
        holding = holdings.get(symbol)

        if not holding:
            return strategy.to_dict()

        current_profit_pct = holding['pnl_pct']

        return {
            **strategy.to_dict(),
            'holding': holding,
            'current_profit_pct': current_profit_pct,
            'next_threshold': strategy.get_next_threshold(current_profit_pct),
            'triggered_thresholds': strategy.get_triggered_thresholds(current_profit_pct)
        }

    def create_strategy(self, crypto_symbol: str, thresholds: List[Dict] = None,
                        mode: str = 'alert', enabled: bool = True) -> ExitStrategy:
        """
        Crée une nouvelle stratégie de sortie

        Args:
            crypto_symbol: Symbole de la crypto
            thresholds: Liste des seuils (utilise défaut si non fourni)
            mode: Mode d'exécution (alert, semi-auto, auto)
            enabled: Activer la stratégie

        Returns:
            Stratégie créée
        """
        crypto = Crypto.get_or_create(crypto_symbol)

        # Vérifier qu'il n'existe pas déjà une stratégie
        existing = ExitStrategy.query.filter_by(crypto_id=crypto.id).first()
        if existing:
            raise ValueError(f"Une stratégie existe déjà pour {crypto_symbol}")

        strategy = ExitStrategy(
            crypto_id=crypto.id,
            enabled=enabled,
            mode=mode
        )

        # Utiliser les seuils par défaut si non fournis
        if thresholds:
            strategy.thresholds = thresholds
        else:
            strategy.thresholds = DEFAULT_EXIT_STRATEGY['thresholds']

        # Configuration de la récupération du capital
        default_recovery = DEFAULT_EXIT_STRATEGY['capital_recovery']
        strategy.capital_recovery_enabled = default_recovery['enabled']
        strategy.capital_recovery_at_pct = default_recovery['at_profit_pct']
        strategy.capital_recovery_amount_pct = default_recovery['recover_pct']

        db.session.add(strategy)
        db.session.commit()

        return strategy

    def update_strategy(self, strategy_id: int, data: Dict[str, Any]) -> Optional[ExitStrategy]:
        """
        Met à jour une stratégie existante

        Args:
            strategy_id: ID de la stratégie
            data: Nouvelles données

        Returns:
            Stratégie mise à jour ou None
        """
        strategy = ExitStrategy.query.get(strategy_id)
        if not strategy:
            return None

        if 'enabled' in data:
            strategy.enabled = data['enabled']
        if 'mode' in data:
            strategy.mode = data['mode']
        if 'thresholds' in data:
            strategy.thresholds = data['thresholds']
        if 'capital_recovery' in data:
            cr = data['capital_recovery']
            strategy.capital_recovery_enabled = cr.get('enabled', strategy.capital_recovery_enabled)
            strategy.capital_recovery_at_pct = cr.get('at_profit_pct', strategy.capital_recovery_at_pct)
            strategy.capital_recovery_amount_pct = cr.get('recover_pct', strategy.capital_recovery_amount_pct)

        db.session.commit()

        return strategy

    def delete_strategy(self, strategy_id: int) -> bool:
        """Supprime une stratégie"""
        strategy = ExitStrategy.query.get(strategy_id)
        if not strategy:
            return False

        db.session.delete(strategy)
        db.session.commit()

        return True

    def check_strategies(self) -> List[StrategyAlert]:
        """
        Vérifie toutes les stratégies actives et crée des alertes si nécessaire

        Returns:
            Liste des nouvelles alertes créées
        """
        strategies = ExitStrategy.query.filter_by(enabled=True).all()
        holdings = {h['symbol']: h for h in portfolio_service.get_holdings()}

        new_alerts = []

        for strategy in strategies:
            symbol = strategy.crypto.symbol
            holding = holdings.get(symbol)

            if not holding:
                continue

            current_profit_pct = holding['pnl_pct']
            current_price = holding['current_price']
            volume = holding['volume']

            self._check_threshold_alerts(
                strategy, current_profit_pct, current_price, volume, new_alerts
            )
            self._check_capital_recovery_alert(
                strategy, holding, current_profit_pct, current_price, new_alerts
            )

        if new_alerts:
            db.session.commit()

        return new_alerts

    def _check_threshold_alerts(self, strategy, current_profit_pct,
                                current_price, volume, new_alerts):
        """Verifie les seuils declenches et cree les alertes correspondantes"""
        triggered = strategy.get_triggered_thresholds(current_profit_pct)

        for threshold in triggered:
            existing_alert = StrategyAlert.query.filter_by(
                strategy_id=strategy.id,
                threshold_pct=threshold['profit_pct'],
                status='pending'
            ).first()

            if not existing_alert:
                sell_pct = threshold['sell_pct']
                volume_to_sell = volume * (sell_pct / 100)
                estimated_value = volume_to_sell * current_price

                alert = StrategyAlert(
                    strategy_id=strategy.id,
                    threshold_pct=threshold['profit_pct'],
                    sell_pct=sell_pct,
                    current_profit_pct=current_profit_pct,
                    current_price=current_price,
                    volume_to_sell=volume_to_sell,
                    estimated_value=estimated_value,
                    alert_type='threshold'
                )
                db.session.add(alert)
                new_alerts.append(alert)

    def _check_capital_recovery_alert(self, strategy, holding,
                                      current_profit_pct, current_price, new_alerts):
        """Verifie et cree une alerte de recuperation du capital si applicable"""
        if not (strategy.capital_recovery_enabled and
                not strategy.capital_recovered and
                current_profit_pct >= strategy.capital_recovery_at_pct):
            return

        existing_cr_alert = StrategyAlert.query.filter_by(
            strategy_id=strategy.id,
            alert_type='capital_recovery',
            status='pending'
        ).first()

        if existing_cr_alert:
            return

        total_invested = holding['total_invested']
        capital_to_recover = total_invested * (strategy.capital_recovery_amount_pct / 100)
        volume_to_sell = capital_to_recover / current_price if current_price > 0 else 0

        alert = StrategyAlert(
            strategy_id=strategy.id,
            threshold_pct=strategy.capital_recovery_at_pct,
            sell_pct=0,
            current_profit_pct=current_profit_pct,
            current_price=current_price,
            volume_to_sell=volume_to_sell,
            estimated_value=capital_to_recover,
            alert_type='capital_recovery'
        )
        db.session.add(alert)
        new_alerts.append(alert)

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Récupère toutes les alertes en attente"""
        alerts = StrategyAlert.query.filter_by(status='pending').order_by(
            StrategyAlert.date.desc()
        ).all()

        return [alert.to_dict() for alert in alerts]

    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une alerte par son ID"""
        alert = StrategyAlert.query.get(alert_id)
        return alert.to_dict() if alert else None

    def execute_alert(self, alert_id: int, actual_price: float = None,
                      actual_volume: float = None, notes: str = None) -> Optional[Transaction]:
        """
        Exécute une alerte (enregistre la vente)

        Args:
            alert_id: ID de l'alerte
            actual_price: Prix réel de vente (si différent)
            actual_volume: Volume réel vendu (si différent)
            notes: Notes additionnelles

        Returns:
            Transaction de vente créée
        """
        alert = StrategyAlert.query.get(alert_id)
        if not alert or alert.status != 'pending':
            return None

        strategy = alert.strategy
        crypto = strategy.crypto

        # Utiliser les valeurs réelles ou estimées
        price = actual_price or alert.current_price
        volume = actual_volume or alert.volume_to_sell

        # Créer la transaction de vente
        tx = Transaction.create_sell(
            crypto_id=crypto.id,
            volume=volume,
            price=price,
            exchange='manual',  # À améliorer avec l'API exchange
            notes=f"Stratégie de sortie - Seuil {alert.threshold_pct}%"
        )

        if notes:
            tx.notes = f"{tx.notes} - {notes}"

        db.session.add(tx)

        # Marquer l'alerte comme exécutée
        alert.execute(price=price, volume=volume)

        # Si c'est une récupération de capital, marquer comme fait
        if alert.alert_type == 'capital_recovery':
            strategy.capital_recovered = True
            db.session.commit()

        return tx

    def dismiss_alert(self, alert_id: int, notes: str = None) -> bool:
        """
        Ignore une alerte

        Args:
            alert_id: ID de l'alerte
            notes: Raison de l'ignorance

        Returns:
            True si succès
        """
        alert = StrategyAlert.query.get(alert_id)
        if not alert or alert.status != 'pending':
            return False

        alert.dismiss(notes=notes)
        return True

    def get_strategy_summary(self) -> Dict[str, Any]:
        """
        Résumé global des stratégies

        Returns:
            Statistiques des stratégies
        """
        total_strategies = ExitStrategy.query.count()
        active_strategies = ExitStrategy.query.filter_by(enabled=True).count()
        pending_alerts = StrategyAlert.query.filter_by(status='pending').count()
        executed_alerts = StrategyAlert.query.filter_by(status='executed').count()

        return {
            'total_strategies': total_strategies,
            'active_strategies': active_strategies,
            'pending_alerts': pending_alerts,
            'executed_alerts': executed_alerts
        }


# Instance globale du service
strategy_service = StrategyService()
