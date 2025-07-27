import gevent.monkey
gevent.monkey.patch_all() # THIS MUST BE THE VERY FIRST LINE

import logging
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Flask imports for webhook server ---
from flask import Flask, request, jsonify
import asyncio

# --- Configuration ---
# Get your bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") # <<< IMPORTANT: Set this in Render environment variables

# --- Webhook Configuration ---
# Render provides the PORT and your service URL as environment variables.
# You'll set WEBHOOK_URL in Render's environment variables.
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # <<< IMPORTANT: Set this in Render environment variables (e.g., https://your-render-service.onrender.com/telegram)
WEBHOOK_LISTEN_IP = "0.0.0.0" # Listen on all available interfaces
WEBHOOK_PORT = int(os.getenv("PORT", 8080)) # Render provides the PORT env var
WEBHOOK_PATH = "/telegram" # The path Telegram sends updates to

# List of channel IDs that users MUST join.
# Your bot MUST be an administrator in these channels with permission to see members.
# Private channel IDs start with -100. Public channel usernames start with @.
# Example: ['-1001234567890', '@YourPublicChannelUsername']
REQUIRED_CHANNELS = [
    '-1002530713919', # Replace with your first required private channel ID
    '@beeetanime',    # Replace with your second required public channel username
    '@mebeeet1',      # Replace with your third required public channel username
]

# List of Telegram User IDs for bot administrators.
# Only these users can use commands like "/start episode_code".
# Get your User ID from @userinfobot or @GetMyID_bot.
ADMIN_IDS = [
    829342319,    # <<< REPLACE THIS WITH YOUR ACTUAL TELEGRAM USER ID
    7299678250,   # <<< REPLACE THIS WITH YOUR ACTUAL TELEGRAM USER ID
    6841115431,   # <<< REPLACE THIS WITH YOUR ACTUAL TELEGRAM USER ID
    # Add more admin User IDs here if you have other admins
]

# File ID of your welcome/logo image.
# IMPORTANT: To get this:
# 1. Send your desired photo to @RawDataBot or @get_id_bot on Telegram.
# 2. Look for the 'file_id' in the JSON response (usually the longest one in the 'photo' array).
# 3. Copy that exact string and paste it here.
WELCOME_PHOTO_FILE_ID = "AgACAgUAAxkBAAE4d9hohHQo4HHzmW25-Sa5pb2vPPMY-gACEscxG6TcIVROLwmefnSo_AQADAgADeQADNgU" # <<< VERIFY AND REPLACE THIS EXACTLY

