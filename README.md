# AI 音乐评论生成器

这个项目使用 NVIDIA DeepSeek R1 模型为豆瓣音乐 Top 25 的歌曲生成专业的音乐评论。

## 项目结构

```
ai-music-comments/
├── musicComments/        # 生成的音乐评论存放目录
├── top25Music_douban.md  # 豆瓣音乐 Top 25 数据
├── music_review_generator.py  # 主脚本
├── activate_env.sh       # 虚拟环境激活脚本
├── venv/                 # 虚拟环境目录
└── README.md             # 项目说明文档
```

## 功能介绍

- 读取 `top25Music_douban.md` 文件中的豆瓣音乐 Top 25 数据
- 为每首音乐调用 NVIDIA DeepSeek R1 API 生成专业音乐评论
- 生成的评论适合在小红书等社交平台发表，字数在 300-500 字左右
- 评论内容包括音乐的艺术特点、表演水准、历史意义和个人感受
- 评论文件以 Markdown 格式保存在 `musicComments` 目录下，文件名为 `[歌曲名].md`

## 使用方法

### 环境准备

1. 确保已安装 Python 3.6 或更高版本
2. 项目使用虚拟环境隔离依赖，已安装必要的依赖包:
   - requests: 用于API请求
   - pandas: 用于数据处理

可以使用以下命令激活虚拟环境：

```bash
# Linux/macOS
source ./activate_env.sh

# Windows (PowerShell)
# 请将PATH添加到项目的venv\Scripts目录
```

### API 密钥配置

使用前需要配置 NVIDIA API 密钥:

```bash
# Linux/macOS
export NVIDIA_API_KEY="你的_API_密钥"

# Windows
set NVIDIA_API_KEY=你的_API_密钥
```

### 运行脚本

激活虚拟环境后，可以直接运行：

```bash
python music_review_generator.py
```

## API 速率限制

NVIDIA DeepSeek R1 API 在官方文档中没有明确的硬性速率限制，但为了避免服务过载和响应延迟，脚本采用了以下策略：

- 请求间隔：每次请求之间至少间隔 6 秒
- 指数退避：遇到限速错误时使用指数退避算法，初始等待 30 秒，之后翻倍增长
- 最大重试次数：对于失败的请求最多重试 5 次
- 每个成功生成的评论后等待 10 秒再处理下一条

## 注意事项

- 生成评论可能需要较长时间，请耐心等待
- 脚本支持断点续传，已生成的评论不会重复生成
- 所有操作日志会记录在 `music_review_generator.log` 文件中 