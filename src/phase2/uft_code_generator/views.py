# src/phase2/uft_code_generator/views.py

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .automation_analyzer import UFTAutomationAnalyzer

# Initialize the analyzer
analyzer = UFTAutomationAnalyzer()

# Setup logger
logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_test_case(request):
    """
    Analyze a test case for UFT automation potential.
    
    Expects:
    - 'test_case_source': 'repository' or 'upload'
    - 'automation_scope': 'full' or 'partial'
    - 'test_case_id': ID of the test case (if source is repository)
    - 'selected_steps': JSON-encoded list of step numbers (if scope is partial)
    - uploaded file (if source is upload)
    
    Returns JSON with analysis results.
    """
    try:
        # Extract parameters
        test_case_source = request.POST.get('test_case_source')
        automation_scope = request.POST.get('automation_scope', 'full')
        test_case_id = request.POST.get('test_case_id')
        selected_steps_json = request.POST.get('selected_steps')
        
        # Parse selected steps if provided
        selected_steps = None
        if selected_steps_json:
            try:
                selected_steps = json.loads(selected_steps_json)
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON for selected steps'
                }, status=400)
        
        # Handle repository source
        if test_case_source == 'repository':
            if not test_case_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'test_case_id is required when source is repository'
                }, status=400)
            
            # Get test case from repository (using sample for now)
            test_case_data = analyzer._get_test_case_by_id(test_case_id)
            
        # Handle file upload source
        elif test_case_source == 'upload':
            if 'file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'File is required when source is upload'
                }, status=400)
            
            # Read file content
            uploaded_file = request.FILES['file']
            file_content = uploaded_file.read()
            
            # Get test case from file
            test_case_data = analyzer.get_test_case_from_file(file_content, uploaded_file.name)
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid test_case_source. Must be "repository" or "upload"'
            }, status=400)
        
        # Analyze test case
        analysis_result = analyzer.analyze_test_case(
            test_case_data=test_case_data,
            selected_steps=selected_steps,
            automation_scope=automation_scope
        )
        
        return JsonResponse(analysis_result)
    
    except Exception as e:
        logger.error(f"Error analyzing test case: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error analyzing test case: {str(e)}"
        }, status=500)
    


@csrf_exempt
def test_endpoint(request):
    """Simple test endpoint to verify API functionality."""
    return JsonResponse({
        'status': 'success',
        'message': 'Test endpoint working',
        'method': request.method,
        'post_keys': list(request.POST.keys()),
        'files_keys': list(request.FILES.keys()) if request.FILES else []
    })    

@csrf_exempt
@require_http_methods(["POST"])
def preview_test_case(request):
    """
    Get a preview of a test case for the UI.
    
    Expects:
    - 'test_case_source': 'repository' or 'upload'
    - 'test_case_id': ID of the test case (if source is repository)
    - uploaded file (if source is upload)
    
    Returns JSON with test case preview.
    """
    try:
        # Extract parameters
        test_case_source = request.POST.get('test_case_source')
        test_case_id = request.POST.get('test_case_id')
        
        # Handle repository source
        if test_case_source == 'repository':
            if not test_case_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'test_case_id is required when source is repository'
                }, status=400)
            
            # Get test case preview from repository
            preview_result = analyzer.get_test_case_preview(test_case_id=test_case_id)
            
        # Handle file upload source
        elif test_case_source == 'upload':
            if 'file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'File is required when source is upload'
                }, status=400)
            
            # Read file content
            uploaded_file = request.FILES['file']
            file_content = uploaded_file.read()
            
            # Get test case preview from file
            preview_result = analyzer.get_test_case_preview(
                file_content=file_content,
                file_name=uploaded_file.name
            )
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid test_case_source. Must be "repository" or "upload"'
            }, status=400)
        
        return JsonResponse(preview_result)
    
    except Exception as e:
        logger.error(f"Error previewing test case: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error previewing test case: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_full_script(request):
    """
    Generate a full UFT script for a test case.
    
    Expects:
    - 'test_case_id': ID of the test case
    - 'script_options': JSON-encoded options for script generation (optional)
    
    Returns JSON with generated script.
    """
    try:
        # Extract parameters
        test_case_id = request.POST.get('test_case_id')
        script_options_json = request.POST.get('script_options', '{}')
        
        if not test_case_id:
            return JsonResponse({
                'status': 'error',
                'message': 'test_case_id is required'
            }, status=400)
        
        # Parse script options
        try:
            script_options = json.loads(script_options_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON for script options'
            }, status=400)
        
        # Get test case data
        test_case_data = analyzer._get_test_case_by_id(test_case_id)
        
        # Analyze steps
        step_analyses = []
        for step in test_case_data.get('steps', []):
            step_analysis = analyzer._analyze_step(step)
            step_analyses.append(step_analysis)
        
        # Generate full script
        script = analyzer._generate_full_uft_script(
            test_case_data=test_case_data,
            step_analyses=step_analyses,
            script_options=script_options
        )
        
        return JsonResponse({
            'status': 'success',
            'script': script,
            'script_name': script_options.get('script_name', f"TC{test_case_id.replace('-', '')}_Script"),
            'message': 'Script generated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error generating full script: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error generating full script: {str(e)}"
        }, status=500)