# Database of your videos.
# Key: Deep link code (e.g., 'episode1', 'promo').
# Value: A dictionary containing 'channel_id' (where the video is stored)
#        and 'message_id' (the message ID of the video in that channel).
# IMPORTANT: To get 'channel_id' and 'message_id' for your videos:
# 1. Upload your video to a Telegram channel (can be private).
# 2. Forward that video message to @RawDataBot or @get_id_bot.
# 3. Look for 'chat_id' (this is your channel_id, usually starts with -100)
#    and 'message_id' in the JSON output.
# 4. The bot will use copy_message, which requires the original message_id, not the file_id.
VIDEO_DATABASE = {
    "S1_Ep1_480p": {
        "channel_id": "-1002530713919", # Ensure this is your actual channel ID
        "message_id": 4,             # Ensure this is the correct message ID
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 01
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
    "S1_Ep1_720p": {
        "channel_id": "-1002530713919", # Ensure this is your actual channel ID
        "message_id": 5,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 01
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep1_1080p": {
        "channel_id": "-1002530713919", # Ensure this is your actual channel ID
        "message_id": 6,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 01
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep2_480p": {
        "channel_id": "-1002530713919",
        "message_id": 7,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 02
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep2_720p": {
        "channel_id": "-1002530713919",
        "message_id": 8,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 02
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep2_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 9,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 02
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep3_480p": {
        "channel_id": "-1002530713919",
        "message_id": 10,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 03
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep3_720p": {
        "channel_id": "-1002530713919",
        "message_id": 11,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 03
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep3_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 12,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 03
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_E4_480p": {
        "channel_id": "-1002530713919",
        "message_id": 13,
        "caption": """<b>\u2756 SQUID GAME

\u2023 Season: 01 | Ep: 04
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep4_720p": {
        "channel_id": "-1002530713919",
        "message_id": 14,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 04
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep4_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 15,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 04
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep5_480p": {
        "channel_id": "-1002530713919",
        "message_id": 16,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 05
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep5_720p": {
        "channel_id": "-1002530713919",
        "message_id": 17,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 05
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep5_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 18,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 05
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep6_480p": {
        "channel_id": "-1002530713919",
        "message_id": 19,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 06
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep6_720p": {
        "channel_id": "-1002530713919",
        "message_id": 20,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 06
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep6_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 21,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 07
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep7_480p": {
        "channel_id": "-1002530713919",
        "message_id": 22,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 07
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep7_720p": {
        "channel_id": "-1002530713919",
        "message_id": 23,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 07
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep7_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 24,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 07
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep8_480p": {
        "channel_id": "-1002530713919",
        "message_id": 25,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 08
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep8_720p": {
        "channel_id": "-1002530713919",
        "message_id": 26,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 08
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep8_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 27,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 08
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep9_480p": {
        "channel_id": "-1002530713919",
        "message_id": 28,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 09
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 480p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep9_720p": {
        "channel_id": "-1002530713919",
        "message_id": 29,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 09
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 720p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
     "S1_Ep9_1080p": {
        "channel_id": "-1002530713919",
        "message_id": 30,
        "caption": """<b>\u2756 SQUID GAME
\u2023 Season: 01 | Ep: 09
\u2023 Audio track: Hind , English| Official
\u2023 Quality: 1080p</b>
\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022
<blockquote>\u25a3 POWERED BY: @beeetanime
\u25a3 MAIN Channel: @Beat_Hindi_Dubbed
\ufeff\u261b\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2022</blockquote>
<blockquote>If video is not in Hindi / English can change from VLC media Player</blockquote>""",
    },
    # Add more episodes/videos here following the same structure
}

VIDEO_DELETE_DELAY_SECONDS = 10 * 60 # 10 minutes
VIDEO_REQUEST_COOLDOWN_SECONDS = 30 # Users must wait 30 seconds between video requests

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING) # Suppress verbose httpx logs
logger = logging.getLogger(__name__)

# Create the Flask app instance
app = Flask(__name__)

# Global variable for the PTB Application instance, initialized once per worker
application = None

# --- Helper Functions ---

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    # You might want to send a more user-friendly message here,
    # but for now, just logging is fine.
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Oops! Something went wrong. Please try again later."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Checks if the user is a member of all required channels.
    If not, sends a message prompting them to join with inline buttons.
    Returns True if user is a member of all, False otherwise.
    """
    not_joined_channels_info = []
    all_joined = True

    for channel_id in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if chat_member.status not in ["member", "creator", "administrator"]:
                all_joined = False
                # Try to get channel info for button text and URL
                try:
                    chat = await context.bot.get_chat(chat_id=channel_id)
                    channel_name = chat.title
                    invite_link = chat.invite_link if chat.invite_link else (f"https://t.me/{chat.username}" if chat.username else None)
                    if invite_link:
                        not_joined_channels_info.append({"name": channel_name, "link": invite_link})
                    else:
                        logger.warning(f"Could not get invite link for channel {channel_id}. Displaying generic button.")
                        not_joined_channels_info.append({"name": f"Join {channel_name}", "link": "https://t.me/"}) # Fallback
                except Exception as e:
                    logger.warning(f"Could not get chat info for {channel_id}: {e}. Displaying raw ID or generic link.")
                    not_joined_channels_info.append({"name": f"Join Channel {channel_id}", "link": "https://t.me/"})

        except Exception as e:
            logger.error(f"Error checking membership for channel {channel_id} (Is bot admin?): {e}")
            all_joined = False
            # Fallback for when bot can't even get chat member info (e.g., not admin in channel)
            not_joined_channels_info.append({"name": f"Join Channel {channel_id}", "link": "https://t.me/"})


    if all_joined:
        return True # User is a member of all required channels
    else:
        # Build inline keyboard buttons for channels
        keyboard_buttons = []
        for channel_info in not_joined_channels_info:
            keyboard_buttons.append([InlineKeyboardButton(channel_info["name"], url=channel_info["link"])])

        # Add the "I have joined" button at the end
        keyboard_buttons.append([InlineKeyboardButton("✅ I have joined", callback_data="check_join_again")])

        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=WELCOME_PHOTO_FILE_ID,
            caption=(
                f"👋 Hey there, <b>{update.effective_user.first_name}</b>! Welcome aboard! 🎉\n\n"
                "To dive into our awesome content, there's just one quick step:\n"
                "Please join the <b>exclusive channels below</b> by tapping the buttons. 👇"
            ),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        
        return False

def is_admin(user_id: int) -> bool:
    """
    Checks if the given user_id is in the list of ADMIN_IDS.
    """
    return user_id in ADMIN_IDS

async def send_resend_button_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job function to send the 'Resend' button message after video deletion.
    """
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    video_code = job_data["video_code"]

    keyboard = [[InlineKeyboardButton("🔄 Get Video Again", callback_data=f"resend_{video_code}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text="Your video has been deleted. By clicking the button below, you can get your video again.",
        reply_markup=reply_markup
    )
    logger.info(f"Resend button message sent for video code {video_code} to chat {chat_id}.")


async def send_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE, video_info: dict):
    """
    Sends a video file from a specified channel and schedules its deletion.
    Also schedules a follow-up message with a resend button.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    source_channel_id = video_info["channel_id"]
    source_message_id = video_info["message_id"]
    caption = video_info.get("caption", "")
    video_code = video_info.get('code') # Get video code for resend button

    # --- Cooldown Check ---
    # Access user_data directly from context, which is associated with the current update's Application
    last_request_time = context.user_data.get('last_video_request_time')
    current_time = time.time()

    if last_request_time and (current_time - last_request_time < VIDEO_REQUEST_COOLDOWN_SECONDS):
        remaining_time = int(VIDEO_REQUEST_COOLDOWN_SECONDS - (current_time - last_request_time))
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Please wait {remaining_time} seconds before requesting another video to prevent spam."
        )
        logger.info(f"User {user_id} hit cooldown for video {video_code}. Remaining: {remaining_time}s")
        return # Stop execution if on cooldown
    
    # Update last request time AFTER cooldown check passes
    context.user_data['last_video_request_time'] = current_time

    try:
        # Use copy_message to send the video from your channel
        sent_video_message = await context.bot.copy_message( # Renamed variable for clarity
            chat_id=chat_id,
            from_chat_id=source_channel_id,
            message_id=source_message_id,
            caption=caption,
            parse_mode="HTML"
        )
        logger.info(f"Video '{video_code}' (message_id: {source_message_id}) sent to {chat_id}")

        # Send initial confirmation message
        sent_confirmation_message = await context.bot.send_message( # Capture this message
            chat_id=chat_id,
            text=f"Your video has been sent! It will be auto-deleted in {int(VIDEO_DELETE_DELAY_SECONDS / 60)} minutes."
        )
        logger.info(f"Confirmation message {sent_confirmation_message.message_id} sent to {chat_id}.")


        # Schedule video deletion
        # Job queue is now accessed from the current context.application
        context.application.job_queue.run_once(
            delete_video_job,
            VIDEO_DELETE_DELAY_SECONDS,
            data={"chat_id": chat_id, "message_id": sent_video_message.message_id}, # Use sent_video_message
            name=f"delete_video_{sent_video_message.message_id}"
        )
        logger.info(f"Deletion scheduled for video message {sent_video_message.message_id} in {chat_id} after {VIDEO_DELETE_DELAY_SECONDS} seconds.")

        # Schedule confirmation message deletion
        context.application.job_queue.run_once(
            delete_video_job, # Re-use the same deletion job function
            VIDEO_DELETE_DELAY_SECONDS,
            data={"chat_id": chat_id, "message_id": sent_confirmation_message.message_id}, # Use sent_confirmation_message
            name=f"delete_confirmation_message_{sent_confirmation_message.message_id}"
        )
        logger.info(f"Deletion scheduled for confirmation message {sent_confirmation_message.message_id} in {chat_id} after {VIDEO_DELETE_DELAY_SECONDS} seconds.")


        # Schedule sending the resend button message *after* the deletion delay
        context.application.job_queue.run_once(
            send_resend_button_job,
            VIDEO_DELETE_DELAY_SECONDS, # Same delay as deletion
            data={"chat_id": chat_id, "video_code": video_code},
            name=f"resend_button_{video_code}_{chat_id}"
        )
        logger.info(f"Resend button message scheduled for video code {video_code} to chat {chat_id} after {VIDEO_DELETE_DELAY_SECONDS} seconds.")

    except Exception as e:
        logger.exception(f"Error in send_video_file for video code {video_info.get('code', 'N/A')}, channel {source_channel_id}, message {source_message_id}:")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, I couldn't send the video right now. Please try again later."
        )

async def delete_video_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job function to delete a video message.
    """
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Message {message_id} in chat {chat_id} deleted successfully.")
    except Exception as e:
        logger.error(f"Error deleting message {message_id} in chat {chat_id}: {e}")
        # Message might already be deleted by user, or bot lost permissions.
        # Often just logging is enough for auto-delete.

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command, welcomes the user, checks membership,
    and handles deep linking with admin restrictions.
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check force join membership first
    if not await check_membership(update, context, user_id):
        return # Stop processing if user hasn't joined required channels

    # Determine if the user is an admin
    user_is_admin = is_admin(user_id)

    # Handle deep linking (when user types /start with an argument, e.g., /start squidgame_ep1)
    if context.args:
        video_code = context.args[0]
        if user_is_admin:
            # ADMIN: Allow using /start with a code
            if video_code in VIDEO_DATABASE:
                video_info = VIDEO_DATABASE[video_code]
                video_info['code'] = video_code # Add code for resend button
                await send_video_file(update, context, video_info)
            else:
                # Admin typed an unrecognized code
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Admin, I don't recognize the video code '<code>{video_code}</code>'.\n\n"
                         "Please check your video database for correct codes.",
                    parse_mode="HTML"
                )
                
        else:
            # NON-ADMIN: Deny /start code command
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🚫 You don't have permission to use specific video codes with the /start command.\n\n"
                     "Please use the direct links provided by the admin or through our official channels.",
                parse_mode="HTML"
            )
    else: # User just sent /start (no arguments)
        # Send the general welcome message, customized by admin status
        if user_is_admin:
            welcome_caption = (
                f"🥳 Fantastic, <b>{user_name}</b>! You're all set! ✨\n\n"
                "Ready to explore? As an admin, you can get your exclusive content by typing specific codes.\n\n"
                "For example, try sending: <code>/start S1_Ep1_480p</code>\n\n"
                "_Stay tuned for more updates and exclusive content!_"
            )
        else:
            welcome_caption = (
                f"🥳 Fantastic, <b>{user_name}</b>! You're all set! ✨\n\n"
                "Welcome to our exclusive content! To access videos, please use the direct links "
                "provided by the admin or found in our official channels.\n\n"
                "_Enjoy the show!_"
            )
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=WELCOME_PHOTO_FILE_ID,
            caption=welcome_caption,
            parse_mode="HTML"
        )

async def check_join_again(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for the "I have joined" button.
    Re-checks membership and then proceeds with the original command if successful.
    """
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    user_id = query.from_user.id

    if await check_membership(update, context, user_id):
        # User has now joined all channels
        await query.edit_message_text(
            text="🎉 Great! Checking your access now..."
        )
        # Re-run start to process potential deep link or show main welcome.
        # This is a simplified approach; in a complex bot, you might store
        # the original command/context to resume precisely.
        await start(update, context) 
    else:
        # Still not joined all
        await query.edit_message_text(
            text="It seems you haven't joined all channels yet. Please make sure you join all of them and try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ I have joined", callback_data="check_join_again")]])
        )

