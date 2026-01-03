import logging
from datetime import datetime
from typing import Optional

import requests

import sys
sys.path.insert(0, "/Users/maxswex/ai-job-alerts")
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
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
        message = f"*AI Job Alert - {today}*\n\n_Nessuna nuova offerta trovata oggi._"
        return self.send_message(message)

    def _format_jobs_messages(self, jobs: list) -> list[str]:
        """Format jobs into Telegram messages, splitting if too long."""
        today = datetime.now().strftime("%d %b %Y")
        header = f"*AI Job Alert - {today}*\n\n"
        footer = f"\n\n_Trovati {len(jobs)} nuovi annunci oggi_"

        messages = []
        current_message = header

        for job in jobs:
            job_text = self._format_job(job)

            # Check if adding this job would exceed limit
            if len(current_message) + len(job_text) + len(footer) > MAX_MESSAGE_LENGTH - 100:
                # Finalize current message and start new one
                current_message += footer
                messages.append(current_message)
                current_message = f"*AI Job Alert (continua...)*\n\n{job_text}"
            else:
                current_message += job_text

        # Add final message
        current_message += footer
        messages.append(current_message)

        return messages

    def _format_job(self, job) -> str:
        """Format single job for Telegram message."""
        # Escape markdown special characters in text fields
        title = self._escape_markdown(job.title)
        company = self._escape_markdown(job.company) if job.company else "N/D"
        location = self._escape_markdown(job.location) if job.location else "N/D"

        text = f"*{title}*\n"
        text += f"_{company}_ - {location}\n"

        if job.salary:
            salary = self._escape_markdown(job.salary)
            text += f"Salario: {salary}\n"

        text += f"[Vedi annuncio]({job.url})\n"
        text += f"Fonte: {job.source}\n\n"

        return text

    def _escape_markdown(self, text: str) -> str:
        """Escape Markdown special characters."""
        if not text:
            return ""

        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f"\\{char}")

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
