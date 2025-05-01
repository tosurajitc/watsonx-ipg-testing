from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import os
import tempfile
import requests
from datetime import datetime

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
    # Your existing view logic here
    pass

def manual_input(request):
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