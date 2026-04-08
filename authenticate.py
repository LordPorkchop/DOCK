import configparser
from loggingService import Logger
from pathlib import Path
import keyring
import requests
import time


def _loadConfig(configPath: Path = Path("./settings.cfg")) -> configparser.ConfigParser:
    """Loads the configuration from the specified .cfg file

    Args:
        configPath (Path, optional): The path to the config file. Defaults to "settings.cfg".

    Raises:
        FileNotFoundError: If the specified config file is not found

    Returns:
        configparser.ConfigParser: The configuration
    """
    config = configparser.ConfigParser()
    loaded = config.read(configPath)
    if not loaded:
        raise FileNotFoundError(f"Could not read configuration file: {configPath}")
    return config


def requestAuthenticationData() -> dict:
    """Requests authentication process data from endpoint specified in config

    Raises:
        ValueError: If the endpoint returns incomplete or invalid data

    Returns:
        dict: The authentication data
    """
    clientId = config["internal"]["appID"]
    authReqURI = config["internal"]["authReqURI"]
    
    logger.info(f"Requesting auth data from {authReqURI}")

    response = requests.post(
        authReqURI,
        data={"client_id": clientId, "scope": "repo"},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Auth request failed: {e} (HTTP {response.status_code})")

    payload = response.json()
    requiredFields = ("device_code", "user_code", "verification_uri", "interval")
    missingFields = [field for field in requiredFields if field not in payload]
    if missingFields:
        raise ValueError(
            f"Missing required fields from auth response: {', '.join(missingFields)}"
        )
    else:
        logger.debug("Auth data valid")

    return {
        "deviceCode": payload["device_code"],
        "userCode": payload["user_code"],
        "verificationURI": payload["verification_uri"],
        "interval": int(payload["interval"]),
        "expiresIn": int(payload.get("expires_in", 900)),
    }


def pollForAccessToken(deviceCode: str, interval: int) -> str:
    """Polls for an access token at the endpoint specified in the config every `interval` seconds. Handles "slow_down" error itself by increasing `interval` by 5.

    Args:
        deviceCode (str): The device code received by `requestAuthenticationData()`
        interval (int): The polling interval received by `requestAuthenticationData()`

    Raises:
        HTTPError: If an error occurs during POST request. Raised by `requests.Response.raise_for_status()`.
        TimeoutError: If the device code expires before authentication is finished
        PermissionError: If the authentication is denied by the user
        RuntimeError: If an unknown error occurs

    Returns:
        str: The access token
    """
    clientId = config["internal"]["appID"]
    authGetURI = config["internal"]["authGetURI"]
    authTimeout = int(config["general"].get("authTimeout", "120"))

    serviceName = config["general"].get("appName", "DOCK")
    accountName = config["general"].get("ghUser", "github") or "github"

    deadline = time.monotonic() + authTimeout
    currentInterval = max(1, int(interval))

    while time.monotonic() < deadline:
        response = requests.post(
            authGetURI,
            data={
                "client_id": clientId,
                "device_code": deviceCode,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()

        payload = response.json()
        if "access_token" in payload:
            accessToken = payload["access_token"]
            keyring.set_password(serviceName, accountName, accessToken)
            return accessToken

        errorCode = payload.get("error")
        if errorCode == "authorization_pending":
            time.sleep(currentInterval)
            continue

        if errorCode == "slow_down":
            currentInterval += 5
            time.sleep(currentInterval)
            continue

        if errorCode == "expired_token":
            raise TimeoutError("Device code expired before authorization completed.")

        if errorCode == "access_denied":
            raise PermissionError("Authorization was denied by the user.")

        raise RuntimeError(f"Unexpected authentication error: {payload}")

    raise TimeoutError("Timed out waiting for access token.")

def saveToken(token:str, appName:str="DOCK", accName:str="GitHub") -> None:
    try:
        keyring.set_password(appName, accName, token)
    except Exception as e:
        logger.error(f"Error during token storing: {e}")
        raise RuntimeError(f"Failed to store token in keychain: {e}")

logger = Logger(name=__name__).getLogger()
try:
    config = _loadConfig()
    logger.info("Config loaded successfully")
except Exception as e:
    raise RuntimeError("Failed to load config!")
