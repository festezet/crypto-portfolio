"""
Routes de l'API REST - Routes etendues (strategies, alerts, fiscal, import/export)
"""
from flask import Blueprint, request, Response
from shared_lib.flask_helpers import success, error

from backend.services.import_export import import_export_service
from backend.services.strategy import strategy_service
from backend.services.fiscal import fiscal_service

api_ext_bp = Blueprint('api_ext', __name__, url_prefix='/api')


# ============================================================
# IMPORT/EXPORT ENDPOINTS
# ============================================================

@api_ext_bp.route('/import', methods=['POST'])
def import_file():
    """Importe un fichier de transactions"""
    if 'file' not in request.files:
        return error(400, 'No file provided')

    file = request.files['file']
    if file.filename == '':
        return error(400, 'No file selected')

    try:
        content = file.read().decode('utf-8')
        source = request.form.get('source', 'auto')

        if source == 'auto':
            source = import_export_service.detect_format(content)

        if source == 'binance':
            result = import_export_service.import_binance_csv(content, file.filename)
        elif source == 'kucoin':
            result = import_export_service.import_kucoin_csv(content, file.filename)
        else:
            mapping = request.form.get('mapping')
            if mapping:
                import json
                mapping = json.loads(mapping)
                result = import_export_service.import_generic_csv(
                    content, mapping,
                    exchange=source or 'manual',
                    filename=file.filename
                )
            else:
                return error(400, 'Unknown format and no mapping provided')

        return success(result)

    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/export/transactions', methods=['GET'])
