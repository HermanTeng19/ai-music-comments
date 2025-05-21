#!/bin/bash

# 激活项目的虚拟环境
export PATH=$(pwd)/venv/bin:$PATH
echo "已激活AI音乐评论生成器虚拟环境"
echo "使用Python: $(which python)"
echo "使用Pip: $(which pip)"
echo "已安装的关键包:"
pip list | grep -E 'requests|pandas'

# 提示如何运行脚本
echo ""
echo "可以使用以下命令运行脚本:"
echo "python music_review_generator.py" 