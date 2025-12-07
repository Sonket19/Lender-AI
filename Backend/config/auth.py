import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
import os

# Initialize Firebase Admin SDK
@lru_cache()
def get_firebase_app():
    """Initialize Firebase Admin SDK (singleton)"""
    if not firebase_admin._apps:
        # Try to get service account path from environment
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', './firebase-service-account.json')
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # If no service account file, try to initialize with default credentials
            # This works in Google Cloud environments
            try:
                firebase_admin.initialize_app()
            except Exception as e:
                print(f"Warning: Could not initialize Firebase Admin SDK: {e}")
                print("Authentication will not work until Firebase is properly configured.")
    
    return firebase_admin.get_app()

# Security scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify Firebase ID token and return user ID
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        str: Firebase user ID (uid)
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    try:
        # Get the token from the Authorization header
        token = credentials.credentials
        
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        
        # Return the user ID
        return decoded_token['uid']
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )

# Initialize Firebase on module import
get_firebase_app()