async def resend_video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for the "Resend" button.
    Re-checks membership and resends the video if allowed.
    """
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    user_id = query.from_user.id
    # Extract the video code from the callback data (e.g., "resend_S1_Ep1_480p")
    video_code = query.data.split('_', 1)[1]

    # Check force join membership first
    if not await check_membership(update, context, user_id):
        return # Stop processing if user hasn't joined required channels

    # User has joined all required channels, proceed to resend
    if video_code in VIDEO_DATABASE:
        video_info = VIDEO_DATABASE[video_code]
        video_info['code'] = video_code # Ensure code is available for future resend buttons
        await send_video_file(update, context, video_info)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, I couldn't find that video to resend. The code might be invalid."
        )

# --- Initial Setup for PTB Application (runs once per Gunicorn worker) ---
try:
    logger.info("PTB Application building and initializing (once per worker process)...")
    # Build the application instance
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers to the application instance
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_join_again, pattern="^check_join_again$"))
    application.add_handler(CallbackQueryHandler(resend_video_callback, pattern="^resend_"))
    application.add_error_handler(error_handler) # Add the error handler

    # Initialize the application. This needs an event loop, which gevent provides.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(application.initialize())
    logger.info(f"PTB Application initialized. _initialized: {application._initialized}")

    # Set webhook here once per worker.
    # In a production Render setup, this is often handled by a separate build command
    # or manual setup to ensure it's idempotent and not called excessively.
    if WEBHOOK_URL:
        target_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        try:
            current_webhook_info = loop.run_until_complete(application.bot.get_webhook_info())
            if current_webhook_info.url != target_webhook_url:
                logger.info(f"Setting webhook to: {target_webhook_url}")
                loop.run_until_complete(application.bot.set_webhook(
                    url=target_webhook_url,
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True # Good for fresh deployments
                ))
                logger.info("Webhook set command executed successfully during startup.")
            else:
                logger.info(f"Webhook already correctly set to: {target_webhook_url}")
        except Exception as e:
            logger.error(f"Error checking or setting webhook during worker startup: {e}", exc_info=True)
    else:
        logger.warning("WEBHOOK_URL environment variable not set. Bot will not function correctly in webhook mode.")

except Exception as e:
    logger.critical(f"FATAL ERROR during PTB Application global initialization: {e}", exc_info=True)
    # Re-raise to prevent worker from starting if initialization fails critically
    raise

@app.route(WEBHOOK_PATH, methods=['POST'])
async def telegram_webhook():
    """Handle incoming Telegram updates."""
    # The 'application' instance is already initialized globally for this worker.
    # We just need to process the update.
    if not application._initialized:
        # This should ideally not happen if startup was successful, but as a last resort:
        logger.error("Application found uninitialized in webhook handler. This indicates a serious startup issue.")
        return jsonify({"status": "error", "message": "Bot not ready (Application uninitialized)"}), 503

    try:
        # Get the update from the request
        update = Update.de_json(request.get_json(force=True), application.bot)
        
        # Process the update using the globally initialized application instance.
        # asyncio.create_task is used here to run the update processing asynchronously
        # without blocking the webhook response, relying on gevent's patching.
        asyncio.create_task(application.process_update(update))
        
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Error receiving or processing webhook update: {e}", exc_info=True)
        # Return 200 OK to Telegram even on internal errors to prevent repeated deliveries
        return jsonify({"status": "error", "message": "Internal server error"}), 200

@app.route('/')
def index():
    """Simple root route for health checks or basic access."""
    return "Telegram Bot Webhook Listener is running!"

# This block is primarily for local development/testing.
# On Render, Gunicorn will directly use the 'app' variable defined above.
if __name__ == "__main__":
    if WEBHOOK_URL:
        logger.info("Running Flask app locally for webhook testing.")
        # When running locally with app.run(), the module-level initialization has already occurred.
        app.run(host=WEBHOOK_LISTEN_IP, port=WEBHOOK_PORT, debug=True, use_reloader=False)
    else:
        logger.info("WEBHOOK_URL not set. Running bot in polling mode (for local development/testing).")
        # In polling mode, the application instance needs to be explicitly run.
        # The 'application' variable is already set up from the module-level initialization.
        application.run_polling(allowed_updates=Update.ALL_TYPES)
