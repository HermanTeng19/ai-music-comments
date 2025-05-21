#!/usr/bin/env python3
import os
import re
import time
import json
import requests
import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("music_review_generator.log")
    ]
)
logger = logging.getLogger(__name__)

# Constants
MD_FILE_PATH = "top25Music_douban.md"
OUTPUT_DIR = "musicComments"
# For Nvidia DeepSeek R1 model
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure API settings
class DeepSeekAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key:
            logger.error("No API key provided. Please set the NVIDIA_API_KEY environment variable.")
            raise ValueError("No API key provided")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting parameters
        # Note: DeepSeek API technically doesn't have a hard limit
        # But we'll implement conservative waiting periods anyway to avoid issues
        self.min_request_interval = 6  # seconds between requests (conservative)
        self.last_request_time = 0
        
        # Exponential backoff parameters for handling rate limits
        self.max_retries = 5
        self.base_wait_time = 30  # 30 seconds base wait time
        
    def generate_review(self, music_info):
        """Generate a music review using DeepSeek R1 model"""
        
        # Rate limiting: sleep if necessary to maintain rate limit
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Format a prompt for DeepSeek R1
        prompt = f"""请你为以下音乐作品写一篇300-500字的乐评，适合在小红书上发表。

音乐信息:
歌曲名: {music_info['歌曲名']}
表演者: {music_info['表演者']}
发行时间: {music_info['发行时间']}
流派: {music_info['流派']}
专辑类型: {music_info['专辑类型']}
介质: {music_info['介质']}
评分: {music_info['评分']}

要求:
1. 乐评要有感染力，文笔优美，情感真挚
2. 分析一下这首歌的艺术特点、表演水准和音乐语言
3. 提及这首歌的文化背景和历史意义
4. 总结这首歌的经典之处和个人感受
5. 字数保持在300-500字之间
6. 加入适合小红书风格的标题和2-3个话题标签"""
        
        # Prepare API request payload
        payload = {
            "model": "deepseek-ai/deepseek-r1",
            "temperature": 0.6,  # DeepSeek R1 recommends 0.5-0.7 for best results
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        for retry_count in range(self.max_retries):
            try:
                # Record request time for rate limiting
                self.last_request_time = time.time()
                
                # Make API request
                logger.info(f"Sending request to DeepSeek API for: {music_info['歌曲名']}")
                response = requests.post(
                    API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=120  # 2 minute timeout (DeepSeek may take time to respond)
                )
                
                # Handle different response statuses
                if response.status_code == 200:
                    result = response.json()
                    # Extract review text from response
                    review_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if not review_text:
                        logger.error(f"Empty response received for {music_info['歌曲名']}")
                        return None
                        
                    return review_text
                
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', self.base_wait_time * (2 ** retry_count)))
                    logger.warning(f"Rate limit exceeded. Attempt {retry_count+1}/{self.max_retries}. "
                                  f"Waiting for {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                else:
                    # Other error
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    # If it's server error (5xx), retry with exponential backoff
                    if 500 <= response.status_code < 600:
                        wait_time = self.base_wait_time * (2 ** retry_count)
                        logger.info(f"Server error, retrying in {wait_time} seconds. "
                                   f"Attempt {retry_count+1}/{self.max_retries}")
                        time.sleep(wait_time)
                        continue
                    return None
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception: {str(e)}")
                wait_time = self.base_wait_time * (2 ** retry_count)
                logger.info(f"Network error, retrying in {wait_time} seconds. "
                           f"Attempt {retry_count+1}/{self.max_retries}")
                time.sleep(wait_time)
                continue
            
            except Exception as e:
                logger.error(f"Error generating review: {str(e)}")
                return None
        
        logger.error(f"Failed to generate review for {music_info['歌曲名']} after {self.max_retries} retries")
        return None
            

def extract_music_info_from_md_line(line):
    """Extract music information from a markdown table line"""
    if not line.strip() or line.startswith('| ---') or line.startswith('# '):
        return None
        
    parts = line.split('|')
    if len(parts) < 9:  # Header + 8 columns
        return None
        
    try:
        # Clean up the parts and extract the information
        parts = [p.strip() for p in parts]
        
        # Extract data from the markdown table row
        music_info = {
            '序号': parts[1],
            '歌曲名': parts[2],
            '表演者': parts[3],
            '发行时间': parts[4],
            '流派': parts[5],
            '专辑类型': parts[6],
            '介质': parts[7],
            '评分': parts[8]
        }
        return music_info
    except Exception as e:
        logger.error(f"Error parsing markdown line: {str(e)}")
        return None


def sanitize_filename(name):
    """Convert a string into a safe filename"""
    # Remove characters that are not allowed in filenames
    safe_name = re.sub(r'[^\w\s.-]', '_', name)
    # Replace spaces with underscores
    safe_name = re.sub(r'\s+', '_', safe_name)
    # Remove leading/trailing periods, spaces, and underscores
    safe_name = safe_name.strip('._')
    # Ensure we have a valid filename
    if not safe_name:
        safe_name = "untitled"
    return safe_name


def save_review(music_info, review_text):
    """Save the review to a markdown file"""
    try:
        # Use the song name as the filename
        song_name = music_info['歌曲名'].split('/')[0].strip()  # Take just the primary name
        filename = sanitize_filename(song_name) + '.md'
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Create the markdown content
        markdown_content = f"""# {music_info['歌曲名']} - 乐评

- 表演者: {music_info['表演者']}
- 发行时间: {music_info['发行时间']}
- 流派: {music_info['流派']}
- 专辑类型: {music_info['专辑类型']}
- 介质: {music_info['介质']}
- 评分: {music_info['评分']}

{review_text}
"""
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        logger.info(f"Saved review to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving review: {str(e)}")
        return None


def main():
    """Main function to process the markdown file and generate reviews"""
    logger.info("Starting music review generation process")
    
    try:
        # Initialize API client
        api_client = DeepSeekAPI()
        
        # Read the markdown file
        with open(MD_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process each line
        for i, line in enumerate(lines):
            music_info = extract_music_info_from_md_line(line)
            if not music_info:
                continue
                
            logger.info(f"Processing entry {music_info['序号']}: {music_info['歌曲名']}")
            
            # Check if review already exists
            song_name = music_info['歌曲名'].split('/')[0].strip()
            filename = sanitize_filename(song_name) + '.md'
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            if os.path.exists(filepath):
                logger.info(f"Review already exists for {song_name}, skipping")
                continue
                
            # Generate review
            review = api_client.generate_review(music_info)
            if review:
                # Save review
                save_review(music_info, review)
                logger.info(f"Completed review for {music_info['歌曲名']}")
            else:
                logger.error(f"Failed to generate review for {music_info['歌曲名']}")
            
            # Add a longer delay between successful operations to avoid triggering rate limits
            wait_time = 10  # seconds
            logger.info(f"Waiting {wait_time} seconds before processing next item")
            time.sleep(wait_time)
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
    
    logger.info("Music review generation process complete")


if __name__ == "__main__":
    main() 