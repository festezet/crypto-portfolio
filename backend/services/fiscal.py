"""
Service de calcul fiscal
Calcul des plus-values selon la méthode FIFO (First In, First Out)
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

from backend.models import db, Crypto, Transaction


@dataclass
class FIFOLot:
    """Représente un lot d'achat pour le calcul FIFO"""
    date: datetime
    volume: float
    price: float
    fee: float

    @property
    def remaining_volume(self):
        return self.volume

    def consume(self, volume: float) -> tuple:
        """
        Consomme une partie du lot

        Returns:
            (volume_consumed, cost_basis, fee_portion)
        """
        consumed = min(volume, self.volume)
        cost_basis = consumed * self.price
        fee_portion = (consumed / self.volume) * self.fee if self.volume > 0 else 0
        self.volume -= consumed
        return consumed, cost_basis, fee_portion


class FiscalService:
    """Service pour les calculs fiscaux"""

    def calculate_yearly_gains(self, year: int) -> Dict[str, Any]:
        """
        Calcule les plus/moins-values pour une année fiscale

        Args:
            year: Année fiscale (ex: 2024)

        Returns:
            Rapport détaillé des gains/pertes
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)

        # Récupérer toutes les transactions
        all_transactions = Transaction.query.order_by(
            Transaction.date.asc()
        ).all()

        # Grouper par crypto
        crypto_transactions = defaultdict(list)
        for tx in all_transactions:
            crypto_transactions[tx.crypto.symbol].append(tx)

        # Calculer les gains par crypto
        gains_by_crypto = {}
        total_gains = 0
        total_losses = 0
        sales_count = 0

        for symbol, transactions in crypto_transactions.items():
            result = self._calculate_crypto_gains(
                symbol, transactions, start_date, end_date
            )
            gains_by_crypto[symbol] = result

            for sale in result['sales']:
                if sale['gain'] >= 0:
                    total_gains += sale['gain']
                else:
                    total_losses += abs(sale['gain'])
                sales_count += 1

        # Résumé
        net_gain = total_gains - total_losses

        return {
            'year': year,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_gains': round(total_gains, 2),
            'total_losses': round(total_losses, 2),
            'net_gain': round(net_gain, 2),
            'sales_count': sales_count,
            'gains_by_crypto': gains_by_crypto,
            'taxable_amount': round(net_gain if net_gain > 0 else 0, 2),
            'reportable_loss': round(abs(net_gain) if net_gain < 0 else 0, 2)
        }

    def _calculate_crypto_gains(self, symbol: str, transactions: List[Transaction],
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Calcule les gains pour une crypto spécifique avec méthode FIFO

        Args:
            symbol: Symbole de la crypto
            transactions: Liste des transactions
            start_date: Début de la période
            end_date: Fin de la période

        Returns:
            Détails des ventes et gains
        """
        fifo_queue = []
        sales = []
        total_volume_sold = 0
        total_proceeds = 0
        total_cost_basis = 0
        total_fees = 0

        for tx in transactions:
            if tx.is_buy:
                fifo_queue.append(FIFOLot(
                    date=tx.date, volume=tx.volume,
                    price=tx.price, fee=tx.fee or 0
                ))

            elif tx.is_sell and start_date <= tx.date <= end_date:
                sale_record = self._process_fifo_sale(tx, fifo_queue)
                sales.append(sale_record)

                total_volume_sold += tx.volume
                total_proceeds += sale_record['proceeds']
                total_cost_basis += sale_record['cost_basis']
                total_fees += sale_record['total_fees']

        total_gain = total_proceeds - total_cost_basis - total_fees

        return {
            'symbol': symbol,
            'sales': sales,
            'summary': {
                'total_volume_sold': round(total_volume_sold, 8),
                'total_proceeds': round(total_proceeds, 2),
                'total_cost_basis': round(total_cost_basis, 2),
                'total_fees': round(total_fees, 2),
                'total_gain': round(total_gain, 2)
            }
        }

    def _process_fifo_sale(self, tx, fifo_queue) -> Dict[str, Any]:
        """Traite une vente selon la methode FIFO et retourne le detail de la cession"""
        volume_to_sell = tx.volume
        cost_basis = 0
        acquisition_fees = 0
        acquisition_dates = []

        while volume_to_sell > 0 and fifo_queue:
            lot = fifo_queue[0]
            if lot.volume <= 0:
                fifo_queue.pop(0)
                continue

            consumed, lot_cost, lot_fee = lot.consume(volume_to_sell)
            cost_basis += lot_cost
            acquisition_fees += lot_fee
            volume_to_sell -= consumed
            acquisition_dates.append({
                'date': lot.date.isoformat(),
                'volume': consumed,
                'price': lot.price
            })

            if lot.volume <= 0:
                fifo_queue.pop(0)

        proceeds = tx.total
        sale_fee = tx.fee or 0
        total_fees_for_sale = acquisition_fees + sale_fee
        gain = proceeds - cost_basis - total_fees_for_sale

        return {
            'date': tx.date.isoformat(),
            'volume': tx.volume,
            'sale_price': tx.price,
            'proceeds': round(proceeds, 2),
            'cost_basis': round(cost_basis, 2),
            'acquisition_fees': round(acquisition_fees, 2),
            'sale_fee': round(sale_fee, 2),
            'total_fees': round(total_fees_for_sale, 2),
            'gain': round(gain, 2),
            'gain_pct': round((gain / cost_basis * 100) if cost_basis > 0 else 0, 2),
            'holding_period_days': self._calculate_holding_period(acquisition_dates, tx.date),
            'acquisition_details': acquisition_dates
        }

    def _calculate_holding_period(self, acquisition_dates: List[Dict],
                                   sale_date: datetime) -> int:
        """Calcule la période de détention moyenne pondérée"""
        if not acquisition_dates:
            return 0

        total_days = 0
        total_volume = 0

        for acq in acquisition_dates:
            acq_date = datetime.fromisoformat(acq['date'])
            days = (sale_date - acq_date).days
            volume = acq['volume']
            total_days += days * volume
            total_volume += volume

        return int(total_days / total_volume) if total_volume > 0 else 0

    def generate_fiscal_report(self, year: int) -> str:
        """
        Génère un rapport fiscal au format texte

        Args:
            year: Année fiscale

        Returns:
            Rapport formaté
        """
        data = self.calculate_yearly_gains(year)

        lines = self._format_report_header(data, year)

        for symbol, crypto_data in data['gains_by_crypto'].items():
            if not crypto_data['sales']:
                continue
            lines.extend(self._format_crypto_detail(symbol, crypto_data))

        lines.extend([
            f"",
            f"=" * 60,
            f"Rapport généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Méthode de calcul : FIFO (First In, First Out)",
            f"=" * 60,
        ])

        return "\n".join(lines)

    def _format_report_header(self, data, year) -> List[str]:
        """Formate l'en-tete et le resume du rapport fiscal"""
        lines = [
            f"=" * 60,
            f"RAPPORT FISCAL CRYPTO - ANNÉE {year}",
            f"=" * 60,
            f"",
            f"RÉSUMÉ",
            f"-" * 40,
            f"Total des plus-values brutes : {data['total_gains']:>12.2f} €",
            f"Total des moins-values       : {data['total_losses']:>12.2f} €",
            f"Plus-value nette             : {data['net_gain']:>12.2f} €",
            f"",
            f"Nombre de cessions           : {data['sales_count']:>12}",
            f"",
        ]

        if data['net_gain'] >= 0:
            lines.append(f"MONTANT IMPOSABLE            : {data['taxable_amount']:>12.2f} €")
        else:
            lines.append(f"MOINS-VALUE REPORTABLE       : {data['reportable_loss']:>12.2f} €")

        lines.extend([f"", f"DÉTAIL PAR CRYPTOMONNAIE", f"=" * 60])
        return lines

    def _format_crypto_detail(self, symbol, crypto_data) -> List[str]:
        """Formate le detail d'une crypto pour le rapport fiscal"""
        summary = crypto_data['summary']
        lines = [
            f"",
            f"{symbol}",
            f"-" * 40,
            f"  Ventes effectuées    : {len(crypto_data['sales'])}",
            f"  Volume total vendu   : {summary['total_volume_sold']:.8f}",
            f"  Prix de cession total: {summary['total_proceeds']:>12.2f} €",
            f"  Prix d'acquisition   : {summary['total_cost_basis']:>12.2f} €",
            f"  Frais totaux         : {summary['total_fees']:>12.2f} €",
            f"  Plus/moins-value     : {summary['total_gain']:>12.2f} €",
            f"",
            f"  Détail des cessions:",
        ]

        for i, sale in enumerate(crypto_data['sales'], 1):
            lines.extend([
                f"    [{i}] {sale['date'][:10]}",
                f"        Volume      : {sale['volume']:.8f}",
                f"        Prix vente  : {sale['sale_price']:.2f} €",
                f"        Produit     : {sale['proceeds']:.2f} €",
                f"        Coût acq.   : {sale['cost_basis']:.2f} €",
                f"        Gain        : {sale['gain']:.2f} € ({sale['gain_pct']:.1f}%)",
                f"        Durée dét.  : {sale['holding_period_days']} jours",
            ])

        return lines

    def export_fiscal_csv(self, year: int) -> str:
        """
        Exporte le rapport fiscal en CSV pour déclaration

        Args:
            year: Année fiscale

        Returns:
            Contenu CSV
        """
        import csv
        import io

        data = self.calculate_yearly_gains(year)

        output = io.StringIO()
        writer = csv.writer(output)

        # En-têtes
        writer.writerow([
            'Date de cession',
            'Crypto',
            'Volume cédé',
            'Prix de cession',
            'Produit de cession',
            'Prix d\'acquisition (FIFO)',
            'Frais totaux',
            'Plus/moins-value',
            'Durée de détention (jours)'
        ])

        # Données
        for symbol, crypto_data in data['gains_by_crypto'].items():
            for sale in crypto_data['sales']:
                writer.writerow([
                    sale['date'][:10],
                    symbol,
                    sale['volume'],
                    sale['sale_price'],
                    sale['proceeds'],
                    sale['cost_basis'],
                    sale['total_fees'],
                    sale['gain'],
                    sale['holding_period_days']
                ])

        return output.getvalue()


# Instance globale du service
fiscal_service = FiscalService()
