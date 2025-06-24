import asyncio
import json
import os
import sqlite3
import logging
import openai
import sys

from logging import getLogger
from typing import Dict
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaWebPage
from dotenv import load_dotenv
from system_prompt_manager import load_configured_system_prompt

load_dotenv()

# Set up logging level from environment variable
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)

logger = getLogger(__name__)

# Environment variables:
# TELEGRAM_API_ID: Telegram API ID
# TELEGRAM_API_HASH: Telegram API hash
# SOURCE_CHANNELS: comma separated list of channel usernames or IDs
# TARGET_CHANNEL: username or ID of the channel to post translations
# OPENAI_API_KEY: key for OpenAI API
# SESSION_NAME (optional): session name or path for Telethon

MAX_MESSAGE_LENGTH = 4096
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
SOURCE_CHANNELS = [ch.strip() for ch in os.environ['SOURCE_CHANNELS'].split(',') if ch.strip()]
TARGET_CHANNEL = os.environ['TARGET_CHANNEL']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
SESSION_NAME = os.environ.get('SESSION_NAME', 'aggregator')

openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

# Global variable to store the system prompt
SYSTEM_PROMPT = None

def init_db(db_path='processed_messages.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_messages (
                    channel TEXT,
                    message_id INTEGER,
                    PRIMARY KEY (channel, message_id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS editor_decisions (
                    channel TEXT,
                    message_id INTEGER,
                    original_text TEXT,
                    decision_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel, message_id)
                )''')
    conn.commit()
    return conn

def is_processed(conn, channel, message_id):
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_messages WHERE channel=? AND message_id=?', (channel, message_id))
    return c.fetchone() is not None

def mark_processed(conn, channel, message_id):
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO processed_messages (channel, message_id) VALUES (?, ?)', (channel, message_id))
    conn.commit()

def save_editor_decision(conn, channel, message_id, original_text, decision_json, timestamp=None):
    c = conn.cursor()
    if timestamp is None:
        c.execute('''INSERT OR REPLACE INTO editor_decisions (channel, message_id, original_text, decision_json)
                     VALUES (?, ?, ?, ?)''', (channel, message_id, original_text, decision_json))
    else:
        c.execute('''INSERT OR REPLACE INTO editor_decisions (channel, message_id, original_text, decision_json, timestamp)
                     VALUES (?, ?, ?, ?, ?)''', (channel, message_id, original_text, decision_json, timestamp))
    conn.commit()


async def ai_editor_in_chief(text: str) -> Dict[str, str] | None:
    # Use the globally loaded system prompt
    global SYSTEM_PROMPT

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError as e:
        logger.warning(f"Cannot decode JSON response: {e}")
        return None

    return content

async def forward_message_with_media(client, original_message, translated_text, target_channel):
    """Forward a message with its media content and translated text"""
    author_info = get_author_info(original_message)
    formatted_text = f"{translated_text}\n\nAuthor: {author_info}"
    
    # Check if the message has media
    if original_message.media and not isinstance(original_message.media, MessageMediaWebPage):
        try:
            # Forward the media with the translated caption
            await client.send_file(
                target_channel,
                original_message.media,
                caption=formatted_text
            )
        except Exception as e:
            logger.warning(f"Error forwarding media: {e}")
            # Fallback: send text only if media forwarding fails
            await client.send_message(target_channel, formatted_text)
    else:
        if len(formatted_text) > 4096:
            logger.warning(f"Message too long: {formatted_text}, skipping")
        else:
            await client.send_message(target_channel, formatted_text)


async def main():
    # Initialize system prompt at startup
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = load_configured_system_prompt()
    logger.info(f"System prompt successfully loaded and configured:\n{SYSTEM_PROMPT}")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    db_conn = init_db()
    for channel in SOURCE_CHANNELS:
        await fetch_latest_messages(client, channel, db_conn)

    @client.on(events.NewMessage(chats=SOURCE_CHANNELS))
    async def handler(event):
        await process_message(db_conn, client, event.message)

    logger.info('Aggregator started. Listening for new messages...')
    await client.run_until_disconnected()


async def fetch_latest_messages(client, channel, db_conn, limit=10):
    async for message in client.iter_messages(channel, limit=limit):
        if message.message:
            await process_message(db_conn, client, message)

async def process_message(db_conn, client, message):
    channel_id = message.chat.username if message.chat and message.chat.username else str(message.chat_id)
    if db_conn:
        if is_processed(db_conn, channel_id, message.id):
            return

    editor_resonse = await ai_editor_in_chief(message.text)
    if editor_resonse and editor_resonse.get("Decision") == "REPOST":
        await forward_message_with_media(client, message, editor_resonse["Translated News"], TARGET_CHANNEL)
        logger.info(f"Reposting message:\n{editor_resonse['Translated News']}")
    else:
        logger.info(f"Rejecting message:\n{editor_resonse['Translated News']}\nReason:\n{editor_resonse['Reasoning']}")

    if db_conn:
        mark_processed(db_conn, channel_id, message.id)
        save_editor_decision(db_conn, channel_id, message.id, message.text, json.dumps(editor_resonse))


def get_author_info(message):
    # Handle author information properly for Telethon
    author_info = "Unknown"
    if hasattr(message, 'sender') and message.sender:
        if hasattr(message.sender, 'username') and message.sender.username:
            author_info = f"https://t.me/{message.sender.username}"
        elif hasattr(message.sender, 'first_name'):
            author_info = message.sender.first_name
    elif hasattr(message, 'author') and message.author:
        if hasattr(message.author, 'username') and message.author.username:
            author_info = f"https://t.me/{message.author.username}"
        elif hasattr(message.author, 'first_name'):
            author_info = message.author.first_name

    return author_info


if __name__ == '__main__':
    asyncio.run(main())
