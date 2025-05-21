# AI Music Review Generator / AI 音乐评论生成器

This project uses the NVIDIA DeepSeek R1 model to generate professional music reviews for the Top 25 songs on Douban Music.

这个项目使用 NVIDIA DeepSeek R1 模型为豆瓣音乐 Top 25 的歌曲生成专业的音乐评论。

## Language Options / 语言选项

- [English Documentation](README_EN.md)
- [中文文档](README_ZH.md)

## Quick Start / 快速开始

### English

1. Activate the virtual environment:
   ```bash
   source ./activate_env.sh
   ```
2. Set API key:
   ```bash
   export NVIDIA_API_KEY="your_API_key"
   ```
3. Run the script:
   ```bash
   python music_review_generator.py
   ```

### 中文

1. 激活虚拟环境:
   ```bash
   source ./activate_env.sh
   ```
2. 设置API密钥:
   ```bash
   export NVIDIA_API_KEY="你的_API_密钥"
   ```
3. 运行脚本:
   ```bash
   python music_review_generator.py
   ```

## Command Line Options / 命令行选项

```bash
python music_review_generator.py [--gui] [--file FILE_PATH] [--output-dir DIR_PATH] [--keep-thinking] [--simulation]
``` 