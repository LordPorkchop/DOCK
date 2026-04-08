import configparser
from importlib import metadata
import logging
from loggingService import Logger
import os
from pathlib import Path
import re
import subprocess
import sys

config = configparser.ConfigParser()
config.read("settings.cfg")


def installDependencies(eventLogger: logging.Logger):
    depFilePath = Path(config["internal"]["depPath"])
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            depFilePath
        ],
        capture_output=True,
        shell=False,
        check=True,
        text=True,
    )
        

def main():
    logger = Logger(name="setup").getLogger()

    if config.getboolean("internal", "setupCompleted"):
        logger.warning("Setup already completed")
        exit(0)

    logger.info("Installing dependencies...")
    try:
        installDependencies(logger)
    except Exception as e:
        logger.exception(f"Failed to install dependencies: {e}")
        exit(1)
    else:
        logger.info("Dependencies installed successfully")


if __name__ == "__main__":
    main()
