import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --- Configuration ---
# Read secret key from environment variable
SECRET_KEY = os.getenv("KARO_JWT_SECRET")
ALGORITHM = "HS256" # Algorithm for signing/verifying

if not SECRET_KEY:
    logger.warning("Environment variable KARO_JWT_SECRET is not set. API authentication will fail.")
    # Consider raising an error here if JWT auth is mandatory for server startup
    # raise EnvironmentError("KARO_JWT_SECRET must be set for API authentication.")

# OAuth2 scheme (tokenUrl is dummy, we only care about Authorization: Bearer header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic model for token data (optional, mainly for type hinting) ---
class TokenData(BaseModel):
    # Add any claims you might put in the token besides 'exp', e.g., 'sub' (subject)
    pass

# --- JWT Creation (Utility function, can be called by CLI command) ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if not SECRET_KEY:
        raise ValueError("Cannot create token: KARO_JWT_SECRET is not set.")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiration (e.g., 30 days)
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FastAPI Dependency for Token Verification ---
async def verify_jwt_token(token: str = Depends(oauth2_scheme)) -> Any: # Return type can be payload dict or user model
    """
    Verifies the JWT token provided in the Authorization header.

    Raises HTTPException 401 if the token is invalid, expired, or missing.
    """
    if not SECRET_KEY:
        logger.error("Attempted token verification but KARO_JWT_SECRET is not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system not configured correctly.",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # You could extract specific claims here if needed, e.g., username: str = payload.get("sub")
        # If extracting claims, validate them using the TokenData model:
        # try:
        #     token_data = TokenData(**payload)
        # except ValidationError:
        #     raise credentials_exception
        # For simple API key usage, just validating the signature and expiry is often enough.
        logger.debug(f"JWT token successfully validated. Payload: {payload}")
        return payload # Return the decoded payload (or specific user data)
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception
    except Exception as e: # Catch other potential errors during decoding
        logger.error(f"Unexpected error during JWT decoding: {e}", exc_info=True)
        raise credentials_exception