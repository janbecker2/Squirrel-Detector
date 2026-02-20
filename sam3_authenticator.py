import os
from dotenv import load_dotenv
from huggingface_hub import login, whoami

class SAM3Auth:
    def __init__(self):
        # Load .env file
        load_dotenv()

    def login(self, token=None):
        # Check if already authenticated 
        try:
            user = whoami()
            print(f"Authenticated as: {user['name']}")
            return True
        except Exception:
            # Not authenticated,  check for token
            tk = token or os.getenv("HF_TOKEN")
            
            if tk:
                try:
                    login(token=tk)
                    print("Login successful via token.")
                    return True
                except Exception as e:
                    print(f"Login failed: {e}")
            
            print("Error: No valid session or token found.")
            return False

SAM3Auth().login()