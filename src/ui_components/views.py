from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import os
import tempfile
import requests
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging



# Existing view functions
def dashboard(request):
    context = {
        'active_menu': 'dashboard',
        'content_title': 'Dashboard',
    }
    return render(request, 'dashboard/dashboard.html', context)

def requirements(request):
    context = {
        'active_menu': 'requirements',
        'content_title': 'Requirements',
        'active_tab': 'jira',  # Default active tab
    }
    return render(request, 'requirements/requirements_input.html', context)

def jira_requirements(request):
    # Your existing view logic here
    pass


# Updated Test Generation view function


def test_generation(request):
    context = {
        'active_menu': 'test_generation',
        'content_title': 'Test Generation & Refinement',
    }
    return render(request, 'test_generation/test_generation_index.html', context)

def test_repository(request):
    context = {
        'active_menu': 'test_repository',
        'content_title': 'Test Repository & Comparison',
    }
    return render(request, 'test_repository/test_repository.html', context)

def test_execution(request):
    context = {
        'active_menu': 'test_execution',
        'content_title': 'Test Execution',
    }
    return render(request, 'test_execution/test_execution.html', context)

def analysis(request):
    context = {
        'active_menu': 'analysis',
        'content_title': 'Analysis & Defects',
    }
    return render(request, 'analysis/analysis.html', context)

def code_automation(request):
    context = {
        'active_menu': 'code_automation',
        'content_title': 'Code & Automation',
    }
    return render(request, 'code_automation/code_automation.html', context)

def reporting(request):
    context = {
        'active_menu': 'reporting',
        'content_title': 'Reporting',
    }
    return render(request, 'reporting/reporting.html', context)

def settings_view(request):
    context = {
        'active_menu': 'settings',
        'content_title': 'Settings',
    }
    return render(request, 'settings/settings.html', context)

# New view functions for Test Generation & Refinement

   

logger = logging.getLogger(__name__)

def login_view(request):
    """
    Handle user login with enhanced debugging
    """
    logger = logging.getLogger(__name__)
    logger.info("Login view accessed")
    
    if request.method == 'POST':
        logger.info("Processing POST request to login view")
        
        # Get form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Log attempt details (be careful not to log actual passwords in production)
        logger.info(f"Login attempt for username: {username}")
        logger.info(f"Password provided: {'Yes' if password else 'No'}")
        
        # Check if username is in the correct format
        if username and not (username.endswith('@ibm.com') or username.endswith('@in.ibm.com')):
            logger.warning(f"Username not in IBM email format: {username}")
            messages.error(request, "Email must be a valid IBM email address ending with @ibm.com or @in.ibm.com")
            return render(request, 'auth/login.html', {'active_menu': 'login', 'content_title': 'Login'})
        
        # Log configured authentication backends
        from django.conf import settings
        logger.info(f"Configured authentication backends: {settings.AUTHENTICATION_BACKENDS if hasattr(settings, 'AUTHENTICATION_BACKENDS') else 'Not defined'}")
        
        # Authenticate the user
        logger.info("Attempting to authenticate user")
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login the user
            logger.info(f"Authentication successful for user: {username}")
            login(request, user)
            
            # Log user details for debugging
            logger.info(f"User ID: {user.id}, Username: {user.username}, Email: {user.email}")
            logger.info(f"Is staff: {user.is_staff}, Is superuser: {user.is_superuser}")
            
            messages.success(request, f"Welcome back, {user.first_name}!")
            
            # Redirect to the page they were trying to access, or dashboard
            next_url = request.GET.get('next', 'ui_components:dashboard')
            logger.info(f"Redirecting to: {next_url}")
            return redirect(next_url)
        else:
            # Authentication failed - log details
            logger.error(f"Authentication failed for username: {username}")
            
            # Try to determine why authentication failed
            try:
                from django.contrib.auth.models import User
                user_exists = User.objects.filter(username=username.split('@')[0]).exists()
                logger.info(f"User exists in database: {user_exists}")
                
                if user_exists:
                    logger.info("User exists but authentication failed - password may be incorrect")
                else:
                    logger.info("User does not exist in database")
            except Exception as e:
                logger.error(f"Error during authentication debugging: {str(e)}")
            
            # Show error message to user
            messages.error(request, "Invalid username or password.")
    
    # If GET request or authentication failed, render the login page
    context = {
        'active_menu': 'login',
        'content_title': 'Login',
    }
    return render(request, 'auth/login.html', context)

def logout_view(request):
    """
    Handle user logout
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('ui_components:dashboard')

@login_required
def user_preferences(request):
    """
    Handle user preferences
    """
    if request.method == 'POST':
        # Handle form submission
        # Update user preferences in the database
        # In a real implementation, this would update more than just the name
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()
        
        messages.success(request, "Your preferences have been updated.")
        return redirect('ui_components:preferences')
    
    # If GET request, render the preferences page
    context = {
        'active_menu': 'settings',
        'content_title': 'User Preferences',
    }
    return render(request, 'auth/preferences.html', context)    