from app.google_forms import TOKEN_FILE, get_credentials

get_credentials()
print(f"Authorized. Token saved to {TOKEN_FILE}")
