# notifier.py
"""
Módulo de notificação para enviar mensagens para serviços como o Telegram.
"""
import logging
import requests
from typing import Optional


class TelegramNotifier:
    """Uma classe para enviar notificações para um chat do Telegram."""

    def __init__(self, token: str, chat_id: str):
        if not token or token == "SEU_TOKEN_AQUI":
            raise ValueError("O token do bot do Telegram não foi configurado.")
        if not chat_id:
            raise ValueError("O Chat ID do Telegram não foi configurado.")

        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send_message(self, message: str) -> bool:
        """
        Envia uma mensagem de texto para o chat configurado.

        Args:
            message: O texto da mensagem a ser enviada.

        Returns:
            True se a mensagem foi enviada com sucesso, False caso contrário.
        """
        if not message or not message.strip():
            logging.warning("[TELEGRAM] Tentativa de enviar mensagem vazia. Abortando.")
            return False
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview':True
        }

        try:
            response = requests.post(self.base_url, json=payload, timeout=20)
            response_json = response.json()
            if not response_json.get('ok'):
                logging.error(f"[TELEGRAM] Erro: {response_json.get('description')}")
                return False

            logging.info("[TELEGRAM] Mensagem enviada com sucesso ao Telegram.")
            return True
        except requests.exceptions.RequestException as e:
            logging.critical(f"[TELEGRAM] Erro Crítico: {e}")
            return False
        except Exception as e:
            logging.error(f"[TELEGRAM] Erro: {e}")
            return False