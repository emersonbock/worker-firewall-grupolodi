# main.py
"""
Orquestrador principal para o monitoramento e controle de firewalls OPNsense.
"""
import logging
import time
from datetime import datetime, timedelta

import config
from notifier import TelegramNotifier
from opnsense_client import OpnSenseApiClient
from utils import get_firewall_policy_state, format_report_message

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def process_firewall_policy(client: OpnSenseApiClient, alias_name: str, desired_state: str, current_states: dict):
    """Gerencia a política de firewall baseada em horário para uma instância."""
    current_state = current_states.get(client.base_url)
    logging.info(f"[FIREWALL] [{client.friendly_name}] Estado da política - Atual: {current_state}, Desejado: {desired_state}")

    if desired_state != current_state:
        logging.info(f"[FIREWALL] [{client.friendly_name}] Mudança de estado detectada. Atualizando alias...")

        alias_uuid = client.find_alias_uuid_by_name(alias_name)
        if not alias_uuid:
            logging.warning(f"[FIREWALL] [{client.friendly_name}] Não foi possível prosseguir sem o UUID do alias '{alias_name}'.")
            return

        content_to_apply = config.ALLOWED_CONTENT if desired_state == config.PolicyState.ALLOWED else config.BLOCKED_CONTENT

        if client.update_alias_content(alias_uuid, content_to_apply):
            if client.apply_firewall_changes():
                current_states[client.base_url] = desired_state
                logging.info(
                    f"[FIREWALL] [{client.friendly_name}] Política de firewall atualizada para '{desired_state}' com sucesso.")
            else:
                logging.error(f"[FIREWALL] [{client.friendly_name}] Falha ao APLICAR as novas regras do alias.")
        else:
            logging.error(f"[FIREWALL] [{client.friendly_name}] Falha ao ATUALIZAR o conteúdo do alias.")
    else:
        logging.info(f"[FIREWALL] [{client.friendly_name}] Nenhuma mudança de política necessária.")


def main():
    """Função principal que executa o loop de monitoramento."""
    logging.info("[INICIALIZANDO] >>> Iniciando monitoramento e controle dos firewalls OPNsense <<<")

    try:
        notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    except ValueError as e:
        logging.critical(f"[INICIALIZANDO] ERRO: {e}. O script não pode continuar.")
        return

    # --- NOVAS VARIÁVEIS PARA CONTROLE DE TEMPO ---
    # Define os intervalos desejados para cada tarefa
    STATUS_CHECK_INTERVAL = timedelta(minutes=1)
    REPORT_SEND_INTERVAL = timedelta(minutes=45)

    # Guarda o horário da última execução de cada tarefa.
    # Inicializamos com um valor no passado para garantir que rodem na primeira vez.
    last_status_check_time = datetime.now() - STATUS_CHECK_INTERVAL
    last_report_send_time = datetime.now() - REPORT_SEND_INTERVAL

    # Dicionário para manter o último estado conhecido de cada firewall
    firewall_policy_states = {}

    try:
        while True:
            # Pega o horário atual no início de cada ciclo do loop
            now = datetime.now()

            # --- BLOCO 1: VERIFICAÇÃO DE STATUS DO FIREWALL (a cada 5 minutos) ---
            if now - last_status_check_time >= STATUS_CHECK_INTERVAL:
                logging.info(
                    f"[FIREWALL] >>> Iniciando a verificação! <<< (a cada {STATUS_CHECK_INTERVAL.total_seconds() / 60:.0f} min) ---")

                desired_policy_state = get_firewall_policy_state(now)

                for instance_config in config.OPNSENSE_INSTANCES:
                    client = OpnSenseApiClient(
                        url=instance_config["url"],
                        api_key=instance_config["api_key"],
                        api_secret=instance_config["api_secret"],
                        verify_ssl=config.VERIFY_SSL
                    )
                    client.friendly_name = instance_config["friendly_name"]
                    logging.info(f"[{client.friendly_name}] Verificando política de alias...")

                    # Executa apenas a lógica de gerenciamento da política
                    process_firewall_policy(
                        client,
                        instance_config["alias_name"],
                        desired_policy_state,
                        firewall_policy_states
                    )

                # Atualiza o horário da última verificação de status
                last_status_check_time = now
                logging.info("[FIREWALL] >>> Finalizando a verificação <<<")

            # --- BLOCO 2: ENVIO DA ANÁLISE/RELATÓRIO (a cada 45 minutos) ---
            if now - last_report_send_time >= REPORT_SEND_INTERVAL:
                logging.info(
                    f"[RELATORIO] >>> Iniciando extração de relatórios. <<< (a cada {REPORT_SEND_INTERVAL.total_seconds() / 60:.0f} min) ---")

                for instance_config in config.OPNSENSE_INSTANCES:
                    client = OpnSenseApiClient(
                        url=instance_config["url"],
                        api_key=instance_config["api_key"],
                        api_secret=instance_config["api_secret"],
                        verify_ssl=config.VERIFY_SSL
                    )
                    client.friendly_name = instance_config["friendly_name"]

                    # Coleta de dados para o relatório
                    logging.info(f"[RELATORIO] ({client.friendly_name}) Coletando dados para o relatório...")
                    system_info = client.get_system_information()
                    activity = client.get_system_activity()
                    temperatures = client.get_temperatures()
                    traffic = client.get_traffic_stats()
                    gateways = client.get_gateway_status()

                    # Formata e envia o relatório
                    report_message = format_report_message(
                        firewall_name=client.friendly_name,
                        system_info=system_info,
                        activity=activity,
                        temperatures=temperatures,
                        traffic=traffic,
                        gateways=gateways
                    )

                    notifier.send_message(report_message)
                    time.sleep(5)  # Pequeno delay para não sobrecarregar a API do Telegram

                # Atualiza o horário do último envio de relatório
                last_report_send_time = now
                logging.info("[RELATORIO] >>> Fim da verificação! <<<")

            # --- AJUSTE NO TEMPO DE ESPERA ---
            # O loop agora dorme por um período curto (ex: 60 segundos).
            # Isso garante que o script verifique os horários a cada minuto,
            # sem consumir muito processador.
            sleep_interval = 60
            logging.debug(f"[LOOP] >>> {sleep_interval} segundos para o próximo ciclo <<<")
            time.sleep(sleep_interval)

    except KeyboardInterrupt:
        logging.info("[LOOP] Script interrompido pelo usuário. Encerrando.")
    except Exception as e:
        logging.critical(f"[LOOP] Erro: {e}", exc_info=True)


if __name__ == "__main__":
    main()