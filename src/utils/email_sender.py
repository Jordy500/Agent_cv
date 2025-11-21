import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import logging

logger = logging.getLogger(__name__)

try:
    from .guards import check_env_var, check_api_key
except ImportError:
    from guards import check_env_var, check_api_key


class EmailSender:
    
    def __init__(self):
        self.sendgrid_enabled = os.environ.get('SENDGRID', 'false').lower() == 'true'
        
        if self.sendgrid_enabled:
            # Guard: Check SendGrid API key
            if not check_api_key('SENDGRID_API_KEY', 'SendGrid'):
                logger.warning('SendGrid API key not set; email sending via SendGrid will fail')
            self.sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        else:
            # Guard: Check SMTP credentials
            smtp_server = check_env_var('SMTP_SERVER')
            email_sender = check_env_var('EMAIL_SENDER')
            password = check_env_var('EMAIL_PASSWORD')
            
            if not all([smtp_server, email_sender, password]):
                logger.warning('Some SMTP credentials are missing; email sending via SMTP may fail')
            
            self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            self.port = int(os.environ.get('SMTP_PORT', 587))
            self.sender_email = os.environ.get('EMAIL_SENDER')
            self.password = os.environ.get('EMAIL_PASSWORD')

    def send_email(self, recipient, subject, body, attachments=None):

        test_mode = os.environ.get('EMAIL_TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            import logging
            logging.getLogger(__name__).info(
                f'[TEST MODE] Email to {recipient} | Subject: {subject}'
            )
            return True
        
        if self.sendgrid_enabled:
            return self._send_via_sendgrid(recipient, subject, body, attachments=attachments)
        else:
            return self._send_via_smtp(recipient, subject, body, attachments=attachments)

    def _send_via_smtp(self, recipient, subject, body, attachments=None):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = self.sender_email
        message['To'] = recipient
        message.attach(MIMEText(body, 'plain'))

        if attachments:
            for att in attachments:
                try:
                    filename, data, mime_type = att
                except Exception:

                    filename, data = att
                    mime_type = 'application/octet-stream'

                part = MIMEBase(*mime_type.split('/', 1))
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                message.attach(part)

        with smtplib.SMTP(self.smtp_server, self.port) as server:
            server.starttls()
            server.login(self.sender_email, self.password)
            server.send_message(message)
        return True

    def _send_via_sendgrid(self, recipient, subject, body, attachments=None):
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

        if attachments:
            sg_atts = []
            for att in attachments:
                try:
                    filename, data, mime_type = att
                except Exception:
                    filename, data = att
                    mime_type = 'application/octet-stream'

                b64 = base64.b64encode(data).decode('ascii')
                sg_atts.append({
                    'content': b64,
                    'type': mime_type,
                    'filename': filename
                })
            payload['attachments'] = sg_atts

        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp