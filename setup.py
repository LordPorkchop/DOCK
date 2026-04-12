import config
from loggingService import Logger
from pathlib import Path
import subprocess
import sys

def installDependencies():
    subprocess.run(
        [
            ".\\.venv\\Scripts\\python.exe",
            "-m",
            "pip",
            "install",
            "-r",
            Path(config.internal.depPath)
        ],
        capture_output=True,
        shell=False,
        check=True,
        text=True,
    )   

def main():
    logger = Logger(name="setup").getLogger()

    if config.internal.setupCompleted:
        logger.warning("Setup already completed")
        exit(0)
    
    if Path(".venv").is_dir():
        logger.info("Virtual environmeant already exists")
    else:
        logger.info("Creating virtual environment...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", ".venv"],
                capture_output=True,
                shell=False,
                check=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.exception(f"Failed to initialize virtual environment: {e}")
            exit(1)

    logger.info("Installing dependencies...")
    try:
        installDependencies()
    except Exception as e:
        logger.exception(f"Failed to install dependencies: {e}")
        exit(1)
    else:
        logger.info("Dependencies installed successfully")


if __name__ == "__main__":
    main()
