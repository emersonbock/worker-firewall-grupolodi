# config.py
"""
Arquivo de configuração central para o monitor OPNsense.
"""
import os
from datetime import time as time_obj
from typing import List, Dict, Any

# --- CONFIGURAÇÕES DO TELEGRAM ---
# Recomenda-se usar variáveis de ambiente para segurança.
# Ex: TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "SEU_TOKEN_AQUI")
TELEGRAM_BOT_TOKEN: str = "7875599445:AAHnSo3yE8QO7L4oNipbsf-Vjz3waRMH1i0"
TELEGRAM_CHAT_ID: str = "-1002751332940" # Ou o seu ID

# --- CONFIGURAÇÕES DAS INSTÂNCIAS OPNsense ---
# Uma lista de dicionários, onde cada dicionário representa um firewall.
OPNSENSE_INSTANCES: List[Dict[str, Any]] = [
    #{
    #    "url": "https://guard-edi",
    #    "url_alternative": "https://168.90.210.154",
    #    "api_key": "aoMCgUDEJGryETBwk/nkwCmnFTBR0/tso4azMRGDKIsbiZXVNyvsSSiDAjcL6lZ0OaeOILyvD6W1+0P/",
    #    "api_secret": "gHplxzqkMU+bi1At+I1pxe++kfRj0hsyJmPGS/ulOdocbhabvpaJY8foHqkKslXLvZJtbjSt+g0hpZ/x",
    #    "alias_name": "filtro_dns_ativo",
    #    "friendly_name": "Edifício Lodi",
    #    "alias_content_active":"lista_de_filtrados lista_de_teste",
    #    "alias_content":"lista_de_teste"
    #},
    {
        "url": "https://guard-fva",
        "url_alternative": "https://168.90.210.158",
        "api_key": "GE88TvRS6Fo5rwswKZ8bm+pwzh9B1OxMcjl8K7vwfTmFRJKF+sjfI9+wRxJox7+z5mkzhFD0cH66lwGT",
        "api_secret": "jgb+NcVMso3lLeUVetgLTvLHGquBGZx/RjBDRmq5Anlx0VODaeBd+X3t2WCGFUvh5HmzfhvaWe7qQApl",
        "alias_name": "filtro_dns_ativo",
        "friendly_name": "Faz. Vô Amantino",
        "alias_content_active":"lista_de_filtrados lista_de_teste",
        "alias_content":"lista_de_teste"
    }
]

# --- CONFIGURAÇÕES GERAIS ---
VERIFY_SSL: bool = False  # Mude para True em produção se usar certificados válidos
CHECK_INTERVAL_SECONDS: int = 900  # 15 minutos

# --- CONFIGURAÇÕES DE POLÍTICA DE CONTEÚDO (ALIAS) ---
BLOCKED_CONTENT: List[str] = ["lista_de_filtrados","lista_de_teste"]
ALLOWED_CONTENT: List[str] = ["lista_de_teste"]

HIGH_PING_THRESHOLD_MS = 50

# --- CONFIGURAÇÕES DE HORÁRIO PARA POLÍTICAS ---
LUNCH_START_TIME: time_obj = time_obj(11, 0)
LUNCH_END_TIME: time_obj = time_obj(13, 0)
SATURDAY_FREE_TIME: time_obj = time_obj(12, 0)

# Enum para estados da política para evitar "magic strings"
class PolicyState:
    BLOCKED = "BLOQUEADO"
    ALLOWED = "LIBERADO"