import os
import sys
import json
import shutil
import subprocess
import platform
import venv
import zipfile
import requests
from pathlib import Path

class BotStarter:
    def __init__(self):
        # Fixed GitHub repository configuration
        self.GITHUB_USER = "0sjk0"
        self.GITHUB_REPO = "new-bot"
        self.REPO_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}"
        self.RELEASE_URL = f"{self.REPO_URL}/releases/latest"
        
        # Local paths
        self.VENV_DIR = "scripts/venv"
        self.TEMP_ZIP = "temp_download.zip"
        
        self.required_packages = [
            "interactions.py",
            "python-dotenv",
            "colorama",
            "requests",
            "aiohttp",
            "typing_extensions"
        ]

        # Determine OS and set appropriate commands
        self.os_type = platform.system().lower()
        if self.os_type == "windows":
            self.python_path = os.path.join(self.VENV_DIR, "Scripts", "python.exe")
            self.pip_path = os.path.join(self.VENV_DIR, "Scripts", "pip.exe")
        else:  # Linux/Mac
            self.python_path = os.path.join(self.VENV_DIR, "bin", "python")
            self.pip_path = os.path.join(self.VENV_DIR, "bin", "pip")

    def setup_virtual_environment(self):
        """Create and set up virtual environment if it doesn't exist."""
        print("\nChecking virtual environment...")
        
        # Create scripts directory if it doesn't exist
        os.makedirs("scripts", exist_ok=True)
        
        # Only create venv if it doesn't exist
        if not os.path.exists(self.VENV_DIR):
            print("Creating new virtual environment...")
            try:
                venv.create(self.VENV_DIR, with_pip=True)
                print("✓ Virtual environment created successfully")
                
                # Upgrade pip in new virtual environment
                self._run_venv_command(["-m", "pip", "install", "--upgrade", "pip"])
                print("✓ Pip upgraded in virtual environment")
            except Exception as e:
                print(f"Failed to create virtual environment: {e}")
                sys.exit(1)
        else:
            print("✓ Using existing virtual environment")

    def _run_venv_command(self, cmd_args, capture_output=False):
        """Run a command in the virtual environment."""
        try:
            if capture_output:
                return subprocess.run(
                    [self.python_path] + cmd_args,
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                subprocess.run(
                    [self.python_path] + cmd_args,
                    check=True
                )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")
            return False

    def get_installed_packages(self):
        """Get a dictionary of installed packages and their versions."""
        try:
            result = self._run_venv_command(
                ["-m", "pip", "list", "--format=json"],
                capture_output=True
            )
            if result and result.stdout:
                packages = json.loads(result.stdout)
                return {pkg["name"].lower(): pkg["version"] for pkg in packages}
            return {}
        except Exception:
            return {}

    def ensure_dependencies(self):
        """Install missing packages and update outdated ones in virtual environment."""
        print("\nChecking required packages...")
        
        # Get currently installed packages
        installed_packages = self.get_installed_packages()
        
        # Check each required package
        packages_to_install = []
        for package in self.required_packages:
            package_name = package.lower()
            if package_name not in installed_packages:
                print(f"Missing package: {package}")
                packages_to_install.append(package)
                continue
                
            # Check if package needs update
            try:
                result = self._run_venv_command(
                    ["-m", "pip", "list", "--outdated", "--format=json"],
                    capture_output=True
                )
                if result and result.stdout:
                    outdated = json.loads(result.stdout)
                    for pkg in outdated:
                        if pkg["name"].lower() == package_name:
                            print(f"Package needs update: {package}")
                            packages_to_install.append(package)
                            break
            except Exception:
                # If we can't check for updates, assume package is up to date
                pass
        
        # Install/update necessary packages
        if packages_to_install:
            print("\nInstalling/updating packages...")
            for package in packages_to_install:
                print(f"Installing/updating {package}...")
                success = self._run_venv_command(
                    ["-m", "pip", "install", "--upgrade", package]
                )
                if success:
                    print(f"✓ Successfully installed/updated {package}")
                else:
                    print(f"✗ Failed to install/update {package}")
                    sys.exit(1)
        else:
            print("✓ All required packages are up to date")

    def get_local_version(self):
        """Get the local version from version.txt if it exists."""
        version_file = os.path.join("scripts", "version.txt")
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return f.read().strip()
            except Exception:
                return None
        return None

    def save_local_version(self, version):
        """Save the current version to version.txt."""
        version_file = os.path.join("scripts", "version.txt")
        os.makedirs(os.path.dirname(version_file), exist_ok=True)
        with open(version_file, 'w') as f:
            f.write(version)

    def download_latest_release(self):
        """Download and extract the latest release only if needed."""
        print("\nChecking for updates...")
        try:
            # Get latest release info
            response = requests.get(self.RELEASE_URL)
            response.raise_for_status()
            release_data = response.json()
            
            # Get latest version
            latest_version = release_data.get('tag_name', release_data.get('id', ''))
            
            # Check if we already have this version
            local_version = self.get_local_version()
            
            if local_version == latest_version and os.path.exists("scripts"):
                print("✓ Already running the latest version")
                return True
                
            print(f"New version available: {latest_version}")
            
            # Create temp directory for extraction
            temp_dir = "temp_download"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            try:
                # Get the zipball URL
                zipball_url = release_data['zipball_url']
                
                # Download the zip file
                print("Downloading release files...")
                response = requests.get(zipball_url, stream=True)
                response.raise_for_status()
                
                zip_path = os.path.join(temp_dir, self.TEMP_ZIP)
                
                # Download zip file
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Extract to temp directory first
                print("Extracting files...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Get the extracted directory name (should be the only directory in temp_dir)
                extracted_dir = next(os.walk(temp_dir))[1][0]
                source_dir = os.path.join(temp_dir, extracted_dir)
                source_scripts = os.path.join(source_dir, "scripts")
                
                # Create scripts directory if it doesn't exist
                os.makedirs("scripts", exist_ok=True)
                
                # Function to safely update files
                def safe_update_directory(src, dst):
                    # Create destination if it doesn't exist
                    os.makedirs(dst, exist_ok=True)
                    
                    # Copy each file, preserving the ones we want to keep
                    for item in os.listdir(src):
                        s = os.path.join(src, item)
                        d = os.path.join(dst, item)
                        
                        if item in ['venv', 'config', 'data', 'logs', 'version.txt']:
                            continue  # Skip these directories and files
                            
                        if os.path.isdir(s):
                            safe_update_directory(s, d)
                        else:
                            # Only copy if file doesn't exist or is different
                            if not os.path.exists(d) or not self.files_are_identical(s, d):
                                shutil.copy2(s, d)
                
                # Update files while preserving important directories
                safe_update_directory(source_scripts, "scripts")
                
                # Save the new version
                self.save_local_version(latest_version)
                
                print("✓ Files updated successfully")
                return True
                
            finally:
                # Clean up temp directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading release: {e}")
            return False
        except Exception as e:
            print(f"Error processing release: {e}")
            return False

    def files_are_identical(self, file1, file2):
        """Compare two files to check if they are identical."""
        try:
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False
                
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                # Compare files in chunks to handle large files
                chunk_size = 8192
                while True:
                    chunk1 = f1.read(chunk_size)
                    chunk2 = f2.read(chunk_size)
                    if chunk1 != chunk2:
                        return False
                    if not chunk1:  # EOF
                        break
            return True
        except Exception:
            return False

    def ensure_env_file(self):
        """Ensure .env file exists with bot token."""
        env_file = os.path.join("scripts", "config", ".env")
        
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(env_file), exist_ok=True)
            
            # Check if .env exists and has a valid token
            token = None
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    content = f.read().strip()
                    if content.startswith("BOT_TOKEN="):
                        existing_token = content[9:].strip()
                        if existing_token:  # Only use token if it's not empty
                            token = existing_token
            
            # If no valid token found, ask for it
            if not token:
                print("\nBot token not set. Please enter your bot token:")
                token = input("Token: ").strip()
                
                if not token:
                    print("Error: Token cannot be empty")
                    return False
                
                # Write the new token to file
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(f"BOT_TOKEN={token}")
                print("✓ Bot token saved successfully")
            
            return True
            
        except Exception as e:
            print(f"Error handling .env file: {e}")
            return False

    def start_bot(self):
        """Start the bot within the starter process."""
        main_script = os.path.join("scripts", "main.py")
        if not os.path.exists(main_script):
            print(f"Error: {main_script} not found!")
            return False
            
        print("\nStarting bot...")
        try:
            # Change to scripts directory
            original_dir = os.getcwd()
            os.chdir("scripts")
            
            # Add scripts directory to Python path
            sys.path.insert(0, os.getcwd())
            
            try:
                # First try to run as module
                import main
                
                # Try different ways the bot might be started
                if hasattr(main, 'run'):
                    main.run()
                elif hasattr(main, 'bot') and hasattr(main.bot, 'run'):
                    main.bot.run()
                elif hasattr(main, 'client') and hasattr(main.client, 'run'):
                    main.client.run()
                else:
                    # If no recognized patterns found, execute the file directly
                    print("No standard run method found, executing main.py directly...")
                    with open("main.py") as f:
                        exec(f.read())
                
            except Exception as e:
                print(f"Error running bot: {e}")
                return False
            finally:
                # Restore original directory
                os.chdir(original_dir)
                
            return True
        except Exception as e:
            print(f"Error starting bot: {e}")
            return False

    def run(self):
        """Main execution method."""
        print("=== Whiteout Survival Bot Starter ===")
        
        # Set up virtual environment first
        self.setup_virtual_environment()
        
        # Install dependencies
        self.ensure_dependencies()
        
        # Download and extract the latest release
        if not self.download_latest_release():
            print("Failed to download bot files. Please check your internet connection and try again.")
            sys.exit(1)
        
        # Ensure bot token is configured
        if not self.ensure_env_file():
            print("Failed to configure bot token.")
            sys.exit(1)
        
        # Start the bot
        if not self.start_bot():
            sys.exit(1)

if __name__ == "__main__":
    starter = BotStarter()
    starter.run()
