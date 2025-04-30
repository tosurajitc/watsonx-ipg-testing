import streamlit as st
import pandas as pd
from typing import Dict, List, Optional




#################### Testing blocl
import streamlit as st
import time
from ui_utils import show_info_message, show_success_message, show_error_message
from state_management import add_notification
import mock_services

def show_automation():
    """Display the code and automation module UI."""
    st.header("Code & Automation Module")
    
    # Create tabs for different functions
    tabs = st.tabs(["Code Generation Agent", "UFT Automation Check"])
    
    with tabs[0]:
        show_code_generation()
    
    with tabs[1]:
        show_uft_automation_check()

def show_code_generation():
    """Display the code generation agent tab."""
    st.subheader("Code Generation Agent")
    
    # Input for code generation
    code_request = st.text_area(
        "Describe the function/action needed",
        placeholder="E.g., Generate Python Selenium code to click button with ID 'submit'",
        height=100
    )
    
    # Language selection
    language_options = ["python", "javascript", "uft", "java", "c#"]
    language = st.selectbox(
        "Select Target Language/Framework",
        options=language_options
    )
    
    # Generate button
    if code_request:
        if st.button("Generate Code", key="generate_code_button"):
            with st.spinner("Generating code..."):
                # Simulate processing time
                time.sleep(3)
                
                # Use mock service to generate code
                generated_code = mock_services.generate_code_snippet(language, code_request)
                
                # Store in session state
                st.session_state["generated_code"] = generated_code
                st.session_state["code_language"] = language
                
                show_success_message("Code generated successfully!")
    
    # Display generated code if available
    if "generated_code" in st.session_state:
        st.markdown("---")
        st.subheader("Generated Code")
        
        # Display code
        with st.expander("Code Snippet", expanded=True):
            st.code(st.session_state["generated_code"], language=st.session_state["code_language"])
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Copy Code", key="copy_code_button"):
                # Can't actually copy to clipboard in Streamlit, but we can show a message
                show_success_message("Code copied to clipboard!")
        
        with col2:
            if st.button("Refine Request", key="refine_request_button"):
                # Clear the generated code to allow for refinement
                del st.session_state["generated_code"]
                del st.session_state["code_language"]
                show_info_message("Please modify your request and generate again.")
                st.experimental_rerun()

def show_uft_automation_check():
    """Display the UFT automation check tab."""
    st.subheader("UFT Automation Check")
    
    # Test case selection for automation check
    test_cases = st.session_state.get("current_test_cases", mock_services.get_test_cases())
    
    test_case_id = st.selectbox(
        "Select a Test Case from the Repository",
        options=[tc["id"] for tc in test_cases],
        format_func=lambda x: f"{x}: {next((tc['title'] for tc in test_cases if tc['id'] == x), '')}"
    )
    
    # Check automation potential button
    if st.button("Analyze for UFT Automation Potential", key="check_automation_button"):
        with st.spinner("Analyzing automation potential..."):
            # Simulate processing time
            time.sleep(3)
            
            # Use mock service to check automation potential
            automation_assessment = mock_services.check_uft_automation_potential(test_case_id)
            
            # Store in session state
            st.session_state["automation_assessment"] = automation_assessment
            
            show_success_message("Analysis complete!")
    
    # Display assessment if available
    if "automation_assessment" in st.session_state:
        st.markdown("---")
        st.subheader("UFT Automation Assessment")
        
        assessment = st.session_state["automation_assessment"]
        
        # Display potential level with appropriate color
        potential = assessment["potential"]
        if potential == "High":
            st.success(f"Automation Potential: {potential}")
        elif potential == "Medium":
            st.warning(f"Automation Potential: {potential}")
        else:  # Low
            st.error(f"Automation Potential: {potential}")
        
        # Display reasons
        st.markdown("### Reasons")
        for reason in assessment["reasons"]:
            st.markdown(f"- {reason}")
        
        # Display suggested libraries
        st.markdown("### Suggested UFT Libraries/Approaches")
        for library in assessment["suggested_libraries"]:
            st.markdown(f"- {library}")
        
        # Generate UFT code button
        if st.button("Generate UFT Code Template", key="generate_uft_template_button"):
            with st.spinner("Generating UFT code template..."):
                # Simulate processing time
                time.sleep(2)
                
                # Generate UFT code using mock service
                uft_code = mock_services.generate_code_snippet("uft", f"Automate test case {test_case_id}")
                
                # Store in session state
                st.session_state["generated_code"] = uft_code
                st.session_state["code_language"] = "vbscript"  # UFT uses VBScript
                
                # Navigate to code generation tab
                st.session_state["active_automation_tab"] = 0
                add_notification(f"Generated UFT code template for {test_case_id}", "success")
                st.experimental_rerun()


