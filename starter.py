import os
import sys
import json
import shutil
import subprocess
import platform
import venv
from urllib.parse import urljoin
from pathlib import Path

class BotStarter:
    def __init__(self):
        # GitHub repository configuration
        self.GITHUB_USER = "your-username"  # Change this to your GitHub username
        self.GITHUB_REPO = "your-repo"      # Change this to your repository name
        self.GITHUB_BRANCH = "main"         # Change this if using a different default branch
        
        # Construct GitHub URLs
        self.REPO_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/contents"
        self.RELEASE_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/releases/latest"
        
        # Local configuration
        self.VERSION_FILE = "version.json"
        self.SCRIPTS_DIR = "scripts"
        self.VENV_DIR = "venv"
        self.CONFIG_FILE = "bot_config.json"
        
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

        # Load or create configuration
        self.load_config()

    def load_config(self):
        """Load or create configuration file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.GITHUB_USER = config.get('github_user', self.GITHUB_USER)
                self.GITHUB_REPO = config.get('github_repo', self.GITHUB_REPO)
                self.GITHUB_BRANCH = config.get('github_branch', self.GITHUB_BRANCH)
                # Update URLs after loading config
                self.REPO_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/contents"
                self.RELEASE_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/releases/latest"
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self.create_initial_config()

    def create_initial_config(self):
        """Create initial configuration file."""
        print("\nFirst-time setup: GitHub repository configuration")
        print("Please enter your GitHub repository information:")
        
        self.GITHUB_USER = input("GitHub username: ").strip()
        self.GITHUB_REPO = input("Repository name: ").strip()
        self.GITHUB_BRANCH = input("Branch name (press Enter for 'main'): ").strip() or "main"
        
        config = {
            'github_user': self.GITHUB_USER,
            'github_repo': self.GITHUB_REPO,
            'github_branch': self.GITHUB_BRANCH
        }
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print("✓ Configuration saved successfully")
            
            # Update URLs after saving config
            self.REPO_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/contents"
            self.RELEASE_URL = f"https://api.github.com/repos/{self.GITHUB_USER}/{self.GITHUB_REPO}/releases/latest"
        except Exception as e:
            print(f"Error saving config: {e}")
            sys.exit(1)

    def verify_repository_access(self):
        """Verify access to the GitHub repository."""
        try:
            cmd_result = self._run_venv_command(
                ["-c", f"import requests; response = requests.get('{self.REPO_URL}'); print(response.status_code)"],
                capture_output=True
            )
            
            if cmd_result and cmd_result.returncode == 0:
                status_code = int(cmd_result.stdout.strip())
                if status_code == 200:
                    print("✓ GitHub repository access verified")
                    return True
                elif status_code == 404:
                    print("✗ Repository not found. Please check your GitHub username and repository name.")
                else:
                    print(f"✗ GitHub API returned status code: {status_code}")
            return False
        except Exception as e:
            print(f"Error verifying repository access: {e}")
            return False

    def setup_virtual_environment(self):
        """Create and set up virtual environment."""
        print("\nSetting up virtual environment...")
        
        # Remove existing venv if it exists
        if os.path.exists(self.VENV_DIR):
            print("Removing existing virtual environment...")
            try:
                shutil.rmtree(self.VENV_DIR)
            except Exception as e:
                print(f"Error removing existing venv: {e}")
                sys.exit(1)

        # Create new virtual environment
        print("Creating new virtual environment...")
        try:
            venv.create(self.VENV_DIR, with_pip=True)
            print("✓ Virtual environment created successfully")
        except Exception as e:
            print(f"Failed to create virtual environment: {e}")
            sys.exit(1)

        # Upgrade pip in virtual environment
        self._run_venv_command(["-m", "pip", "install", "--upgrade", "pip"])
        print("✓ Pip upgraded in virtual environment")

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

    def ensure_dependencies(self):
        """Install and verify all required packages in virtual environment."""
        print("\nInstalling required packages in virtual environment...")
        
        for package in self.required_packages:
            print(f"Installing {package}...")
            success = self._run_venv_command(
                ["-m", "pip", "install", "--upgrade", package]
            )
            if success:
                print(f"✓ Successfully installed {package}")
            else:
                print(f"✗ Failed to install {package}")
                sys.exit(1)

    def ensure_env_file(self):
        """Ensure .env file exists with bot token."""
        if not os.path.exists(".env"):
            print("\nNo .env file found. Creating one...")
            token = input("Please enter your bot token: ").strip()
            
            with open(".env", "w") as f:
                f.write(f"BOT_TOKEN={token}\n")
            print("✓ Created .env file with bot token")
        else:
            print("✓ .env file exists")

    def get_local_versions(self):
        """Get version information of local files."""
        if not os.path.exists(self.VERSION_FILE):
            return {}
        try:
            with open(self.VERSION_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    def get_remote_versions(self):
        """Get latest versions from GitHub repository."""
        try:
            # Use requests from virtual environment
            cmd_result = self._run_venv_command(
                ["-c", "import requests; response = requests.get('" + self.RELEASE_URL + "'); print(response.text)"],
                capture_output=True
            )
            if cmd_result and cmd_result.returncode == 0:
                release_data = json.loads(cmd_result.stdout)
                return {
                    "version": release_data["tag_name"],
                    "files": self._get_files_from_release(release_data)
                }
        except Exception as e:
            print(f"Error fetching remote versions: {e}")
        return None

    def _get_files_from_release(self, release_data):
        """Extract file information from release data."""
        try:
            cmd_result = self._run_venv_command(
                ["-c", "import requests; response = requests.get('" + self.REPO_URL + "'); print(response.text)"],
                capture_output=True
            )
            if cmd_result and cmd_result.returncode == 0:
                files = {}
                for item in json.loads(cmd_result.stdout):
                    if item["type"] == "file":
                        files[item["path"]] = item["sha"]
                return files
        except Exception as e:
            print(f"Error fetching file information: {e}")
        return {}

    def download_file(self, file_path, sha):
        """Download a specific file from the repository."""
        try:
            url = urljoin(self.REPO_URL, file_path)
            download_script = f"""
