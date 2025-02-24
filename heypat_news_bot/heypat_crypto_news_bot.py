from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
import asyncio
import websockets
import json
import requests
from datetime import datetime

load_dotenv("conf.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "heypat_crypto_news_bot "  # Replace with your bot's username (without @)

# Telegram API base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def get_post_content(user): # Get the post content (similar to the API call in JS)

    try:
        response = requests.get("https://heypat.ai/getPostContent.php?req=38572snasisgi32529814uj9b3211x1&user="+user)
        response.raise_for_status()  # Raise an exception for 4xx/5xx status codes
        data = response.json()
        return data['jwt'], data['prompt']
    except Exception as e:
        print(f"Error fetching post content: {e}")
        raise

async def connect_websocket_and_send_auth(jwt, prompt):# WebSocket connection to handle the prompt
    uri = "wss://api.dappier.com/app/webchatbotws?chatbot_id=657273749383785b0522c743"

    async with websockets.connect(uri) as ws:
        # Authenticate
        auth_message = {"type": "auth", "token": jwt}
        await ws.send(json.dumps(auth_message))
        await asyncio.sleep(1)

        # Send the prompt
        prompt_message = {"type": "usermessage", "message": prompt}
        await ws.send(json.dumps(prompt_message))

        # Receive the response
        response = await ws.recv()
        response_data = json.loads(response)
        if response_data.get("type") == "aimessage":
            return response_data["message"]
        return "I couldn't process that request."
    """
    Sends a message to a Telegram bot.

    Parameters:
    - bot_token: Your bot's API token from BotFather
    - chat_id: The recipient's chat ID (group or user)
    - message: The message to send
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # Optional: Use "Markdown" or "HTML" for formatting
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

def get_updates(offset=None): # Get updates
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def send_telegram_message(chat_id, text, reply_to_message_id=None): # Send a message
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_to_message_id": reply_to_message_id,
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

async def process_updates(): # Process incoming updates
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            chat_id = message["chat"]["id"]
            reply_to_message_id = message.get("message_id")

            # Check if the bot is mentioned
            if f"@{BOT_USERNAME}" in text:
                # Extract the prompt (everything after @bot_username)
                prompt = text.split(f"@{BOT_USERNAME}", 1)[-1].strip()

                # Handle the prompt via WebSocket
                try:
                    jwt, _ = get_post_content(str(chat_id))  # Assuming JWT is fetched here
                    response_message = await connect_websocket_and_send_auth(jwt, prompt)
                except Exception as e:
                    response_message = f"Error: {e}"

                # Reply to the message in the group
                send_telegram_message(chat_id, response_message, reply_to_message_id)

        await asyncio.sleep(1)


# Run the bot
if __name__ == "__main__":
    asyncio.run(process_updates())
