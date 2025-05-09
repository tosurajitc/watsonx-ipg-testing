# src/phase1/test_case_manager/llm_helper.py

import os
import logging
import json
from typing import Dict, List, Any, Optional
import requests
import uuid
from io import BytesIO
import pandas as pd
from datetime import datetime
import traceback
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
# Import from src.common
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    LLMConnectionError,
    LLMResponseError
)

logger = logging.getLogger(__name__)

class LLMHelper:
    """
    Helper class to interact with LLM services for test case generation.
    """
    
    def __init__(self, api_key: str = None, model: str = "llama"):
        """
        Initialize the LLM helper.
        
        Args:
            api_key (str, optional): API key for LLM service. If None, uses env variable.
            model (str, optional): Model to use. Default is llama.
        """
        # Determine which API to use - GROQ by default, watsonx in production
        self.use_watsonx = os.environ.get("USE_WATSONX", "False").lower() in ["true", "1", "yes"]
        
        # GROQ configuration (default)
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.groq_api_base = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1")
        self.groq_model = os.environ.get("GROQ_MODEL", "llama3-70b-8192")
        
        # watsonx.ai configuration
        self.watsonx_api_key = os.environ.get("WATSONX_API_KEY")
        self.watsonx_url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.watsonx_model = os.environ.get("WATSONX_MODEL", "ibm/granite-13b-chat-v2")
        self.watsonx_project_id = os.environ.get("WATSONX_PROJECT_ID")
        self.watsonx_space_id = os.environ.get("WATSONX_SPACE_ID")
        
        # Legacy compatibility
        self.api_key = api_key or (self.watsonx_api_key if self.use_watsonx else self.groq_api_key)
        self.model = model
        
        if self.use_watsonx and not self.watsonx_api_key:
            logger.warning("No API key provided for watsonx.ai. LLM integration will not function.")
        elif not self.use_watsonx and not self.groq_api_key:
            logger.warning("No API key provided for GROQ. LLM integration will not function.")
    
    def generate_test_case_structure(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a test case structure from a simple prompt.
        
        Args:
            prompt (str): Simple prompt like "Generate login test cases for Admin user"
            
        Returns:
            Dict[str, Any]: Structured test case data
            
        Raises:
            LLMConnectionError: If connection to LLM fails
            LLMResponseError: If LLM response cannot be parsed
        """
        try:
            # Create an enhanced prompt
            enhanced_prompt = self._create_enhanced_prompt(prompt)
            
            # Call the appropriate LLM API based on configuration
            if self.use_watsonx:
                response = self._call_watsonx_api(enhanced_prompt)
            else:
                response = self._call_groq_api(enhanced_prompt)
            
            # Parse and validate the response
            test_case_data = self._parse_llm_response(response, prompt)
            
            return test_case_data
        
        except requests.RequestException as e:
            logger.error(f"Failed to connect to LLM API: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to LLM API: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error generating test case structure: {str(e)}")
            raise  # Re-raise the exception
    
    def _create_enhanced_prompt(self, user_prompt: str) -> str:
        """
        Create an enhanced prompt that instructs the LLM to generate a structured test case.
        """
        return f"""
        Generate a **comprehensive and detailed software test case** based on the user request: "{user_prompt}"

        🔐 **CRITICAL REQUIREMENTS**:
        1. Each test step **must include**:
        - "TEST STEP DESCRIPTION": A clear, two-sentence minimum description of the action to be performed. Use the existing data as reference and enhance it without losing any information.
        - "EXPECTED RESULT": A specific, observable, and verifiable outcome. It must directly correspond to the action in the TEST STEP DESCRIPTION.

        2. **Do not leave the 'EXPECTED RESULT' field empty or vague** — it should clearly define what indicates success for each step.

        📋 **Expected Output Format** (JSON):
        {{
            "SUBJECT": "Functional area/module under test (reuse the same value from input data)",
            "TEST CASE": "Title or purpose of the test case (reuse the same as provided)",
            "TEST CASE NUMBER": "Preserve the original test case ID",
            "steps": [
                {{
                    "STEP NO": 1,
                    "TEST STEP DESCRIPTION": "Enhanced and clear action description. Start from the original, and enrich it with technical detail or clarification, ensuring at least two meaningful sentences.",
                    "DATA": "Input test data required for execution (if applicable)",
                    "REFERENCE VALUES": "Any reference values tied to this step (optional, include if available)",
                    "VALUES": "Expected values linked to the step (optional, include if available)",
                    "EXPECTED RESULT": "Precisely what should be observed after executing the step. This must validate success/failure clearly.",
                    "TRANS CODE": "Use the same transaction code from the input data",
                    "TEST USER ID/ROLE": "User ID or role performing the step (retain original)",
                    "STATUS": "Not Executed"
                }},
                // Continue for subsequent steps incrementing STEP NO
            ],
            "TYPE": "Type of test (Functional, Performance, Regression, etc. — use existing value)"
        }}

        🔍 **Guidelines for Step Generation**:
        - The **TEST STEP DESCRIPTION** must be clear, action-oriented, and aligned with the original intent, but refined for completeness.
        - The **EXPECTED RESULT** must be tightly coupled with the step description, specifying **what outcome qualifies as a success**.
        - Populate **DATA**, **REFERENCE VALUES**, and **VALUES** based on available inputs. Leave blank only if information is genuinely unavailable.
        - Ensure consistency, completeness, and traceability of each step.
        - Provide a refined and complete test case for: "{user_prompt}"

        ⚠️ **Mandatory**: Every test step **must** include a meaningful TEST STEP DESCRIPTION and a non-generic, verifiable EXPECTED RESULT.
        """

# Add this at the beginning of the testcase_refiner.py file with the other imports


    # Then replace the entire _call_groq_api function with this improved version:
    def _call_groq_api(self, prompt: str) -> str:
        """
        Call the GROQ API with the prompt, using a session with retries and extended timeout.
        """
        if not self.groq_api_key:
            raise LLMConnectionError("No API key available for GROQ. Please configure GROQ_API_KEY environment variable.")
        
        # Create a session with retry capability
        session = requests.Session()
        
        # Configure retry strategy with backoff
        retry_strategy = Retry(
            total=3,               # Try up to 3 times in total
            backoff_factor=2,      # Wait 2, 4, 8 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["POST"]
        )
        
        # Mount the adapter to the session
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "You are a test case generation assistant. Generate detailed test cases in JSON format based on user prompts."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        try:
            # Use the session with a very generous timeout
            response = session.post(
                f"{self.groq_api_base}/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=120  # 2 minutes timeout
            )
            
            # Log the status code for debugging
            logger.info(f"GROQ API response status code: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return content
            else:
                raise LLMConnectionError("GROQ API response did not contain expected 'choices' field")
                
        except Exception as e:
            # Log the full exception for debugging
            logger.error(f"GROQ API call failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise LLMConnectionError(f"Failed to connect to GROQ API: {str(e)}")
    
    def _call_watsonx_api(self, prompt: str) -> str:
        """
        Call the watsonx.ai API with the prompt.
        
        Args:
            prompt (str): Enhanced prompt for the LLM
            
        Returns:
            str: Response from the LLM
            
        Raises:
            LLMConnectionError: If API call fails
        """
        if not self.watsonx_api_key:
            raise LLMConnectionError("No API key available for watsonx.ai. Please configure WATSONX_API_KEY environment variable.")
        
        headers = {
            "Authorization": f"Bearer {self.watsonx_api_key}",
            "Content-Type": "application/json"
        }
        
        generation_url = f"{self.watsonx_url}/ml/v1/generation"
        
        payload = {
            "model_id": self.watsonx_model,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 2000,
                "min_new_tokens": 100,
                "temperature": 0.2,  # Lower temperature for more deterministic outputs
                "stop_sequences": ["\n\n\n"]
            }
        }
        
        # Add project_id and space_id only if they exist
        if self.watsonx_project_id:
            payload["project_id"] = self.watsonx_project_id
            
        if self.watsonx_space_id:
            payload["space_id"] = self.watsonx_space_id
        
        response = requests.post(generation_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if "results" in result and len(result["results"]) > 0:
            content = result["results"][0].get("generated_text", "")
            return content
        else:
            raise LLMConnectionError("watsonx.ai API response did not contain expected 'results' field")
    
    def _parse_llm_response(self, response: str, original_prompt: str) -> Dict[str, Any]:
        """
        Parse and validate the LLM response.
        
        Args:
            response (str): LLM response text
            original_prompt (str): Original user prompt
            
        Returns:
            Dict[str, Any]: Parsed test case data
            
        Raises:
            LLMResponseError: If parsing fails
        """
        try:
            # First try direct JSON loading (for GROQ with json_object mode)
            try:
                test_case_data = json.loads(response)
            except json.JSONDecodeError:
                # Extract JSON from response text (in case the LLM added extra text)
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    raise LLMResponseError("No valid JSON found in LLM response. The model failed to generate a structured test case.")
                
                json_str = response[start_idx:end_idx]
                test_case_data = json.loads(json_str)
            
            # Validate the structure
            required_fields = ["SUBJECT", "TEST CASE", "steps", "TYPE"]
            missing_fields = [field for field in required_fields if field not in test_case_data]
            if missing_fields:
                raise LLMResponseError(f"LLM response missing required fields: {', '.join(missing_fields)}. Cannot generate a valid test case without these fields.")
            
            if not isinstance(test_case_data.get("steps"), list) or not test_case_data["steps"]:
                raise LLMResponseError("Steps field must be a non-empty list. The LLM failed to generate any test steps.")
            
            # Add TEST CASE NUMBER if missing
            if "TEST CASE NUMBER" not in test_case_data:
                # Generate a TC-XXXXX style ID
                test_case_data["TEST CASE NUMBER"] = f"TC-{uuid.uuid4().hex[:5].upper()}"
            
            # Validate each step
            step_required_fields = [
                "STEP NO", "TEST STEP DESCRIPTION", "DATA", 
                "EXPECTED RESULT", "TEST USER ID/ROLE", "STATUS"
            ]
            
            for i, step in enumerate(test_case_data["steps"]):
                missing_step_fields = [field for field in step_required_fields if field not in step]
                
                # Only auto-add some fields if they're missing, for others we'll raise an error
                if "STEP NO" not in step:
                    step["STEP NO"] = i + 1
                
                if "STATUS" not in step:
                    step["STATUS"] = "Not Executed"
                
                # Add empty strings for optional fields
                for field in ["REFERENCE VALUES", "VALUES", "TRANS CODE"]:
                    if field not in step:
                        step[field] = ""
                
                # Remove these from the missing fields list
                missing_step_fields = [f for f in missing_step_fields if f not in ["STEP NO", "STATUS", "REFERENCE VALUES", "VALUES", "TRANS CODE"]]
                
                if missing_step_fields:
                    raise LLMResponseError(f"Step {i+1} is missing required fields: {', '.join(missing_step_fields)}. Cannot generate a valid test case without these fields.")
            
            return test_case_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            raise LLMResponseError(f"Failed to parse LLM response as JSON: {str(e)}. The model did not generate valid JSON for test case creation.")
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise LLMResponseError(f"Error parsing LLM response: {str(e)}. Unable to generate a test case from the model output.")
        
        
    def process_test_case_file(self, file_content, file_name=None):
        """
        Process a test case file and generate refinement suggestions.
        
        Args:
            file_content (bytes): The content of the test case file
            file_name (str, optional): The name of the file
            
        Returns:
            dict: A dictionary with refinement suggestions and analysis results
        """
        try:
            # Import needed libraries
            from io import BytesIO
            import pandas as pd
            import numpy as np
            from datetime import datetime
            import uuid
            import json
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info("Starting test case file processing")
            
            # Create BytesIO and read DataFrame
            file_io = BytesIO(file_content)
            
            # Read Excel with explicit NA values to catch #N/A and other Excel error values
            test_case_df = pd.read_excel(
                file_io, 
                engine='openpyxl',
                na_values=['#N/A', '#N/A N/A', '#NA', '-NaN', 'NaN', 'NA', 'NULL', 'null', 'NAN', 'nan', '-nan', 'None', 'none'],
                keep_default_na=True
            )
            logger.info(f"Excel file read successfully with shape: {test_case_df.shape}")
            
            # COMPREHENSIVE NaN HANDLING: Replace all NaN, None, NA values with empty strings
            test_case_df = test_case_df.replace({np.nan: "", None: "", "NaN": "", "NULL": "", "null": ""})
            test_case_df = test_case_df.fillna("")  # Double insurance against NaN values
            logger.info("NaN values replaced with empty strings")
            
            # Extract test case ID
            test_case_id = None
            if "TEST CASE NUMBER" in test_case_df.columns and not test_case_df["TEST CASE NUMBER"].iloc[0] == "":
                test_case_id = str(test_case_df["TEST CASE NUMBER"].iloc[0])
            else:
                test_case_id = f"TC-{uuid.uuid4().hex[:8].upper()}"
            logger.info(f"Test case ID: {test_case_id}")
            
            # Extract data from first row of DataFrame - with NaN protection
            test_case_name = "Untitled Test Case"
            subject = "Unknown"
            test_user_role = "Unassigned"
            test_type = "Functional"
            
            # Safe extraction with defaults
            if len(test_case_df) > 0:
                row = test_case_df.iloc[0]
                test_case_name = str(row.get("TEST CASE", "")) or "Untitled Test Case"
                subject = str(row.get("SUBJECT", "")) or "Unknown"
                test_user_role = str(row.get("TEST USER ID/ROLE", "")) or "Unassigned"
                test_type = str(row.get("TYPE", "")) or "Functional"
            
            # Prepare test case data for LLM
            test_case_data = {
                "format_version": "1.0",
                "test_case_info": {
                    "test_case_number": test_case_id,
                    "test_case_name": test_case_name,
                    "subject": subject,
                    "type": test_type,
                    "total_steps": len(test_case_df)
                },
                "steps": []
            }
            
            # Process each row to create the steps data - with NaN protection
            for idx, row in test_case_df.iterrows():
                # Safe string conversion for all values with defaults
                step = {
                    "step_no": str(row.get("STEP NO", "") or idx + 1),
                    "description": str(row.get("TEST STEP DESCRIPTION", "") or ""),
                    "data": str(row.get("DATA", "") or ""),
                    "expected_result": str(row.get("EXPECTED RESULT", "") or ""),
                    "values": str(row.get("VALUES", "") or ""),
                    "reference_values": str(row.get("REFERENCE VALUES", "") or "")
                }
                test_case_data["steps"].append(step)
            
            logger.info(f"Processed {len(test_case_data['steps'])} steps")
            
            # SPECIAL JSON SERIALIZATION TEST - early verification of JSON compatibility
            try:
                # Test JSON serialization before proceeding
                json.dumps(test_case_data)
                logger.info("Test case data successfully serialized to JSON")
            except TypeError as json_error:
                logger.error(f"JSON serialization error detected: {str(json_error)}")
                # Find problematic fields and fix them
                for step in test_case_data["steps"]:
                    for field, value in step.items():
                        if not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                            logger.warning(f"Problematic field detected: {field} = {value} of type {type(value)}")
                            step[field] = str(value)  # Convert to string
                # Try serialization again
                json.dumps(test_case_data)
                logger.info("JSON serialization issues fixed")
            
            # Create prompt for LLM
            prompt = f"""
            You are a test engineering expert. Your task is to refine and enhance the clarity and completeness of 
            software test cases, particularly the fields TEST STEP DESCRIPTION and EXPECTED RESULT.

            Please do not change the meaning or purpose of the test, but improve grammar, technical accuracy, logical sequence, 
            and clarity. Use formal language appropriate for software QA documentation.
                        
            {test_case_data}
            
            """
            
            # Generate LLM response
            try:
                logger.info("Calling LLM to generate response")
                llm_response = self.generate_test_case_structure(prompt)
                logger.info("LLM response generated successfully")
            except Exception as llm_error:
                logger.error(f"LLM error: {str(llm_error)}")
                
                # Create fallback response
                llm_response = None
                logger.info("Using fallback response due to LLM error")
            
            # FINAL JSON SAFETY CHECK - ensure all values are JSON serializable
            safe_original_test_case = []
            for row in test_case_df.to_dict('records'):
                safe_row = {}
                for k, v in row.items():
                    if pd.isna(v) or v is None:
                        safe_row[k] = ""
                    elif isinstance(v, (int, float)) and (np.isnan(v) if isinstance(v, float) else False):
                        safe_row[k] = ""
                    else:
                        safe_row[k] = str(v) if not isinstance(v, (int, float, bool)) else v
                safe_original_test_case.append(safe_row)
            
            # Return the complete analysis
            result = {
                "status": "success",
                "message": "Test case successfully processed and refined",
                "data": {
                    "test_case_id": test_case_id,
                    "test_case_info": {
                        "test_case_number": test_case_id,
                        "test_case_name": test_case_name,
                        "subject": subject,
                        "type": test_type,
                        "total_steps": len(test_case_df)
                    },
                    "original_test_case": safe_original_test_case,
                    "processed_data": test_case_data,
                    "llm_response": llm_response
                }
            }
            
            # Final serialization test
            try:
                json.dumps(result)
                logger.info("Final response successfully serialized to JSON")
            except TypeError as json_error:
                logger.error(f"Final JSON serialization error: {str(json_error)}")
                
                # Fallback to a minimal response
                return {
                    "status": "success",
                    "message": "Test case processed with serialization issues",
                    "data": {
                        "test_case_id": test_case_id,
                        "warning": "Some data was removed due to JSON serialization issues"
                    }
                }
            
            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing test case file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return error response
            return {
                "status": "error",
                "message": f"Error processing test case file: {str(e)}",
                "error_details": traceback.format_exc()
            }   