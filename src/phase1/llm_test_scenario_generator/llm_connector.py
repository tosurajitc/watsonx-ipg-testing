"""
LLM Connector Module for the LLM Test Scenario Generator.

This module connects to various LLM services (GROQ initially, watsonx later)
and manages prompts for test scenario generation.

The module reads API keys and endpoint configuration from environment variables
to avoid hardcoding sensitive information.

Usage:
    connector = LLMConnector()
    response = await connector.generate_completion(prompt)
"""

import os
import json
import logging
import httpx
import asyncio
import time
from typing import Dict, List, Any, Union, Optional, Tuple
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class LLMConnector:
    """Class for connecting to LLM services and managing prompts."""

    # Default models for different services
    DEFAULT_MODELS = {
        "groq": "llama3-70b-8192",  # Default GROQ model
        "watsonx": "ibm/granite-13b-chat-v2",  # Default watsonx model
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM Connector.

        Args:
            config: Optional configuration dictionary that can override .env settings
        """
        # Load environment variables from .env file
        load_dotenv()
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Initialize connector configuration
        self.initialize_config()
        
        # Set up HTTP client for API calls
        self.client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for LLM calls

    def setup_logging(self) -> None:
        """Configure logging for the LLM connector."""
        log_level = self.config.get('log_level', logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def initialize_config(self) -> None:
        """Initialize configuration from environment variables and provided config."""
        # Determine which LLM service to use
        self.llm_service = self.config.get("llm_service") or os.getenv("LLM_SERVICE", "groq").lower()
        self.logger.info(f"Using LLM service: {self.llm_service}")
        
        # Set up service-specific configuration
        if self.llm_service == "groq":
            self.setup_groq_config()
        elif self.llm_service == "watsonx":
            self.setup_watsonx_config()
        else:
            self.logger.error(f"Unsupported LLM service: {self.llm_service}")
            raise ValueError(f"Unsupported LLM service: {self.llm_service}")
        
        # General LLM parameters (can be overridden by specific calls)
        self.temperature = self.config.get("temperature") or float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = self.config.get("max_tokens") or int(os.getenv("LLM_MAX_TOKENS", "8000"))
        self.top_p = self.config.get("top_p") or float(os.getenv("LLM_TOP_P", "0.8"))

    def setup_groq_config(self) -> None:
        """Set up configuration for GROQ API."""
        self.api_key = self.config.get("api_key") or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            self.logger.error("GROQ API key not found in environment variables or config")
            raise ValueError("GROQ API key not found. Set GROQ_API_KEY environment variable or provide in config")
        
        # FIX: Set api_base without the /chat/completions part
        self.api_base = self.config.get("api_base") or os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
        print(f"DEBUG - API Base: {self.api_base}")
        self.model = self.config.get("model") or os.getenv("GROQ_MODEL", self.DEFAULT_MODELS["groq"])
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # FIX: Now correctly construct the chat endpoint URL
        self.chat_endpoint = f"{self.api_base}/chat/completions"
        print(f"DEBUG - Chat Endpoint: {self.chat_endpoint}")
        self.logger.info(f"GROQ configuration set up with model: {self.model}")

    def setup_watsonx_config(self) -> None:
        """Set up configuration for watsonx API."""
        self.api_key = self.config.get("api_key") or os.getenv("WATSONX_API_KEY")
        if not self.api_key:
            self.logger.error("watsonx API key not found in environment variables or config")
            raise ValueError("watsonx API key not found. Set WATSONX_API_KEY environment variable or provide in config")
        
        self.ibm_cloud_url = self.config.get("ibm_cloud_url") or os.getenv(
            "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
        )
        self.project_id = self.config.get("project_id") or os.getenv("WATSONX_PROJECT_ID")
        self.model = self.config.get("model") or os.getenv("WATSONX_MODEL", self.DEFAULT_MODELS["watsonx"])
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # watsonx API endpoints
        self.api_base = f"{self.ibm_cloud_url}/ml/v1-beta/generation"
        self.logger.info(f"watsonx configuration set up with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def generate_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a completion using the configured LLM service.

        Args:
            prompt: The main prompt text
            system_prompt: Optional system prompt (for chat models)
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            top_p: Optional top_p override
            stream: Whether to stream the response

        Returns:
            Dictionary containing the LLM response
        """
        # Use provided parameters or fall back to defaults
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        top_p = top_p if top_p is not None else self.top_p
        
        if self.llm_service == "groq":
            return await self._generate_groq_completion(
                prompt, system_prompt, temperature, max_tokens, top_p, stream
            )
        elif self.llm_service == "watsonx":
            return await self._generate_watsonx_completion(
                prompt, system_prompt, temperature, max_tokens, top_p, stream
            )
        else:
            self.logger.error(f"Unsupported LLM service for completion: {self.llm_service}")
            raise ValueError(f"Unsupported LLM service: {self.llm_service}")

    async def _generate_groq_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8000,
        top_p: float = 0.8,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate completion using GROQ API.

        Args:
            prompt: The main prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            stream: Whether to stream the response

        Returns:
            Dictionary containing the GROQ response
        """
        start_time = time.time()
        self.logger.info(f"Generating completion with GROQ, model: {self.model}")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        try:
            # DEBUG: Log the exact URL being used
            self.logger.debug(f"Sending request to URL: {self.chat_endpoint}")
            
            response = await self.client.post(
                self.chat_endpoint,
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            response_data = response.json()
            
            # Log time and token usage
            elapsed_time = time.time() - start_time
            input_tokens = response_data.get("usage", {}).get("prompt_tokens", -1)
            output_tokens = response_data.get("usage", {}).get("completion_tokens", -1)
            
            self.logger.info(
                f"GROQ completion generated in {elapsed_time:.2f}s, "
                f"input tokens: {input_tokens}, output tokens: {output_tokens}"
            )
            
            # Extract and return the relevant completion text
            completion_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "text": completion_text,
                "raw_response": response_data,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "elapsed_time": elapsed_time
            }
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error occurred while calling GROQ API: {e.response.text}")
            raise
        except (httpx.RequestError, json.JSONDecodeError) as e:
            self.logger.error(f"Error occurred while calling GROQ API: {str(e)}")
            raise

    async def _generate_watsonx_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8000,
        top_p: float = 0.8,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate completion using watsonx API.

        Args:
            prompt: The main prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            stream: Whether to stream the response

        Returns:
            Dictionary containing the watsonx response
        """
        start_time = time.time()
        self.logger.info(f"Generating completion with watsonx, model: {self.model}")
        
        # Combine system prompt and user prompt for watsonx
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        full_prompt += prompt
        
        # watsonx API requires project_id for authorization
        if not self.project_id:
            self.logger.error("watsonx project ID not found in environment variables or config")
            raise ValueError("watsonx project ID not found. Set WATSONX_PROJECT_ID environment variable")
        
        # Construct payload based on watsonx API requirements
        payload = {
            "model_id": self.model,
            "input": full_prompt,
            "parameters": {
                "decoding_method": "greedy",
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "top_p": top_p,
                "repetition_penalty": 1.1,
                "stop_sequences": []
            },
            "project_id": self.project_id
        }
        
        try:
            response = await self.client.post(
                self.api_base,
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            response_data = response.json()
            
            # Extract generated text from watsonx response
            generated_text = response_data.get("results", [{}])[0].get("generated_text", "")
            
            # Log timing information
            elapsed_time = time.time() - start_time
            self.logger.info(f"watsonx completion generated in {elapsed_time:.2f}s")
            
            return {
                "text": generated_text,
                "raw_response": response_data,
                "elapsed_time": elapsed_time,
                # watsonx might not provide token counts in the same way as OpenAI/GROQ
                "input_tokens": -1,  
                "output_tokens": -1
            }
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error occurred while calling watsonx API: {e.response.text}")
            raise
        except (httpx.RequestError, json.JSONDecodeError) as e:
            self.logger.error(f"Error occurred while calling watsonx API: {str(e)}")
            raise

    # ==== Prompt Management Methods ====

    async def generate_test_scenarios(
        self, 
        requirements: Dict[str, Any],
        num_scenarios: int = 5,
        detail_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate test scenarios from requirements using the LLM.

        Args:
            requirements: Dictionary of requirements (from document_processor)
            num_scenarios: Number of scenarios to generate
            detail_level: Level of detail for scenarios ("low", "medium", "high")

        Returns:
            Dictionary containing generated test scenarios
        """
        self.logger.info(f"Generating {num_scenarios} test scenarios with {detail_level} detail level")
        
        # Prepare prompt for test scenario generation
        system_prompt = self._get_scenario_system_prompt()
        user_prompt = self._get_scenario_user_prompt(requirements, num_scenarios, detail_level)
        
        # Generate completion
        response = await self.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4  # Slightly higher temperature for creative scenarios
        )
        
        # Process and structure the response
        scenarios = self._parse_scenario_response(response["text"])
        
        return {
            "scenarios": scenarios,
            "metadata": {
                "num_requested": num_scenarios,
                "num_generated": len(scenarios),
                "detail_level": detail_level,
                "requirements_source": requirements.get("document_type", "unknown"),
                "model_used": self.model,
                "elapsed_time": response.get("elapsed_time", -1)
            },
            "raw_llm_response": response["text"]
        }

    def _get_scenario_system_prompt(self) -> str:
        """Get the system prompt for test scenario generation."""
        return """You are an expert test engineer specialized in converting software requirements into comprehensive test scenarios. Your task is to analyze the provided requirements and create detailed, testable scenarios that would verify the system works as expected.

Focus on:
1. Full coverage of functional and non-functional requirements
2. Edge cases and exception paths
3. Realistic user workflows
4. Clear, measurable outcomes
5. Scenarios that can be further broken down into specific test cases

Format each test scenario with:
- Test Scenario ID (TS-XXX-YY format)
- Title (concise description)
- Description (detailed explanation)
- Related requirements (if provided in the input)
- Priority (High/Medium/Low based on business impact)"""

    def _get_scenario_user_prompt(
        self,
        requirements: Dict[str, Any],
        num_scenarios: int = 5,
        detail_level: str = "medium"
    ) -> str:
        """
        Generate the user prompt for test scenario generation.

        Args:
            requirements: Dictionary of requirements (from document_processor)
            num_scenarios: Number of scenarios to generate
            detail_level: Level of detail for scenarios ("low", "medium", "high")

        Returns:
            Formatted user prompt for the LLM
        """
        prompt = f"Please create {num_scenarios} test scenarios with {detail_level} level of detail based on the following requirements:\n\n"
        
        # Add user stories if available
        if requirements.get("user_stories"):
            prompt += "USER STORIES:\n"
            for idx, story in enumerate(requirements["user_stories"], 1):
                prompt += f"{idx}. As a {story.get('role', 'user')}, I want {story.get('goal', '')} so that {story.get('benefit', '')}\n"
            prompt += "\n"
        
        # Add requirements if available
        if requirements.get("requirements"):
            prompt += "REQUIREMENTS:\n"
            for idx, req in enumerate(requirements["requirements"], 1):
                req_id = req.get("id", f"REQ-{idx}")
                req_text = req.get("text", "")
                req_type = req.get("type", "")
                
                prompt += f"{req_id}: {req_text}"
                if req_type:
                    prompt += f" [Type: {req_type}]"
                prompt += "\n"
            prompt += "\n"
        
        # Add acceptance criteria if available
        if requirements.get("acceptance_criteria"):
            prompt += "ACCEPTANCE CRITERIA:\n"
            for idx, criteria in enumerate(requirements["acceptance_criteria"], 1):
                prompt += f"{idx}. {criteria}\n"
            prompt += "\n"
        
        # If none of the structured data is available, add raw text
        if not (requirements.get("user_stories") or requirements.get("requirements") or requirements.get("acceptance_criteria")):
            if requirements.get("raw_text"):
                prompt += "REQUIREMENTS TEXT:\n"
                prompt += requirements["raw_text"][:2000]  # Limit to avoid token overflow
                prompt += "\n\n"
        
        # Add instructions based on detail level
        if detail_level == "low":
            prompt += "Create basic test scenarios covering the main functionality. Keep descriptions brief.\n\n"
        elif detail_level == "high":
            prompt += "Create comprehensive test scenarios with detailed descriptions. Cover edge cases, negative testing, and all possible user workflows.\n\n"
        else:  # medium
            prompt += "Create balanced test scenarios covering key functionality and common edge cases. Include clear descriptions.\n\n"
        
        prompt += """Format each test scenario as follows:

Test Scenario ID: TS-XXX-YY (where XXX relates to the requirement/story ID if available)
Title: [Brief descriptive title]
Description: [Detailed description explaining what needs to be tested]
Related Requirements: [List related requirement IDs]
Priority: [High/Medium/Low]

Ensure each scenario is testable and has clear pass/fail criteria."""
        
        return prompt

    def _parse_scenario_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract structured test scenarios.

        Args:
            response_text: Raw text response from LLM

        Returns:
            List of dictionaries containing structured test scenarios
        """
        scenarios = []
        current_scenario = {}
        
        # Define common field names and possible variations
        field_patterns = {
            "id": ["Test Scenario ID:", "Scenario ID:", "ID:"],
            "title": ["Title:"],
            "description": ["Description:"],
            "related_requirements": ["Related Requirements:", "Requirements:", "Requirement ID:"],
            "priority": ["Priority:"]
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new scenario
            if any(pattern in line for pattern in field_patterns["id"]):
                # Save previous scenario if it exists
                if current_scenario and "id" in current_scenario:
                    scenarios.append(current_scenario)
                
                # Start new scenario
                current_scenario = {}
                for pattern in field_patterns["id"]:
                    if pattern in line:
                        current_scenario["id"] = line.split(pattern)[1].strip()
                        break
            
            # Process other fields
            else:
                for field, patterns in field_patterns.items():
                    if field != "id":  # ID is handled separately above
                        for pattern in patterns:
                            if line.startswith(pattern):
                                value = line.split(pattern)[1].strip()
                                current_scenario[field] = value
                                break
                
                # If not a field header, could be continuation of description
                if "description" in current_scenario and not any(p in line for p in [item for sublist in field_patterns.values() for item in sublist]):
                    if not line.startswith("-") and not line[0].isdigit():
                        current_scenario["description"] += f" {line}"
        
        # Add the last scenario if it exists
        if current_scenario and "id" in current_scenario:
            scenarios.append(current_scenario)
        
        return scenarios

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        connector = LLMConnector()
        
        # Example requirements for testing
        requirements = {
            "document_type": "text",
            "requirements": [
                {"id": "REQ-1", "text": "The system shall authenticate users with username and password.", "type": "functional"},
                {"id": "REQ-2", "text": "The system shall implement two-factor authentication using mobile OTP.", "type": "functional"}
            ],
            "user_stories": [
                {"role": "banking user", "goal": "authenticate securely", "benefit": "my account remains protected"}
            ],
            "acceptance_criteria": [
                "Users can log in with valid credentials",
                "OTP is sent to registered mobile number",
                "Invalid login attempts are limited to 3 before account lockout"
            ]
        }
        
        try:
            scenarios = await connector.generate_test_scenarios(requirements, num_scenarios=2)
            print(json.dumps(scenarios, indent=2))
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            await connector.close()
    
    asyncio.run(example())