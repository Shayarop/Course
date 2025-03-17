import os
import re
import cv2
import requests
import yt_dlp
import numpy as np
import time
import ffmpeg
import logging
from pyrogram import Client, filters
from pdf2image import convert_from_path

# Telegram Bot Credentials (from Railway environment variables)
API_ID = 28898876  # Replace with your API ID
API_HASH = "750da282e4b6db0418689021275b62c3"  # Replace with your API hash
BOT_TOKEN = "7722512659:AAGCPSygqqFMbWWo3WRU_30gWr4LHmAhb0k"

bot = Client("txt_to_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Logging Configuration
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to log debugging messages
def debug_log(message):
    logging.debug(f"🔍 {message}")

# Function to measure execution time
def track_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        debug_log(f"⏳ {func.__name__} took {elapsed_time:.2f} seconds.")
        return result
    return wrapper

# Function to download M3U8 video
@track_time
def download_m3u8_video(m3u8_url, output_path):
    debug_log(f"Downloading M3U8 video: {m3u8_url}")
    ydl_opts = {"format": "best", "outtmpl": output_path, "quiet": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m3u8_url])
        debug_log(f"✅ Video downloaded: {output_path}")
        return output_path
    except Exception as e:
        debug_log(f"❌ M3U8 Download Failed: {e}")
        return None

# Function to convert PDF to images
@track_time
def pdf_to_images(pdf_url):
    debug_log(f"Downloading PDF: {pdf_url}")
    response = requests.get(pdf_url)
    if response.status_code != 200:
        debug_log(f"❌ Failed to download PDF: {pdf_url}")
        return []

    pdf_path = "temp.pdf"
    with open(pdf_path, "wb") as f:
        f.write(response.content)

    try:
        images = convert_from_path(pdf_path)
        img_paths = []
        for i, img in enumerate(images):
            img_path = f"pdf_page_{i}.jpg"
            img.save(img_path, "JPEG")
            img_paths.append(img_path)
        os.remove(pdf_path)
        debug_log(f"✅ Converted {len(images)} PDF pages to images.")
        return img_paths
    except Exception as e:
        debug_log(f"❌ PDF to Image Conversion Failed: {e}")
        return []

# Function to process uploaded TXT file and extract video/PDF links
@track_time
def process_text_file(file_path):
    debug_log(f"Processing uploaded TXT file: {file_path}")
    
    if not os.path.exists(file_path):
        debug_log("❌ Uploaded TXT file not found.")
        return [], [], ""

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.readlines()
    
    video_links = []
    pdf_links = []
    captions = "".join(content)  

    for line in content:
        if ".m3u8" in line:
            match = re.search(r"(https?://[^\s]+\.m3u8)", line)
            if match:
                video_links.append(match.group(1))
        elif ".pdf" in line:
            match = re.search(r"(https?://[^\s]+\.pdf)", line)
            if match:
                pdf_links.append(match.group(1))

    debug_log(f"Extracted {len(video_links)} video links and {len(pdf_links)} PDF links.")
    return video_links, pdf_links, captions

@bot.on_message(filters.document & filters.private)
async def handle_uploaded_txt(client, message):
    debug_log("Received uploaded TXT file.")
    
    file_path = await message.download()
    debug_log(f"TXT file saved at {file_path}")

    # Extract filename for caption
    filename = os.path.basename(file_path).replace(".txt", ".mp4")

    video_links, pdf_links, _ = process_text_file(file_path)

    if not video_links and not pdf_links:
        await message.reply_text("❌ No valid video or PDF links found in the uploaded file.")
        return

    video_path = download_m3u8_video(video_links[0], filename) if video_links else None
    image_paths = sum([pdf_to_images(pdf) for pdf in pdf_links], [])

    pdf_video_path = filename if image_paths else None
    final_video_path = pdf_video_path if pdf_video_path else video_path

    if final_video_path:
        await message.reply_video(final_video_path, caption=filename)
        os.remove(final_video_path)

    debug_log(f"✅ Process completed. Video '{filename}' sent to the user.")

bot.run()
