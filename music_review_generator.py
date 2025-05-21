#!/usr/bin/env python3
import os
import re
import time
import json
import requests
import pandas as pd
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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

# Constants (defaults that can be overridden)
DEFAULT_MD_FILE_PATH = "top25Music_douban.md"
DEFAULT_OUTPUT_DIR = "musicComments"
# For Nvidia DeepSeek R1 model
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Configure API settings
class DeepSeekAPI:
    def __init__(self, api_key=None, keep_thinking=False, simulation_mode=False):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key and not simulation_mode:
            logger.error("No API key provided. Please set the NVIDIA_API_KEY environment variable.")
            raise ValueError("No API key provided")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # New options
        self.keep_thinking = keep_thinking
        self.simulation_mode = simulation_mode
        
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
        
        if self.simulation_mode:
            logger.info(f"SIMULATION MODE: Would call API for: {music_info['歌曲名']}")
            # Return a simple placeholder review in simulation mode
            return self._generate_simulation_review(music_info)
        
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
        
        # Add thinking option if requested
        if self.keep_thinking:
            payload["parameters"] = {
                "keep_thinking": True
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
                    
                    # 移除思考过程（如果不需要保留）
                    if not self.keep_thinking:
                        # 使用正则表达式移除<think>...</think>标签及其内容
                        import re
                        review_text = re.sub(r'<think>.*?</think>\s*', '', review_text, flags=re.DOTALL)
                        logger.info("思考过程已从结果中移除")
                        
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
    
    def _generate_simulation_review(self, music_info):
        """Generate a simulation review for testing purposes"""
        song_name = music_info['歌曲名'].split('/')[0].strip()
        artist = music_info['表演者']
        genre = music_info['流派']
        rating = music_info['评分']
        
        return f"""# 【遇见经典】{song_name}，{artist}的音乐心灵之旅 #音乐分享 #乐评 #经典回顾

这首由{artist}演绎的《{song_name}》是{genre}音乐中不可忽视的瑰宝，评分高达{rating}分，足见其艺术成就与听众认可度。

作品以其独特的音乐语言和细腻的情感表达，展现了艺术家深厚的音乐素养和独到的创作视角。音乐中时而澎湃激昂，时而柔情似水的情绪转换，无不牵动听众的心弦，让人沉浸在一场听觉与情感的盛宴中。

从历史角度看，这首歌曾在当时的音乐环境中掀起波澜，不仅丰富了{genre}音乐的表现形式，更为后来的音乐创作提供了新的可能性。它所承载的时代背景和文化内涵，使其成为了音乐史上浓墨重彩的一笔。

每次聆听，都能发现新的感动和启发，这正是经典的魅力所在。无论是在悲伤时寻求抚慰，还是在喜悦时寻求共鸣，它总能给予我们恰到好处的情感陪伴。

如果你还没有聆听过这首作品，强烈推荐将其加入你的音乐清单，感受那穿越时空的音符之美。

#音乐治愈 #经典重温 #{genre}之美"""


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


def save_review(music_info, review_text, output_dir):
    """Save the review to a markdown file"""
    try:
        # Use the song name as the filename
        song_name = music_info['歌曲名'].split('/')[0].strip()  # Take just the primary name
        filename = sanitize_filename(song_name) + '.md'
        filepath = os.path.join(output_dir, filename)
        
        # 检查文件是否存在，记录覆盖日志
        if os.path.exists(filepath):
            logger.info(f"覆盖已存在的评论文件: {filepath}")
        
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


class ReviewGeneratorGUI:
    """GUI interface for the music review generator"""
    
    def __init__(self, root):
        self.root = root
        root.title("AI 音乐评论生成器")
        root.geometry("700x500")
        
        # Set up main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="数据文件", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_path = tk.StringVar(value=DEFAULT_MD_FILE_PATH)
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="浏览...", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Output directory
        output_frame = ttk.LabelFrame(main_frame, text="输出目录", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="10")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Keep thinking process option
        self.keep_thinking = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="保留DeepSeek R1的思考过程", 
            variable=self.keep_thinking
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        # Simulation mode option
        self.simulation_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="模拟运行（不实际调用API）", 
            variable=self.simulation_mode
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        # Progress reporting
        self.progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.progress_text = tk.Text(self.progress_frame, height=10, width=80)
        self.progress_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for progress text
        scrollbar = ttk.Scrollbar(self.progress_text, orient="vertical", command=self.progress_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.progress_text.configure(yscrollcommand=scrollbar.set)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            orient="horizontal", 
            length=680, 
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(
            button_frame, 
            text="开始生成", 
            command=self.start_generation
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="退出", 
            command=root.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def browse_file(self):
        """Open file dialog to select markdown file"""
        filename = filedialog.askopenfilename(
            title="选择包含豆瓣音乐Top25数据的Markdown文件",
            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
    
    def browse_output_dir(self):
        """Open directory dialog to select output directory"""
        dirname = filedialog.askdirectory(title="选择评论输出目录")
        if dirname:
            self.output_dir.set(dirname)
    
    def log_message(self, message):
        """Add message to the progress text box"""
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_generation(self):
        """Start the review generation process"""
        md_file = self.file_path.get()
        output_dir = self.output_dir.get()
        keep_thinking = self.keep_thinking.get()
        simulation_mode = self.simulation_mode.get()
        
        if not os.path.exists(md_file):
            messagebox.showerror("错误", f"找不到指定的Markdown文件: {md_file}")
            return
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Clear progress text
        self.progress_text.delete(1.0, tk.END)
        self.log_message(f"开始处理文件: {md_file}")
        self.log_message(f"输出目录: {output_dir}")
        self.log_message(f"保留思考过程: {'是' if keep_thinking else '否'}")
        self.log_message(f"模拟模式: {'是' if simulation_mode else '否'}")
        self.log_message("----------------------------")
        
        # Start processing in a separate thread to avoid blocking the UI
        import threading
        thread = threading.Thread(
            target=self.process_file,
            args=(md_file, output_dir, keep_thinking, simulation_mode)
        )
        thread.daemon = True
        thread.start()
    
    def process_file(self, md_file, output_dir, keep_thinking, simulation_mode):
        """Process the markdown file and generate reviews"""
        try:
            # Initialize API client
            api_client = DeepSeekAPI(
                keep_thinking=keep_thinking,
                simulation_mode=simulation_mode
            )
            
            # Read the markdown file
            with open(md_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter out valid music entries
            music_entries = []
            for line in lines:
                music_info = extract_music_info_from_md_line(line)
                if music_info:
                    music_entries.append(music_info)
            
            if not music_entries:
                self.log_message("错误: 未在文件中找到有效的音乐条目")
                messagebox.showerror("错误", "未在文件中找到有效的音乐条目")
                return
            
            total_entries = len(music_entries)
            self.log_message(f"找到 {total_entries} 个音乐条目")
            
            # Reset progress bar
            self.progress_var.set(0)
            
            # Process each music entry
            for i, music_info in enumerate(music_entries):
                # Update progress
                progress_percent = (i / total_entries) * 100
                self.progress_var.set(progress_percent)
                
                song_name = music_info['歌曲名'].split('/')[0].strip()
                self.log_message(f"处理 [{i+1}/{total_entries}]: {song_name}")
                
                # 不再检查文件是否存在，直接生成评论
                self.log_message(f"为 '{song_name}' 生成评论...")
                review = api_client.generate_review(music_info)
                
                if review:
                    # Save review
                    filepath = save_review(music_info, review, output_dir)
                    if filepath:
                        self.log_message(f"成功保存评论到: {filepath}")
                    else:
                        self.log_message(f"保存评论失败: {song_name}")
                else:
                    self.log_message(f"生成评论失败: {song_name}")
                
                # Add a longer delay between successful operations to avoid triggering rate limits
                if not simulation_mode:
                    wait_time = 10  # seconds
                    self.log_message(f"等待 {wait_time} 秒后处理下一条...")
                    time.sleep(wait_time)
            
            # Set progress to 100% when done
            self.progress_var.set(100)
            self.log_message("----------------------------")
            self.log_message("音乐评论生成完成!")
            messagebox.showinfo("完成", "音乐评论生成完成!")
            
        except Exception as e:
            error_msg = f"处理过程中出错: {str(e)}"
            self.log_message(error_msg)
            logger.error(error_msg, exc_info=True)
            messagebox.showerror("错误", error_msg)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI 音乐评论生成器")
    parser.add_argument("--gui", action="store_true", help="启动图形用户界面")
    parser.add_argument("--file", type=str, default=DEFAULT_MD_FILE_PATH, 
                        help=f"指定Markdown数据文件路径 (默认: {DEFAULT_MD_FILE_PATH})")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"指定评论输出目录 (默认: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--keep-thinking", action="store_true",
                        help="保留DeepSeek R1的思考过程")
    parser.add_argument("--simulation", action="store_true",
                        help="模拟运行（不实际调用API）")
    return parser.parse_args()


def process_file_cli(md_file_path, output_dir, keep_thinking, simulation_mode):
    """Process markdown file in CLI mode"""
    logger.info("Starting music review generation process")
    
    try:
        # Initialize API client
        api_client = DeepSeekAPI(
            keep_thinking=keep_thinking,
            simulation_mode=simulation_mode
        )
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Read the markdown file
        with open(md_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process each line
        for i, line in enumerate(lines):
            music_info = extract_music_info_from_md_line(line)
            if not music_info:
                continue
                
            logger.info(f"Processing entry {music_info['序号']}: {music_info['歌曲名']}")
            
            # 不再检查文件是否存在，直接生成评论
            song_name = music_info['歌曲名'].split('/')[0].strip()
            logger.info(f"Generating review for {song_name}")
                
            # Generate review
            review = api_client.generate_review(music_info)
            if review:
                # Save review
                save_review(music_info, review, output_dir)
                logger.info(f"Completed review for {music_info['歌曲名']}")
            else:
                logger.error(f"Failed to generate review for {music_info['歌曲名']}")
            
            # Add a longer delay between successful operations to avoid triggering rate limits
            if not simulation_mode:
                wait_time = 10  # seconds
                logger.info(f"Waiting {wait_time} seconds before processing next item")
                time.sleep(wait_time)
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
    
    logger.info("Music review generation process complete")


def main():
    """Main function"""
    args = parse_arguments()
    
    # Launch GUI if requested or if no command-line args provided
    if args.gui or len(os.sys.argv) == 1:
        root = tk.Tk()
        app = ReviewGeneratorGUI(root)
        root.mainloop()
    else:
        # Run in CLI mode
        process_file_cli(
            args.file, 
            args.output_dir, 
            args.keep_thinking,
            args.simulation
        )


if __name__ == "__main__":
    main() 