from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
import json

# Setup logger
logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def get_processed_requirements_api(request):
    """
    API endpoint to get processed requirements.
    
    This endpoint retrieves processed requirements from the session or database,
    and returns them as a JSON response. If no processed requirements are available,
    it returns sample data.
    
    Returns:
        JsonResponse: JSON response with requirements data
    """
    try:
        # Try to get processed requirements from session first
        requirements_results = request.session.get('requirements_results', {})
        requirements_data = requirements_results.get('requirements', {})
        
        # Check if we have requirements data
        if requirements_data and 'requirements' in requirements_data:
            actual_requirements = requirements_data.get('requirements', [])
            if actual_requirements:
                # Return the actual processed requirements
                return JsonResponse({
                    "status": "success",
                    "data": {
                        "requirements": actual_requirements
                    }
                })
        
        # If not in session, try to retrieve from database
        # Assuming you have a model for storing processed requirements
        # Note: Implement this part once you have database models set up
        
        # If no actual requirements are available, return sample data
        sample_requirements = [
            {
                "id": "REQ-001",
                "title": "User Authentication",
                "description": "The system shall provide user authentication functionality",
                "source": "Sample Data",
                "status": "Processed",
                "priority": "High"
            },
            {
                "id": "REQ-002",
                "title": "Password Reset",
                "description": "Users shall be able to reset their passwords",
                "source": "Sample Data",
                "status": "Processed",
                "priority": "Medium"
            },
            {
                "id": "REQ-003",
                "title": "Test Case Generation",
                "description": "The system shall generate test cases from requirements",
                "source": "Sample Data",
                "status": "Processed",
                "priority": "High"
            },
            {
                "id": "REQ-004",
                "title": "Test Case Review",
                "description": "The system shall allow for review and refinement of test cases",
                "source": "Sample Data",
                "status": "Processed",
                "priority": "Medium"
            }
        ]
        
        logger.info("No actual processed requirements found. Returning sample data.")
        
        # Return sample data
        return JsonResponse({
            "status": "success",
            "data": {
                "requirements": sample_requirements
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_processed_requirements_api: {str(e)}")
        
        # Return error response
        error_response = {
            "status": "error",
            "message": f"Failed to get processed requirements: {str(e)}"
        }
        
        return JsonResponse(error_response, status=500)

def jira_requirements(request):
    """
    Handle JIRA requirements ingestion
    """
    if request.method == 'POST':
        # Process JIRA requirements ingestion logic
        try:
            # Your JIRA connection and requirements fetching logic
            messages.success(request, 'Successfully fetched requirements from JIRA')
        except Exception as e:
            messages.error(request, f'Error fetching requirements: {str(e)}')
    
    return render(request, 'requirements/requirements_input.html', {
        'active_tab': 'jira'
    })

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