def export_transactions():
    """Exporte les transactions"""
    format_type = request.args.get('format', 'csv')
    crypto_id = request.args.get('crypto_id', type=int)
    exchange = request.args.get('exchange')

    try:
        if format_type == 'json':
            content = import_export_service.export_transactions_json(
                crypto_id=crypto_id,
                exchange=exchange
            )
            mimetype = 'application/json'
            filename = 'transactions.json'
        else:
            content = import_export_service.export_transactions_csv(
                crypto_id=crypto_id,
                exchange=exchange
            )
            mimetype = 'text/csv'
            filename = 'transactions.csv'

        return Response(
            content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return error(500, str(e))


# ============================================================
# STRATEGIES ENDPOINTS
# ============================================================

@api_ext_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """Récupère les stratégies de sortie"""
    try:
        strategies = strategy_service.get_strategies()
        return success(strategies)
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/strategies/<int:strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """Récupère une stratégie"""
    try:
        strategy = strategy_service.get_strategy(strategy_id)
        if strategy:
            return success(strategy)
        return error(404, 'Strategy not found')
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/strategies', methods=['POST'])
def create_strategy():
    """Crée une stratégie de sortie"""
    data = request.get_json()

    if 'symbol' not in data:
        return error(400, 'Missing symbol')

    try:
        strategy = strategy_service.create_strategy(
            crypto_symbol=data['symbol'],
            thresholds=data.get('thresholds'),
            mode=data.get('mode', 'alert'),
            enabled=data.get('enabled', True)
        )
        return success(strategy.to_dict(), 201)
    except ValueError as e:
        return error(400, str(e))
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/strategies/<int:strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """Met à jour une stratégie"""
    data = request.get_json()

    try:
        strategy = strategy_service.update_strategy(strategy_id, data)
        if strategy:
            return success(strategy.to_dict())
        return error(404, 'Strategy not found')
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """Supprime une stratégie"""
    try:
        if strategy_service.delete_strategy(strategy_id):
            return success()
        return error(404, 'Strategy not found')
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/strategies/check', methods=['POST'])
def check_strategies():
    """Vérifie les stratégies et crée les alertes"""
    try:
        alerts = strategy_service.check_strategies()
        return success({
            'new_alerts': len(alerts),
            'alerts': [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return error(500, str(e))


# ============================================================
# ALERTS ENDPOINTS
# ============================================================

@api_ext_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Récupère les alertes en attente"""
    try:
        alerts = strategy_service.get_pending_alerts()
        return success(alerts)
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/alerts/<int:alert_id>/execute', methods=['POST'])
def execute_alert(alert_id):
    """Exécute une alerte (enregistre la vente)"""
    data = request.get_json() or {}

    try:
        tx = strategy_service.execute_alert(
            alert_id,
            actual_price=data.get('price'),
            actual_volume=data.get('volume'),
            notes=data.get('notes')
        )
        if tx:
            return success({'transaction': tx.to_dict()})
        return error(404, 'Alert not found or already processed')
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id):
    """Ignore une alerte"""
    data = request.get_json() or {}

    try:
        if strategy_service.dismiss_alert(alert_id, notes=data.get('notes')):
            return success()
        return error(404, 'Alert not found or already processed')
    except Exception as e:
        return error(500, str(e))


# ============================================================
# FISCAL ENDPOINTS
# ============================================================

@api_ext_bp.route('/fiscal/<int:year>', methods=['GET'])
def get_fiscal_report(year):
    """Récupère le rapport fiscal pour une année"""
    try:
        report = fiscal_service.calculate_yearly_gains(year)
        return success(report)
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/fiscal/<int:year>/consolidated', methods=['GET'])
def get_fiscal_consolidated(year):
    """Récupère le récap fiscal consolidé multi-plateformes"""
    try:
        # Crypto P&L from app DB (FIFO)
        crypto_report = fiscal_service.calculate_yearly_gains(year)

        # Hardcoded data from 2025 analysis (Trade Republic IFU + Revolut)
        # TODO: move to DB when data model supports non-crypto assets
        consolidated = {
            'year': year,
            'crypto': {
                'gains_by_crypto': crypto_report.get('gains_by_crypto', {}),
                'total_gains': crypto_report.get('total_gains', 0),
                'total_losses': crypto_report.get('total_losses', 0),
                'net_gain': crypto_report.get('net_gain', 0),
                'sales_count': crypto_report.get('sales_count', 0),
            },
            'trade_republic': {
                'interests': 789.0,
                'dividends': 632.0,
                'pv_mobilieres': 25.0,
                'pfu_paid': 143.0,
                'crypto_pv': 25.0,
                'details': [
                    {'label': 'Intérêts compte courant (2TR)', 'amount': 789.0},
                    {'label': 'Dividendes (2TS)', 'amount': 632.0},
                    {'label': 'PV mobilières actions (3VG)', 'amount': 25.0},
                    {'label': 'PFU déjà prélevé (2CK)', 'amount': 143.0},
                ]
            },
            'revolut': {
                'schneider_pv': 0.22,
                'schneider_div': 0.57,
                'currency_losses': {
                    'CHF': -0.63,   # 30.46 CHF achetés €33.02, 22.66 vendus €23.93
                    'JPY': -0.78,   # ¥1593 achetés €10, vendus €9.22
                    'XAU': -1.19,   # 0.05 XAU acheté €150, vendu €150.31 - fee €1.50
                    'DKK': -0.46,   # 1548 DKK achetés €208.14, 641 vendus €85.72
                },
                'total_currency_loss': -3.06,
                'currency_fees': 2.54,  # fees explicites sur conversions devises
                'details': [
                    {'label': 'Schneider Electric PV', 'amount': 0.22},
                    {'label': 'Schneider Electric dividende', 'amount': 0.57},
                    {'label': 'Perte change CHF (22.66 CHF vendus)', 'amount': -0.63},
                    {'label': 'Perte change JPY (¥1 593 vendus)', 'amount': -0.78},
                    {'label': 'Perte or XAU (0.0495 XAU vendu)', 'amount': -1.19},
                    {'label': 'Perte change DKK (641 DKK vendus)', 'amount': -0.46},
                    {'label': 'Frais conversion devises (5 opérations)', 'amount': -2.54},
                ]
            },
            'fees_total': {
                'kucoin_trading': 16.67,
                'kucoin_convert_spread': 140.0,
                'kucoin_withdrawal': 208.0,
                'binance': 0.0,
                'kraken': 0.0,
                'revolut_buy': 122.64,
                'revolut_send': 55.98,
                'total': 530.62,
            },
            'tax_cases': [
                # Pré-rempli par le fisc (toutes sources confondues)
                {'case': '2DC', 'label': 'Dividendes actions (abattement 40%)',
                 'amount': 63.0, 'prefilled': True,
                 'source': 'Pré-rempli (inclut Trade Republic)'},
                {'case': '2TR', 'label': 'Intérêts et placements',
                 'amount': 7364.0, 'prefilled': True,
                 'source': 'Pré-rempli (TR + Crédit Coop + autres)'},
                {'case': '2BH', 'label': 'RCM bruts (2DC + 2TR)',
                 'amount': 7427.0, 'prefilled': True,
                 'source': 'Pré-rempli'},
                {'case': '2CK', 'label': 'PFU déjà prélevé',
                 'amount': 950.0, 'prefilled': True,
                 'source': 'Pré-rempli (tous établissements)'},
                # À saisir manuellement
                {'case': '3VG', 'label': 'PV mobilières', 'amount': 25.0,
                 'prefilled': False,
                 'source': 'Trade Republic + Revolut'},
                {'case': '2086', 'label': 'PV crypto — NON REQUIS',
                 'amount': 0, 'prefilled': False,
                 'source': 'Sursis d\'imposition : échanges crypto→USDT uniquement, aucune conversion en EUR'},
                {'case': '3916', 'label': 'Comptes étrangers (intégré à la déclaration en ligne)',
                 'amount': None, 'prefilled': False,
                 'source': '5 comptes : Kucoin, Binance, Kraken, Revolut, Trade Republic'},
                {'case': '7UD', 'label': 'Dons organismes aide (75%)',
                 'amount': 317.0, 'prefilled': False,
                 'source': 'MSF, Médecins du Monde, Croix-Rouge'},
                {'case': '7UF', 'label': 'Dons autres organismes (66%)',
                 'amount': 457.0, 'prefilled': False,
                 'source': 'WWF, Oxfam, UNICEF, LPO'},
            ],
            'donations': {
                'associations': [
                    {'name': 'WWF', 'monthly': 12.0,
                     'jan': 12.0, 'total': 144.0, 'regime': '66%', 'case': '7UF'},
                    {'name': 'MSF', 'monthly': 8.0,
                     'jan': 35.0, 'feb': 15.0, 'mar': 15.0,
                     'total': 137.0, 'regime': '75%', 'case': '7UD'},
                    {'name': 'Oxfam', 'monthly': 8.0,
                     'jan': 20.0, 'total': 108.0, 'regime': '66%', 'case': '7UF'},
                    {'name': 'Médecins du Monde', 'monthly': 8.0,
                     'jan': 20.0, 'total': 108.0, 'regime': '75%', 'case': '7UD'},
                    {'name': 'UNICEF', 'monthly': 10.0,
                     'jan': 25.0, 'total': 135.0, 'regime': '66%', 'case': '7UF'},
                    {'name': 'LPO', 'monthly': 5.0,
                     'jan': 15.0, 'total': 70.0, 'regime': '66%', 'case': '7UF'},
                    {'name': 'Croix-Rouge', 'monthly': 6.0,
                     'jan': 6.0, 'total': 72.0, 'regime': '75%', 'case': '7UD'},
                ],
                'total': 774.0,
                'total_7UD': 317.0,   # MSF 137 + MDM 108 + Croix-Rouge 72
                'total_7UF': 457.0,   # WWF 144 + Oxfam 108 + UNICEF 135 + LPO 70
                'reduction_7UD': 237.75,  # 317 * 75%
                'reduction_7UF': 301.62,  # 457 * 66%
                'total_reduction': 539.37,
                'source': 'Crédit Coopératif — prélèvements mensuels',
            },
            'foreign_accounts': [
                {'platform': 'Kucoin', 'country': 'Seychelles',
                 'opened': '2025-05', 'closed': '2025-12',
                 'max_value': 14500},
                {'platform': 'Binance', 'country': 'Cayman Islands',
                 'opened': '2025-05', 'closed': None,
                 'max_value': 5000},
                {'platform': 'Kraken', 'country': 'USA',
                 'opened': '2025-05', 'closed': None,
                 'max_value': 12000},
                {'platform': 'Revolut', 'country': 'Lithuania',
                 'opened': '2025-04', 'closed': None,
                 'max_value': 15000},
                {'platform': 'Trade Republic', 'country': 'Germany',
                 'opened': '2025-08', 'closed': None,
                 'max_value': 6000},
            ]
        }

        # 2025: No crypto-to-fiat conversions — all trades were crypto-to-crypto
        # (XMR→USDT, HYPE→USDT) benefiting from sursis d'imposition
        # No 2086 form required, no taxable crypto gains
        consolidated['crypto']['sursis_imposition'] = True
        consolidated['crypto']['sursis_detail'] = (
            "Aucune cession crypto → EUR en 2025. "
            "Les échanges crypto→USDT bénéficient du sursis d'imposition "
            "(art. 150 VH bis CGI). Formulaire 2086 non requis."
        )
        # Acquisition costs preserved for future sales
        consolidated['crypto']['prix_acquisition_total'] = 11189.62
        consolidated['crypto']['detail_acquisition'] = (
            "Achats: 11 000€ + fees exchange: 11€ + frais Revolut: 178,62€"
        )

        return success(consolidated)
    except Exception as e:
        return error(500, str(e))


@api_ext_bp.route('/fiscal/<int:year>/export', methods=['GET'])
def export_fiscal_report(year):
    """Exporte le rapport fiscal"""
    format_type = request.args.get('format', 'text')

    try:
        if format_type == 'csv':
            content = fiscal_service.export_fiscal_csv(year)
            mimetype = 'text/csv'
            filename = f'rapport_fiscal_{year}.csv'
        else:
            content = fiscal_service.generate_fiscal_report(year)
            mimetype = 'text/plain'
            filename = f'rapport_fiscal_{year}.txt'

        return Response(
            content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return error(500, str(e))
