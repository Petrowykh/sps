import requests
import os
from loguru import logger

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            logger.success("Telegram notifier initialized")
        else:
            logger.warning("Telegram credentials not found - notifications disabled")
    
    def send_message(self, text: str) -> bool:
        """Простая отправка сообщения в Telegram"""
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Telegram message sent: {text[:100]}...")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

# Глобальный инстанс
telegram_notifier = TelegramNotifier()