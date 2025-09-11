import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

class AlertSystem: 
    def __init__(self, config):
        self.config = config.get('alert_methods', {})
    
    def send_telegram_alert(self, message):
        telegram_config = self.config.get('telegram', {})
        if telegram_config.get('enabled'):
            bot_token = telegram_config.get('bot_token', '')
            chat_id = telegram_config.get('chat_id', '')
            
            if not bot_token or not chat_id:
                logger.warning("Configuração do Telegram incompleta")
                return False
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id, 
                'text': message,
                'parse_mode': 'HTML'
            }
            try:
                response = requests.post(url, json=payload, timeout=10)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Erro ao enviar alerta Telegram: {e}")
                return False
        return False
    
    def send_email_alert(self, subject, message):
        email_config = self.config.get('email', {})
        if email_config.get('enabled'):
            try:
                msg = MIMEMultipart()
                msg['Subject'] = subject
                msg['From'] = email_config.get('username', '')
                msg['To'] = email_config.get('to', email_config.get('username', ''))
                
                msg.attach(MIMEText(message, 'plain'))
                
                with smtplib.SMTP(
                    email_config.get('smtp_server', ''), 
                    email_config.get('smtp_port', 587)
                ) as server:
                    server.starttls()
                    server.login(
                        email_config.get('username', ''), 
                        email_config.get('password', '')
                    )
                    server.send_message(msg)
                
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar email: {e}")
                return False
        return False
    
    def send_console_alert(self, message):
        logger.info(f"🔔 ALERTA: {message}")
        return True
    
    def send_alert(self, subject, message, alert_type='console'):
        """
        Envia alerta pelo método especificado
        
        Args:
            subject: Assunto do alerta
            message: Mensagem do alerta
            alert_type: 'telegram', 'email' ou 'console'
        """
        if alert_type == 'telegram':
            return self.send_telegram_alert(f"<b>{subject}</b>\n{message}")
        elif alert_type == 'email':
            return self.send_email_alert(subject, message)
        else:
            return self.send_console_alert(f"{subject}: {message}")