import requests
url = '{url}'
response = requests.get(url)
if response.status_code == 200:
    file_data = response.json()
    if file_data['sha'] == '{sha}':
        content_response = requests.get(file_data['download_url'])
        if content_response.status_code == 200:
            with open('{file_path}', 'wb') as f:
                f.write(content_response.content)
            print('success')
"""
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            result = self._run_venv_command(["-c", download_script], capture_output=True)
            return result and "success" in result.stdout
        except Exception as e:
            print(f"Error downloading {file_path}: {e}")
        return False

    def update_files(self):
        """Update local files if newer versions are available."""
        local_versions = self.get_local_versions()
        remote_versions = self.get_remote_versions()

        if not remote_versions:
            print("Could not fetch remote versions. Update aborted.")
            return False

        updates_needed = False
        for file_path, remote_sha in remote_versions["files"].items():
            local_sha = local_versions.get("files", {}).get(file_path)
            if local_sha != remote_sha:
                print(f"Updating {file_path}...")
                if self.download_file(file_path, remote_sha):
                    updates_needed = True
                else:
                    print(f"Failed to update {file_path}")

        if updates_needed:
            with open(self.VERSION_FILE, 'w') as f:
                json.dump(remote_versions, f)
            print("Updates completed successfully.")
            return True
        
        print("No updates needed.")
        return False

    def run(self):
        """Main execution method."""
        print("=== Whiteout Survival Bot Starter ===")
        
        # Verify repository access
        if not self.verify_repository_access():
            print("\nWould you like to reconfigure the GitHub repository?")
            if input("(y/n): ").strip().lower() == 'y':
                self.create_initial_config()
                if not self.verify_repository_access():
                    print("Still unable to access repository. Please check your settings and try again.")
                    sys.exit(1)
            else:
                sys.exit(1)
        
        # Set up virtual environment
        self.setup_virtual_environment()
        
        # Install dependencies in virtual environment
        self.ensure_dependencies()
        
        # Ensure .env file exists
        self.ensure_env_file()
        
        print("\nChecking for updates...")
        if self.update_files():
            print("Updates installed. Restarting...")
            self._run_venv_command(sys.argv)
            sys.exit(0)
        
        # Start the main bot
        main_script = os.path.join(self.SCRIPTS_DIR, "main.py")
        if os.path.exists(main_script):
            print("\nStarting bot...")
            self._run_venv_command([main_script])
        else:
            print(f"\nError: {main_script} not found!")

if __name__ == "__main__":
    starter = BotStarter()
    starter.run()
