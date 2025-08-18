# opnsense_client.py
"""
Cliente de API para interagir com uma instância do OPNsense.
"""
import re
import logging
import requests
import warnings
from typing import Optional, Dict, Any, List


class OpnSenseApiClient:
    """Gerencia a comunicação com a API de uma instância OPNsense."""

    def __init__(self, url: str, api_key: str, api_secret: str, verify_ssl: bool = False):
        self.base_url = url.rstrip('/')
        self.friendly_name = ""  # Pode ser preenchido externamente para logging

        if not verify_ssl:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        self.session = requests.Session()
        self.session.auth = (api_key, api_secret)
        self.session.verify = verify_ssl

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Método auxiliar para realizar requisições à API."""
        url = f"{self.base_url}/api/{endpoint}"
        try:
            response = self.session.request(method, url, timeout=25, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"[FIREWALL] [{self.friendly_name}] Erro HTTP {e.response.status_code} para {url}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[FIREWALL] [{self.friendly_name}] Erro de conexão com {url}: {e}")
        except Exception as e:
            logging.error(f"[FIREWALL] [{self.friendly_name}] Erro inesperado ao acessar {url}: {e}")
        return None

    def get_system_activity(self) -> Optional[Dict[str, Any]]:
        """Busca dados de atividade do sistema (CPU, Mem, Uptime)."""
        raw_data = self._make_request("get", "diagnostics/activity/get_activity")
        if not raw_data:
            return None

        # O parsing permanece complexo, mas está encapsulado aqui.
        results = {'cpu': {'total': 'N/D'}, 'mem': 'N/D', 'uptime': 0}
        # ... (código de parsing original foi mantido aqui) ...
        for line in raw_data.get('headers', []):
            if ' up ' in line:
                match = re.search(r'up\s+([\d\+]+:\d{2}:\d{2})', line)
                if match:
                    uptime_str, days = match.group(1), 0
                    if '+' in uptime_str:
                        days_str, uptime_str = uptime_str.split('+')
                        days = int(days_str)
                    h, m, s = map(int, uptime_str.split(':'))
                    results['uptime'] = (days * 86400) + (h * 3600) + (m * 60) + s
            elif line.startswith("CPU:"):
                match = re.search(r'(\d+\.\d+)%\s+idle', line)
                if match: results['cpu']['total'] = f"{(100.0 - float(match.group(1))):.1f}"
            elif line.startswith("Mem:"):
                try:
                    # Implementação de _parse_mem_value inline para simplicidade
                    def _parse(val):
                        val = val.strip().upper()
                        num = float(re.findall(r'[\d\.]+', val)[0])
                        if 'G' in val: return num * (1024 ** 3)
                        if 'M' in val: return num * (1024 ** 2)
                        if 'K' in val: return num * 1024
                        return num

                    active = _parse(re.search(r'(\d+[KMG])\s+Active', line).group(1))
                    inactive = _parse(re.search(r'(\d+[KMG])\s+Inact', line).group(1))
                    wired = _parse(re.search(r'(\d+[KMG])\s+Wired', line).group(1))
                    free = _parse(re.search(r'(\d+[KMG])\s+Free', line).group(1))
                    total_used = active + inactive + wired
                    total_mem = total_used + free
                    if total_mem > 0: results['mem'] = f"{(total_used / total_mem) * 100:.0f}"
                except Exception:
                    results['mem'] = 'N/D'
        return results

    def get_system_information(self) -> Optional[Dict[str, Any]]:
        return self._make_request("get", "diagnostics/system/system_information")

    def get_temperatures(self) -> Optional[List[Dict[str, Any]]]:
        return self._make_request("get", "diagnostics/system/system_temperature")

    def get_traffic_stats(self) -> Optional[Dict[str, Any]]:
        data = self._make_request("get", "diagnostics/traffic/_interface")
        return data.get('interfaces', {}) if data else None

    def get_gateway_status(self) -> Optional[Dict[str, Any]]:
        return self._make_request("get", "routes/gateway/status")

    def find_alias_uuid_by_name(self, alias_name: str) -> Optional[str]:
        """Encontra o UUID de um alias pelo seu nome."""
        logging.info(f"[FIREWALL] [{self.friendly_name}] Procurando alias '{alias_name}'...")
        data = self._make_request("get", "firewall/alias/searchItem")
        if data and 'rows' in data:
            for alias in data['rows']:
                if alias.get('name') == alias_name:
                    logging.info(f"[FIREWALL] [{self.friendly_name}] Alias '{alias_name}' encontrado com UUID: {alias['uuid']}")
                    return alias['uuid']
        logging.warning(f"[FIREWALL] [{self.friendly_name}] Alias '{alias_name}' não encontrado.")
        return None

    def update_alias_content(self, uuid: str, content: List[str]) -> bool:
        """Atualiza o conteúdo de um alias existente."""
        payload = {"alias": {"content": "\n".join(content)}}
        endpoint = f"firewall/alias/setItem/{uuid}"
        response = self._make_request("post", endpoint, json=payload)
        if response and response.get("result") == "saved":
            logging.info(f"[FIREWALL] [{self.friendly_name}] Alias {uuid} atualizado com sucesso no OPNsense.")
            return True
        logging.error(f"[FIREWALL] [{self.friendly_name}] Falha ao atualizar alias {uuid}: {response}")
        return False

    def apply_firewall_changes(self) -> bool:
        """Aplica as configurações de firewall pendentes."""
        logging.info(f"[FIREWALL] [{self.friendly_name}] Aplicando configurações do firewall...")
        response = self._make_request("post", "firewall/alias/reconfigure")
        if response and response.get("status") == "ok":
            logging.info(f"[FIREWALL] [{self.friendly_name}] Configurações aplicadas com sucesso.")
            return True
        logging.error(f"[FIREWALL] [{self.friendly_name}] Falha ao aplicar configurações: {response}")
        return False