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
    return render(request, 'dashboard.html', context)

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


def file_upload(request):
    """
    Handle file upload for requirements processing.
    
    This view processes the uploaded requirements file,
    generates test scenarios, and stores the results for display.
    """
    if request.method == 'POST':
        try:
            # Get the uploaded file
            requirement_file = request.FILES.get('requirement_file')
            
            if not requirement_file:
                from django.contrib import messages
                messages.error(request, "Please select a file to upload.")
                return redirect('ui_components:requirements')
            
            # Create a temporary file to save the upload
            import tempfile
            import os
            
            # Get file extension
            file_extension = os.path.splitext(requirement_file.name)[1].lower()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file_path = temp_file.name
                # Write uploaded file content to temporary file
                for chunk in requirement_file.chunks():
                    temp_file.write(chunk)
            
            try:
                # Import necessary modules for processing
                from src.phase1.llm_test_scenario_generator.document_processor import DocumentProcessor
                from src.phase1.llm_test_scenario_generator.scenario_generator import ScenarioGenerator
                import asyncio
                import logging
                
                logger = logging.getLogger(__name__)
                logger.info(f"Processing file: {requirement_file.name}")
                
                # Process the document
                doc_processor = DocumentProcessor()
                requirements = doc_processor.process_document(temp_file_path)
                
                logger.info(f"Document processed successfully. Found {len(requirements.get('requirements', []))} requirements, " +
                           f"{len(requirements.get('user_stories', []))} user stories, " +
                           f"Raw text length: {len(requirements.get('raw_text', ''))}")
                
                # Generate scenarios
                scenario_generator = ScenarioGenerator()
                
                # Run the async function in a synchronous context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                scenarios = loop.run_until_complete(
                    scenario_generator.generate_scenarios_from_document(
                        temp_file_path,
                        num_scenarios=5,
                        detail_level="medium"
                    )
                )
                loop.close()
                
                logger.info(f"Generated {len(scenarios.get('scenarios', []))} test scenarios.")
                
                # Store results in session for the results page
                # Note: Convert any non-serializable objects to serializable form
                # Django session requires data to be JSON serializable
                request.session['requirements_results'] = {
                    'requirements': requirements,
                    'scenarios': scenarios,
                    'source': 'file',
                    'file_name': requirement_file.name
                }
                
                # In production, we would add database storage here:
                # from myapp.models import RequirementDocument, TestScenario
                # document = RequirementDocument.objects.create(name=requirement_file.name, ...)
                
                # And SharePoint integration:
                # from sharepoint_integration import upload_to_sharepoint
                # sharepoint_url = upload_to_sharepoint(temp_file_path, requirement_file.name)
                # request.session['requirements_results']['sharepoint_url'] = sharepoint_url
                
                # Redirect to results page
                return redirect('ui_components:requirements_results')
                
            finally:
                # Clean up the temporary file
                try:
                    # Ensure file is closed properly
                    import time
                    time.sleep(0.1)  # Small delay to ensure file is not in use
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {e}")
                
        except Exception as e:
            # Log the error and show an error message
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing file upload: {str(e)}")
            
            from django.contrib import messages
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('ui_components:requirements')
    
    # If it's not a POST request, redirect to the requirements page
    return redirect('ui_components:requirements')


def manual_input(request):
    """
    Handle manual text input for requirements processing.
    
    This view processes the requirements text submitted through the manual input form,
    generates test scenarios, and returns the results to the user.
    """
    # Check if it's a POST request
    if request.method == 'POST':
        try:
            # Get the requirements text from the form
            requirements_text = request.POST.get('requirement_text', '')
            
            if not requirements_text.strip():
                # If the text is empty, show an error message
                from django.contrib import messages
                messages.error(request, "Please enter some requirements text.")
                return redirect('ui_components:requirements')
            
            # Import the necessary modules for processing
            from src.phase1.llm_test_scenario_generator.document_processor import DocumentProcessor
            from src.phase1.llm_test_scenario_generator.scenario_generator import ScenarioGenerator
            import asyncio
            
            # Process the input text
            doc_processor = DocumentProcessor()
            requirements = doc_processor.process_raw_input(requirements_text)
            
            # Generate scenarios (need to handle async)
            scenario_generator = ScenarioGenerator()
            
            # Run the async function in a synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            scenarios = loop.run_until_complete(
                scenario_generator.generate_scenarios_from_text(
                    requirements_text,
                    num_scenarios=5,
                    detail_level="medium"
                )
            )
            loop.close()
            
            # Store results in session for the results page
            request.session['requirements_results'] = {
                'requirements': requirements,
                'scenarios': scenarios,
                'source': 'manual'
            }
            
            # Redirect to results page
            return redirect('ui_components:requirements_results')
            
        except Exception as e:
            # Log the error and show an error message
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing manual input: {str(e)}")
            
            from django.contrib import messages
            messages.error(request, f"Error processing requirements: {str(e)}")
            return redirect('ui_components:requirements')
    
    # If it's not a POST request, redirect to the requirements page
    return redirect('ui_components:requirements')

