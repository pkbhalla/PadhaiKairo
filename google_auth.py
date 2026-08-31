import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
import requests as _requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.config import OAUTH_CLIENT_SECRET_FILE, TOKEN_FILE, OAUTH_SCOPES

FASTAPI_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")


def get_client_config() -> Dict[str, Any]:
    """
    Retrieve Google OAuth client config with multiple robust fallbacks:
    1. OAUTH_CLIENT_SECRET_JSON / GOOGLE_CLIENT_SECRET_JSON env vars.
    2. Explicit GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET (or OAUTH_CLIENT_ID/SECRET) env vars.
    3. Local client_secret.json or OAUTH_CLIENT_SECRET_FILE on disk.
    4. Any client_secret*.json in root directory.
    """
    # 1. Full JSON string in env var
    env_json = os.getenv("OAUTH_CLIENT_SECRET_JSON") or os.getenv("GOOGLE_CLIENT_SECRET_JSON")
    if env_json:
        try:
            return json.loads(env_json)
        except Exception:
            pass

    # 2. Key/secret from env vars
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT", "project-925dcd70-fea8-462c-b7a"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            }
        }

    # 3. Files on disk (local development)
    candidates = [
        OAUTH_CLIENT_SECRET_FILE,
        "client_secret.json",
        "client_secret (2).json",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # 4. Any client_secret*.json in current directory
    for f in Path(".").glob("client_secret*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass

    return {}


def get_flow(redirect_uri: str = FASTAPI_REDIRECT_URI) -> Flow:
    """Create OAuth Flow using client configuration."""
    cfg = get_client_config()
    if not cfg:
        raise ValueError(
            "OAuth Client Credentials not found! Please set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET (or OAUTH_CLIENT_SECRET_JSON) in your Cloud Run environment variables."
        )
    return Flow.from_client_config(
        cfg,
        scopes=OAUTH_SCOPES,
        redirect_uri=redirect_uri,
    )


def get_authorization_url(redirect_uri: str = FASTAPI_REDIRECT_URI) -> str:
    """Return the Google OAuth authorization URL to redirect the user to."""
    flow = get_flow(redirect_uri)
    
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
    )
    
    # Strip PKCE parameters to avoid Missing code verifier issue
    auth_url = re.sub(r"&code_challenge=[^&]*", "", auth_url)
    auth_url = re.sub(r"&code_challenge_method=[^&]*", "", auth_url)
    
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str = FASTAPI_REDIRECT_URI) -> Credentials:
    """Exchange OAuth authorization code for credentials via direct POST and save token.json."""
    cfg = get_client_config()
    secret_data = cfg.get("web") or cfg.get("installed") or {}
    
    client_id = secret_data.get("client_id")
    client_secret = secret_data.get("client_secret")
    token_uri = secret_data.get("token_uri", "https://oauth2.googleapis.com/token")

    if not client_id or not client_secret:
        raise ValueError("Missing client_id or client_secret for token exchange.")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    
    response = _requests.post(token_uri, data=payload)
    if not response.ok:
        raise Exception(f"Token exchange failed: {response.text}")
        
    token_data = response.json()
    
    # Construct Credentials object
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=OAUTH_SCOPES
    )
    
    try:
        token_path = Path(TOKEN_FILE)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    except Exception as e:
        print(f"Notice: Could not write token file: {e}")
        
    return creds


def get_oauth_credentials() -> Optional[Credentials]:
    """Load, refresh, or return None for existing OAuth credentials."""
    token_path = Path(TOKEN_FILE)
    if not token_path.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), OAUTH_SCOPES)
    except Exception:
        return None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            return None

    return creds if (creds and creds.valid) else None


def get_user_info(creds: Credentials) -> dict:
    """Fetch Google account user info (email, name, picture) for given credentials."""
    try:
        service = build("oauth2", "v2", credentials=creds)
        return service.userinfo().get().execute()
    except Exception:
        return {}


def logout() -> None:
    """Delete local token.json (clears session)."""
    token_path = Path(TOKEN_FILE)
    if token_path.exists():
        try:
            token_path.unlink()
        except Exception:
            pass


def is_authenticated() -> bool:
    """Quick check: does a valid token exist?"""
    return get_oauth_credentials() is not None
