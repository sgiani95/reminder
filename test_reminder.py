#!/usr/bin/env python3
"""
Quick standalone test for send_reminders quote rotation logic
Run: python3 test_send_reminders.py
"""

import asyncio
from datetime import datetime, timedelta
import random
import re
import requests
from html import unescape
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_quote")

# ────────────────────────────────────────────────
#  Your constants (copied from the function)
# ────────────────────────────────────────────────
GROUP_CHAT_ID = -1002593119445

LANGUAGE_ROTATION = ["it", "en", "it", "de", "it", "en", "it"]

FALLBACK_IT = "Buon giorno! Oggi nessun appuntamento – ecco un piccolo fatto italiano: La pizza Margherita è stata inventata nel 1889 a Napoli!"
FALLBACK_EN = "Good morning! No appointments today – here's a fun fact: The first pizza Margherita was created in 1889 in Naples!"
FALLBACK_DE = "Guten Morgen! Heute keine Termine – ein kleiner Fakt: Die Pizza Margherita wurde 1889 in Neapel erfunden!"

WIKI_URLS = {
    "it": "https://it.wikiquote.org/wiki/Pagina_principale",
    "en": "https://en.wikiquote.org/wiki/Main_Page",
    "de": "https://de.wikiquote.org/wiki/Hauptseite"
}

HEADERS = {'User-Agent': 'Test-Quote-Script/1.0'}

# ────────────────────────────────────────────────
#  Minimal fake bot & context
# ────────────────────────────────────────────────
class FakeBot:
    async def send_message(self, chat_id, text, **_):
        print("\n" + "═" * 70)
        print(f"[FAKE SEND to {chat_id}] ({datetime.now().strftime('%A')})")
        print(text)
        print("═" * 70 + "\n")

class FakeContext:
    def __init__(self):
        self.bot = FakeBot()

# ────────────────────────────────────────────────
#  The send_reminders function (standalone version)
# ────────────────────────────────────────────────
async def send_reminders_test(events=None):
    if events is None:
        events = []  # simulate no events

    current_time = datetime.now()
    reminder_threshold = current_time + timedelta(hours=24)

    upcoming = []
    for e in events:
        if e.get("type") == "terminated" and e.get("active"):
            dt, _, _ = parse_datetime(e["time"])  # assume you have this function
            if dt and current_time <= dt <= reminder_threshold:
                upcoming.append(e)

    fake_context = FakeContext()

    if upcoming:
        print(f"Found {len(upcoming)} upcoming → would send reminders")
        return

    # No events → rotating quote
    weekday = current_time.isoweekday()          # 1=Mon ... 7=Sun
    lang = LANGUAGE_ROTATION[weekday - 1]

    print(f"\nToday is weekday {weekday} → language = {lang.upper()}")

    quote = None
    lang_name = {"it": "Italian", "en": "English", "de": "German"}[lang]

    try:
        r = requests.get(WIKI_URLS[lang], headers=HEADERS, timeout=10)
        r.raise_for_status()
        html = r.text

        # Tuned patterns for current page structure (July 2025)
        if lang == "it":
            m = re.search(
                r'(?:Citazione del giorno|Citazione della settimana).*?>(“[^”]+?”)\s*([^<]+)',
                html, re.DOTALL | re.I
            )
        elif lang == "en":
            m = re.search(
                r'(?:Quote of the day|Quote of the week).*?>([^~]+?)\s*~([^~]+?)~',
                html, re.DOTALL | re.I
            )
        else:  # de
            m = re.search(
                r'(?:Zitat der Woche|Zitat des Tages).*?>(“[^”]+?”)\s*([^<]+)',
                html, re.DOTALL | re.I
            )

        if m:
            if lang == "en":
                quote_text = m.group(1).strip()
                author = m.group(2).strip()
                quote = f"{quote_text}\n~ {author} ~"
            else:
                quote = m.group(1).strip()
            quote = unescape(quote)
            quote = re.sub(r'<.*?>|\[\[.*?\]\]|{{.*?}}|\[http[^\]]+\]', '', quote)
            quote = re.sub(r'\s+', ' ', quote).strip()
            if len(quote) > 20:
                print(f"→ Extracted {lang_name} quote ({len(quote)} chars)")
            else:
                quote = None
    except Exception as e:
        logger.warning(f"Fetch failed for {lang_name}: {e}")

    if not quote:
        quote = {
            "it": FALLBACK_IT,
            "en": FALLBACK_EN,
            "de": FALLBACK_DE
        }[lang]
        print(f"→ Using fallback for {lang_name}")

    header = {
        "it": "Buongiorno! Oggi nessun appuntamento – ecco la citazione del giorno:\n\n",
        "en": "Good morning! No appointments today – here’s the quote of the day:\n\n",
        "de": "Guten Morgen! Heute keine Termine – hier ist das Zitat der Woche:\n\n"
    }[lang]

    final = header + quote

    print("\n" + "═"*70)
    print(f"FINAL MESSAGE ({lang.upper()}):")
    print(final)
    print("═"*70 + "\n")

    await fake_context.bot.send_message(GROUP_CHAT_ID, final)

# Minimal parse_datetime stub (copy yours or use this)
def parse_datetime(t):
    try:
        if "todo" in t.lower():
            return None, "todo", False
        # Add your real parsing logic here if needed for test 2
        dt = datetime.strptime(t, "%Y-%m-%d %H:%M")
        return dt, t, False
    except:
        return None, None, False

# ────────────────────────────────────────────────
#  Run tests
# ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test 1: No upcoming events (should send quote) ===")
    asyncio.run(send_reminders_test(events=[]))

    print("\n=== Test 2: Has upcoming event (should send reminder) ===")
    fake_event = {
        "type": "terminated",
        "active": True,
        "time": (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
        "message": "Test meeting in 4 hours"
    }
    asyncio.run(send_reminders_test(events=[fake_event]))

    print("\nDone.")