# Updated Test Generation view function

def requirements_results(request):
    """
    Display the results of requirements processing.
    """
    # Get results from session
    results = request.session.get('requirements_results', {})
    
    # Check if results exist
    if not results:
        from django.contrib import messages
        messages.error(request, "No processed requirements found. Please submit requirements first.")
        return redirect('ui_components:requirements')
    
    context = {
        'active_menu': 'requirements',
        'content_title': 'Requirements Processing Results',
        'requirements': results.get('requirements', {}),
        'scenarios': results.get('scenarios', {}),
        'source': results.get('source', 'unknown')
    }
    
    return render(request, 'requirements/requirements_results.html', context)

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
    return render(request, 'test_repository/index.html', context)

def test_execution(request):
    context = {
        'active_menu': 'test_execution',
        'content_title': 'Test Execution',
    }
    return render(request, 'test_execution/index.html', context)

def analysis(request):
    context = {
        'active_menu': 'analysis',
        'content_title': 'Analysis & Defects',
    }
    return render(request, 'analysis/index.html', context)

def code_automation(request):
    context = {
        'active_menu': 'code_automation',
        'content_title': 'Code & Automation',
    }
    return render(request, 'code_automation/index.html', context)

def reporting(request):
    context = {
        'active_menu': 'reporting',
        'content_title': 'Reporting',
    }
    return render(request, 'reporting/index.html', context)

def settings_view(request):
    context = {
        'active_menu': 'settings',
        'content_title': 'Settings',
    }
    return render(request, 'settings/index.html', context)

# New view functions for Test Generation & Refinement

@require_POST
def test_generation_generate(request):
    """
    Handle API request to generate test cases
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        
        # Call the backend API
        api_url = 'http://localhost:5000/api/test-cases/generate'
        if data.get('sourceType') == 'requirements' and data.get('requirementIds'):
            # Batch generation
            api_url = 'http://localhost:5000/api/test-cases/generate-batch'
            
        response = requests.post(api_url, json=data)
        response_data = response.json()
        
        # Return the API response
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_POST
def test_generation_refine(request):
    """
    Handle API request to refine an existing test case
    """
    try:
        # Check if we have a file upload
        if 'test_case_file' in request.FILES:
            test_case_file = request.FILES['test_case_file']
            
            # Save the uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(test_case_file.name)[1]) as temp_file:
                for chunk in test_case_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Call the backend API to analyze the test case
            files = {'test_case_file': open(temp_path, 'rb')}
            response = requests.post('http://localhost:5000/api/test-cases/refine', files=files)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            # Return the API response
            return JsonResponse(response.json())
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No test case file provided'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_POST
def export_test_cases_excel(request):
    """
    Handle API request to export test cases to Excel
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        
        # Call the backend API
        response = requests.post(
            'http://localhost:5000/api/test-cases/export-excel', 
            json=data,
            stream=True
        )
        
        # Create HTTP response with the Excel file
        http_response = HttpResponse(
            response.content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Set the filename for download
        filename = data.get('filename', 'test_cases') + '.xlsx'
        http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return http_response
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_POST
def compare_with_repository(request):
    """
    Handle API request to compare test cases with repository
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        
        # Call the backend API
        response = requests.post(
            'http://localhost:5000/api/test-cases/compare-with-repository', 
            json=data
        )
        
        # Return the API response
        return JsonResponse(response.json())
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    

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