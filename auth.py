import os
import hmac
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status, Depends

load_dotenv()
@dataclass
class ApiClient:
    client_id: str
    api_key: str
    scopes: set[str]


def load_api_clients() -> list[ApiClient]:
    raw = os.getenv("API_KEYS", "")
    clients: list[ApiClient] = []

    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue

        try:
            client_id, api_key, scopes_raw = item.split(":", 2)
        except ValueError:
            raise RuntimeError("Invalid API_KEYS format")

        clients.append(
            ApiClient(
                client_id=client_id,
                api_key=api_key,
                scopes={scope.strip() for scope in scopes_raw.split(",") if scope.strip()},
            )
        )

    return clients


API_CLIENTS = load_api_clients()


def get_api_client(x_api_key: str | None = Header(default=None)) -> ApiClient:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    for client in API_CLIENTS:
        if hmac.compare_digest(x_api_key, client.api_key):
            return client

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_scope(required_scope: str):
    def dependency(client: ApiClient = Depends(get_api_client)) -> ApiClient:
        if required_scope not in client.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )

        return client

    return dependency