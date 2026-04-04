import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterable


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
                if not pipInstall(dep) and check:
                    raise RuntimeError(f"Failed to install dependency '{dep}'")
        except Exception as e:
            if check:
                raise RuntimeError(f"Failed to install dependency {dep}: {e}")
            else:
                continue
