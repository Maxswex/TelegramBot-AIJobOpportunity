import logging
from datetime import datetime
from typing import Optional

import requests

import sys
sys.path.insert(0, "/Users/maxswex/ai-job-alerts")
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.utils import is_italian_location, is_remote_location

logger = logging.getLogger(__name__)

# Telegram message character limit
MAX_MESSAGE_LENGTH = 4096


class TelegramBot:
    """Simple Telegram bot for sending job alerts."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a text message to the configured chat."""
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API error: {result}")
                return False

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            # Log response text for debugging
            try:
                logger.error(f"Response: {response.text}")
            except:
                pass
            return False

    def send_job_alert(self, jobs: list) -> bool:
        """Format and send job listings as Telegram message."""
        if not jobs:
            return self._send_no_jobs_message()

        messages = self._format_jobs_messages(jobs)

        success = True
        for msg in messages:
            if not self.send_message(msg):
                success = False

        return success

    def _send_no_jobs_message(self) -> bool:
        """Send message when no new jobs found."""
        today = datetime.now().strftime("%d %b %Y")
        message = f"🔔 <b>AI Job Alert</b> | {today}\n\n<i>Nessuna nuova offerta trovata oggi.</i>"
        return self.send_message(message)

    def _group_jobs_by_region(self, jobs: list) -> dict:
        """Group jobs into Italy, Europe, and Remote categories."""
        grouped = {
            "italy": [],
            "europe": [],
            "remote": [],
        }

        for job in jobs:
            location = job.location or ""
            if is_italian_location(location):
                grouped["italy"].append(job)
            elif is_remote_location(location):
                grouped["remote"].append(job)
            else:
                grouped["europe"].append(job)

        return grouped

    def _format_jobs_messages(self, jobs: list) -> list[str]:
        """Format jobs into Telegram messages with geographic sections (HTML format)."""
        today = datetime.now().strftime("%d %b %Y")
        header = f"🔔 <b>AI Job Alert</b> | {today}\n\n"

        grouped = self._group_jobs_by_region(jobs)

        messages = []
        current_message = header

        # Section headers
        sections = [
            ("italy", "──────────────────\n🇮🇹 <b>ITALIA</b>\n──────────────────\n\n"),
            ("europe", "──────────────────\n🇪🇺 <b>EUROPA</b>\n──────────────────\n\n"),
            ("remote", "──────────────────\n🌍 <b>REMOTE</b>\n──────────────────\n\n"),
        ]

        for section_key, section_header in sections:
            section_jobs = grouped[section_key]
            if not section_jobs:
                continue

            # Check if we need to add section header
            if len(current_message) + len(section_header) > MAX_MESSAGE_LENGTH - 200:
                messages.append(current_message)
                current_message = "🔔 <b>AI Job Alert (continua)</b>\n\n"

            current_message += section_header

            for job in section_jobs:
                job_text = self._format_job(job)

                # Check if adding this job would exceed limit
                if len(current_message) + len(job_text) > MAX_MESSAGE_LENGTH - 100:
                    messages.append(current_message)
                    current_message = f"🔔 <b>AI Job Alert (continua)</b>\n\n{job_text}"
                else:
                    current_message += job_text

        # Add footer
        footer = f"\n──────────────────\n📊 <b>Trovati {len(jobs)} nuovi annunci</b>"
        if len(current_message) + len(footer) > MAX_MESSAGE_LENGTH:
            messages.append(current_message)
            current_message = footer
        else:
            current_message += footer

        messages.append(current_message)

        return messages

    def _format_job(self, job) -> str:
        """Format single job as a card for Telegram message (HTML format)."""
        # Escape HTML special characters in text fields
        title = self._escape_html(job.title)
        company = self._escape_html(job.company) if job.company else "N/D"
        location = self._escape_html(job.location) if job.location else "N/D"
        source = self._escape_html(job.source) if job.source else "N/D"

        text = f"💼 <b>{title}</b>\n"
        text += f"🏢 {company}\n"
        text += f"📍 {location}\n"

        if job.salary:
            salary = self._escape_html(job.salary)
            text += f"💰 {salary}\n"
        else:
            text += "💰 Da concordare\n"

        text += f"📢 <i>{source}</i>\n"
        text += f'🔗 <a href="{job.url}">Candidati qui</a>\n\n'

        return text

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters for Telegram."""
        if not text:
            return ""

        # Escape HTML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        return text


def get_chat_id():
    """
    Helper function to get your chat ID.
    Run this after sending a message to your bot.
    """
    token = TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    try:
        response = requests.get(url, timeout=30)
        data = response.json()

        if data.get("ok") and data.get("result"):
            for update in data["result"]:
                chat = update.get("message", {}).get("chat", {})
                chat_id = chat.get("id")
                username = chat.get("username", "N/A")
                print(f"Chat ID: {chat_id}, Username: {username}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run this to get your chat ID
    get_chat_id()
