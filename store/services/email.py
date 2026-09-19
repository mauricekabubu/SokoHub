from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging


logger = logging.getLogger(__name__)


class EmailService:

    def __init__(self, api_key):
        self.sg = SendGridAPIClient(api_key)

    def send_email(self, from_email, to_email, subject, content):
        try:
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=content,
            )

            response = self.sg.send(message)

            logger.info(
                f"Email sent to {to_email}. "
                f"Status code: {response.status_code}"
            )

            return response

        except Exception as e:
            logger.error(
                f"Error sending email to {to_email}: {e}"
            )

            return None