from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import os
import tempfile
import requests
from datetime import datetime  # Add this import
import pandas as pd
from src.phase1.test_case_manager.testcase_generator import TestCaseGenerator
import logging
import traceback
from src.phase1.test_case_manager.testcase_refiner import LLMHelper
import numpy as np

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that safely handles NaN, numpy types, etc."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj) if not np.isnan(obj) else ""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        if pd.isna(obj):
            return ""
        if isinstance(obj, (np.bool_)):
            return bool(obj)
        try:
            return super(SafeJSONEncoder, self).default(obj)
        except TypeError:
            return str(obj)  # Convert any other unserializable objects to strings
        

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
@csrf_exempt
def test_generation_refine(request):
    """
    Analyze and refine a test case from database or uploaded file.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Starting test_generation_refine function")
        
        # Check if we have a file upload
        if request.FILES and 'test_case_file' in request.FILES:
            logger.info("Processing uploaded file")
            file = request.FILES['test_case_file']
            logger.info(f"File name: {file.name}")
            
            # Read file content
            file_content = file.read()
            logger.info(f"Read file content, size: {len(file_content)} bytes")
            
            # Initialize LLM helper and process file
            from src.phase1.test_case_manager.testcase_refiner import LLMHelper
            llm_helper = LLMHelper()
            
            # Delegate processing to LLM helper
            result = llm_helper.process_test_case_file(file_content, file.name)
            
            # Return the result directly
            return JsonResponse(result, encoder=SafeJSONEncoder)
        else:
            logger.warning("No file in request")
            return JsonResponse({"status": "error", "message": "No file provided"}, status=400)
    
    except Exception as e:
        import traceback
        logging.error(f"Error in test_generation_refine: {str(e)}")
        logging.error(traceback.format_exc())
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
@require_POST
def test_generation_from_prompt(request):
    if request.method == 'POST':
        try:
            # Parse request data
            request_data = json.loads(request.body)
            
            if not request_data or 'prompt' not in request_data:
                return JsonResponse({
                    "status": "error",
                    "error": {
                        "type": "ValidationError",
                        "title": "Missing Information",
                        "message": "Please provide a prompt or keywords for test case generation.",
                        "details": None,
                        "user_action": "Please enter a prompt describing what you want to test."
                    }
                }, status=400)
            
            prompt = request_data['prompt']
            
            # Log the received prompt
            logger.info(f"Generating test case from prompt: {prompt[:100]}...")
            
            # Generate test case
            generator = TestCaseGenerator()
            test_case_df = generator.generate_test_case_from_prompt(prompt)
            
            # Convert DataFrame to dict for JSON response
            test_case_data = test_case_df.to_dict('records')
            
            logger.info(f"Successfully generated test case with {len(test_case_data)} steps")
            
            # Create a standardized scenario object from the prompt
            scenario = {
                "id": f"PROMPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "name": prompt[:50] + ("..." if len(prompt) > 50 else ""),
                "description": prompt,
                "subject": "Test Generation",
                "type": "Functional"
            }
            
            # Return success response with consistent structure
            # IMPORTANT: Keep this format consistent with what the frontend expects
            response_data = {
                "status": "success",
                "message": "Test case generated successfully from prompt",
                "data": {
                    "test_case": test_case_data,
                    "scenario": scenario
                }
            }
            
            # Log the response structure (not the full content)
            logger.info(f"Returning response with structure: {list(response_data.keys())}")
            logger.info(f"Data keys: {list(response_data['data'].keys())}")
            logger.info(f"Test case contains {len(test_case_data)} items")
            
            return JsonResponse(response_data)
            
        except Exception as e:
            # Log the error
            logger.exception(f"Failed to generate test case from prompt: {str(e)}")
            
            # Create user-friendly error response
            error_type = type(e).__name__
            
            # Set default error information
            error_title = "Test Case Generation Failed"
            error_message = "There was an error generating the test case."
            error_details = str(e)
            user_action = "Please try again later or contact support."
            
            # Customize based on error type
            if "LLMConnectionError" in error_type or "API_KEY" in str(e):
                error_title = "LLM Service Connection Failed"
                error_message = "Unable to connect to the AI service for test case generation."
                error_details = "The system could not connect to the required LLM service."
                user_action = "Please ensure the API_KEY environment variable is properly configured. Contact your system administrator."
            
            # Return structured error response
            return JsonResponse({
                "status": "error",
                "error": {
                    "type": error_type,
                    "title": error_title,
                    "message": error_message,
                    "details": error_details,
                    "user_action": user_action
                }
            }, status=500)  # Using 500 instead of 400 for server errors
    
    # If not POST request
    return JsonResponse({
        "status": "error",
        "message": "Method not allowed"
    }, status=405)


@require_POST
def test_generation_export_excel(request):
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



@csrf_exempt
def test_llm_diagnostics(request):
    """
    Diagnostic endpoint to test LLM connection with detailed logging
    """
    logger = logging.getLogger(__name__)
    
    # Default options
    test_options = {
        "test_environment": True,
        "test_initialization": True,
        "test_direct_api": True,
        "test_helper_methods": True
    }
    
    test_prompt = "Generate a simple test case for login"
    test_service = None  # Default to configured service
    
    # Process request body if POST
    if request.method == 'POST':
        try:
            body_data = json.loads(request.body)
            if 'test_options' in body_data:
                test_options.update(body_data['test_options'])
            if 'prompt' in body_data:
                test_prompt = body_data['prompt']
            if 'service' in body_data:
                test_service = body_data['service']
        except json.JSONDecodeError:
            pass  # Use defaults if JSON parsing fails
    
    results = {
        "environment_variables": {},
        "connection_test": {},
        "detailed_error": None
    }
    
    try:
        # The rest of the diagnostics code as before, but using the options
        # to selectively run tests based on test_options...
        
        return JsonResponse(results)
    except Exception as e:
        logger.error(f"Overall diagnostics error: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }, status=500)
    

############################################ DB connectivity check ###########################################################
'''
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def check_database_content(request):
    """Diagnostic endpoint to check database content"""
    try:
        # Import the MetadataManager class
        from src.phase1.test_case_manager.metadata_manager import MetadataManager
        
        # Create an instance of MetadataManager
        metadata_manager = MetadataManager()
        
        # Now call the instance method with criteria
        test_cases = metadata_manager.search_test_cases({})  # Empty criteria to get all
        
        # Return the count and basic info about test cases
        return JsonResponse({
            "status": "success",
            "test_case_count": len(test_cases),
            "test_cases": [
                {
                    "id": tc.get("TEST_CASE_ID"),
                    "name": tc.get("TEST_CASE", ""),
                    "owner": tc.get("OWNER", ""),
                    "has_file": metadata_manager.file_exists_for_test_case(tc.get("TEST_CASE_ID", ""))
                }
                for tc in test_cases[:10]  # Limit to 10 for display
            ]
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }, status=500)        
 '''
############################################## Test LLM connection ############################################################################################################    



def test_llm_connection(request):
    """
    Simple endpoint to test the connection to the GROQ LLM API.
    This helps diagnose if there are issues with the API key or connectivity.
    """
    try:
        # Initialize the LLM helper
        llm_helper = LLMHelper()
        
        # Create a very simple test prompt
        test_prompt = "Generate a single step test case for logging into a system"
        
        # Log that we're attempting to call the API
        logger.info("Attempting to connect to LLM API with test prompt")
        
        # Call the API with a simple prompt
        result = llm_helper.generate_test_case_structure(test_prompt)
        
        # If we get here, the API call was successful
        return JsonResponse({
            "status": "success",
            "message": "Successfully connected to LLM API",
            "api_used": "watsonx" if llm_helper.use_watsonx else "groq",
            "model_used": llm_helper.watsonx_model if llm_helper.use_watsonx else llm_helper.groq_model,
            "sample_response": result
        })
        
    except Exception as e:
        # Log the error details
        logger.error(f"LLM connection test failed: {str(e)}")
        
        # Return detailed error information
        return JsonResponse({
            "status": "error",
            "message": f"Failed to connect to LLM API: {str(e)}",
            "error_type": type(e).__name__,
            "error_details": str(e)
        }, status=500)


@require_POST
@csrf_exempt
def apply_test_case_refinements(request):
    """
    Apply refinements to a test case and store the updated version in the database.
    Specifically updates TEST STEP DESCRIPTION, DATA, and EXPECTED RESULT fields
    for steps identified by TEST CASE NUMBER and STEP NO from the original test case.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        
        # Validate required fields
        if not data or 'test_case_id' not in data or 'refinements' not in data:
            return JsonResponse({
                "status": "error", 
                "message": "Missing required parameters: test_case_id and refinements"
            }, status=400)
        
        # Extract fields
        test_case_id = data['test_case_id']
        refinements = data['refinements']
        changed_by = data.get('changed_by', 'Web UI User')
        
        logger.info(f"Applying refinements to test case: {test_case_id}")
        
        # Initialize the MetadataManager
        from src.phase1.test_case_manager.metadata_manager import MetadataManager
        metadata_manager = MetadataManager()
        
        # Check if test case exists
        existing_metadata = metadata_manager.get_test_case_metadata(test_case_id)
        if not existing_metadata:
            logger.error(f"Test case {test_case_id} not found")
            return JsonResponse({
                "status": "error",
                "message": f"Test case {test_case_id} not found"
            }, status=404)
        
        # Log existing steps for reference
        existing_steps = existing_metadata.get('STEPS', [])
        if existing_steps:
            step_numbers = [s.get('STEP_NO') for s in existing_steps]
            logger.info(f"Found existing steps with numbers: {step_numbers}")
        
        # Get database connection
        conn = metadata_manager._get_db_connection()
        cursor = conn.cursor()
        
        # Track updates
        updates_applied = 0
        
        try:
            # Process each step refinement
            step_refinements = refinements.get('step_refinements', [])
            logger.info(f"Processing {len(step_refinements)} step refinements")
            
            for step_refinement in step_refinements:
                step_no = step_refinement.get('step_no')
                updates = step_refinement.get('updates', {})
                
                if not step_no or not updates:
                    logger.warning(f"Skipping invalid refinement: missing step_no or updates")
                    continue
                
                logger.info(f"Processing updates for step {step_no}")
                
                # Focus only on the specific fields we want to update
                field_updates = {}
                for field in ['TEST STEP DESCRIPTION', 'DATA', 'EXPECTED RESULT']:
                    if field in updates:
                        field_updates[field.lower()] = updates[field]
                
                if not field_updates:
                    logger.warning(f"No relevant fields to update for step {step_no}")
                    continue
                
                # Build SQL update statement with only the fields we want to update
                set_clauses = []
                params = []
                
                for field, value in field_updates.items():
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
                
                # Add modified_date
                set_clauses.append("modified_date = NOW()")
                
                # Add WHERE clause parameters
                params.append(test_case_id)
                params.append(step_no)
                
                # Execute the update
                update_sql = f"""
                UPDATE test_cases
                SET {', '.join(set_clauses)}
                WHERE test_case_number = %s AND step_no = %s
                """
                
                cursor.execute(update_sql, params)
                rows_affected = cursor.rowcount
                
                logger.info(f"Updated {rows_affected} rows for step {step_no}")
                
                if rows_affected > 0:
                    updates_applied += rows_affected
            
            # If we made changes, commit them
            if updates_applied > 0:
                conn.commit()
                logger.info(f"Committed {updates_applied} updates to database")
            else:
                logger.warning("No updates were applied, rolling back transaction")
                conn.rollback()
                
        except Exception as db_error:
            logger.error(f"Database operation error: {str(db_error)}")
            if conn:
                conn.rollback()
            raise db_error
            
        finally:
            # Return connection to pool
            if conn:
                metadata_manager._return_db_connection(conn)
        
        # Return appropriate response
        if updates_applied > 0:
            return JsonResponse({
                "status": "success",
                "message": f"Successfully applied {updates_applied} updates to test case",
                "data": {
                    "test_case_id": test_case_id,
                    "updates_applied": updates_applied,
                    "timestamp": datetime.now().isoformat()
                }
            })
        else:
            return JsonResponse({
                "status": "warning",
                "message": "No updates were applied to the test case",
                "data": {
                    "test_case_id": test_case_id,
                    "updates_applied": 0,
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }, status=500)
    

######################################### Excel parsing check ###################################################################################
''' 
@csrf_exempt
def test_excel_file(request):
    """Test parsing an Excel file and return basic information."""
    try:
        if request.method == 'POST' and request.FILES.get('test_case_file'):
            file = request.FILES['test_case_file']
            
            # Create a temporary file to store the uploaded content
            import tempfile
            import pandas as pd
            
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(file.read())
                temp_path = temp_file.name
                
            # Try to read the Excel file
            try:
                df = pd.read_excel(temp_path, engine='openpyxl')
                
                # Return basic information about the file
                return JsonResponse({
                    'status': 'success',
                    'message': 'Excel file parsed successfully',
                    'rows': len(df),
                    'columns': list(df.columns),
                    'sample_data': df.head(2).to_dict('records')
                })
            except Exception as excel_error:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to parse Excel file: {str(excel_error)}',
                    'error_type': type(excel_error).__name__
                }, status=400)
            finally:
                # Clean up temporary file
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No file provided'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error processing request: {str(e)}'
        }, status=500)


########################################## data processing test #################################################################################################
@csrf_exempt
def test_data_processing(request):
    """Test how Excel data is processed and prepared for the LLM."""
    try:
        if request.method == 'POST' and request.FILES.get('test_case_file'):
            file = request.FILES['test_case_file']
            
            # Create a temporary file
            import tempfile
            import pandas as pd
            from src.phase1.test_case_manager.testcase_refiner import TestCaseRefiner
            
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(file.read())
                temp_path = temp_file.name
            
            try:
                # Parse the Excel file using the actual refiner
                refiner = TestCaseRefiner()
                test_case_df = refiner.load_test_case(temp_path)
                
                # Get the data that would be used for analysis
                # This is where we're testing the data preparation logic
                test_case_data = {
                    "format_version": "1.0",
                    "test_case_info": {
                        "test_case_number": test_case_df.iloc[0].get("TEST CASE NUMBER", "Unknown"),
                        "test_case_name": test_case_df.iloc[0].get("TEST CASE", "Unknown"),
                        "subject": test_case_df.iloc[0].get("SUBJECT", "Unknown"),
                        "type": test_case_df.iloc[0].get("TYPE", "Unknown"),
                        "total_steps": len(test_case_df)
                    },
                    "steps": []
                }
                
                # Process each row to create the steps data
                for _, row in test_case_df.iterrows():
                    step = {
                        "step_no": row.get("STEP NO", ""),
                        "description": row.get("TEST STEP DESCRIPTION", ""),
                        "data": row.get("DATA", ""),
                        "expected_result": row.get("EXPECTED RESULT", ""),
                        "values": row.get("VALUES", ""),
                        "reference_values": row.get("REFERENCE VALUES", "")
                    }
                    test_case_data["steps"].append(step)
                
                # Create the prompt that would be sent to the LLM
                # This simulates what would happen in the actual code
                prompt = f"""
                Analyze this test case and suggest improvements:
                
                {test_case_data}
                
                Provide detailed suggestions for improving:
                1. Test step descriptions
                2. Expected results
                3. Test data
                4. Overall test structure
                """
                
                # Return all the diagnostic information
                return JsonResponse({
                    "status": "success",
                    "message": "Data processing test completed",
                    "original_test_case": test_case_df.to_dict('records'),
                    "processed_data": test_case_data,
                    "prompt_for_llm": prompt
                })
                
            except Exception as process_error:
                return JsonResponse({
                    "status": "error",
                    "message": f"Data processing error: {str(process_error)}",
                    "error_type": type(process_error).__name__,
                    "error_details": str(process_error)
                }, status=400)
            finally:
                # Clean up temporary file
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            return JsonResponse({
                "status": "error",
                "message": "No file provided or incorrect request method"
            }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Error processing request: {str(e)}"
        }, status=500)
  

###################################### LLM Response Processing ###################################################
@csrf_exempt
def llm_response_processing(request):
    """Test the LLM integration with a simple prompt."""
    try:
        from src.phase1.test_case_manager.llm_helper import LLMHelper
        
        # Initialize the LLM helper
        llm_helper = LLMHelper()
        
        # Create a simple test prompt
        test_prompt = """
        Analyze this test case and suggest improvements:
        
        {
          "test_case_info": {
            "test_case_number": "TC19",
            "test_case_name": "Revenue Recognition report",
            "subject": "Revenue Recognition",
            "type": "MANUAL",
            "total_steps": 1
          },
          "steps": [
            {
              "step_no": 7,
              "description": "Validate all columns in the report",
              "data": "Company code, Contract number, SOW number",
              "expected_result": "All values are correct",
              "values": "",
              "reference_values": ""
            }
          ]
        }
        
        Provide detailed suggestions for improving:
        1. Test step descriptions
        2. Expected results
        3. Test data
        4. Overall test structure
        """
        
        # Call the LLM
        llm_response = llm_helper.generate_test_case_structure(test_prompt)
        
        # Return the response
        return JsonResponse({
            "status": "success",
            "message": "LLM integration test completed",
            "llm_response": llm_response
        })
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Error testing LLM integration: {str(e)}",
            "error_type": type(e).__name__,
            "error_details": str(e)
        }, status=500)

'''

##################################### test LLM data and UI display #####################################################################
# In src/phase1/test_case_manager/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

# Import necessary components
from src.phase1.test_case_manager.testcase_refiner import LLMHelper


@csrf_exempt
def test_data_processing(request):
    """
    Process test data using LLM to generate test steps.
    
    This endpoint handles POST requests with either:
    - A file upload (Excel/XLSX)
    - JSON data with test prompts
    
    Returns:
        JsonResponse with status and LLM-generated test case data
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"}, status=405)
    
    try:
        # Initialize components
        llm_helper = LLMHelper()
        
        if 'file' in request.FILES:
            # Handle file upload
            uploaded_file = request.FILES['file']
            
            # Process the file
            # For now, we'll use a simple prompt based on the filename
            file_name = uploaded_file.name
            prompt = f"Generate test steps for {file_name}"
            
            # Get LLM response
            llm_response = llm_helper.generate_test_case_structure(prompt)
            
            return JsonResponse({
                "status": "success",
                "message": "LLM integration test completed",
                "llm_response": llm_response
            })
            
        elif request.content_type == 'application/json':
            # Handle JSON request
            try:
                data = json.loads(request.body)
                prompt = data.get('prompt', '')
                
                if not prompt:
                    return JsonResponse({
                        "status": "error", 
                        "message": "Missing prompt in request"
                    }, status=400)
                
                # Get LLM response
                llm_response = llm_helper.generate_test_case_structure(prompt)
                
                return JsonResponse({
                    "status": "success",
                    "message": "LLM integration test completed",
                    "llm_response": llm_response
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    "status": "error", 
                    "message": "Invalid JSON body"
                }, status=400)
        else:
            return JsonResponse({
                "status": "error", 
                "message": "No file or JSON data found in request"
            }, status=400)
            
    except Exception as e:
        logger.exception("Error processing test data")
        return JsonResponse({
            "status": "error",
            "message": f"Error processing test data: {str(e)}"
        }, status=500)