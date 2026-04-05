import configparser
from loggingService import Logger
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterable

config = configparser.ConfigParser()
config.read("settings.cfg")


def getDependencies(fp: Path = Path("./requirements.txt")) -> list[str]:
    """Fetches the dependant packages stored in a requirements.txt-like file

    Args:
        fp (Path, optional): Where the file is located. Defaults to Path("./requirements.txt").

    Raises:
        RuntimeError: If an error occurs during file parsing
        ValueError: If `fp` does not exist, is not a directory or does not end with '.txt'
        RuntimeError: If an error occurs during evaluation of stored expressions

    Returns:
        list[str]: All dependencies if any expression alongside equals `True`
    """
    deps = []
    if fp.is_file() and os.path.exists(fp) and fp.name.endswith(".txt"):
        try:
            with open(fp, "r") as file:
                content = file.read()
        except Exception as e:
            raise RuntimeError(f"Error while parsing dependencies: {e}")
    else:
        raise ValueError(f"'{fp}' is not a valid file")

    for line in content.splitlines():
        if ";" in line:
            expr = line.split(";")[-1].replace("_", ".").strip()
            try:
                conditionMet = eval(
                    expr, {"__builtins__": None}, {"sys": sys, "platform": platform}
                )
            except Exception as e:
                raise RuntimeError(f"Error while evaluating condition '{expr}': {e}")
            else:
                if conditionMet:
                    deps.append(line.split(";")[0].strip())
        else:
            deps.append(line.strip())

    return deps


def installDependencies(
    d: Iterable[str], check: bool = True, nonRedundant: bool = False
) -> None:
    """Installs a set of packages via pip. Designed to receive the output of `getDependencies` as an input.

    Args:
        d (Iterable[str]): A set of packages to install
        check (bool, optional): Whether to raise errors if installing fails. Defaults to True.
        nonRedundant (bool, optional): Whether to check if packages are already installed before trying with pip. Decreases time consumption greatly. Defaults to False.

    Raises:
        RuntimeError: If the pip install of a package fails and `check` equals `True`
    """

    def pipInstall(pkg: str) -> bool:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True,
                check=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    for dep in d:
        try:
            if nonRedundant:
                try:
                    __import__(dep)
                except ModuleNotFoundError:
                    if not pipInstall(dep) and check:
                        raise RuntimeError(f"Failed to install dependency '{dep}'")
            else:
                subprocess.call([sys.executable, "-m", "pip", "install", "-r", config["internal"]["depPath"]])
        except Exception as e:
            if check:
                raise RuntimeError(f"Failed to install dependency {dep}: {e}")
            else:
                continue


def main():
    logger = Logger(name="setup").getLogger()

    if config.getboolean("internal", "setupCompleted"):
        logger.warning("Setup already completed")
        logger.info("Exiting with code 0")
        exit(0)

    logger.debug("Fetching dependencies...")
    deps = getDependencies(Path(config["internal"]["depPath"]))
    logger.debug(f"{len(deps)} found, installing...")
    installDependencies(deps, nonRedundant=True)
    logger.info("All dependencies installed")

    import requests
    import keyring


if __name__ == "__main__":
    main()
