import base64
import logging
import secrets
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings

logger = logging.getLogger(__name__)

security = HTTPBasic()

class BasicAuthMiddleware:
    """
    Middleware to handle Basic Authentication for API endpoints
    """
    
    def __init__(self, app):
        self.app = app
        
        # Get credentials and settings from the settings object
        self.username = settings.BASIC_AUTH_USERNAME
        self.password = settings.BASIC_AUTH_PASSWORD
        self.auth_enabled = settings.ENABLE_BASIC_AUTH
        
        # Log warning if using default credentials in production
        if (
            self.auth_enabled and 
            self.username == "admin" and 
            self.password == "password" and
            settings.ENVIRONMENT.value == "production"
        ):
            logger.warning("Using default basic auth credentials in production - this is insecure!")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through non-HTTP requests (like WebSockets)
            await self.app(scope, receive, send)
            return
            
        # Create a request object to work with
        request = Request(scope, receive=receive, send=send)
        path = request.url.path
        
        logger.debug(f"Request path: {path}")
        
        # Check if this path should bypass authentication
        should_bypass = (
            not self.auth_enabled or
            path.startswith("/static") or
            path == "/api/health" or
            path.startswith("/api/health?") or
            path == "/"
        )
        
        if should_bypass:
            logger.debug(f"Bypassing authentication for path: {path}")
            await self.app(scope, receive, send)
            return
        
        # For all other paths, implement authentication
        headers = dict(request.headers.items())
        authorization = headers.get("authorization", "")
        scheme, param = get_authorization_scheme_param(authorization)
        
        # No auth header or wrong scheme
        if not authorization or scheme.lower() != "basic":
            logger.debug(f"No valid auth for path: {path}")
            response = Response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
                content="Unauthorized"
            )
            await response(scope, receive, send)
            return
        
        # Invalid auth format
        if not param:
            logger.debug(f"Invalid auth format for path: {path}")
            response = Response(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                headers={"WWW-Authenticate": "Basic"},
                content="Unauthorized"
            )
            await response(scope, receive, send)
            return
            
        try:
            # Decode and validate credentials
            decoded = base64.b64decode(param).decode("ascii")
            username, _, password = decoded.partition(":")
            
            correct_username = secrets.compare_digest(username, self.username)
            correct_password = secrets.compare_digest(password, self.password)
            
            if not (correct_username and correct_password):
                client_host = scope.get("client")[0] if scope.get("client") else "unknown"
                logger.warning(f"Failed login attempt for user '{username}' from {client_host}")
                response = Response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Basic"},
                    content="Unauthorized"
                )
                await response(scope, receive, send)
                return
                
            # Credentials are valid, proceed with request
            logger.debug(f"Authentication successful for path: {path}")
            await self.app(scope, receive, send)
            
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            response = Response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
                content="Unauthorized"
            )
            await response(scope, receive, send)
            return


# For securing Swagger UI
def authenticate_swagger(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Function to authenticate Swagger UI access using Basic Auth
    """
    correct_username = secrets.compare_digest(credentials.username, settings.BASIC_AUTH_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.BASIC_AUTH_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return "authenticated"