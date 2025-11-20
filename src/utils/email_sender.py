import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests


class EmailSender:
    """Simple wrapper d'envoi d'email.

    Comporte deux modes :
    - SMTP classique (par défaut)
    - SendGrid via API si la variable SENDGRID == 'true'
    Les secrets (mot de passe SMTP ou clé SendGrid) doivent venir de variables d'environnement.
    """

    def __init__(self):
        self.sendgrid_enabled = os.environ.get('SENDGRID', 'false').lower() == 'true'
        if self.sendgrid_enabled:
            self.sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        else:
            self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            self.port = int(os.environ.get('SMTP_PORT', 587))
            self.sender_email = os.environ.get('EMAIL_SENDER')
            self.password = os.environ.get('EMAIL_PASSWORD')

    def send_email(self, recipient, subject, body):
        if self.sendgrid_enabled:
            return self._send_via_sendgrid(recipient, subject, body)
        else:
            return self._send_via_smtp(recipient, subject, body)

    def _send_via_smtp(self, recipient, subject, body):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = self.sender_email
        message['To'] = recipient
        message.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_server, self.port) as server:
            server.starttls()
            server.login(self.sender_email, self.password)
            server.send_message(message)

    def _send_via_sendgrid(self, recipient, subject, body):
        api_key = self.sendgrid_api_key
        if not api_key:
            raise RuntimeError('SENDGRID_API_KEY not set in environment')
        url = 'https://api.sendgrid.com/v3/mail/send'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'personalizations': [{
                'to': [{'email': recipient}],
                'subject': subject
            }],
            'from': {'email': os.environ.get('EMAIL_SENDER')},
            'content': [{'type': 'text/plain', 'value': body}]
        }
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp