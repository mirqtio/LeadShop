"""
Google OAuth Authentication Integration
Provides Google OAuth 2.0 authentication for the assessment UI
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google.auth.exceptions import GoogleAuthError
import jwt
from jwt.exceptions import InvalidTokenError
import logging

logger = logging.getLogger(__name__)

# OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

class GoogleAuth:
    """Google OAuth authentication handler"""
    
    def __init__(self):
        if not GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
        self.client_id = GOOGLE_CLIENT_ID
        
    def verify_google_token(self, token: str) -> Dict[str, Any]:
        """Verify Google ID token and return user info"""
        try:
            # Verify the token against Google's servers
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                self.client_id
            )
            
            # Additional validation
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
                
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'email_verified': idinfo.get('email_verified', False)
            }
            
        except GoogleAuthError as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token for authenticated user"""
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            'sub': user_data['google_id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'picture': user_data['picture'],
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'access_token'
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT access token and return user info"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            if payload.get('type') != 'access_token':
                raise InvalidTokenError("Invalid token type")
                
            return {
                'google_id': payload['sub'],
                'email': payload['email'],
                'name': payload['name'],
                'picture': payload['picture']
            }
            
        except InvalidTokenError as e:
            logger.error(f"JWT token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

# Global auth instance
google_auth = GoogleAuth()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    return google_auth.verify_access_token(token)

async def optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Optional authentication dependency - returns None if not authenticated"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        token = auth_header.split(" ")[1]
        return google_auth.verify_access_token(token)
    except:
        return None