################### Testing block endss here

class CodeAndAutomationUI:
    def __init__(self):
        """
        Initialize the Code & Automation Module UI
        """
        self.programming_languages = [
            "Python", 
            "JavaScript", 
            "Java", 
            "C#", 
            "Ruby", 
            "TypeScript"
        ]
        
        self.automation_frameworks = {
            "Python": ["Selenium", "Pytest", "Robot Framework"],
            "JavaScript": ["Cypress", "Puppeteer", "Selenium WebDriver"],
            "Java": ["Selenium", "TestNG", "Cucumber"],
            "C#": [".NET Selenium", "SpecFlow", "Coded UI"],
            "Ruby": ["Watir", "Capybara", "RSpec"],
            "TypeScript": ["Playwright", "Cypress", "Selenium"]
        }
        
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[Dict]:
        """
        Load test cases for UFT automation analysis
        
        Returns:
            List of test case dictionaries
        """
        # Placeholder for actual test case loading
        return [
            {
                "id": "TC-001",
                "name": "User Login",
                "description": "Validate user login functionality",
                "complexity": "Low",
                "ui_elements": ["Login Form", "Username Field", "Password Field", "Submit Button"]
            },
            {
                "id": "TC-002",
                "name": "Product Search",
                "description": "Search for a product in the catalog",
                "complexity": "Medium", 
                "ui_elements": ["Search Bar", "Search Button", "Filter Dropdowns", "Results Grid"]
            },
            {
                "id": "TC-003",
                "name": "Complex Workflow",
                "description": "Multi-step checkout process",
                "complexity": "High",
                "ui_elements": ["Cart", "Shipping Form", "Payment Gateway", "Confirmation Page"]
            }
        ]

    def render_code_generation_section(self):
        """
        Render the code generation interface
        """
        st.subheader("Code Generation")
        
        # Input for code generation request
        generation_prompt = st.text_area(
            "Describe the function/action you need code for:",
            placeholder="e.g., Generate Python Selenium code to click button with ID 'submit'"
        )
        
        # Language and framework selection
        col1, col2 = st.columns(2)
        
        with col1:
            selected_language = st.selectbox(
                "Select Programming Language", 
                options=self.programming_languages
            )
        
        with col2:
            # Dynamically update frameworks based on selected language
            selected_framework = st.selectbox(
                "Select Framework", 
                options=self.automation_frameworks.get(selected_language, ["No frameworks available"])
            )
        
        # Generate code button
        if st.button("Generate Code"):
            if generation_prompt:
                # Placeholder for actual code generation
                # In real implementation, this would call a code generation service
                generated_code = self._generate_code_snippet(
                    generation_prompt, 
                    selected_language, 
                    selected_framework
                )
                
                # Display generated code
                st.code(generated_code, language=selected_language.lower())
                
                # Refinement and export options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Copy Code"):
                        st.code(generated_code)
                
                with col2:
                    if st.button("Refine Code"):
                        st.text_area("Refine your request", value=generation_prompt)
            else:
                st.warning("Please provide a code generation prompt")

    def _generate_code_snippet(self, prompt: str, language: str, framework: str) -> str:
        """
        Generate a code snippet based on the prompt
        
        Args:
            prompt (str): User's code generation request
            language (str): Selected programming language
            framework (str): Selected framework
        
        Returns:
            str: Generated code snippet
        """
        # Placeholder implementation with example code generations
        if language == "Python" and framework == "Selenium":
            return f'''
# Code for: {prompt}
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def click_submit_button():
    """Click submit button with specific ID"""
    driver = webdriver.Chrome()  # or appropriate WebDriver
    driver.get("https://example.com")
    
    # Wait for button to be clickable
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "submit"))
    )
    submit_button.click()
    
    # Add additional logic as needed
    driver.quit()

# Call the function
click_submit_button()
'''
        elif language == "JavaScript" and framework == "Cypress":
            return f'''
// Code for: {prompt}
describe('Submit Button Test', () => {{
  it('clicks submit button', () => {{
    cy.visit('https://example.com')
    cy.get('#submit').click()
    // Add assertions or additional actions
  }})
}})
'''
        else:
            return f"// Placeholder code for {prompt} in {language} with {framework}"

    def render_uft_automation_analysis(self):
        """
        Render UFT automation potential analysis section
        """
        st.subheader("UFT Automation Feasibility")
        
        # Select test case for UFT automation analysis
        selected_test_case = st.selectbox(
            "Select Test Case for UFT Automation Analysis",
            options=[f"{tc['id']} - {tc['name']}" for tc in self.test_cases]
        )
        
        # Analyze button
        if st.button("Analyze UFT Automation Potential"):
            # Find selected test case
            test_case = next(
                (tc for tc in self.test_cases 
                 if f"{tc['id']} - {tc['name']}" == selected_test_case), 
                None
            )
            
            if test_case:
                # Placeholder for actual UFT automation analysis
                automation_assessment = self._analyze_uft_automation_potential(test_case)
                
                # Display assessment
                st.markdown("### Automation Potential Assessment")
                
                # Visualization of assessment
                assessment_data = {
                    "Potential Level": automation_assessment['potential_level'],
                    "Complexity": test_case['complexity'],
                    "UI Elements Count": len(test_case['ui_elements'])
                }
                
                # Create DataFrame for display
                df = pd.DataFrame.from_dict(assessment_data, orient='index', columns=['Value'])
                st.dataframe(df)
                
                # Detailed assessment
                st.markdown("#### Detailed Analysis")
                st.write(automation_assessment['detailed_analysis'])
                
                # Recommended UFT libraries/approaches
                st.markdown("#### Recommended UFT Libraries/Approaches")
                for approach in automation_assessment['recommended_approaches']:
                    st.markdown(f"- {approach}")

    def _analyze_uft_automation_potential(self, test_case: Dict) -> Dict:
        """
        Analyze UFT automation potential for a given test case
        
        Args:
            test_case (Dict): Test case details
        
        Returns:
            Dict: Automation potential assessment
        """
        # Determine automation potential based on complexity and UI elements
        complexity_map = {
            "Low": 0.8,
            "Medium": 0.6,
            "High": 0.3
        }
        
        # Calculate potential based on complexity and number of UI elements
        potential_score = (
            complexity_map.get(test_case['complexity'], 0.5) * 
            (1 + len(test_case['ui_elements']) / 10)
        )
        
        # Determine potential level
        if potential_score > 0.7:
            potential_level = "High"
            recommended_approaches = [
                "Standard UFT Object Recognition",
                "Keyword-driven Testing",
                "Minimal Custom Scripting Required"
            ]
        elif potential_score > 0.4:
            potential_level = "Medium"
            recommended_approaches = [
                "Hybrid Object Recognition",
                "Moderate Custom Object Mapping",
                "Selective Keyword-driven Approach"
            ]
        else:
            potential_level = "Low"
            recommended_approaches = [
                "Complex Visual Verification Needed",
                "Significant Custom Scripting Required",
                "Consider Alternative Automation Strategies"
            ]
        
        return {
            "potential_level": potential_level,
            "detailed_analysis": f"""
Automation Potential for Test Case {test_case['id']}:
- Complexity: {test_case['complexity']}
- Number of UI Elements: {len(test_case['ui_elements'])}
- Assessment: {potential_level} potential for UFT automation
            """.strip(),
            "recommended_approaches": recommended_approaches
        }

    def render(self):
        """
        Render the entire Code & Automation Module UI
        """
        st.title("Code & Automation Module")
        
        # Create tabs for different functionalities
        tab1, tab2 = st.tabs([
            "Code Generation", 
            "UFT Automation Analysis"
        ])
        
        with tab1:
            self.render_code_generation_section()
        
        with tab2:
            self.render_uft_automation_analysis()

def main():
    """
    Main function to run the Code & Automation Module
    """
    automation_ui = CodeAndAutomationUI()
    automation_ui.render()

if __name__ == "__main__":
    main()