# AI Music Review Generator

This project uses the NVIDIA DeepSeek R1 model to generate professional music reviews for the Top 25 songs on Douban Music.

## Project Structure

```
ai-music-comments/
├── musicComments/        # Directory for generated music reviews
├── top25Music_douban.md  # Douban Music Top 25 data
├── music_review_generator.py  # Main script
├── activate_env.sh       # Virtual environment activation script
├── venv/                 # Virtual environment directory
└── README.md             # Project documentation
```

## Features

- Reads Douban Music Top 25 data from the `top25Music_douban.md` file
- Calls the NVIDIA DeepSeek R1 API to generate professional music reviews for each song
- Generated reviews are suitable for social media platforms like Xiaohongshu, with around 300-500 words
- Reviews include analysis of artistic features, performance standards, historical significance, and personal impressions
- Reviews are saved in Markdown format in the `musicComments` directory, with filenames as `[song_name].md`
- By default, existing reviews will be overwritten with newly generated content

## Usage Instructions

### Environment Setup

1. Ensure you have Python 3.6 or higher installed
2. The project uses a virtual environment with the following dependencies:
   - requests: for API requests
   - pandas: for data processing

You can activate the virtual environment using:

```bash
# Linux/macOS
source ./activate_env.sh

# Windows (PowerShell)
# Please add PATH to the project's venv\Scripts directory
```

### API Key Configuration

Before using, you need to configure the NVIDIA API key:

```bash
# Linux/macOS
export NVIDIA_API_KEY="your_API_key"

# Windows
set NVIDIA_API_KEY=your_API_key
```

### Running the Script

After activating the virtual environment, you can run:

```bash
python music_review_generator.py
```

### Command Line Options

The script supports several command line options:

```bash
python music_review_generator.py [--gui] [--file FILE_PATH] [--output-dir DIR_PATH] [--keep-thinking] [--simulation]
```

Options:
- `--gui`: Launch the graphical user interface instead of command line mode
- `--file`: Specify the path to the markdown file containing music data (default: `top25Music_douban.md`)
- `--output-dir`: Specify the directory for saving generated reviews (default: `musicComments`)
- `--keep-thinking`: Preserve the AI's thinking process in the generated reviews
- `--simulation`: Run in simulation mode without making actual API calls (useful for testing)

## API Rate Limiting

While the NVIDIA DeepSeek R1 API doesn't have explicit hard rate limits in the official documentation, to avoid service overload and response delays, the script implements the following strategies:

- Request interval: At least 6 seconds between each request
- Exponential backoff: When rate limit errors are encountered, initial wait of 30 seconds, then doubled for subsequent attempts
- Maximum retries: Failed requests are retried up to 5 times
- After each successful review generation, wait 10 seconds before processing the next item

## Notes

- Generating reviews may take a considerable amount of time, please be patient
- All existing reviews will be overwritten with newly generated content
- All operations are logged in the `music_review_generator.log` file 