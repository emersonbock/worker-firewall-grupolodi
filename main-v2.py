# main.py
"""
Orquestrador principal para o monitoramento de saúde de firewalls OPNsense.
"""
import logging
import time
from datetime import datetime, timedelta

import config
from notifier import TelegramNotifier
from opnsense_client import OpnSenseApiClient
from utils import format_report_message

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def check_firewall_health(gateways_status: dict, high_ping_threshold: float) -> tuple[bool, list]:
    """
    Verifica a saúde dos gateways do firewall.

    Args:
        gateways_status: Dicionário com o status dos gateways vindo da API.
        high_ping_threshold: Limite de latência em ms para gerar um alerta.

    Returns:
        Uma tupla contendo:
        - bool: True se houver algum problema, False caso contrário.
        - list: Uma lista de strings descrevendo os problemas encontrados.
    """
    problems_found = []

    if not gateways_status or 'items' not in gateways_status:
        logging.warning("[SAUDE] Resposta sobre status dos gateways é inválida ou vazia.")
        problems_found.append("⚠️ Não foi possível obter o status dos gateways.")
        return True, problems_found

    for gateway in gateways_status['items']:
        name = gateway.get('name', 'N/A')
        status = gateway.get('status', 'unknown')
        delay_str = gateway.get('delay', '0.0ms')

        # 1. Verificar se o gateway está offline
        if status != 'online':
            problem_msg = f"🔴 **Gateway Offline:** `{name}` (Status: {status})"
            problems_found.append(problem_msg)
            logging.warning(f"[SAUDE] Alerta detectado: {problem_msg}")

        # 2. Verificar se o ping (latência) está alto
        try:
            # Extrai o valor numérico da latência (ex: "10.5ms" -> 10.5)
            latency_ms = float(delay_str.replace('ms', ''))
            if latency_ms > high_ping_threshold:
                problem_msg = f"🟡 **Ping Alto:** `{name}` (Latência: {latency_ms:.2f}ms)"
                problems_found.append(problem_msg)
                logging.warning(f"[SAUDE] Alerta detectado: {problem_msg}")
        except (ValueError, TypeError):
            logging.error(f"[SAUDE] Não foi possível converter a latência '{delay_str}' para número no gateway {name}.")

    return bool(problems_found), problems_found


def main():
    """Função principal que executa o loop de monitoramento."""
    logging.info("[INICIALIZANDO] >>> Iniciando monitoramento de saúde dos firewalls OPNsense <<<")

    try:
        notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    except ValueError as e:
        logging.critical(f"[INICIALIZANDO] ERRO: {e}. O script não pode continuar.")
        return

    # Intervalo entre as verificações (2 minutos)
    CHECK_INTERVAL_SECONDS = 120

    # Intervalo para enviar notificação de "Tudo OK" (30 minutos)
    OK_NOTIFICATION_INTERVAL = timedelta(minutes=30)

    # Guarda o horário da última notificação "OK" enviada.
    # Inicializamos com um valor no passado para garantir que a primeira notificação seja enviada.
    last_ok_notification_time = datetime.now() - OK_NOTIFICATION_INTERVAL

    try:
        while True:
            now = datetime.now()
            logging.info("[LOOP] >>> Iniciando novo ciclo de verificação de saúde <<<")

            any_problem_in_any_firewall = False

            for instance_config in config.OPNSENSE_INSTANCES:
                client = OpnSenseApiClient(
                    url=instance_config["url"],
                    api_key=instance_config["api_key"],
                    api_secret=instance_config["api_secret"],
                    verify_ssl=config.VERIFY_SSL,
                )
                client.friendly_name = instance_config["friendly_name"]
                logging.info(f"[{client.friendly_name}] Verificando saúde...")

                # Coleta os dados de saúde
                gateways = client.get_gateway_status()
                # Poderíamos coletar mais dados aqui se quiséssemos incluí-los nos alertas
                # system_info = client.get_system_information()
                # temperatures = client.get_temperatures()

                # Analisa os dados coletados
                has_problem, problem_details = check_firewall_health(
                    gateways,
                    config.HIGH_PING_THRESHOLD_MS
                )

                if has_problem:
                    any_problem_in_any_firewall = True
                    # Monta e envia notificação de ALERTA imediatamente
                    alert_header = f"🚨 *ALERTA DE SAÚDE NO FIREWALL: {client.friendly_name}* 🚨"
                    # Junta os problemas encontrados em uma única string
                    problems_text = "\n".join(problem_details)
                    full_message = f"{alert_header}\n\n{problems_text}"

                    logging.warning(f"[{client.friendly_name}] ENVIANDO ALERTA: {problems_text}")
                    notifier.send_message(full_message)

            # Após verificar todos os firewalls, decidimos se enviamos o relatório "OK"
            if not any_problem_in_any_firewall:
                logging.info("[SAUDE] Todos os firewalls estão operando normalmente.")
                # Verifica se já passou tempo suficiente para enviar um novo relatório de "OK"
                if now - last_ok_notification_time >= OK_NOTIFICATION_INTERVAL:
                    logging.info(
                        f"[NOTIFICACAO] Enviando relatório periódico de status 'OK' (a cada {OK_NOTIFICATION_INTERVAL.total_seconds() / 60:.0f} min).")

                    # Monta uma mensagem simples de status OK
                    ok_message = f"✅ *Relatório de Status*\n\nTodos os firewalls monitorados estão operando normalmente.\n\n_Próxima verificação em {CHECK_INTERVAL_SECONDS / 60:.0f} minutos._"

                    notifier.send_message(ok_message)

                    # Atualiza o horário da última notificação enviada
                    last_ok_notification_time = now
                else:
                    minutes_to_next_report = (OK_NOTIFICATION_INTERVAL - (
                                now - last_ok_notification_time)).total_seconds() / 60
                    logging.info(
                        f"[NOTIFICACAO] Status 'OK'. Próximo relatório em {minutes_to_next_report:.1f} minutos.")

            # Aguarda 2 minutos para o próximo ciclo
            logging.info(f"[LOOP] >>> Ciclo finalizado. Aguardando {CHECK_INTERVAL_SECONDS} segundos. <<<")
            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("[LOOP] Script interrompido pelo usuário. Encerrando.")
    except Exception as e:
        logging.critical(f"[LOOP] Erro inesperado: {e}", exc_info=True)
        # Envia notificação sobre o erro no próprio script
        notifier.send_message(
            f"🆘 *ERRO CRÍTICO NO SCRIPT DE MONITORAMENTO*\n\nOcorreu uma exceção não tratada:\n`{e}`\n\nO script pode ter sido encerrado. Verifique os logs.")


if __name__ == "__main__":
    main()