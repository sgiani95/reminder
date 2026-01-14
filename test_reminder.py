import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from handlers import send_reminders, EVENT_MANAGER, config  # Assumes handlers.py is updated

async def run_reminder():
    # Mock context: Async send_message that prints (no real Telegram)
    class MockContext:
        bot = AsyncMock()  # Use AsyncMock for awaitable methods
        bot.send_message = AsyncMock()  # Make it async
        bot.send_message.side_effect = lambda chat_id, text: print(f"[BOT SENDING] {text}")
    
    mock_ctx = MockContext()
    
    # Mock empty upcoming events (no reminders branch)
    with patch.object(EVENT_MANAGER, 'get_upcoming_for_reminders', return_value=[]):
        await send_reminders(mock_ctx)

if __name__ == "__main__":
    asyncio.run(run_reminder())