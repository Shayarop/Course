import os
import re
import cv2
import requests
import yt_dlp
import numpy as np
import time
import ffmpeg
from pyrogram import Client, filters
from pdf2image import convert_from_path

API_ID = 28898876  # Replace with your API ID
API_HASH = "750da282e4b6db0418689021275b62c3"  # Replace with your API hash
BOT_TOKEN = "7722512659:AAGCPSygqqFMbWWo3WRU_30gWr4LHmAhb0k"  # Replace with your bot token

bot = Client("txt_to_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# File path (uploaded text file)
TEXT_FILE_PATH = "/mnt/data/RPSC 1st Grade Geography हिमालय Batch.txt"

# Debug log function
def debug_log(message):
    print(f"🔍 DEBUG: {message}")

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
def download_m3u8_video(m3u8_url, output_path="merged_video.mp4"):
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

# Function to add text overlay to an image
def add_text_overlay(image_path, text, output_path):
    img = cv2.imread(image_path)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, (50, 100), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(output_path, img)

# Function to create a video from images using OpenCV
@track_time
def create_video_from_images(image_paths, captions, output_path="pdf_video.mp4"):
    if not image_paths:
        debug_log("❌ No images found to create video.")
        return None

    debug_log(f"Creating video from {len(image_paths)} images.")

    frame = cv2.imread(image_paths[0])
    if frame is None:
        debug_log("❌ Error loading first image.")
        return None

    height, width, _ = frame.shape
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(output_path, fourcc, 5, (width, height))  # 5 FPS for smooth transition

    for idx, img_path in enumerate(image_paths):
        captioned_img_path = f"captioned_{idx}.jpg"
        add_text_overlay(img_path, captions[idx] if idx < len(captions) else "No Caption", captioned_img_path)
        img = cv2.imread(captioned_img_path)
        video.write(img)

    video.release()
    debug_log(f"✅ Video saved: {output_path}")
    return output_path

# Function to process text file and extract captions
@track_time
def process_text_file(file_path):
    debug_log("Processing text file...")
    if not os.path.exists(file_path):
        debug_log(f"❌ Text file not found: {file_path}")
        return [], [], []

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.readlines()

    video_links = []
    pdf_links = []
    captions = []

    for line in content:
        match = re.match(r"\((.*?)\) (.*?) \((.*?)\):(.+)", line.strip())
        if match:
            category, title, tag, url = match.groups()
            captions.append(f"{category} - {title}")
            if url.endswith(".m3u8"):
                video_links.append(url)
            elif url.endswith(".pdf"):
                pdf_links.append(url)

    debug_log(f"Extracted {len(video_links)} video links, {len(pdf_links)} PDF links, and {len(captions)} captions.")
    return video_links, pdf_links, captions

@bot.on_message(filters.command("convert"))
async def handle_txt_file(client, message):
    start_time = time.time()
    debug_log("Received /convert command.")

    if not os.path.exists(TEXT_FILE_PATH):
        await message.reply_text("❌ No uploaded file found in /mnt/data/. Please upload your file first.")
        return

    video_links, pdf_links, captions = process_text_file(TEXT_FILE_PATH)

    video_path = download_m3u8_video(video_links[0]) if video_links else None
    image_paths = sum([pdf_to_images(pdf) for pdf in pdf_links], [])

    pdf_video_path = create_video_from_images(image_paths, captions) if image_paths else None
    final_video_path = pdf_video_path if pdf_video_path else video_path

    if final_video_path:
        with open(TEXT_FILE_PATH, "r", encoding="utf-8") as file:
            full_caption = file.read()

        await message.reply_video(final_video_path, caption=full_caption)
        os.remove(final_video_path)

    elapsed_time = time.time() - start_time
    debug_log(f"🎬 Total conversion time: {elapsed_time:.2f} seconds.")

bot.run()
