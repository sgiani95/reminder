# PytstsyToDo: a Telegram Calendar Bot

A Python module for a Telegram bot that manages scheduled messages for group chats, such as "MammamiaPizzeria". The bot allows group members to add terminated events (e.g., "Pizza night!") and recurring to-do tasks (e.g., "Fix bike"), with reminders sent daily at 8 AM. Runs on headless Ubuntu, optimized for mobile interaction.

## Features

- **Terminated Events**: Schedule one-time events with reminders at 8 AM for three days (two days before, one day before, day of).
  - Example: `/todo Pizza night! 2025-07-25 19:00` → Reminders on 2025-07-23, 2025-07-24, 2025-07-25 at 8 AM.
- **To-Do Events**: Add tasks with daily 8 AM reminders until completed.
  - Example: `/todo Fix bike todo` → Daily reminders until `/done Fix bike`.
- **Commands**: Mobile-friendly, sent in group chat (e.g., "MammamiaPizzeria").
  - `/todo <message> <YYYY-MM-DD HH:MM|MM-DD HH:MM|todo>`: Add event.
  - `/done <message>`: Complete to-do, notifies group (e.g., "Fix bike completed by @UserName").
  - `/list`: Show upcoming events.
  - `/help`: Show commands.
- **Storage**: Events stored in a JSON file.
- **Restrictions**: Only group members can add/remove events (enforced by Telegram).
- **Reliability**: Logging to `telegram_message.log`, input validation.

## Requirements

- Python 3.8+
- `python-telegram-bot==13.7`
- Headless Ubuntu (Raspberry Pi optional)
- Telegram bot token (from @BotFather)
- Group chat ID (e.g., for "MammamiaPizzeria")

## Setup

1. **Install Dependencies**:

   ```bash
   pip install python-telegram-bot==13.7
   ```
2. **Create Telegram Bot** (to be completed in Step 1):
   - Message `@BotFather` on Telegram, send `/newbot`.
   - Set name (e.g., "MammamiaCalendarBot") and username (e.g., `@MammamiaCalendarBot`).
   - Save the bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).
3. **Get Group Chat ID** (to be completed in Step 1):
   - Add `@GetIDsBot` to your group (e.g., "MammamiaPizzeria").
   - Send a message (e.g., "Test").
   - Note the chat ID (e.g., `-123456789`).
   - Remove `@GetIDsBot`.
4. **Configure Bot**:
   - Update the bot token and chat ID in the module (to be provided in Step 2).
5. **Run the Bot**:
   - Run the Python script (to be provided in Step 3).

   ```bash
   python3 bot.py
   ```

## Usage

- **Add Terminated Event**:

  ```bash
  /todo Pizza night! 2025-07-25 19:00
  /todo Pizza night! 07-25 19:00  # Uses 2025 or 2026 if past
  ```
- **Add To-Do**:

  ```bash
  /todo Fix bike todo
  ```
- **Complete To-Do**:

  ```bash
  /done Fix bike
  ```
- **List Events**:

  ```bash
  /list
  ```
- **Help**:

  ```bash
  /help
  ```

## Notes

- **Time Format**: Use `YYYY-MM-DD HH:MM` or `MM-DD HH:MM`. For `MM-DD`, the year is 2025 unless the date is past (e.g., in July 2025, `01-25` is 2026-01-25).
- **Errors**: Bot responds with errors (e.g., "Invalid time. Use YYYY-MM-DD HH:MM or MM-DD HH:MM or 'todo'.") or "Message not found." for `/done`.
- **Persistence**: Events saved to a JSON file.
- **Mobile-Friendly**: Designed for group members using Telegram on mobile phones.

## Development Status

- **Step 0**: Objectives finalized.
- **Next Steps**:
  - Step 1: Set up Telegram bot (create bot, get chat ID).
  - Step 2: Send test message to group.
  - Step 3: Implement scheduling and event storage.

## License

GNU Lesser General Public License Version 3.