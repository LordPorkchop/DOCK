import configparser
from importlib import metadata
from loggingService import Logger
import os
from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Iterable

config = configparser.ConfigParser()
config.read("settings.cfg")


def _normalizeDistName(name:str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()

def getDependencies(fp: Path = Path("./requirements.txt")) -> list[str]:
    if not (fp.is_file() and os.path.exists(fp) and fp.name.endswith(".txt")):
        raise ValueError(f"'{fp}' is not a valid file")
    
    try:
        content = fp.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Error while parsing dependencies: {e}")
        
    deps: list[str] = []
    env = default_environment()
    
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        
        try:
            req = Requirement(line)
        except InvalidRequirement as e:
            raise RuntimeError(f"Invalid requirement: {e}")
        
        if req.marker is None or req.marker.evaluate(env): #type: ignore
            deps.append(str(req))

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
                shell=False,
            )
        except subprocess.CalledProcessError:
            return False
        else:
            return True
    if nonRedundant:
        for dep in d:
            try:
                try:
                    __import__(dep)
                except ModuleNotFoundError:
                    if not pipInstall(dep) and check: # Attempts to install package, checks for fail
                        raise RuntimeError(f"Failed to install dependency '{dep}'")     
            except Exception as e:
                if check:
                    raise RuntimeError(f"Failed to install dependency {dep}: {e}")
                else:
                    continue
    else:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", config["internal"]["depPath"]],
                capture_output=True,
                check=True,
                shell=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            if check:
                raise RuntimeError(f"Failed to install dependencies: {e}")


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


if __name__ == "__main__":
    main()
