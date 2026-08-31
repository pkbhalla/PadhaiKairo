import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import webbrowser
from google_auth_oauthlib.flow import Flow
from core.config import OAUTH_CLIENT_SECRET_FILE, TOKEN_FILE, OAUTH_SCOPES

def main():
    flow = Flow.from_client_secrets_file(
        OAUTH_CLIENT_SECRET_FILE,
        scopes=OAUTH_SCOPES,
        redirect_uri="http://localhost:8080/"
    )
    # 64-char valid code verifier
    flow.code_verifier = "a" * 64
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    
    print("\n" + "="*70)
    print("OPEN THIS LINK IN YOUR BROWSER:")
    print(auth_url)
    print("="*70 + "\n")
    
    try:
        webbrowser.open(auth_url)
    except:
        pass
        
    resp = input("After consenting, paste the FULL redirected URL here: ").strip()
    
    if resp.startswith("http"):
        flow.fetch_token(authorization_response=resp)
    else:
        flow.fetch_token(code=resp)
        
    creds = flow.credentials
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print("\nSUCCESS! Saved credentials to", TOKEN_FILE)

if __name__ == "__main__":
    main()
