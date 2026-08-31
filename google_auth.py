import os
import json
import requests as _requests
from pathlib import Path
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.config import OAUTH_CLIENT_SECRET_FILE, TOKEN_FILE, OAUTH_SCOPES


FASTAPI_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")


# ─── FastAPI-integrated OAuth (browser flow through main app) ─────────────────

def get_flow(redirect_uri: str = FASTAPI_REDIRECT_URI) -> Flow:
    """Create OAuth Flow."""
    if not os.path.exists(OAUTH_CLIENT_SECRET_FILE):
        raise FileNotFoundError(
            f"Client secret not found at '{OAUTH_CLIENT_SECRET_FILE}'. "
            "Download it from GCP Console → APIs & Services → Credentials."
        )
    return Flow.from_client_secrets_file(
        OAUTH_CLIENT_SECRET_FILE,
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
    
    # Force strip PKCE parameters because google-auth-oauthlib forces them 
    # and setting code_challenge_method=None doesn't actually stop it.
    import re
    auth_url = re.sub(r"&code_challenge=[^&]*", "", auth_url)
    auth_url = re.sub(r"&code_challenge_method=[^&]*", "", auth_url)
    
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str = FASTAPI_REDIRECT_URI) -> Credentials:
    """Exchange OAuth authorization code for credentials via manual POST (bypassing PKCE checks) and save token.json."""
    if not os.path.exists(OAUTH_CLIENT_SECRET_FILE):
        raise FileNotFoundError(f"Client secret not found at '{OAUTH_CLIENT_SECRET_FILE}'.")
        
    with open(OAUTH_CLIENT_SECRET_FILE, "r") as f:
        client_secrets = json.load(f)
        
    # The JSON structure usually has a 'web' or 'installed' key
    secret_data = client_secrets.get("web") or client_secrets.get("installed")
    if not secret_data:
        raise ValueError("Invalid client_secret.json structure.")
        
    client_id = secret_data.get("client_id")
    client_secret = secret_data.get("client_secret")
    token_uri = secret_data.get("token_uri", "https://oauth2.googleapis.com/token")

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
    
    token_path = Path(TOKEN_FILE)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
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
        token_path.unlink()


def is_authenticated() -> bool:
    """Quick check: does a valid token exist?"""
    return get_oauth_credentials() is not None


# ─── Legacy CLI flow (kept for backward compatibility / dev CLI use) ───────────

def smoke_test_oauth():
    """Smoke test to verify Google Calendar, Gmail, and UserInfo access."""
    print("--- Testing OAuth Credentials ---")
    creds = get_oauth_credentials()
    if not creds:
        print("[ERR] No valid credentials found. Run OAuth flow via browser first.")
        return

    try:
        info = get_user_info(creds)
        print(f"[OK] Connected as: {info.get('email')}")
    except Exception as e:
        print(f"[ERR] Userinfo failed: {e}")

    try:
        svc = build("calendar", "v3", credentials=creds)
        result = svc.events().list(calendarId="primary", maxResults=3).execute()
        print(f"[OK] Google Calendar OK. Upcoming events: {len(result.get('items', []))}")
    except Exception as e:
        print(f"[ERR] Calendar: {e}")

    try:
        build("gmail", "v1", credentials=creds)
        print("[OK] Gmail API ready.")
    except Exception as e:
        print(f"[ERR] Gmail: {e}")


if __name__ == "__main__":
    smoke_test_oauth()
