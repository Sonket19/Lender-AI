from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from google.cloud import firestore
from config.settings import settings
from services.email_service import send_verification_email
import secrets
import string
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

router = APIRouter(prefix="/api/auth", tags=["auth"])
db = firestore.Client(project=settings.GCP_PROJECT_ID)

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    email: EmailStr
    code: str

class GoogleLoginRequest(BaseModel):
    email: EmailStr
    uid: str
    name: str = None
    photo_url: str = None

def generate_code(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

@router.post("/send-code")
async def send_code(request: EmailRequest):
    """Generate and send verification code"""
    try:
        code = generate_code()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Store code in Firestore
        db.collection('verification_codes').document(request.email).set({
            'code': code,
            'expires_at': expires_at.isoformat() + "Z",
            'created_at': datetime.utcnow().isoformat() + "Z"
        })
        
        # Send email
        await send_verification_email(request.email, code)
        
        return {"message": "Verification code sent"}
        
    except Exception as e:
        print(f"Error sending code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-code")
async def verify_code(request: VerifyRequest):
    """Verify code and create/update user"""
    try:
        # Normalize email to lowercase
        email = request.email.lower()
        doc_ref = db.collection('verification_codes').document(email)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=400, detail="Invalid or expired code")
            
        data = doc.to_dict()
        
        # Check expiration
        expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        if datetime.utcnow() > expires_at.replace(tzinfo=None):
            raise HTTPException(status_code=400, detail="Code expired")
            
        # Check code match
        if data['code'] != request.code:
            raise HTTPException(status_code=400, detail="Invalid code")
            
        # Code is valid, delete it
        doc_ref.delete()
        
        # Create/Update user
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        # Generate display name logic
        email_prefix = email.split('@')[0]
        random_suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
        display_name = f"{email_prefix}{random_suffix}"

        if not user_doc.exists:
            print(f"Creating new user document for {email} with name {display_name}")
            user_ref.set({
                'email': email,
                'name': display_name,
                'created_at': datetime.utcnow().isoformat() + "Z",
                'last_login': datetime.utcnow().isoformat() + "Z",
                'auth_method': 'email'
            })
        else:
            print(f"Updating existing user document for {email}")
            user_ref.update({
                'last_login': datetime.utcnow().isoformat() + "Z"
            })
            # If name is missing or is 'User', update it with the new generated name
            current_data = user_doc.to_dict()
            if 'name' not in current_data or current_data.get('name') == 'User' or not current_data.get('name'):
                user_ref.update({'name': display_name})
                print(f"Updated Firestore name to {display_name}")
            else:
                display_name = current_data.get('name')
                print(f"Using existing Firestore name: {display_name}")
            
        # Generate Custom Token for Firebase Auth
        try:
            print(f"Attempting to generate custom token for {email}")
            
            # Ensure Firebase Auth user exists and has the correct display name
            try:
                user_record = firebase_admin.auth.get_user_by_email(email)
                print(f"Found Firebase user: {user_record.uid}, Current Display Name: {user_record.display_name}")
                
                # Always update display name to match Firestore if they differ
                if user_record.display_name != display_name:
                     print(f"Updating Firebase Auth display name to: {display_name}")
                     firebase_admin.auth.update_user(user_record.uid, display_name=display_name)
            except firebase_admin.auth.UserNotFoundError:
                # Create user if not exists
                print(f"Creating new Firebase user for {email}")
                firebase_admin.auth.create_user(
                    uid=email,
                    email=email,
                    display_name=display_name
                )

            custom_token = firebase_admin.auth.create_custom_token(email)
            custom_token_str = custom_token.decode('utf-8')
            print("Custom token generated successfully")
        except Exception as e:
            print(f"Error generating custom token: {e}")
            # Print detailed credential info if available
            try:
                print(f"App name: {firebase_admin.get_app().name}")
                print(f"Project ID: {firebase_admin.get_app().project_id}")
                
                # Try to get the service account email or principal
                from google.auth import default
                creds, _ = default()
                if hasattr(creds, 'service_account_email'):
                    print(f"Running as Service Account: {creds.service_account_email}")
                elif hasattr(creds, 'signer_email'):
                     print(f"Running as Signer: {creds.signer_email}")
                else:
                    print("Running as User Credentials (ADC)")
            except Exception as debug_err:
                print(f"Could not get identity info: {debug_err}")
            raise HTTPException(status_code=500, detail=f"Failed to generate auth token: {str(e)}")
        
        return {
            "message": "Verified successfully",
            "user": {
                "email": request.email,
                "name": display_name,
                "auth_method": "email"
            },
            "custom_token": custom_token_str
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/google-login")
async def google_login(request: GoogleLoginRequest):
    """Handle Google login"""
    try:
        # Create/Update user
        user_ref = db.collection('users').document(request.email)
        user_doc = user_ref.get()
        
        user_data = {
            'email': request.email,
            'uid': request.uid,
            'name': request.name,
            'photo_url': request.photo_url,
            'last_login': datetime.utcnow().isoformat() + "Z",
            'auth_method': 'google'
        }
        
        if not user_doc.exists:
            user_data['created_at'] = datetime.utcnow().isoformat() + "Z"
            user_ref.set(user_data)
        else:
            user_ref.update(user_data)
            
        return {
            "message": "Login successful",
            "user": user_data
        }
        
    except Exception as e:
        print(f"Error in google login: {e}")
        raise HTTPException(status_code=500, detail=str(e))
