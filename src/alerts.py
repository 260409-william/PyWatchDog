import requests
import smtplib
from email.mime.text import MIMEText

class AlertSystem:
    def __init__(self, config):
        self.config = config
    
    def send_telegram_alert(self, message):
        if self.config['alert_methods']['telegram']['enabled']:
            bot_token = self.config['alert_methods']['telegram']['bot_token']
            chat_id = self.config['alert_methods']['telegram']['chat_id']
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message
            }
            
            try:
                response = requests.post(url, data=payload)
                return response.status_code == 200
            except Exception as e:
                print(f"Erro ao enviar alerta Telegram: {e}")
                return False
    
    def send_email_alert(self, subject, message):
        if self.config['alert_methods']['email']['enabled']:
            try:
                email_config = self.config['alert_methods']['email']
                msg = MIMEText(message)
                msg['Subject'] = subject
                msg['From'] = email_config['username']
                msg['To'] = email_config['username']
                
                with smtplib.SMTP(
                    email_config['smtp_server'],
                    email_config['smtp_port']
                ) as server:
                    server.starttls()
                    server.login(
                        email_config['username'],
                        email_config['password']
                    )
                    server.send_message(msg)
                return True
            except Exception as e:
                print(f"Erro ao enviar email: {e}")
                return False
    
    def send_console_alert(self, message):
        print(f"🔔 ALERTA: {message}")
        return True
    
    def send_alert(self, subject, message, alert_type='console'):
        if alert_type == 'telegram':
            return self.send_telegram_alert(message)
        elif alert_type == 'email':
            return self.send_email_alert(subject, message)
        else:
            return self.send_console_alert(message)
