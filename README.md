# Whiteout Survival Bot - Starter System

This is the starter system for the Whiteout Survival Discord Bot. It handles automatic updates and bot initialization.

## Features

- Automatic dependency installation
- Version checking and file updates from GitHub repository
- Automatic bot restart after updates
- Safe file management with SHA verification
- Modular design with separate scripts directory

## File Structure

```
├── starter.py          # Main starter script
├── version.json        # Stores version information
└── scripts/           # Contains bot scripts
    └── main.py        # Main bot script
```

## How It Works

1. **Dependency Check**: The starter automatically checks and installs required Python packages.
2. **Update Check**: Compares local files with the latest version on GitHub.
3. **File Management**: Downloads and updates necessary files while maintaining version control.
4. **Bot Initialization**: Starts the main bot script after ensuring everything is up to date.

## Usage

1. Download `starter.py`
2. Run the script:
```bash
python starter.py
```

The starter will handle everything else automatically, including:
- Checking for updates
- Installing/updating required files
- Starting the bot

## Configuration

The starter uses these default settings:
- Repository URL: Set in the `REPO_URL` variable
- Version file: `version.json`
- Scripts directory: `scripts/`

## Error Handling

The starter includes comprehensive error handling for:
- Network issues
- File access problems
- Missing dependencies
- Invalid updates

## Requirements

- Python 3.8 or higher
- Internet connection for updates
- GitHub repository access
