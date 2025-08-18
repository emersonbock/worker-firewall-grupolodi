# utils.py
"""
Funções utilitárias para formatação de dados e lógica de negócio.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

from config import LUNCH_START_TIME, LUNCH_END_TIME, SATURDAY_FREE_TIME, PolicyState


def get_firewall_policy_state(now: datetime) -> str:
    """
    Determina o estado desejado da política de firewall (BLOQUEADO ou LIBERADO)
    com base na data e hora atuais.
    """
    current_time = now.time()
    weekday = now.weekday()  # Segunda=0, Domingo=6

    if weekday == 6:  # Domingo
        return PolicyState.ALLOWED
    if weekday == 5:  # Sábado
        return PolicyState.ALLOWED if current_time >= SATURDAY_FREE_TIME else PolicyState.BLOCKED
    if 0 <= weekday < 5:  # Dias de semana
        is_lunch_time = LUNCH_START_TIME <= current_time < LUNCH_END_TIME
        return PolicyState.ALLOWED if is_lunch_time else PolicyState.BLOCKED

    return PolicyState.BLOCKED  # Padrão de segurança


def _format_uptime(seconds: int) -> str:
    """Formata segundos em um formato legível (dias, horas, minutos)."""
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"

def _format_bytes_to_gb(bytes_str: str) -> str:
    """Converte uma string de bytes para Gigabytes (GB) com duas casas decimais."""
    try:
        gb = int(bytes_str) / (1024 ** 3)
        return f"{gb:.2f} GB"
    except (ValueError, TypeError):
        return "0.00 GB"
# --- Fim das Funções Auxiliares ---


def format_report_message(
        firewall_name: str,
        system_info: Dict[str, Any],
        activity: Dict[str, Any],
        temperatures: List[Dict[str, Any]],
        traffic: Dict[str, Any],
        gateways: Dict[str, Any]) -> str:
    """
    Constrói a mensagem de relatório formatada em HTML para o Telegram.
    """
    parts = [f" <b>{firewall_name}</b> 📍\n"]

    # Atividade do Sistema
    if activity:
        uptime = _format_uptime(activity.get("uptime", 0))
        cpu = activity.get('cpu', {}).get('total', 'N/D')
        mem = activity.get('mem', 'N/D')
        parts.append(f"  - CPU: <code>{cpu}%</code> | Memória: <code>{mem}%</code>")
        parts.append(f"  - Tempo Ligado: <code>{uptime}</code>")

    # Temperatura
    if temperatures and isinstance(temperatures, list) and temperatures:
        cpu_temps = [
            float(t['temperature']) for t in temperatures
            if t.get('type') == 'cpu' and str(t.get('temperature', '')).replace('.', '', 1).isdigit()
        ]
        if cpu_temps:
            avg_temp = sum(cpu_temps) / len(cpu_temps)
            parts.append(f"  - Temp. Média CPU: <code>{avg_temp:.1f}°C</code>")

    # Gateways
    # Adiciona uma linha em branco antes desta seção para separação visual
    if gateways and 'items' in gateways and gateways['items']:
        parts.append(f"\n🛰️ <b>Status dos Gateways:</b>\n")
        for gw in gateways['items']:
            # Ignora gateways que contenham "VPN" no nome
            if "VPN" not in gw.get('name', ''):
                status_icon = "🟢" if gw.get('status') in ['okay', 'force_down', 'none'] else "🔴"
                status_text = gw.get('status_translated', 'N/D')
                loss = gw.get('loss', 'N/D')
                delay = gw.get('delay', 'N/D')
                # Use a tag <code> para dados que devem ser alinhados ou se beneficiam de fonte monoespaçada
                parts.append(f"  {status_icon} {gw.get('name', 'N/D')}: {status_text}\n     Perda: <code>{loss}</code>  Latência: <code>{delay}</code>")

    # Tráfego de Rede
    # Adiciona uma linha em branco antes desta seção
    if traffic:
        parts.append(f"\n📊 <b>Tráfego de Rede</b>")
        for if_name, if_data in traffic.items():
            friendly_name = if_data.get('name', if_name).upper()
            if "VPN" not in friendly_name:
                received = _format_bytes_to_gb(if_data.get('bytes received', '0'))
                transmitted = _format_bytes_to_gb(if_data.get('bytes transmitted', '0'))
                # Usa \n para as quebras de linha ao invés de <br>
                parts.append(f"\n   <b>{friendly_name}:</b>\n    📥 Recebido: <code>{received}</code>\n    📤 Transmitido: <code>{transmitted}</code>")
    parts.append('\n<a href="https://pmetecnologia.com.br"><blockquote>Monitorado por PME TECNOLOGIA</blockquote></a>')
    # Junta todas as partes com quebras de linha
    return "\n".join(parts)