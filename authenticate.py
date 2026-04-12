import config
import keyring
import requests
import time
from typing import Optional


def getAuthenticatonData() -> dict:
    """Requests auth data from GitHub

    Raises:
        HTTPError: If the web request fails
        ValueError: If the response is incomplete or invalid

    Returns:
        dict: Containing `deviceCode`, `userCode`, `verificationURI`, `pollingInterval` and `expiresIn`
    """
    appID = config.internal.appID
    uri = config.internal.authReqURI

    res = requests.post(
        uri,
        data={"client_id": appID, "scope": "repo"},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    
    res.raise_for_status()

    payload = res.json()
    requiredFields = ("device_code", "user_code", "verification_uri", "interval")
    missingFields = [field for field in requiredFields if field not in payload]
    if missingFields:
        raise ValueError(
            f"Missing required fields from auth response: {', '.join(missingFields)}"
        )

    return {
        "deviceCode": payload["device_code"],
        "userCode": payload["user_code"],
        "verificationURI": payload["verification_uri"],
        "pollingInterval": int(payload["interval"]),
        "expiresIn": int(payload.get("expires_in", 900)),
    }

def pollAndStoreToken(deviceCode: str, deviceCodeExpiry: int, pollingInterval: int, accountName: Optional[str] = None) -> tuple[str, str]:
    """Retrieves the GitHub access token and saves it to keyring with the specified account name. Will use "github" if none is present

    Args:
        deviceCode (str): The device code returned by `requestAuthenticationData()`
        accountName (str, optional): A custom account name for keyring. Defaults to None.
        pollingInterval (int, optional): Polling interval in seconds. Defaults to 5.

    Raises:
        TimeoutError: If the device code expires
        PermissionError: If the user denies authorization
        ValueError: If `deviceCode` is invalid
        RuntimeError: If an unknown error occurs

    Returns:
        tuple[str, str]: service and account name under which the access token was saved
    """
    clientID = config.internal.appID
    uri = config.internal.authGetURI
    srvcName = str(config.general.appName).lower()
    accName = accountName or "github"
    
    deadline = time.monotonic() + deviceCodeExpiry
    cInterval = max(1, pollingInterval)
    
    while time.monotonic() < deadline:
        res = requests.post(
            uri,
            data={
                "client_id": clientID,
                "device_code": deviceCode,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
            timeout=15
        )
        
        res.raise_for_status()
        
        payload = res.json()
        
        print(payload)
        
        if "access_token" in payload:
            token = payload["access_token"]
            keyring.set_password(srvcName, accName, token)
            config.update("github", "authCompleted", "true")
            return srvcName, accName
        
        errorCode = payload.get("error")
        
        if errorCode == "authorization_pending":
            time.sleep(cInterval)
            continue
        
        if errorCode == "slow_down":
            cInterval += 5
            time.sleep(cInterval)
            continue
        
        if errorCode == "expired_token":
            raise TimeoutError("Device code expired before authorization was completed")
        
        if errorCode == "access_denied":
            raise PermissionError("User denied authorization")
        
        if errorCode == "incorrect_device_code":
            raise ValueError("Incorrect device code")
        
        raise RuntimeError(f"Unexpected authentication error: {payload}")

    raise TimeoutError("Timed out waiting for access token")
