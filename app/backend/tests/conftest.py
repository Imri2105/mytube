import os

# Set before the app is imported; values only need to look plausible.
os.environ.setdefault("COGNITO_ISSUER", "https://cognito-idp.il-central-1.amazonaws.com/test")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client")
