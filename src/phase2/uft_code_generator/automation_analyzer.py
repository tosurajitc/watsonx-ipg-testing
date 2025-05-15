# src/phase2/uft_code_generator/automation_analyzer.py
# Part 1: Class initialization and test case handling functions

import logging
import re
import json
import os
import uuid
import pandas as pd
from io import BytesIO
from typing import Dict, List, Any, Tuple, Optional, Set
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

class AutomationPotential(Enum):
    """Enumeration for automation potential categories"""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class UFTAutomationAnalyzer:
    """
    Analyzes test cases to determine their potential for UFT automation.
    Provides recommendations, identifies challenges, and suggests UFT approaches.
    Designed to integrate with the UFT Automation tab in code_automation.html.
    """
    
    def __init__(self):
        """Initialize the UFT Automation Analyzer."""
        print("Initializing UFTAutomationAnalyzer...")
        logger.info("Initializing UFTAutomationAnalyzer...")
        
        # Keywords that suggest high automation potential
        self.high_potential_keywords = [
            'click', 'enter', 'type', 'select', 'check', 'uncheck', 'submit',
            'navigate', 'login', 'logout', 'verify text', 'verify field',
            'input', 'dropdown', 'button', 'checkbox', 'radio', 'form',
            'table', 'tab', 'menu', 'link', 'upload', 'download'
        ]
        
        # Keywords that suggest medium automation complexity
        self.medium_complexity_keywords = [
            'drag and drop', 'hover', 'double click', 'right click', 
            'scroll', 'alert', 'popup', 'dialog', 'modal', 'iframe',
            'dynamic content', 'ajax', 'wait for', 'captcha', 'tooltip',
            'datepicker', 'calendar', 'auto-complete', 'suggestion'
        ]
        
        # Keywords that suggest low automation potential or high complexity
        self.low_potential_keywords = [
            'compare images', 'visual check', 'captcha', 'ocr', 'scan',
            'biometric', 'voice', 'video', 'audio', 'fingerprint',
            'manual verification', 'human judgment', 'external device',
            'hardware interaction', 'sensor', 'camera', 'microphone'
        ]
        
        # UFT-specific object types and their automation-friendly score (1-10)
        self.uft_object_types = {
            'WebButton': 9,
            'WebCheckBox': 9,
            'WebEdit': 9,
            'WebElement': 8,
            'WebFile': 7,
            'WebList': 8,
            'WebRadioGroup': 8,
            'WebTable': 7,
            'WebTreeView': 6,
            'Browser': 9,
            'Dialog': 7,
            'WinButton': 8,
            'WinCheckBox': 8,
            'WinComboBox': 8,
            'WinEdit': 8,
            'WinListView': 7,
            'WinMenu': 7,
            'WinObject': 6,
            'WinRadioButton': 8,
            'WinTable': 7,
            'WinTreeView': 6,
            'ActiveX': 5,
            'JavaApplet': 4,
            'JavaObject': 5,
            'SAP': 6,
            'Terminal': 5,
            'CustomObject': 3
        }

        # LLM configuration
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
        
        # Check configuration
        if self.use_watsonx and not self.watsonx_api_key:
            logger.warning("No API key provided for watsonx.ai. LLM integration will not function.")
        elif not self.use_watsonx and not self.groq_api_key:
            logger.warning("No API key provided for GROQ. LLM integration will not function.")
        
        logger.info("UFTAutomationAnalyzer initialization complete")
    
    def get_test_case_from_file(self, file_content: bytes, file_name: str = None) -> Dict[str, Any]:
        """
        Extract test case data from an uploaded file.
        
        Args:
            file_content (bytes): The content of the uploaded file
            file_name (str, optional): The name of the file
            
        Returns:
            Dict[str, Any]: The extracted test case data
        """
        try:
            # Create BytesIO and read DataFrame
            file_io = BytesIO(file_content)
            
            # Check file extension to determine how to read it
            if file_name and file_name.lower().endswith(('.xlsx', '.xls')):
                # Read Excel with pandas
                test_case_df = pd.read_excel(file_io, engine='openpyxl')
                
                # Convert DataFrame to dict structure
                test_case_data = self._convert_df_to_test_case(test_case_df)
                return test_case_data
            else:
                # For non-Excel files, just return sample data for now
                # In a real implementation, this would handle various file formats
                return self._get_sample_login_test_case()
                
        except Exception as e:
            logger.error(f"Error extracting test case from file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Return sample data as fallback
            return self._get_sample_login_test_case()
    
    def _convert_df_to_test_case(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert a pandas DataFrame to test case dictionary structure.
        
        Args:
            df (pd.DataFrame): The DataFrame containing test case data
            
        Returns:
            Dict[str, Any]: Structured test case data
        """
        try:
            # Handle empty dataframe
            if df.empty:
                return self._get_sample_login_test_case()
            
            # Replace NaN values with empty strings
            df = df.fillna('')
            
            # Extract test case info from first row or use defaults
            test_case_name = str(df.get('TEST CASE', ['Untitled Test Case']).iloc[0])
            test_case_number = str(df.get('TEST CASE NUMBER', [f'TC-{uuid.uuid4().hex[:5].upper()}']).iloc[0])
            subject = str(df.get('SUBJECT', ['Unknown']).iloc[0])
            test_type = str(df.get('TYPE', ['Functional']).iloc[0])
            
            # Extract steps
            steps = []
            for idx, row in df.iterrows():
                # Convert row to dict and handle missing columns
                step = {
                    'STEP NO': row.get('STEP NO', idx + 1),
                    'TEST STEP DESCRIPTION': row.get('TEST STEP DESCRIPTION', ''),
                    'EXPECTED RESULT': row.get('EXPECTED RESULT', ''),
                    'DATA': row.get('DATA', ''),
                    'VALUES': row.get('VALUES', ''),
                    'REFERENCE VALUES': row.get('REFERENCE VALUES', ''),
                    'TRANS CODE': row.get('TRANS CODE', ''),
                    'TEST USER ID/ROLE': row.get('TEST USER ID/ROLE', ''),
                    'STATUS': row.get('STATUS', 'Not Executed')
                }
                steps.append(step)
            
            # Create test case structure
            test_case_data = {
                'TEST CASE NUMBER': test_case_number,
                'TEST CASE': test_case_name,
                'SUBJECT': subject,
                'TYPE': test_type,
                'steps': steps
            }
            
            return test_case_data
            
        except Exception as e:
            logger.error(f"Error converting DataFrame to test case: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Return sample data as fallback
            return self._get_sample_login_test_case()
    
    def get_test_case_preview(self, test_case_id: str = None, file_content: bytes = None, file_name: str = None) -> Dict[str, Any]:
        """
        Generate a preview of the test case for display in the UI.
        
        Args:
            test_case_id (str, optional): ID of the test case to retrieve from repository
            file_content (bytes, optional): Content of the uploaded test case file
            file_name (str, optional): Name of the uploaded file
            
        Returns:
            Dict[str, Any]: Test case preview with basic information
        """
        try:
            # Handle repository test case retrieval
            if test_case_id:
                # In a real implementation, this would query the test case repository
                # For simplicity, we'll return a sample test case based on the login example
                test_case_data = self._get_sample_login_test_case()
            
            # Handle file upload  
            elif file_content and file_name:
                # Extract test case data from the file
                test_case_data = self.get_test_case_from_file(file_content, file_name)
            
            else:
                return {
                    'status': 'error',
                    'message': 'Either test_case_id or file_content must be provided'
                }
            
            # Format the test case for preview
            steps = test_case_data.get('steps', [])
            
            preview = {
                'test_case_id': test_case_data.get('TEST CASE NUMBER', test_case_id) or 'TC-1001',
                'test_case_name': test_case_data.get('TEST CASE', 'Login Functionality'),
                'subject': test_case_data.get('SUBJECT', 'Authentication'),
                'type': test_case_data.get('TYPE', 'Functional'),
                'total_steps': len(steps),
                'steps_preview': []
            }
            
            # Preview of each step (limited info)
            for step in steps:
                step_preview = {
                    'step_no': step.get('STEP NO', ''),
                    'action': step.get('TEST STEP DESCRIPTION', ''),
                    'expected_result': step.get('EXPECTED RESULT', ''),
                    'data': step.get('DATA', ''),
                    'selectable': True  # By default all steps are selectable for analysis
                }
                preview['steps_preview'].append(step_preview)
            
            return {
                'status': 'success',
                'preview': preview
            }
            
        except Exception as e:
            logger.error(f"Error generating test case preview: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f"Failed to generate test case preview: {str(e)}"
            }
    
    def _get_sample_login_test_case(self) -> Dict[str, Any]:
        """
        Get a sample login test case for demonstration.
        
        Returns:
            Dict[str, Any]: Sample test case data
        """
        return {
            'TEST CASE NUMBER': 'TC-1001',
            'TEST CASE': 'Login Functionality',
            'SUBJECT': 'Authentication',
            'TYPE': 'Functional',
            'steps': [
                {
                    'STEP NO': 1,
                    'TEST STEP DESCRIPTION': 'Navigate to login page',
                    'EXPECTED RESULT': 'Login page is displayed',
                    'DATA': 'App URL: https://example.com/login',
                    'TEST USER ID/ROLE': 'Standard User',
                    'STATUS': 'Not Executed'
                },
                {
                    'STEP NO': 2,
                    'TEST STEP DESCRIPTION': 'Enter username in the input field',
                    'EXPECTED RESULT': 'Username is entered in the field',
                    'DATA': 'Username: testuser',
                    'TEST USER ID/ROLE': 'Standard User',
                    'STATUS': 'Not Executed'
                },
                {
                    'STEP NO': 3,
                    'TEST STEP DESCRIPTION': 'Enter password in the input field',
                    'EXPECTED RESULT': 'Password is entered in the field, masked with asterisks',
                    'DATA': 'Password: password123',
                    'TEST USER ID/ROLE': 'Standard User',
                    'STATUS': 'Not Executed'
                },
                {
                    'STEP NO': 4,
                    'TEST STEP DESCRIPTION': 'Click the login button',
                    'EXPECTED RESULT': 'System processes the login request',
                    'DATA': '',
                    'TEST USER ID/ROLE': 'Standard User',
                    'STATUS': 'Not Executed'
                },
                {
                    'STEP NO': 5,
                    'TEST STEP DESCRIPTION': 'Verify welcome message is displayed',
                    'EXPECTED RESULT': 'Welcome message appears with user\'s name',
                    'DATA': 'Expected message: Welcome, testuser!',
                    'TEST USER ID/ROLE': 'Standard User',
                    'STATUS': 'Not Executed'
                }
            ]
        }
    
    def _get_current_date(self) -> str:
        """
        Get current date in a formatted string.
        
        Returns:
            str: Formatted date string
        """
        from datetime import datetime
        return datetime.now().strftime('%B %d, %Y')
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message (str): Error message
            
        Returns:
            Dict[str, Any]: Error response
        """
        return {
            'status': 'error',
            'message': message
        }
    


        # Add these new methods for LLM integration
    def _enhance_analysis_with_llm(self, test_case_data: Dict[str, Any], step_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance step analyses with LLM insights if LLM is configured.
        
        Args:
            test_case_data (Dict[str, Any]): Overall test case data
            step_analyses (List[Dict[str, Any]]): Basic analyses to enhance
            
        Returns:
            List[Dict[str, Any]]: Enhanced analyses with LLM insights
        """
        # Check if LLM is available
        if not ((self.use_watsonx and self.watsonx_api_key) or self.groq_api_key):
            logger.info("No LLM API keys configured. Using only rule-based analysis.")
            return step_analyses
        
        enhanced_analyses = []
        
        for i, analysis in enumerate(step_analyses):
            # Get the corresponding step from the test case data
            step_no = analysis.get('step_no')
            matching_steps = [s for s in test_case_data.get('steps', []) if str(s.get('STEP NO', '')) == str(step_no)]
            
            if matching_steps:
                step = matching_steps[0]
                # Get LLM insights for this step
                llm_insights = self._call_llm_for_analysis(test_case_data, step)
                
                # Enhance the analysis with LLM insights
                if llm_insights:
                    # Prefer LLM's assessment for certain fields if available
                    if 'automation_potential' in llm_insights:
                        analysis['automation_potential'] = llm_insights['automation_potential']
                    
                    if 'difficulty' in llm_insights:
                        analysis['difficulty'] = llm_insights['difficulty']
                    
                    if 'challenges' in llm_insights and llm_insights['challenges']:
                        analysis['challenges'] = llm_insights['challenges']
                    
                    if 'notes' in llm_insights and llm_insights['notes']:
                        analysis['notes'] = llm_insights['notes']
                    
                    # Add new LLM-specific fields
                    analysis['llm_enhanced'] = True
                    if 'best_practices' in llm_insights:
                        analysis['best_practices'] = llm_insights['best_practices']
                    
                    if 'uft_objects' in llm_insights:
                        analysis['identified_objects'] = llm_insights['uft_objects']
            
            enhanced_analyses.append(analysis)
        
        return enhanced_analyses

    def _call_llm_for_analysis(self, test_case_data: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to analyze a single test step for automation potential.
        
        Args:
            test_case_data (Dict[str, Any]): Overall test case data
            step (Dict[str, Any]): The individual step to analyze
            
        Returns:
            Dict[str, Any]: LLM-enhanced analysis with advanced insights
        """
        try:
            # Create prompt for LLM analysis
            prompt = self._create_llm_prompt(test_case_data, step)
            
            # Call appropriate LLM based on configuration
            if self.use_watsonx and self.watsonx_api_key:
                llm_response = self._call_watsonx_api(prompt)
            elif self.groq_api_key:
                llm_response = self._call_groq_api(prompt)
            else:
                logger.warning("No LLM API keys configured. Falling back to rule-based analysis.")
                return {}
            
            # Parse LLM response
            return self._parse_llm_response(llm_response)
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
        


    def _create_llm_prompt(self, test_case_data: Dict[str, Any], step: Dict[str, Any]) -> str:
        """
        Create a prompt for LLM analysis.
        
        Args:
            test_case_data (Dict[str, Any]): Overall test case data
            step (Dict[str, Any]): The test step to analyze
            
        Returns:
            str: Formatted prompt for LLM
        """
        # Check for special analysis types
        analysis_type = step.get('ANALYSIS_TYPE', '')
        
        # Complexity breakdown analysis
        if analysis_type == 'complexity_breakdown':
            steps_text = step.get('DATA', '')
            return f"""
            Analyze the complexity breakdown of the following test steps for UFT (Unified Functional Testing) automation:

            TEST CASE: {test_case_data.get('TEST CASE', 'Complexity Analysis')}
            
            STEPS:
            {steps_text}
            
            Please provide a complexity assessment for each of the following categories:
            1. UI Interaction - complexity of the UI elements and interactions
            2. Data Handling - complexity of data input, validation, and processing
            3. Verification Points - complexity of outcome validation and assertion
            4. Technical Challenges - complexity of technical implementation challenges
            
            Your response MUST include all four categories.
            
            For each category, provide:
            - A complexity score (0-100) where 0 is simplest and 100 is most complex
            - A complexity level ("Low", "Medium", or "High")
            - A badge_class value for UI display ("bg-success" for Low, "bg-warning" for Medium, "bg-danger" for High)
            
            Return a JSON response with the following structure:
            {{
            "complexity_breakdown": {{
                "UI Interaction": {{
                "complexity": 30,
                "badge": "Low",
                "badge_class": "bg-success"
                }},
                "Data Handling": {{
                "complexity": 60,
                "badge": "Medium",
                "badge_class": "bg-warning"
                }},
                "Verification Points": {{
                "complexity": 80,
                "badge": "High",
                "badge_class": "bg-danger"
                }},
                "Technical Challenges": {{
                "complexity": 45,
                "badge": "Medium",
                "badge_class": "bg-warning"
                }}
            }}
            }}
            
            It is critical that you follow this exact JSON structure including the outer "complexity_breakdown" field.
            """
        
        # UFT recommendations analysis
        elif analysis_type == 'recommendations':
            return f"""
            Generate recommendations for UFT (Unified Functional Testing) libraries and approaches for the following test case:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide a list of up to 5 specific recommendations for implementing this test case in UFT.
            These should include suggested add-ins, libraries, techniques, or best practices.
            
            Format your response as a JSON object with a "recommendations" field containing the list:
            
            {{
            "recommendations": [
                "Recommendation 1",
                "Recommendation 2",
                "Recommendation 3",
                "Recommendation 4",
                "Recommendation 5"
            ]
            }}
            """
        
        # Challenges and approaches analysis
        elif analysis_type == 'challenges_approaches':
            return f"""
            Identify the key challenges and suggested approaches for automating the following test case with UFT:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide:
            1. A list of specific challenges that might make this test case difficult to automate
            2. A corresponding list of suggested approaches to address each challenge
            
            Format your response as a JSON object with "challenges" and "approaches" fields:
            
            {{
            "challenges": [
                "Challenge 1",
                "Challenge 2",
                "Challenge 3"
            ],
            "approaches": [
                "Approach 1",
                "Approach 2",
                "Approach 3"
            ]
            }}
            
            Note: The lists should have the same length, with each approach corresponding to the challenge at the same index.
            """
        
        # UFT code generation
        elif analysis_type == 'uft_code':
            return f"""
            Generate a UFT (Unified Functional Testing) VBScript code sample for the following test case:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide a complete UFT VBScript code sample that implements this test case.
            The code should:
            1. Include proper header documentation
            2. Set up the UFT environment
            3. Implement each step with appropriate object recognition
            4. Include error handling
            5. Report results
            
            Format your response as a JSON object with a "uft_code" field containing the VBScript code:
            
            {{
            "uft_code": "' UFT Script\\nOption Explicit\\n..."
            }}
            """
        
        # Approach recommendation
        elif analysis_type == 'approach_recommendation':
            return f"""
            Generate an overall approach recommendation for implementing the following test case in UFT:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            AVERAGE AUTOMATION SCORE: {step.get('DATA', '')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide a detailed paragraph explaining the recommended approach for automating this test case with UFT.
            Include information about the test case's suitability for automation and any specific recommendations.
            
            Format your response as a JSON object with an "approach_recommendation" field containing your text:
            
            {{
            "approach_recommendation": "Your detailed recommendation text here..."
            }}
            """
        
        # Libraries list
        elif analysis_type == 'libraries_list':
            return f"""
            Generate a list of recommended UFT libraries and add-ins for the following test case:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide a list of UFT libraries, add-ins, and extensions that would be helpful for automating this test case.
            Each item should include the name of the component and a brief explanation of why it's needed.
            
            Format your response as a JSON object with a "libraries_list" field containing the list:
            
            {{
            "libraries_list": [
                "<strong>Web Add-in:</strong> For web browser automation capabilities",
                "<strong>Additional Library:</strong> Brief explanation of why it's needed",
                "..."
            ]
            }}
            """
        
        # Effort estimation
        elif analysis_type == 'effort_estimation':
            return f"""
            Estimate the effort required to automate the following test case with UFT:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            {step.get('DATA', '')}
            
            STEPS:
            {self._format_steps_for_prompt(test_case_data.get('steps', []))}
            
            Please provide an effort estimation with the following information:
            1. Estimated hours to implement the automation
            2. Estimated person-days (assuming 8-hour days)
            3. Confidence level in the estimate (High, Medium, or Low)
            4. Breakdown of effort (step implementation, setup, maintenance)
            
            Format your response as a JSON object with an "effort_estimation" field:
            
            {{
            "effort_estimation": {{
                "estimated_hours": 20.5,
                "estimated_person_days": 2.6,
                "confidence": "Medium",
                "breakdown": {{
                "step_implementation": 15.0,
                "setup_effort": 4.0,
                "maintenance_overhead": 1.5
                }}
            }}
            }}
            """
        
        # Standard step analysis (default)
        else:
            return f"""
            Analyze this test step for UFT (Unified Functional Testing) automation potential:
            
            TEST CASE: {test_case_data.get('TEST CASE', 'Unknown')}
            TEST CASE NUMBER: {test_case_data.get('TEST CASE NUMBER', 'Unknown')}
            
            STEP DETAILS:
            - Step Number: {step.get('STEP NO', 'Unknown')}
            - Description: {step.get('TEST STEP DESCRIPTION', '')}
            - Expected Result: {step.get('EXPECTED RESULT', '')}
            - Test Data: {step.get('DATA', '')}
            
            Please provide a JSON response with the following:
            1. automation_potential: "High", "Medium", or "Low"
            2. difficulty: "Easy", "Medium", or "Hard"
            3. challenges: List of specific challenges for automating this step
            4. notes: Detailed notes about automating this step
            5. best_practices: Suggestions for automation best practices
            6. uft_objects: List of UFT objects that would be used
            
            Format your response as a valid JSON object.
            """

    def _format_steps_for_prompt(self, steps: List[Dict[str, Any]]) -> str:
        """
        Format test steps for including in a prompt.
        
        Args:
            steps (List[Dict[str, Any]]): Test steps to format
            
        Returns:
            str: Formatted steps text
        """
        steps_text = ""
        for step in steps:
            step_no = step.get('STEP NO', '')
            description = step.get('TEST STEP DESCRIPTION', '')
            expected = step.get('EXPECTED RESULT', '')
            
            steps_text += f"Step {step_no}: {description}\n"
            if expected:
                steps_text += f"   Expected Result: {expected}\n"
        
        return steps_text

    def _call_groq_api(self, prompt: str) -> str:
        """
        Call the GROQ API with the prompt.
        
        Args:
            prompt (str): The prompt for the LLM
            
        Returns:
            str: Response from the LLM
        """
        if not self.groq_api_key:
            raise ValueError("No API key available for GROQ. Please configure GROQ_API_KEY environment variable.")
        
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
                {"role": "system", "content": "You are an expert in UFT automation analysis. Provide concise, accurate assessments of test steps for automation potential."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }
        
        try:
            # Use the session with a generous timeout
            response = session.post(
                f"{self.groq_api_base}/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=60  # 1 minute timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return content
            else:
                raise ValueError("GROQ API response did not contain expected 'choices' field")
        
        except Exception as e:
            # Log the full exception for debugging
            logger.error(f"GROQ API call failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _call_watsonx_api(self, prompt: str) -> str:
        """
        Call the watsonx.ai API with the prompt.
        
        Args:
            prompt (str): The prompt for the LLM
            
        Returns:
            str: Response from the LLM
        """
        if not self.watsonx_api_key:
            raise ValueError("No API key available for watsonx.ai. Please configure WATSONX_API_KEY environment variable.")
        
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
                "max_new_tokens": 1000,
                "min_new_tokens": 100,
                "temperature": 0.2,  # Lower temperature for more deterministic outputs
                "stop_sequences": ["}"]  # Stop at the end of the JSON
            }
        }
        
        # Add project_id and space_id only if they exist
        if self.watsonx_project_id:
            payload["project_id"] = self.watsonx_project_id
            
        if self.watsonx_space_id:
            payload["space_id"] = self.watsonx_space_id
        
        response = requests.post(generation_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if "results" in result and len(result["results"]) > 0:
            content = result["results"][0].get("generated_text", "")
            return content
        else:
            raise ValueError("watsonx.ai API response did not contain expected 'results' field")

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured format.
        
        Args:
            response (str): Raw response from the LLM
            
        Returns:
            Dict[str, Any]: Structured data from the response
        """
        try:
            # First try direct JSON loading
            try:
                parsed_data = json.loads(response)
                return parsed_data
            except json.JSONDecodeError:
                # Extract JSON from response text (in case the LLM added extra text)
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    logger.warning("No valid JSON found in LLM response")
                    return {}
                
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {}




    # Part 2: Step analysis and object identification functions
    def analyze_test_case(self, test_case_data: Dict[str, Any], 
                        selected_steps: Optional[List[int]] = None, 
                        automation_scope: str = "full") -> Dict[str, Any]:
        """
        Analyze a test case to determine its UFT automation potential using LLM.
        Matches the parameters expected by code_automation.html.
        
        Args:
            test_case_data (Dict[str, Any]): Test case data including steps
            selected_steps (Optional[List[int]]): List of step numbers to analyze, None for all steps
            automation_scope (str): "full" for full test case analysis or "partial" for selected steps
                
        Returns:
            Dict[str, Any]: Analysis results with automation potential score and recommendations
        """
        try:
            logger.info(f"Analyzing test case for UFT automation potential: {test_case_data.get('TEST CASE NUMBER', 'Unknown ID')}")
            
            # Check if LLM API keys are available
            if not ((self.use_watsonx and self.watsonx_api_key) or self.groq_api_key):
                logger.warning("No LLM API keys configured. Cannot perform test case analysis.")
                return {
                    'status': 'error',
                    'message': 'LLM analysis unavailable - no API keys configured',
                    'test_case_number': test_case_data.get('TEST CASE NUMBER', 'Unknown'),
                    'test_case_name': test_case_data.get('TEST CASE', 'Unknown')
                }
            
            # Extract steps
            all_steps = test_case_data.get('steps', [])
            if not all_steps:
                return self._create_error_response("No test steps found in the test case data")
            
            # Filter steps based on selection if needed
            if automation_scope == "partial" and selected_steps:
                # Convert all step numbers to strings for consistent comparison
                selected_step_numbers = set(str(step_num) for step_num in selected_steps)
                steps = [step for step in all_steps if str(step.get('STEP NO', '')) in selected_step_numbers]
                if not steps:
                    return self._create_error_response("No valid steps selected for analysis")
            else:
                steps = all_steps
            
            # Analyze each step using LLM
            step_analyses = []
            
            for step in steps:
                step_analysis = self._analyze_step(step)
                step_analyses.append(step_analysis)
            
            # If any step analysis failed with an error message, handle it
            if any("LLM analysis unavailable" in analysis.get('notes', '') for analysis in step_analyses):
                return {
                    'status': 'error',
                    'message': 'LLM analysis unavailable - no API keys configured',
                    'test_case_number': test_case_data.get('TEST CASE NUMBER', 'Unknown'),
                    'test_case_name': test_case_data.get('TEST CASE', 'Unknown')
                }
            
            # Calculate overall automation score from LLM analyses
            total_automation_score = 0
            total_weight = 0
            
            for analysis in step_analyses:
                score = analysis.get('automation_score', 0)
                
                # Weight earlier steps more heavily (if step_no is numeric)
                try:
                    step_no = int(analysis.get('step_no', 1))
                    weight = max(1, 10 - (step_no - 1) * 0.5)
                except (ValueError, TypeError):
                    weight = 1  # Default weight if step_no is not numeric
                
                total_automation_score += score * weight
                total_weight += weight
            
            # Calculate overall automation potential
            avg_automation_score = total_automation_score / total_weight if total_weight > 0 else 0
            
            # Determine overall potential category based on average score
            if avg_automation_score >= 7.5:
                potential_category = "High"
                potential_rating = "High Potential"
                potential_description = "Standard UI elements with predictable interactions"
            elif avg_automation_score >= 5:
                potential_category = "Medium"
                potential_rating = "Medium Potential"
                potential_description = "Some advanced UI interactions required, moderate challenges"
            
            elif avg_automation_score >= 1:
                potential_category = "Low"
                potential_rating = "Low Potential"
                potential_description = "Complex UI elements or interactions that are difficult to automate"

            else:
                potential_category = "No"
                potential_rating = "LLM Analysis Unavailable"
                potential_description = "No availability of LLM API keys for analysis"
            
            # Get complexity breakdown using LLM
            complexity_breakdown = self._calculate_complexity_breakdown(step_analyses)
            
            # Check if complexity breakdown contains an error
            if 'error' in complexity_breakdown:
                complexity_error = complexity_breakdown['error']
                # Create a standardized error format that the UI can handle
                complexity_breakdown = {
                    'UI Interaction': {
                        'complexity': 0,
                        'badge': 'Error',
                        'badge_class': 'bg-secondary',
                        'message': complexity_error
                    },
                    'Data Handling': {
                        'complexity': 0,
                        'badge': 'Error',
                        'badge_class': 'bg-secondary',
                        'message': complexity_error
                    },
                    'Verification Points': {
                        'complexity': 0,
                        'badge': 'Error',
                        'badge_class': 'bg-secondary',
                        'message': complexity_error
                    },
                    'Technical Challenges': {
                        'complexity': 0,
                        'badge': 'Error',
                        'badge_class': 'bg-secondary',
                        'message': complexity_error
                    }
                }
            
            # Generate UFT recommendations using LLM
            # Create a synthetic step for recommendations
            recommendations_step = {
                'STEP NO': 'recommendations',
                'TEST STEP DESCRIPTION': 'Generate UFT recommendations',
                'EXPECTED RESULT': 'List of UFT recommendations',
                'DATA': '',
                'ANALYSIS_TYPE': 'recommendations'  # Special flag for LLM
            }
            
            # Use LLM to generate recommendations
            recommendations_analysis = self._call_llm_for_analysis(test_case_data, recommendations_step)
            uft_recommendations = recommendations_analysis.get('recommendations', [])
            
            # Use LLM to identify challenges and approaches
            challenges_step = {
                'STEP NO': 'challenges',
                'TEST STEP DESCRIPTION': 'Identify challenges and approaches',
                'EXPECTED RESULT': 'Lists of challenges and approaches',
                'DATA': '',
                'ANALYSIS_TYPE': 'challenges_approaches'  # Special flag for LLM
            }
            
            # Use LLM to generate challenges and approaches
            challenges_analysis = self._call_llm_for_analysis(test_case_data, challenges_step)
            challenges = challenges_analysis.get('challenges', [])
            approaches = challenges_analysis.get('approaches', [])
            
            # Use LLM to generate starter UFT code
            code_step = {
                'STEP NO': 'code',
                'TEST STEP DESCRIPTION': 'Generate starter UFT code',
                'EXPECTED RESULT': 'UFT code sample',
                'DATA': '',
                'ANALYSIS_TYPE': 'uft_code'  # Special flag for LLM
            }
            
            # Use LLM to generate starter code
            code_analysis = self._call_llm_for_analysis(test_case_data, code_step)
            starter_code = code_analysis.get('uft_code', '')
            
            # Generate approach recommendation using LLM
            approach_step = {
                'STEP NO': 'approach',
                'TEST STEP DESCRIPTION': 'Generate approach recommendation',
                'EXPECTED RESULT': 'UFT approach recommendation',
                'DATA': f"Average automation score: {avg_automation_score}",
                'ANALYSIS_TYPE': 'approach_recommendation'  # Special flag for LLM
            }
            
            # Use LLM to generate approach recommendation
            approach_analysis = self._call_llm_for_analysis(test_case_data, approach_step)
            approach_recommendation = approach_analysis.get('approach_recommendation', '')
            
            # Generate libraries list using LLM
            libraries_step = {
                'STEP NO': 'libraries',
                'TEST STEP DESCRIPTION': 'Generate UFT libraries list',
                'EXPECTED RESULT': 'List of UFT libraries',
                'DATA': '',
                'ANALYSIS_TYPE': 'libraries_list'  # Special flag for LLM
            }
            
            # Use LLM to generate libraries list
            libraries_analysis = self._call_llm_for_analysis(test_case_data, libraries_step)
            libraries_list = libraries_analysis.get('libraries_list', [])
            
            # Generate effort estimation using LLM
            effort_step = {
                'STEP NO': 'effort',
                'TEST STEP DESCRIPTION': 'Estimate automation effort',
                'EXPECTED RESULT': 'Effort estimation',
                'DATA': f"Average automation score: {avg_automation_score}, Step count: {len(steps)}",
                'ANALYSIS_TYPE': 'effort_estimation'  # Special flag for LLM
            }
            
            # Use LLM to generate effort estimation
            effort_analysis = self._call_llm_for_analysis(test_case_data, effort_step)
            estimated_effort = effort_analysis.get('effort_estimation', {})
            
            # Combine results
            analysis_result = {
                # Core information
                'test_case_number': test_case_data.get('TEST CASE NUMBER', 'Unknown'),
                'test_case_name': test_case_data.get('TEST CASE', 'Untitled Test Case'),
                'analysis_scope': automation_scope,
                'steps_analyzed': [str(step.get('STEP NO', 'Unknown')) for step in steps],
                
                # Overall assessment
                'automation_potential': potential_category,
                'automation_score': round(avg_automation_score * 10),  # Scale to 0-100 for UI
                'automation_rating': potential_rating,
                'automation_summary': potential_description,
                
                # Detailed analysis
                'step_analyses': self._format_step_analyses_for_ui(step_analyses),
                'complexity_breakdown': complexity_breakdown,
                'uft_recommendations': uft_recommendations,
                'challenges': challenges,
                'suggested_approaches': approaches,
                
                # Code and implementation
                'uft_starter_code': starter_code,
                'uft_approach_recommendation': approach_recommendation,
                'uft_libraries_list': libraries_list,
                
                # Effort estimation
                'estimated_effort': estimated_effort,
                
                # Status
                'status': 'success',
                'message': 'Analysis completed successfully',
            }
            
            logger.info(f"Completed UFT automation analysis with score: {avg_automation_score}")
            return analysis_result
                
        except Exception as e:
            logger.error(f"Error analyzing test case for UFT automation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_error_response(f"Error during analysis: {str(e)}")

    def _analyze_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an individual test step for automation potential using LLM.
        
        Args:
            step (Dict[str, Any]): The test step data
            
        Returns:
            Dict[str, Any]: Analysis of the step's automation potential
        """
        try:
            # Check if LLM API keys are available
            if not ((self.use_watsonx and self.watsonx_api_key) or self.groq_api_key):
                logger.warning("No LLM API keys configured. Cannot perform test step analysis.")
                return {
                    'step_no': step.get('STEP NO', 'Unknown'),
                    'description': step.get('TEST STEP DESCRIPTION', ''),
                    'automation_potential': 'Unknown',
                    'automation_score': 0,
                    'difficulty': 'Unknown',
                    'identified_objects': [],
                    'challenges': ["LLM analysis unavailable - no API keys configured"],
                    'notes': "LLM model not available for analysis. Please configure API keys for watsonx.ai or GROQ.",
                    'uft_code_snippet': ""
                }
            
            # Create a fake test case data structure to provide context
            test_case_data = {
                'TEST CASE NUMBER': 'SINGLE_STEP',
                'TEST CASE': 'Single Step Analysis',
                'steps': [step]
            }
            
            # Call LLM for analysis
            llm_analysis = self._call_llm_for_analysis(test_case_data, step)
            
            # If LLM analysis failed, return error message
            if not llm_analysis:
                logger.error(f"LLM analysis failed for step: {step.get('STEP NO', 'Unknown')}")
                return {
                    'step_no': step.get('STEP NO', 'Unknown'),
                    'description': step.get('TEST STEP DESCRIPTION', ''),
                    'automation_potential': 'Unknown',
                    'automation_score': 0,
                    'difficulty': 'Unknown',
                    'identified_objects': [],
                    'challenges': ["LLM analysis failed"],
                    'notes': "LLM model analysis failed. Please try again or check your API configuration.",
                    'uft_code_snippet': ""
                }
            
            # Convert automation_potential to score (0-10 scale)
            automation_score = 0
            if llm_analysis.get('automation_potential') == 'High':
                automation_score = 8.5
            elif llm_analysis.get('automation_potential') == 'Medium':
                automation_score = 6.0
            elif llm_analysis.get('automation_potential') == 'Low':
                automation_score = 3.5
            
            # Generate a sample UFT code snippet using LLM if not provided
            uft_code_snippet = llm_analysis.get('uft_code', "")
            if not uft_code_snippet and llm_analysis.get('uft_objects'):
                # Create another LLM prompt specifically for code generation
                code_prompt = self._create_code_generation_prompt(step, llm_analysis.get('uft_objects', []))
                code_response = None
                
                # Call appropriate LLM based on configuration
                if self.use_watsonx and self.watsonx_api_key:
                    code_response = self._call_watsonx_api(code_prompt)
                elif self.groq_api_key:
                    code_response = self._call_groq_api(code_prompt)
                
                if code_response:
                    # Extract code from response
                    uft_code_snippet = self._extract_code_from_response(code_response)
            
            # Return analysis result with LLM-provided information
            return {
                'step_no': step.get('STEP NO', 'Unknown'),
                'description': step.get('TEST STEP DESCRIPTION', ''),
                'automation_potential': llm_analysis.get('automation_potential', 'Unknown'),
                'automation_score': automation_score,
                'difficulty': llm_analysis.get('difficulty', 'Unknown'),
                'identified_objects': llm_analysis.get('uft_objects', []),
                'challenges': llm_analysis.get('challenges', []),
                'notes': llm_analysis.get('notes', ""),
                'uft_code_snippet': uft_code_snippet,
                'best_practices': llm_analysis.get('best_practices', []),
                'llm_enhanced': True
            }
            
        except Exception as e:
            logger.error(f"Error in step analysis: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'step_no': step.get('STEP NO', 'Unknown'),
                'description': step.get('TEST STEP DESCRIPTION', ''),
                'automation_potential': 'Unknown',
                'automation_score': 0,
                'difficulty': 'Unknown',
                'identified_objects': [],
                'challenges': [f"Error during analysis: {str(e)}"],
                'notes': "An error occurred during LLM analysis.",
                'uft_code_snippet': ""
            }
        

    def _create_code_generation_prompt(self, step: Dict[str, Any], identified_objects: List[str]) -> str:
        """
        Create a prompt specifically for UFT code generation.
        
        Args:
            step (Dict[str, Any]): The test step data
            identified_objects (List[str]): The identified UFT objects
            
        Returns:
            str: Formatted prompt for code generation
        """
        prompt = f"""
        Generate UFT (Unified Functional Testing) VBScript code for the following test step:
        
        STEP DETAILS:
        - Description: {step.get('TEST STEP DESCRIPTION', '')}
        - Expected Result: {step.get('EXPECTED RESULT', '')}
        - Test Data: {step.get('DATA', '')}
        
        IDENTIFIED UFT OBJECTS: {', '.join(identified_objects)}
        
        Please generate ONLY the VBScript code (no explanation or context).
        The code should:
        1. Be valid UFT VBScript syntax
        2. Include comments explaining what it does
        3. Be concise but complete for this specific step
        4. Use appropriate error handling
        5. Use appropriate object identification based on the identified objects
        
        Example format:
        ' Step: Click login button
        Browser("name:=Login Page").Page("title:=Login").WebButton("name:=login").Click
        If Err.Number <> 0 Then
            Reporter.ReportEvent micFail, "Click Login", "Failed to click login button: " & Err.Description
        End If
        """
        return prompt

    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract clean code snippet from LLM response.
        
        Args:
            response (str): The LLM response text
            
        Returns:
            str: Extracted code snippet
        """
        # Try to identify code blocks with markers
        if "```" in response:
            # Extract content between code markers
            start = response.find("```") + 3
            # Skip language identifier if present
            if "\n" in response[start:]:
                start = response.find("\n", start) + 1
            end = response.rfind("```")
            if end > start:
                return response[start:end].strip()
        
        # If no code markers, try to find VBScript-like content
        vbscript_indicators = ["'", "Browser(", "WebEdit(", "WebButton(", "Reporter.ReportEvent"]
        for indicator in vbscript_indicators:
            if indicator in response:
                # Return from first line containing indicator
                lines = response.split("\n")
                for i, line in enumerate(lines):
                    if indicator in line:
                        return "\n".join(lines[i:]).strip()
        
        # If no clear code patterns found, return the whole response
        return response.strip()



    def _format_step_analyses_for_ui(self, step_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format step analyses for the UI display.
        
        Args:
            step_analyses (List[Dict[str, Any]]): Raw step analyses
            
        Returns:
            List[Dict[str, Any]]: Formatted step analyses for UI
        """
        formatted_analyses = []
        for analysis in step_analyses:
            formatted_analysis = {
                'step': f"Step {analysis['step_no']}: {analysis['description']}",
                'automation_difficulty': analysis.get('difficulty', 'Unknown'),
                'notes': analysis.get('notes', 'No notes available'),
                'badge_class': self._get_badge_class_for_difficulty(analysis.get('difficulty', 'Unknown'))
            }
            formatted_analyses.append(formatted_analysis)
        return formatted_analyses
    
    def _get_badge_class_for_difficulty(self, difficulty: str) -> str:
        """
        Get badge class for difficulty level.
        
        Args:
            difficulty (str): Difficulty level
            
        Returns:
            str: Badge class for UI
        """
        if difficulty == 'Easy':
            return 'bg-success'
        elif difficulty == 'Medium':
            return 'bg-warning'
        elif difficulty == 'Hard':
            return 'bg-danger'
        else:
            return 'bg-secondary'  # For unknown or error cases



    def _calculate_complexity_breakdown(self, step_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate complexity breakdown for UI display using LLM.
        
        Args:
            step_analyses (List[Dict[str, Any]]): Step analyses
            
        Returns:
            Dict[str, Any]: Complexity breakdown or error message
        """
        # Check if LLM API keys are available
        if not ((self.use_watsonx and self.watsonx_api_key) or self.groq_api_key):
            logger.warning("No LLM API keys configured. Cannot calculate complexity breakdown.")
            return {'error': 'LLM analysis unavailable - no API keys configured'}
        
        try:
            # Create a synthetic test case for LLM analysis
            test_case_data = {
                'TEST CASE NUMBER': 'COMPLEXITY_ANALYSIS',
                'TEST CASE': 'Complexity Analysis',
                'steps': []
            }
            
            # Format steps data for LLM analysis
            steps_text = ""
            for analysis in step_analyses:
                step_no = analysis.get('step_no', '')
                description = analysis.get('description', '')
                
                # Add formatted step text
                steps_text += f"Step {step_no}: {description}\n"
                
                # Also add to test case for context
                test_case_data['steps'].append({
                    'STEP NO': step_no,
                    'TEST STEP DESCRIPTION': description,
                    'EXPECTED RESULT': '',
                    'DATA': ''
                })

            # Create a special analysis step for complexity breakdown
            complexity_step = {
                'STEP NO': 'complexity_analysis',
                'TEST STEP DESCRIPTION': 'Analyze complexity breakdown for all test steps',
                'EXPECTED RESULT': 'Complexity assessment for UI, Data, Verification, and Technical aspects',
                'DATA': steps_text,  # Include the formatted step text
                'ANALYSIS_TYPE': 'complexity_breakdown'  # This will trigger the specialized prompt
            }
            
            # Call the LLM for complexity analysis using the existing function
            llm_analysis = self._call_llm_for_analysis(test_case_data, complexity_step)
            
            # Check if LLM analysis succeeded
            if not llm_analysis:
                logger.error("LLM failed to analyze complexity breakdown")
                return {'error': 'LLM analysis failed - no response received'}
            
            # Extract complexity breakdown from the LLM response
            complexity_breakdown = llm_analysis.get('complexity_breakdown', {})
            
            # Check if we got valid complexity data
            if not complexity_breakdown:
                logger.error("LLM response did not contain expected complexity_breakdown data")
                return {'error': 'LLM analysis did not provide expected complexity breakdown format'}
            
            # Return the complexity breakdown directly from LLM with no modifications
            return complexity_breakdown
            
        except Exception as e:
            logger.error(f"Error analyzing complexity breakdown: {str(e)}")
            return {'error': f'Error during complexity analysis: {str(e)}'}



    def _generate_approach_recommendation(self, avg_score: float, step_analyses: List[Dict[str, Any]]) -> str:
        """
        Generate an overall approach recommendation.
        
        Args:
            avg_score (float): The average automation score
            step_analyses (List[Dict[str, Any]]): Step analyses
            
        Returns:
            str: Approach recommendation
        """
        if avg_score >= 7.5:
            return "Based on the analysis, this test case is highly suitable for UFT automation using standard object identification methods. The test involves standard web UI elements that can be easily recognized by UFT's Object Repository."
        elif avg_score >= 5:
            return "This test case has moderate automation potential with UFT. While most steps can be automated, some verification steps and dynamic elements will require special handling. Consider implementing synchronization mechanisms and custom verification logic."
        else:
            return "This test case presents significant challenges for UFT automation. Consider a hybrid approach with manual intervention for complex steps, or redesign the test case to improve automation potential."

    def _generate_libraries_list(self, step_analyses: List[Dict[str, Any]]) -> List[str]:
        """
        Generate list of recommended UFT libraries and add-ins.
        
        Args:
            step_analyses (List[Dict[str, Any]]): Step analyses
            
        Returns:
            List[str]: Recommended libraries and add-ins
        """
        libraries = []
        
        # Collect all identified objects
        all_objects = []
        for step in step_analyses:
            all_objects.extend(step.get('identified_objects', []))
            
        # Recommend Web Add-in if any web objects
        if any(obj.startswith('Web') for obj in all_objects):
            libraries.append("<strong>Web Add-in:</strong> For web browser automation capabilities")
            
        # Recommend Windows Add-in if any Windows objects
        if any(obj.startswith('Win') for obj in all_objects):
            libraries.append("<strong>ActiveX Add-in:</strong> For desktop application components if necessary")
            
        # Always recommend Web Extensions for modern web apps
        libraries.append("<strong>Web Extensions:</strong> For enhanced HTML object recognition")
        
        # Add additional libraries based on specific challenges
        all_challenges = []
        for step in step_analyses:
            all_challenges.extend(step.get('challenges', []))
            
        if any('image' in challenge.lower() for challenge in all_challenges):
            libraries.append("<strong>Image Checkpoint Extension:</strong> For visual comparison operations")
            
        if any('data' in challenge.lower() for challenge in all_challenges):
            libraries.append("<strong>Excel Add-in:</strong> For data-driven testing capabilities")
        
        return libraries

    def _generate_starter_uft_code(self, test_case_data: Dict[str, Any], step_analyses: List[Dict[str, Any]]) -> str:
        """
        Generate a starter UFT code for the test case.
        
        Args:
            test_case_data (Dict[str, Any]): Test case data
            step_analyses (List[Dict[str, Any]]): Step analyses
            
        Returns:
            str: Starter UFT code
        """
        test_case_name = test_case_data.get('TEST CASE', 'Test Case')
        test_case_id = test_case_data.get('TEST CASE NUMBER', 'TC-0000')
        
        # Create header
        code = f"'UFT Script - {test_case_name} Automation\n"
        code += f"'Generated for test case {test_case_id}\n\n"
        code += "'==========================================================\n"
        code += f"' Description: Automated test for {test_case_name}\n"
        code += "' Author: Watsonx for IPG Testing\n"
        code += f"' Date: {self._get_current_date()}\n"
        code += "'==========================================================\n\n"
        
        # Add required libraries and default settings
        code += "' Load required libraries and set defaults\n"
        code += "LoadFunctionLibrary(\"CommonFunctions.qfl\")\n"
        code += "Option Explicit\n\n"
        
        # Add script body based on steps
        code += "' Navigate to application\n"
        code += "SystemUtil.Run \"chrome.exe\", \"https://example.com/login\"\n"
        code += "Wait 3\n\n"
        
        # Add object repository references
        code += "' Set up the object repository references\n"
        code += "With Browser(\"name:=Login Page\").Page(\"title:=Login\")\n"
        
        # Add steps
        for i, step_analysis in enumerate(step_analyses):
            step_no = step_analysis.get('step_no', i + 1)
            step_desc = step_analysis.get('description', '')
            
            code += f"    \n    ' Step {step_no}: {step_desc}\n"
            
            # Extract the code part from the snippet (remove the comment part)
            code_snippet = step_analysis.get('uft_code_snippet', '')
            if code_snippet:
                # Remove the comment/description part if present
                if "'" in code_snippet and "\n" in code_snippet:
                    code_snippet = code_snippet.split("\n", 1)[1]
                
                # Indent and add to main code
                code_snippet = "    " + code_snippet.replace("\n", "\n    ")
                code += f"{code_snippet}\n"
                code += f"    Reporter.ReportEvent micPass, \"Step {step_no}\", \"{step_desc} executed successfully\"\n"
            else:
                code += f"    ' TODO: Implement step {step_no}\n"
                
        # Close the With block
        code += "End With\n"
        
        return code

    def _generate_full_uft_script(self, test_case_data: Dict[str, Any], step_analyses: List[Dict[str, Any]], 
                                script_options: Dict[str, Any] = None) -> str:
        """
        Generate a complete UFT script with all components.
        
        Args:
            test_case_data (Dict[str, Any]): Test case data
            step_analyses (List[Dict[str, Any]]): Step analyses
            script_options (Dict[str, Any], optional): Script generation options
            
        Returns:
            str: Complete UFT script
        """
        # Set default options if not provided
        if script_options is None:
            script_options = {
                'script_name': f"TC{test_case_data.get('TEST CASE NUMBER', '0000').replace('-', '')}_Script",
                'author': "Watsonx for IPG Testing",
                'version': "1.0",
                'include_header': True,
                'include_environment_setup': True,
                'include_error_recovery': True,
                'include_cleanup': True,
                'include_reporting': True
            }
        
        test_case_name = test_case_data.get('TEST CASE', 'Test Case')
        test_case_id = test_case_data.get('TEST CASE NUMBER', 'TC-0000')
        script_name = script_options.get('script_name', f"TC{test_case_id.replace('-', '')}_Script")
        author = script_options.get('author', "Watsonx for IPG Testing")
        version = script_options.get('version', "1.0")
        
        # Initialize code
        code = ""
        
        # Add header documentation
        if script_options.get('include_header', True):
            code += f"'===========================================================================\n"
            code += f"' Script Name: {script_name}\n"
            code += f"' Script Purpose: Automated test for {test_case_name}\n"
            code += f"' Test Case ID: {test_case_id}\n"
            code += f"' Author: {author}\n"
            code += f"' Version: {version}\n"
            code += f"' Date: {self._get_current_date()}\n"
            code += f"'===========================================================================\n\n"
        
        # Add environment setup
        if script_options.get('include_environment_setup', True):
            code += "'===========================================================================\n"
            code += "' Environment Setup\n"
            code += "'===========================================================================\n"
            code += "Option Explicit\n\n"
            
            # Add function library references
            code += "' Load required function libraries\n"
            code += "LoadFunctionLibrary \"CommonFunctions.qfl\"\n"
            
            # Add global variables
            code += "\n' Global Variables\n"
            code += "Dim TestStatus, TestCaseID, TestDescription\n"
            code += "TestCaseID = \"" + test_case_id + "\"\n"
            code += "TestDescription = \"" + test_case_name + "\"\n\n"
            
            # Add constants
            code += "' Constants\n"
            code += "Const MAX_WAIT_TIME = 20 ' Maximum wait time in seconds\n"
            code += "Const APP_URL = \"https://example.com/login\"\n\n"
        
        # Add error recovery
        if script_options.get('include_error_recovery', True):
            code += "'===========================================================================\n"
            code += "' Error Recovery\n"
            code += "'===========================================================================\n"
            code += "On Error Resume Next ' Enable error handling\n\n"
            
            code += "' Register error handler for exceptions\n"
            code += "RegisterUserFunc \"ErrorHandler\", \"HandleError\"\n\n"
            
            code += "' Error handler function\n"
            code += "Function HandleError()\n"
            code += "    ' Log error details\n"
            code += "    Reporter.ReportEvent micFail, \"Error\", \"Error occurred: \" & Err.Description & \" (\" & Err.Number & \")\"\n"
            code += "    \n"
            code += "    ' Take screenshot\n"
            code += "    Desktop.CaptureBitmap \"Screenshots\\Error_\" & TestCaseID & \"_\" & FormatDateTime(Now, 2) & \"_\" & FormatDateTime(Now, 4) & \".png\", True\n"
            code += "    \n"
            code += "    ' Set test status to failed\n"
            code += "    TestStatus = \"Failed\"\n"
            code += "    \n"
            code += "    ' Continue execution after the error\n"
            code += "    Err.Clear\n"
            code += "End Function\n\n"
        
        # Add main test script
        code += "'===========================================================================\n"
        code += "' Main Test Script\n"
        code += "'===========================================================================\n"
        
        # Set initial test status
        code += "' Initialize test status\n"
        code += "TestStatus = \"Passed\"\n\n"
        
        # Add reporting start
        if script_options.get('include_reporting', True):
            code += "' Log test start\n"
            code += "Reporter.ReportEvent micInfo, \"Test Start\", \"Starting execution of test case: \" & TestCaseID & \" - \" & TestDescription\n\n"
        
        # Launch application
        code += "' Launch application\n"
        code += "Reporter.ReportEvent micInfo, \"Launch Application\", \"Launching browser and navigating to application\"\n"
        code += "SystemUtil.Run \"chrome.exe\", \"https://example.com/login\"\n"
        code += "Wait 3 ' Wait for browser to initialize\n\n"
        
        # Test steps implementation
        code += "' Main test steps\n"
        code += "With Browser(\"name:=Login Page\").Page(\"title:=Login\")\n"
        
        # Add steps
        for i, step_analysis in enumerate(step_analyses):
            step_no = step_analysis.get('step_no', i + 1)
            step_desc = step_analysis.get('description', '')
            
            code += f"    \n    ' Step {step_no}: {step_desc}\n"
            code += f"    Reporter.ReportEvent micInfo, \"Step {step_no}\", \"{step_desc}\"\n"
            
            # Extract the code part from the snippet (remove the comment part)
            code_snippet = step_analysis.get('uft_code_snippet', '')
            if code_snippet:
                # Remove the comment/description part if present
                if "'" in code_snippet and "\n" in code_snippet:
                    code_snippet = code_snippet.split("\n", 1)[1]
                
                # Indent and add to main code
                code_snippet = "    " + code_snippet.replace("\n", "\n    ")
                code += f"{code_snippet}\n"
                
                # Add verification reporting
                if 'verify' in step_desc.lower() or 'check' in step_desc.lower() or 'validate' in step_desc.lower():
                    code += "    If Err.Number = 0 Then\n"
                    code += f"        Reporter.ReportEvent micPass, \"Step {step_no}\", \"Verification successful\"\n"
                    code += "    Else\n"
                    code += f"        Reporter.ReportEvent micFail, \"Step {step_no}\", \"Verification failed: \" & Err.Description\n"
                    code += "        TestStatus = \"Failed\"\n"
                    code += "        Err.Clear\n"
                    code += "    End If\n"
                else:
                    code += "    If Err.Number = 0 Then\n"
                    code += f"        Reporter.ReportEvent micPass, \"Step {step_no}\", \"Step executed successfully\"\n"
                    code += "    Else\n"
                    code += f"        Reporter.ReportEvent micFail, \"Step {step_no}\", \"Step failed: \" & Err.Description\n"
                    code += "        TestStatus = \"Failed\"\n"
                    code += "        Err.Clear\n"
                    code += "    End If\n"
            else:
                code += f"    ' TODO: Implement step {step_no}\n"
                code += f"    Reporter.ReportEvent micWarning, \"Step {step_no}\", \"Implementation needed\"\n"
                
        # Close the With block
        code += "End With\n\n"
        
        # Add cleanup actions
        if script_options.get('include_cleanup', True):
            code += "'===========================================================================\n"
            code += "' Cleanup Actions\n"
            code += "'===========================================================================\n"
            code += "' Close the browser\n"
            code += "Reporter.ReportEvent micInfo, \"Cleanup\", \"Closing browser\"\n"
            code += "SystemUtil.CloseProcessByName \"chrome.exe\"\n\n"
        
        # Add test summary
        if script_options.get('include_reporting', True):
            code += "' Log test completion\n"
            code += "If TestStatus = \"Passed\" Then\n"
            code += "    Reporter.ReportEvent micPass, \"Test Complete\", \"Test case " + test_case_id + " completed successfully\"\n"
            code += "Else\n"
            code += "    Reporter.ReportEvent micFail, \"Test Complete\", \"Test case " + test_case_id + " failed\"\n"
            code += "End If\n"
        
        return code

    def _estimate_automation_effort(self, avg_score: float, step_count: int) -> Dict[str, Any]:
        """
        Estimate the effort required for automation.
        
        Args:
            avg_score (float): Average automation score
            step_count (int): Number of steps
            
        Returns:
            Dict[str, Any]: Effort estimation
        """
        # Base effort per step based on automation score
        if avg_score >= 8:
            base_effort_per_step = 0.5  # hours
        elif avg_score >= 6:
            base_effort_per_step = 1.0  # hours
        elif avg_score >= 4:
            base_effort_per_step = 2.0  # hours
        else:
            base_effort_per_step = 3.0  # hours
            
        # Calculate total hours
        total_effort_hours = base_effort_per_step * step_count
        
        # Add overhead for setup, maintenance, etc.
        setup_effort = 4.0  # hours
        maintenance_overhead = total_effort_hours * 0.2  # 20% overhead
        
        # Total effort
        total_effort = total_effort_hours + setup_effort + maintenance_overhead
        
        # Convert to person-days (assuming 8-hour days)
        person_days = round(total_effort / 8, 1)
        
        return {
            'estimated_hours': round(total_effort, 1),
            'estimated_person_days': person_days,
            'confidence': 'High' if avg_score >= 7 else 'Medium' if avg_score >= 5 else 'Low',
            'breakdown': {
                'step_implementation': round(total_effort_hours, 1),
                'setup_effort': setup_effort,
                'maintenance_overhead': round(maintenance_overhead, 1)
            }
        }
    
    # Part 4: API integration and utility functions
    def analyze_test_case_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API endpoint method to analyze a test case based on request data.
        Provides a standardized interface for the frontend UI.
        
        Args:
            request_data (Dict[str, Any]): Request data with the following fields:
                - test_case_data: Test case data or ID
                - automation_scope: "full" or "partial"
                - selected_steps: List of step numbers to analyze (optional)
                
        Returns:
            Dict[str, Any]: Analysis results formatted for the UI
        """
        try:
            logger.info("API request received for test case analysis")
            
            # Extract parameters from request
            test_case_data = request_data.get('test_case_data')
            automation_scope = request_data.get('automation_scope', 'full')
            selected_steps = request_data.get('selected_steps', None)
            
            # Validate required parameters
            if not test_case_data:
                return self._create_error_response("Missing test_case_data in request")
            
            # If test_case_data is a string (ID), fetch test case from repository
            if isinstance(test_case_data, str):
                test_case_data = self._get_test_case_by_id(test_case_data)
            
            # Analyze test case
            analysis_result = self.analyze_test_case(
                test_case_data=test_case_data,
                selected_steps=selected_steps,
                automation_scope=automation_scope
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_error_response(f"API error: {str(e)}")

    # API endpoint for the frontend to call to get a test case preview
    def get_test_case_preview_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API endpoint method to get a test case preview based on request data.
        
        Args:
            request_data (Dict[str, Any]): Request data with the following fields:
                - test_case_id: ID of the test case to retrieve (optional)
                - file_content: Base64-encoded content of the test case file (optional)
                - file_name: Name of the test case file (optional)
                
        Returns:
            Dict[str, Any]: Test case preview formatted for the UI
        """
        try:
            logger.info("API request received for test case preview")
            
            # Extract parameters from request
            test_case_id = request_data.get('test_case_id')
            file_content_b64 = request_data.get('file_content')
            file_name = request_data.get('file_name')
            
            # At least one of test_case_id or file_content must be provided
            if not test_case_id and not file_content_b64:
                return self._create_error_response("Either test_case_id or file_content must be provided")
            
            # Convert base64 content to bytes if provided
            file_content = None
            if file_content_b64:
                import base64
                try:
                    file_content = base64.b64decode(file_content_b64)
                except Exception as e:
                    return self._create_error_response(f"Invalid file content: {str(e)}")
            
            # Get test case preview
            preview_result = self.get_test_case_preview(
                test_case_id=test_case_id,
                file_content=file_content,
                file_name=file_name
            )
            
            return preview_result
            
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_error_response(f"API error: {str(e)}")

    # API endpoint for the frontend to call to generate full UFT script
    def generate_full_script_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API endpoint method to generate a full UFT script based on request data.
        
        Args:
            request_data (Dict[str, Any]): Request data with the following fields:
                - test_case_id: ID of the test case to use
                - script_options: Options for script generation (optional)
                
        Returns:
            Dict[str, Any]: Generated script
        """
        try:
            logger.info("API request received for full UFT script generation")
            
            # Extract parameters from request
            test_case_id = request_data.get('test_case_id')
            script_options = request_data.get('script_options', {})
            
            # Validate required parameters
            if not test_case_id:
                return self._create_error_response("Missing test_case_id in request")
            
            # Get test case data
            test_case_data = self._get_test_case_by_id(test_case_id)
            
            # Analyze steps first
            step_analyses = []
            for step in test_case_data.get('steps', []):
                step_analysis = self._analyze_step(step)
                step_analyses.append(step_analysis)
            
            # Generate full script
            script = self._generate_full_uft_script(
                test_case_data=test_case_data,
                step_analyses=step_analyses,
                script_options=script_options
            )
            
            return {
                'status': 'success',
                'script': script,
                'script_name': script_options.get('script_name', f"TC{test_case_id.replace('-', '')}_Script"),
                'message': 'Script generated successfully'
            }
            
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_error_response(f"API error: {str(e)}")

    def _get_test_case_by_id(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get a test case by ID from the repository.
        In a real implementation, this would query a database or service.
        
        Args:
            test_case_id (str): Test case ID
            
        Returns:
            Dict[str, Any]: Test case data
        """
        logger.info(f"Getting test case by ID: {test_case_id}")
        
        # In a real implementation, this would query a repository
        # For demonstration, we'll return the sample test case
        sample_case = self._get_sample_login_test_case()
        
        # Update the ID to match the requested ID
        sample_case['TEST CASE NUMBER'] = test_case_id
        
        return sample_case


    # Export analysis results to various formats for reporting
    def export_analysis_results(self, analysis_result: Dict[str, Any], export_format: str = 'json') -> Dict[str, Any]:
        """
        Export analysis results to various formats for reporting.
        
        Args:
            analysis_result (Dict[str, Any]): Analysis results
            export_format (str, optional): Export format ('json', 'html', 'excel')
            
        Returns:
            Dict[str, Any]: Export result
        """
        try:
            # Basic report data
            test_case_number = analysis_result.get('test_case_number', 'Unknown')
            test_case_name = analysis_result.get('test_case_name', 'Unknown')
            export_data = None
            
            if export_format == 'json':
                # Export as JSON
                import json
                export_data = json.dumps(analysis_result, indent=2)
                content_type = 'application/json'
                filename = f"{test_case_number}_UFT_Analysis.json"
                
            elif export_format == 'html':
                # Create HTML report
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>UFT Automation Analysis: {test_case_number}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1, h2, h3 {{ color: #333; }}
                        .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                        .high {{ color: green; }}
                        .medium {{ color: orange; }}
                        .low {{ color: red; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    <h1>UFT Automation Analysis Report</h1>
                    <div class="section">
                        <h2>Test Case Information</h2>
                        <p><strong>Test Case ID:</strong> {test_case_number}</p>
                        <p><strong>Test Case Name:</strong> {test_case_name}</p>
                        <p><strong>Analysis Date:</strong> {self._get_current_date()}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Automation Potential</h2>
                        <p><strong>Overall Potential:</strong> <span class="{analysis_result.get('automation_potential', '').lower()}">{analysis_result.get('automation_potential', 'Unknown')}</span></p>
                        <p><strong>Automation Score:</strong> {analysis_result.get('automation_score', 0)}%</p>
                        <p><strong>Description:</strong> {analysis_result.get('automation_summary', '')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Estimated Effort</h2>
                        <p><strong>Estimated Hours:</strong> {analysis_result.get('estimated_effort', {}).get('estimated_hours', 0)} hours</p>
                        <p><strong>Estimated Person Days:</strong> {analysis_result.get('estimated_effort', {}).get('estimated_person_days', 0)} days</p>
                        <p><strong>Confidence:</strong> {analysis_result.get('estimated_effort', {}).get('confidence', 'Unknown')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Step Analysis</h2>
                        <table>
                            <tr>
                                <th>Step</th>
                                <th>Difficulty</th>
                                <th>Notes</th>
                            </tr>
                """
                
                # Add each step analysis
                for step in analysis_result.get('step_analyses', []):
                    difficulty_class = 'high' if step.get('automation_difficulty') == 'Easy' else 'medium' if step.get('automation_difficulty') == 'Medium' else 'low'
                    html_content += f"""
                            <tr>
                                <td>{step.get('step', '')}</td>
                                <td class="{difficulty_class}">{step.get('automation_difficulty', '')}</td>
                                <td>{step.get('notes', '')}</td>
                            </tr>
                    """
                
                # Close step table and add recommendations
                html_content += f"""
                        </table>
                    </div>
                    
                    <div class="section">
                        <h2>Recommendations</h2>
                        <h3>UFT Libraries</h3>
                        <ul>
                """
                
                # Add libraries
                for library in analysis_result.get('uft_libraries_list', []):
                    # Remove HTML tags for cleaner display
                    clean_library = library.replace('<strong>', '').replace('</strong>', '')
                    html_content += f"        <li>{clean_library}</li>\n"
                
                html_content += """
                        </ul>
                        
                        <h3>Implementation Approaches</h3>
                        <ul>
                """
                
                # Add approaches
                for approach in analysis_result.get('suggested_approaches', []):
                    html_content += f"        <li>{approach}</li>\n"
                
                html_content += """
                        </ul>
                    </div>
                </body>
                </html>
                """
                
                export_data = html_content
                content_type = 'text/html'
                filename = f"{test_case_number}_UFT_Analysis.html"
                
            elif export_format == 'excel':
                # Create Excel report using pandas
                try:
                    import pandas as pd
                    import io
                    
                    # Create Excel writer
                    output = io.BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    
                    # Summary sheet
                    summary_data = {
                        'Test Case ID': [test_case_number],
                        'Test Case Name': [test_case_name],
                        'Automation Potential': [analysis_result.get('automation_potential', 'Unknown')],
                        'Automation Score': [analysis_result.get('automation_score', 0)],
                        'Estimated Hours': [analysis_result.get('estimated_effort', {}).get('estimated_hours', 0)],
                        'Estimated Person Days': [analysis_result.get('estimated_effort', {}).get('estimated_person_days', 0)],
                        'Analysis Date': [self._get_current_date()]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Step Analysis sheet
                    step_data = []
                    for step in analysis_result.get('step_analyses', []):
                        step_data.append({
                            'Step': step.get('step', ''),
                            'Difficulty': step.get('automation_difficulty', ''),
                            'Notes': step.get('notes', '')
                        })
                    
                    if step_data:
                        steps_df = pd.DataFrame(step_data)
                        steps_df.to_excel(writer, sheet_name='Step Analysis', index=False)
                    
                    # Recommendations sheet
                    recommendations_data = []
                    
                    # Add UFT libraries
                    for library in analysis_result.get('uft_libraries_list', []):
                        # Remove HTML tags
                        clean_library = library.replace('<strong>', '').replace('</strong>', '')
                        recommendations_data.append({
                            'Category': 'UFT Library',
                            'Recommendation': clean_library
                        })
                    
                    # Add approaches
                    for approach in analysis_result.get('suggested_approaches', []):
                        recommendations_data.append({
                            'Category': 'Implementation Approach',
                            'Recommendation': approach
                        })
                    
                    if recommendations_data:
                        recommendations_df = pd.DataFrame(recommendations_data)
                        recommendations_df.to_excel(writer, sheet_name='Recommendations', index=False)
                    
                    # Save and get the Excel data
                    writer.close()
                    output.seek(0)
                    export_data = output.getvalue()
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    filename = f"{test_case_number}_UFT_Analysis.xlsx"
                    
                except ImportError:
                    # If pandas is not available, fall back to JSON
                    import json
                    export_data = json.dumps(analysis_result, indent=2)
                    content_type = 'application/json'
                    filename = f"{test_case_number}_UFT_Analysis.json"
                    
            else:
                # Unsupported format
                return {
                    'status': 'error',
                    'message': f"Unsupported export format: {export_format}"
                }
            
            return {
                'status': 'success',
                'data': export_data,
                'content_type': content_type,
                'filename': filename,
                'message': f"Successfully exported analysis results as {export_format}"
            }
            
        except Exception as e:
            logger.error(f"Error exporting analysis results: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f"Error exporting analysis results: {str(e)}"
            }

