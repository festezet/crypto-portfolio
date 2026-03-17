"""
Service de récupération des prix en temps réel
Utilise CoinGecko API (gratuit) ou les APIs des exchanges
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

from backend.config import COINGECKO_API_URL, CRYPTO_MAPPING, BASE_CURRENCY


class PriceService:
    """Service pour récupérer les prix des cryptomonnaies"""

    def __init__(self):
        self._cache = {}
        self._cache_duration = 60  # Durée du cache en secondes
        self._last_request_time = 0
        self._min_request_interval = 1.5  # Délai minimum entre requêtes (rate limiting)

    def _rate_limit(self):
        """Respecte le rate limiting de l'API"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _is_cache_valid(self, symbol: str) -> bool:
        """Vérifie si le cache est encore valide"""
        if symbol not in self._cache:
            return False
        cache_time = self._cache[symbol].get('timestamp', 0)
        return (time.time() - cache_time) < self._cache_duration

    def get_price(self, symbol: str, currency: str = None) -> Optional[float]:
        """
        Récupère le prix d'une crypto en temps réel

        Args:
            symbol: Symbole de la crypto (ex: BTC, ETH)
            currency: Devise de référence (défaut: EUR)

        Returns:
            Prix en float ou None si erreur
        """
        currency = (currency or BASE_CURRENCY).lower()
        symbol = symbol.upper()

        # Vérifier le cache
        cache_key = f"{symbol}_{currency}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['price']

        # Récupérer l'ID CoinGecko
        coingecko_id = CRYPTO_MAPPING.get(symbol)
        if not coingecko_id:
            print(f"Warning: No CoinGecko ID for {symbol}")
            return None

        try:
            self._rate_limit()
            url = f"{COINGECKO_API_URL}/simple/price"
            params = {
                'ids': coingecko_id,
                'vs_currencies': currency,
                'include_24hr_change': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if coingecko_id in data and currency in data[coingecko_id]:
                price = data[coingecko_id][currency]
                change_24h = data[coingecko_id].get(f'{currency}_24h_change', 0)

                # Mettre en cache
                self._cache[cache_key] = {
                    'price': price,
                    'change_24h': change_24h,
                    'timestamp': time.time()
                }
                return price

        except requests.RequestException as e:
            print(f"Error fetching price for {symbol}: {e}")

        return None

    def get_prices(self, symbols: List[str], currency: str = None) -> Dict[str, float]:
        """
        Récupère les prix de plusieurs cryptos en une seule requête

        Args:
            symbols: Liste de symboles (ex: ['BTC', 'ETH'])
            currency: Devise de référence (défaut: EUR)

        Returns:
            Dictionnaire {symbol: price}
        """
        currency = (currency or BASE_CURRENCY).lower()
        result = {}

        to_fetch = self._collect_cached_prices(symbols, currency, result)
        if not to_fetch:
            return result

        ids_map = self._build_coingecko_ids_map(to_fetch)
        if not ids_map:
            return result

        self._fetch_and_cache_prices(ids_map, currency, result)
        return result

    def _collect_cached_prices(self, symbols: List[str], currency: str,
                               result: Dict[str, float]) -> List[str]:
        """Collecte les prix en cache et retourne les symboles manquants"""
        to_fetch = []
        for symbol in symbols:
            symbol = symbol.upper()
            cache_key = f"{symbol}_{currency}"
            if self._is_cache_valid(cache_key):
                result[symbol] = self._cache[cache_key]['price']
            else:
                to_fetch.append(symbol)
        return to_fetch

    def _build_coingecko_ids_map(self, symbols: List[str]) -> Dict[str, str]:
        """Construit le mapping CoinGecko ID -> symbol"""
        ids_map = {}
        for symbol in symbols:
            cg_id = CRYPTO_MAPPING.get(symbol)
            if cg_id:
                ids_map[cg_id] = symbol
        return ids_map

    def _fetch_and_cache_prices(self, ids_map: Dict[str, str],
                                currency: str, result: Dict[str, float]):
        """Fetch les prix depuis l'API et met en cache"""
        try:
            self._rate_limit()
            url = f"{COINGECKO_API_URL}/simple/price"
            params = {
                'ids': ','.join(ids_map.keys()),
                'vs_currencies': currency,
                'include_24hr_change': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            for cg_id, symbol in ids_map.items():
                if cg_id in data and currency in data[cg_id]:
                    price = data[cg_id][currency]
                    change_24h = data[cg_id].get(f'{currency}_24h_change', 0)

                    cache_key = f"{symbol}_{currency}"
                    self._cache[cache_key] = {
                        'price': price,
                        'change_24h': change_24h,
                        'timestamp': time.time()
                    }
                    result[symbol] = price

        except requests.RequestException as e:
            print(f"Error fetching prices: {e}")

    def get_price_change_24h(self, symbol: str, currency: str = None) -> Optional[float]:
        """Récupère le changement de prix sur 24h en pourcentage"""
        currency = (currency or BASE_CURRENCY).lower()
        symbol = symbol.upper()
        cache_key = f"{symbol}_{currency}"

        # Forcer la mise à jour si pas en cache
        if not self._is_cache_valid(cache_key):
            self.get_price(symbol, currency)

        if cache_key in self._cache:
            return self._cache[cache_key].get('change_24h')
        return None

    def get_historical_price(self, symbol: str, date: datetime,
                             currency: str = None) -> Optional[float]:
        """
        Récupère le prix historique d'une crypto à une date donnée

        Args:
            symbol: Symbole de la crypto
            date: Date pour laquelle récupérer le prix
            currency: Devise de référence

        Returns:
            Prix historique ou None
        """
        currency = (currency or BASE_CURRENCY).lower()
        symbol = symbol.upper()

        coingecko_id = CRYPTO_MAPPING.get(symbol)
        if not coingecko_id:
            return None

        try:
            self._rate_limit()
            date_str = date.strftime('%d-%m-%Y')
            url = f"{COINGECKO_API_URL}/coins/{coingecko_id}/history"
            params = {'date': date_str, 'localization': 'false'}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'market_data' in data and 'current_price' in data['market_data']:
                return data['market_data']['current_price'].get(currency)

        except requests.RequestException as e:
            print(f"Error fetching historical price for {symbol}: {e}")

        return None

    def get_market_chart(self, symbol: str, days: int = 30,
                         currency: str = None) -> Optional[List[tuple]]:
        """
        Récupère l'historique des prix sur une période

        Args:
            symbol: Symbole de la crypto
            days: Nombre de jours d'historique
            currency: Devise de référence

        Returns:
            Liste de tuples (timestamp, price) ou None
        """
        currency = (currency or BASE_CURRENCY).lower()
        symbol = symbol.upper()

        coingecko_id = CRYPTO_MAPPING.get(symbol)
        if not coingecko_id:
            return None

        try:
            self._rate_limit()
            url = f"{COINGECKO_API_URL}/coins/{coingecko_id}/market_chart"
            params = {
                'vs_currency': currency,
                'days': days,
                'interval': 'daily' if days > 1 else 'hourly'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'prices' in data:
                return [(datetime.fromtimestamp(p[0] / 1000), p[1]) for p in data['prices']]

        except requests.RequestException as e:
            print(f"Error fetching market chart for {symbol}: {e}")

        return None

    def clear_cache(self):
        """Vide le cache des prix"""
        self._cache.clear()


# Instance globale du service
price_service = PriceService()
