"""
IBM Cloud IAM authentication backend for Django - Simplified for testing
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class IBMCloudAuthBackend(BaseBackend):
    """
    Simplified authentication backend for testing
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user with simplified logic for testing
        
        Args:
            request: The request object
            username: The username (IBM email)
            password: The user's password
            
        Returns:
            User: The authenticated user or None
        """
        # Log authentication attempt for debugging
        logger.info(f"Authentication attempt for username: {username}")
        
        if not username or not password:
            logger.error("Missing username or password")
            return None
        
        # For testing: accept any username ending with @ibm.com and any non-empty password
        if (username.endswith('@ibm.com') or username.endswith('@in.ibm.com')) and password:
            # Extract username from email
            user_name = username.split('@')[0]
            
            try:
                # Try to get existing user
                user = User.objects.get(username=user_name)
                logger.info(f"Found existing user: {user_name}")
            except User.DoesNotExist:
                # Create a new user
                logger.info(f"Creating new user: {user_name}")
                user = User.objects.create_user(
                    username=user_name,
                    email=username,
                    password=password  # Set the password for the user
                )
                
                # Set some default user information
                user.first_name = user_name.capitalize()
                user.last_name = "User"
                user.save()
            
            # Log successful authentication
            logger.info(f"Authentication successful for: {username}")
            return user
        
        # Log failed authentication
        logger.error(f"Authentication failed for: {username}")
        return None
    
    def get_user(self, user_id):
        """
        Get a user by ID
        
        Args:
            user_id: The user's ID
            
        Returns:
            User: The user or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found with ID: {user_id}")
            return None