@require_http_methods(["GET"])
def recommend_libraries(request, test_case_id):
    """
    Get recommended UFT libraries for a test case.
    
    Parameters:
    - test_case_id: The ID of the test case
    
    Returns JSON with recommended libraries.
    """
    try:
        # Get test case from repository
        test_case_data = analyzer._get_test_case_by_id(test_case_id)
        
        # Analyze steps
        step_analyses = []
        for step in test_case_data.get('steps', []):
            step_analysis = analyzer._analyze_step(step)
            step_analyses.append(step_analysis)
        
        # Generate library recommendations
        libraries = analyzer._generate_libraries_list(step_analyses)
        
        return JsonResponse({
            'status': 'success',
            'libraries': libraries
        })
    
    except Exception as e:
        logger.error(f"Error recommending libraries: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error recommending libraries: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def is_test_case_automatable(request):
    """
    Quick check to determine if a test case is automatable with UFT.
    
    Expects:
    - 'test_case_data': JSON-encoded test case data
    
    Returns JSON with automation potential.
    """
    try:
        # Extract test case data
        test_case_data_json = request.POST.get('test_case_data')
        
        if not test_case_data_json:
            return JsonResponse({
                'status': 'error',
                'message': 'test_case_data is required'
            }, status=400)
        
        # Parse test case data
        try:
            test_case_data = json.loads(test_case_data_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON for test case data'
            }, status=400)
        
        # Check if automatable
        result = analyzer.is_test_case_automatable(test_case_data)
        
        return JsonResponse(result)
    
    except Exception as e:
        logger.error(f"Error checking if test case is automatable: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error checking if test case is automatable: {str(e)}",
            'automatable': False,
            'potential': 'Unknown',
            'score': 0,
            'reason': f"Error during analysis: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def batch_analyze_test_cases(request):
    """
    Analyze multiple test cases in batch mode.
    
    Expects:
    - 'test_case_ids': JSON-encoded list of test case IDs
    
    Returns JSON with results for each test case and summary.
    """
    try:
        # Extract test case IDs
        test_case_ids_json = request.POST.get('test_case_ids')
        
        if not test_case_ids_json:
            return JsonResponse({
                'status': 'error',
                'message': 'test_case_ids is required'
            }, status=400)
        
        # Parse test case IDs
        try:
            test_case_ids = json.loads(test_case_ids_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON for test case IDs'
            }, status=400)
        
        # Analyze test cases
        result = analyzer.batch_analyze_test_cases(test_case_ids)
        
        return JsonResponse(result)
    
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error in batch analysis: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def export_analysis_results(request):
    """
    Export analysis results to various formats for reporting.
    
    Expects:
    - 'analysis_result': JSON-encoded analysis results
    - 'export_format': Export format ('json', 'html', 'excel')
    
    Returns the exported data with appropriate content type.
    """
    try:
        # Extract parameters
        analysis_result_json = request.POST.get('analysis_result')
        export_format = request.POST.get('export_format', 'json')
        
        if not analysis_result_json:
            return JsonResponse({
                'status': 'error',
                'message': 'analysis_result is required'
            }, status=400)
        
        # Parse analysis result
        try:
            analysis_result = json.loads(analysis_result_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON for analysis result'
            }, status=400)
        
        # Export analysis results
        result = analyzer.export_analysis_results(analysis_result, export_format)
        
        if result['status'] == 'success':
            # Return exported data with appropriate content type
            response = HttpResponse(
                result['data'],
                content_type=result['content_type']
            )
            response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
            return response
        else:
            return JsonResponse(result, status=500)
    
    except Exception as e:
        logger.error(f"Error exporting analysis results: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f"Error exporting analysis results: {str(e)}"
        }, status=500)