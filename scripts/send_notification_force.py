#!/usr/bin/env python3
"""Force send notifications for testing (min_match_score=0.0)
"""
from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender

def main():
    print('Force-sending notifications (min_match_score=0.0)')
    email_sender = EmailSender()
    offers = [
        {
            'id': 'job_001',
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'required_skills': ['Python', 'Django', 'PostgreSQL'],
        },
        {
            'id': 'job_002',
            'title': 'Full Stack Engineer',
            'company': 'StartupXYZ',
            'required_skills': ['JavaScript', 'React', 'Node.js', 'Python'],
        }
    ]
    job_analyzer = JobOfferAnalyzer(offers)
    # run analysis (will set match_score to 0% for the sample data unless skills provided)
    job_analyzer.compare_job_offers(cv_skills=['Python','Django','React'])

    notifier = NotificationAgent(job_analyzer=job_analyzer, email_sender=email_sender, min_match_score=0.0)
    recipient = email_sender.sender_email or 'test@example.com'
    print(f'Sending to {recipient}...')
    sent = notifier.send_notifications(recipient_email=recipient, force=True)
    print(f'Sent: {sent}')

if __name__ == '__main__':
    main()
