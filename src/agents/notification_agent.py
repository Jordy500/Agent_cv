import logging
import re

logger = logging.getLogger(__name__)


class NotificationAgent:
    """Sends email notifications for job offers that match candidate skills.
    
    This agent monitors matched job offers from the JobOfferAnalyzer
    and notifies the candidate via email when a good match is found.
    """

    def __init__(self, job_analyzer, email_sender, min_match_score=0.7):
        """Initialize the notification agent.
        
        Args:
            job_analyzer: JobOfferAnalyzer instance (provides analyzed_offers)
            email_sender: EmailSender instance (for sending emails)
            min_match_score: minimum score (0.0-1.0) to trigger notification; default 0.7
        """
        self.job_analyzer = job_analyzer
        self.email_sender = email_sender
        self.min_match_score = min_match_score
        self.sent_notifications = []  # Track sent notifications to avoid duplicates

    def send_notifications(self, recipient_email=None, force=False, generated_letters=None):
        """Send email notifications for matching job offers.
        
        Args:
            recipient_email: email address to send to; if None, read from env or skip
            force: if True, send even if already sent (for testing)
            generated_letters: dict of {offer_key: letter_text} for personalized letters
        
        Returns:
            number of notifications sent
        """
        if not self.job_analyzer.analyzed_offers:
            logger.debug('No analyzed offers available for notifications')
            return 0

        # Get recipient email from parameter or try environment
        if not recipient_email:
            import os
            recipient_email = os.environ.get('NOTIFICATION_EMAIL')
            if not recipient_email:
                logger.debug('No recipient email provided and NOTIFICATION_EMAIL not set; skipping notifications')
                return 0

        # Guard: validate email format
        if not self._is_valid_email(recipient_email):
            logger.warning(f'Invalid email address format: {recipient_email}; skipping notifications')
            return 0

        # Default to empty dict if no letters provided
        if generated_letters is None:
            generated_letters = {}

        # Filter offers with good match
        matched_offers = [
            o for o in self.job_analyzer.analyzed_offers
            if o.get('match_score', 0) >= self.min_match_score
        ]

        if not matched_offers:
            logger.debug(f'No offers with match_score >= {self.min_match_score}; no notifications to send')
            return 0

        sent_count = 0
        for offer in matched_offers:
            offer_key = f"{offer['title']}_{offer['company']}"

            # Skip if already sent (unless force=True)
            if offer_key in self.sent_notifications and not force:
                logger.debug(f'Notification already sent for "{offer_key}"; skipping')
                continue

            # Build and send email (include motivation letter if available)
            try:
                subject = self._build_subject(offer)
                motivation_letter = generated_letters.get(offer_key)
                body = self._build_email_body(offer, motivation_letter=motivation_letter)

                # If there's a motivation letter, generate a PDF attachment
                attachments = None
                if motivation_letter:
                    try:
                        from utils.pdf_generator import create_pdf_bytes
                        pdf_bytes = create_pdf_bytes(motivation_letter, title=f"Lettre de motivation - {offer['title']}")
                        filename = f"Lettre_{offer['title'].replace(' ', '_')}_{offer['company'].replace(' ', '_')}.pdf"
                        attachments = [(filename, pdf_bytes, 'application/pdf')]
                    except Exception as e:
                        logger.warning(f'Failed to generate PDF attachment for {offer_key}: {e}')

                self.email_sender.send_email(recipient_email, subject, body, attachments=attachments)

                self.sent_notifications.append(offer_key)
                sent_count += 1

                logger.info(
                    f'Notification sent for "{offer["title"]}" at {offer["company"]} '
                    f'({int(offer["match_score"] * 100)}% match) to {recipient_email}'
                )
            except Exception as e:
                logger.warning(f'Failed to send notification for "{offer_key}": {e}')

        logger.info(f'Notifications: {sent_count} sent out of {len(matched_offers)} matching offers')
        return sent_count

    def _build_subject(self, offer):
        """Build email subject line."""
        match_percent = int(offer['match_score'] * 100)
        return f"Nouvelle offre {match_percent}% - {offer['title']} - {offer['company']}"

    def _build_email_body(self, offer, motivation_letter=None):
        """Build email body with job details and optional motivation letter.
        
        Args:
            offer: job offer dict
            motivation_letter: optional generated motivation letter text
        
        Returns:
            formatted email body string
        """
        matched_skills = offer.get('matched_skills', [])
        required_skills = offer.get('required_skills', [])
        
        # Calculate missing skills for 100% match
        missing_skills = [skill for skill in required_skills if skill not in matched_skills]

        # Optionally translate the description to French using OpenAI if available
        try:
            import os
            from utils.openai_client import chat_completion
            desc = offer.get('description', 'N/A')
            if desc and desc.strip() and os.environ.get('GPT_3_API_KEY'):
                try:
                    msg = [{"role": "user", "content": f"Traduire en français le texte suivant, répondre uniquement par la traduction:\n\n{desc}"}]
                    translated = chat_completion(msg, model="gpt-3.5-turbo", max_tokens=300)
                    # Use translated text if it looks non-empty
                    if translated and len(translated) > 0:
                        description_text = translated
                    else:
                        description_text = desc
                except Exception:
                    description_text = desc
            else:
                description_text = offer.get('description', 'N/A')
        except Exception:
            # If openai helper not available, fallback to original
            description_text = offer.get('description', 'N/A')

        # Get the offer URL if available
        offer_url = offer.get('url', offer.get('link', ''))
        
        body = f"""Bonjour,

Bonne nouvelle ! Nous avons trouvé une opportunité qui correspond à votre profil :

📋 Poste : {offer['title']}
🏢 Entreprise : {offer['company']}
📊 Taux de correspondance : {int(offer['match_score'] * 100)}%"""
        
        # Add URL if available
        if offer_url:
            body += f"""
🔗 Postuler : {offer_url}"""
        
        body += f"""

Description :
{description_text}

Compétences requises :
{', '.join(required_skills) if required_skills else 'N/A'}

✅ Vos compétences correspondantes ({len(matched_skills)}/{len(required_skills)}) :
{', '.join(matched_skills) if matched_skills else 'Aucune correspondance'}"""
        
        # Add missing skills section if applicable
        if missing_skills:
            body += f"""

📚 Compétences à développer pour un match à 100% ({len(missing_skills)}) :
{', '.join(missing_skills)}

💡 Conseil : Développer ces compétences augmenterait vos chances d'obtenir ce poste."""
        else:
            body += """

🎯 Félicitations ! Vous possédez 100% des compétences requises pour ce poste !"""
        
        body += f"""

        Ce poste semble bien correspondre à votre profil. Veuillez le consulter et envisager de postuler si vous êtes intéressé.
        """

        # Add motivation letter if available
        if motivation_letter:
            body += f"""

---
LETTRE DE MOTIVATION PERSONNALISÉE
---

{motivation_letter}"""

        body += """

Cordialement,
L'équipe Agent_CV

---
Ceci est une notification automatique."""

        return body.strip()

    def _is_valid_email(self, email):
        """Validate email address format using regex.
        
        Args:
            email: email address string to validate
        
        Returns:
            True if email format is valid, False otherwise
        """
        # Basic RFC 5322 email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def get_notification_history(self):
        """Return list of offers for which notifications have been sent."""
        return self.sent_notifications.copy()

    def clear_notification_history(self):
        """Clear the notification history (useful for testing or re-sending)."""
        self.sent_notifications.clear()
        logger.info('Notification history cleared')