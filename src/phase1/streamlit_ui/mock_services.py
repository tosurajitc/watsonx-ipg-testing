"""
mock_services.py - Mock implementations of backend services for UI demonstration
"""
import pandas as pd
import random
from datetime import datetime, timedelta
import json
import time

# ====== MOCK DATA ======

# Sample requirements
MOCK_REQUIREMENTS = [
    {"id": "REQ-001", "title": "User Authentication", "source": "JIRA", "status": "Analyzed"},
    {"id": "REQ-002", "title": "Dashboard Creation", "source": "JIRA", "status": "Pending Analysis"},
    {"id": "REQ-003", "title": "Profile Management", "source": "File Upload", "status": "Analyzed"},
    {"id": "REQ-004", "title": "Payment Processing", "source": "Manual Input", "status": "Error"},
    {"id": "REQ-005", "title": "Reporting Module", "source": "JIRA", "status": "Analyzed"},
]

# Sample test cases
MOCK_TEST_CASES = [
    {
        "id": "TC-001",
        "title": "Verify login with valid credentials",
        "status": "Active",
        "owner": "John Doe",
        "type": "Automated",
        "steps": [
            {"step_no": 1, "description": "Navigate to login page", "expected": "Login page loads"},
            {"step_no": 2, "description": "Enter valid username", "expected": "Username accepted"},
            {"step_no": 3, "description": "Enter valid password", "expected": "Password accepted"},
            {"step_no": 4, "description": "Click login button", "expected": "User is logged in"},
        ],
    },
    {
        "id": "TC-002",
        "title": "Verify login with invalid credentials",
        "status": "Active",
        "owner": "Jane Smith",
        "type": "Manual",
        "steps": [
            {"step_no": 1, "description": "Navigate to login page", "expected": "Login page loads"},
            {"step_no": 2, "description": "Enter invalid username", "expected": "Username accepted"},
            {"step_no": 3, "description": "Enter invalid password", "expected": "Password accepted"},
            {"step_no": 4, "description": "Click login button", "expected": "Error message displayed"},
        ],
    },
    {
        "id": "TC-003",
        "title": "Verify dashboard widgets",
        "status": "Under Maintenance",
        "owner": "John Doe",
        "type": "Automated",
        "steps": [
            {"step_no": 1, "description": "Login to application", "expected": "Login successful"},
            {"step_no": 2, "description": "Navigate to dashboard", "expected": "Dashboard loads"},
            {"step_no": 3, "description": "Verify pending tasks widget", "expected": "Widget displays data"},
            {"step_no": 4, "description": "Verify recent activity widget", "expected": "Widget displays data"},
        ],
    },
    {
        "id": "TC-004",
        "title": "Verify profile updates",
        "status": "Obsolete",
        "owner": "Jane Smith",
        "type": "Manual",
        "steps": [
            {"step_no": 1, "description": "Login to application", "expected": "Login successful"},
            {"step_no": 2, "description": "Navigate to profile", "expected": "Profile page loads"},
            {"step_no": 3, "description": "Update profile information", "expected": "Updates accepted"},
            {"step_no": 4, "description": "Save changes", "expected": "Changes saved successfully"},
        ],
    },
    {
        "id": "TC-005",
        "title": "Verify payment processing",
        "status": "Active",
        "owner": "John Doe",
        "type": "Automated",
        "steps": [
            {"step_no": 1, "description": "Login to application", "expected": "Login successful"},
            {"step_no": 2, "description": "Navigate to payment page", "expected": "Payment page loads"},
            {"step_no": 3, "description": "Enter payment details", "expected": "Details accepted"},
            {"step_no": 4, "description": "Confirm payment", "expected": "Payment processed successfully"},
        ],
    },
]

# Sample execution runs
MOCK_EXECUTION_RUNS = [
    {
        "id": "RUN-001",
        "status": "Completed",
        "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "end_time": (datetime.now() - timedelta(days=1, hours=22)).isoformat(),
        "pass_count": 8,
        "fail_count": 2,
        "blocked_count": 0,
    },
    {
        "id": "RUN-002",
        "status": "In Progress",
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "pass_count": 3,
        "fail_count": 1,
        "blocked_count": 0,
    },
    {
        "id": "RUN-003",
        "status": "Failed",
        "start_time": (datetime.now() - timedelta(days=2)).isoformat(),
        "end_time": (datetime.now() - timedelta(days=2, hours=23)).isoformat(),
        "pass_count": 4,
        "fail_count": 6,
        "blocked_count": 0,
    },
]

# Sample defects
MOCK_DEFECTS = [
    {
        "id": "DEF-001",
        "summary": "Login page not loading on mobile devices",
        "status": "Open",
        "severity": "High",
        "assignee": "John Developer",
        "created_date": (datetime.now() - timedelta(days=3)).isoformat(),
    },
    {
        "id": "DEF-002",
        "summary": "Dashboard shows incorrect data",
        "status": "In Progress",
        "severity": "Medium",
        "assignee": "Jane Developer",
        "created_date": (datetime.now() - timedelta(days=2)).isoformat(),
    },
    {
        "id": "DEF-003",
        "summary": "Profile picture upload not working",
        "status": "Closed",
        "severity": "Low",
        "assignee": "John Developer",
        "created_date": (datetime.now() - timedelta(days=5)).isoformat(),
    },
]

# ====== MOCK SERVICE FUNCTIONS ======

def get_requirements():
    """Return mock requirements."""
    return MOCK_REQUIREMENTS

def get_test_cases():
    """Return mock test cases."""
    return MOCK_TEST_CASES

def get_execution_runs():
    """Return mock execution runs."""
    return MOCK_EXECUTION_RUNS

def get_defects():
    """Return mock defects."""
    return MOCK_DEFECTS

def get_test_case_by_id(test_case_id):
    """Return a specific test case by ID."""
    for tc in MOCK_TEST_CASES:
        if tc["id"] == test_case_id:
            return tc
    return None

def generate_test_cases_from_requirements(requirements_ids):
    """Generate mock test cases from requirements."""
    # Simulate processing time
    time.sleep(2)
    
    new_test_cases = []
    for req_id in requirements_ids:
        req = next((r for r in MOCK_REQUIREMENTS if r["id"] == req_id), None)
        if req:
            test_case_id = f"TC-{random.randint(100, 999)}"
            new_test_case = {
                "id": test_case_id,
                "title": f"Test case for {req['title']}",
                "status": "Active",
                "owner": "AI Generated",
                "type": "Manual",
                "steps": [
                    {"step_no": 1, "description": "Setup test environment", "expected": "Environment ready"},
                    {"step_no": 2, "description": f"Execute test for {req['title']}", "expected": "Test executed"},
                    {"step_no": 3, "description": "Verify results", "expected": "Results verified"},
                ],
            }
            new_test_cases.append(new_test_case)
    
    return new_test_cases

def refine_test_case(test_case_id, suggestions=None):
    """Mock function to refine a test case."""
    # Simulate processing time
    time.sleep(2)
    
    test_case = get_test_case_by_id(test_case_id)
    if not test_case:
        return None
    
    # Create a refined version with additional steps
    refined_test_case = test_case.copy()
    refined_test_case["steps"] = test_case["steps"].copy()
    refined_test_case["steps"].append({
        "step_no": len(test_case["steps"]) + 1,
        "description": "Perform additional validation",
        "expected": "Additional validation passed"
    })
    
    return refined_test_case

def compare_with_repository(test_case):
    """Mock function to compare test case with repository."""
    # Simulate processing time
    time.sleep(2)
    
    # Random match result
    match_type = random.choice(["exact", "partial", "new"])
    
    if match_type == "exact":
        # Find random existing test case
        existing_case = random.choice(MOCK_TEST_CASES)
        return {
            "result": "Exact Match Found",
            "existing_case": existing_case,
            "differences": []
        }
    elif match_type == "partial":
        # Find random existing test case
        existing_case = random.choice(MOCK_TEST_CASES)
        return {
            "result": "Partial Match Found",
            "existing_case": existing_case,
            "differences": [
                "Step 2 has different expected result",
                "Missing validation step",
                "Different test data referenced"
            ]
        }
    else:
        return {
            "result": "New Test Case",
            "existing_case": None,
            "differences": []
        }

def execute_test_cases(test_case_ids, execution_mode="Automated"):
    """Mock function to execute test cases."""
    # Simulate processing time
    time.sleep(3)
    
    # Create new execution run
    run_id = f"RUN-{random.randint(100, 999)}"
    
    if execution_mode == "Automated":
        # Simulate automated execution results
        pass_count = random.randint(0, len(test_case_ids))
        fail_count = len(test_case_ids) - pass_count
        
        execution_run = {
            "id": run_id,
            "status": "Completed",
            "start_time": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "blocked_count": 0,
        }
    else:
        # Simulate manual execution setup
        execution_run = {
            "id": run_id,
            "status": "Pending",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "pass_count": 0,
            "fail_count": 0,
            "blocked_count": len(test_case_ids),
        }
    
    # Add to mock execution runs
    MOCK_EXECUTION_RUNS.append(execution_run)
    
    return execution_run

def analyze_failure(test_case_id, step_no):
    """Mock function to analyze a test failure."""
    # Simulate processing time
    time.sleep(2)
    
    # Generate random analysis results
    analyses = [
        {
            "potential_causes": [
                "Database connection timeout",
                "Invalid test data",
                "Environment configuration issue"
            ],
            "remediation": [
                "Check database connectivity",
                "Verify test data is up to date",
                "Review environment configuration"
            ]
        },
        {
            "potential_causes": [
                "UI element not found",
                "Page load timeout",
                "JavaScript error"
            ],
            "remediation": [
                "Update element locator",
                "Increase timeout values",
                "Check browser console for JavaScript errors"
            ]
        },
        {
            "potential_causes": [
                "API returned unexpected response",
                "Authorization token expired",
                "Rate limit exceeded"
            ],
            "remediation": [
                "Verify API contract",
                "Implement token refresh mechanism",
                "Implement rate limiting handling"
            ]
        }
    ]
    
    return random.choice(analyses)

def create_defect(test_case_id, step_no, error_details):
    """Mock function to create a defect."""
    # Simulate processing time
    time.sleep(1)
    
    # Get test case
    test_case = get_test_case_by_id(test_case_id)
    if not test_case:
        return None
    
    # Create new defect
    defect_id = f"DEF-{random.randint(100, 999)}"
    step = next((s for s in test_case["steps"] if s["step_no"] == step_no), None)
    
    if step:
        defect = {
            "id": defect_id,
            "summary": f"Test Case {test_case_id} failed at step {step_no}: {step['description']}",
            "status": "Open",
            "severity": random.choice(["High", "Medium", "Low"]),
            "assignee": random.choice(["John Developer", "Jane Developer"]),
            "created_date": datetime.now().isoformat(),
        }
        
        # Add to mock defects
        MOCK_DEFECTS.append(defect)
        
        return defect
    
    return None

def generate_code_snippet(language, description):
    """Mock function to generate code snippets."""
    # Simulate processing time
    time.sleep(2)
    
    if language == "python":
        return """
# Python code for web automation
from selenium import webdriver
from selenium.webdriver.common.by import By

def test_login():
    # Initialize driver
    driver = webdriver.Chrome()
    
    # Navigate to login page
    driver.get("https://example.com/login")
    
    # Enter credentials
    driver.find_element(By.ID, "username").send_keys("test_user")
    driver.find_element(By.ID, "password").send_keys("password123")
    
    # Click login button
    driver.find_element(By.ID, "login-button").click()
    
    # Verify login success
    assert "Dashboard" in driver.title
    
    # Close driver
    driver.quit()
"""
    elif language == "javascript":
        return """
// JavaScript code for web automation
const { Builder, By, Key, until } = require('selenium-webdriver');

async function testLogin() {
  let driver = await new Builder().forBrowser('chrome').build();
  try {
    // Navigate to login page
    await driver.get('https://example.com/login');
    
    // Enter credentials
    await driver.findElement(By.id('username')).sendKeys('test_user');
    await driver.findElement(By.id('password')).sendKeys('password123');
    
    // Click login button
    await driver.findElement(By.id('login-button')).click();
    
    // Verify login success
    await driver.wait(until.titleContains('Dashboard'), 5000);
  } finally {
    await driver.quit();
  }
}

testLogin();
"""
    elif language == "uft":
        return """
' UFT code for web automation
Browser("Login").Page("Login").WebEdit("username").Set "test_user"
Browser("Login").Page("Login").WebEdit("password").Set "password123"
Browser("Login").Page("Login").WebButton("login-button").Click

' Verify login success
If Browser("Login").Page("Dashboard").Exist(5) Then
    Reporter.ReportEvent micPass, "Login Test", "Successfully logged in"
Else
    Reporter.ReportEvent micFail, "Login Test", "Failed to login"
End If
"""
    else:
        return f"// Code generation for {language} is not supported yet."

def check_uft_automation_potential(test_case_id):
    """Mock function to check UFT automation potential."""
    # Simulate processing time
    time.sleep(1)
    
    # Get test case
    test_case = get_test_case_by_id(test_case_id)
    if not test_case:
        return None
    
    # Random assessment
    assessments = [
        {
            "potential": "High",
            "reasons": [
                "Standard UI elements",
                "Predictable application behavior",
                "Well-defined test steps"
            ],
            "suggested_libraries": [
                "UFT Web Extension",
                "UFT Standard Library"
            ]
        },
        {
            "potential": "Medium",
            "reasons": [
                "Custom UI components",
                "Some dynamic elements",
                "Moderate complexity"
            ],
            "suggested_libraries": [
                "UFT Web Extension",
                "UFT Advanced Library",
                "Custom Object Recognition"
            ]
        },
        {
            "potential": "Low",
            "reasons": [
                "Complex visual validations",
                "Highly dynamic UI",
                "Integration with third-party components"
            ],
            "suggested_libraries": [
                "UFT Advanced Library",
                "Custom Framework Development",
                "Consider API testing instead"
            ]
        }
    ]
    
    return random.choice(assessments)

def generate_report():
    """Mock function to generate a report."""
    # Simulate processing time
    time.sleep(2)
    
    # Create mock report data
    report_data = {
        "report_id": f"REP-{random.randint(100, 999)}",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_test_cases": len(MOCK_TEST_CASES),
            "total_executions": len(MOCK_EXECUTION_RUNS),
            "pass_rate": f"{random.randint(70, 95)}%",
            "total_defects": len(MOCK_DEFECTS),
            "open_defects": sum(1 for d in MOCK_DEFECTS if d["status"] == "Open"),
        },
        "test_execution_summary": [
            {
                "run_id": run["id"],
                "status": run["status"],
                "pass_count": run["pass_count"],
                "fail_count": run["fail_count"],
                "blocked_count": run["blocked_count"],
            }
            for run in MOCK_EXECUTION_RUNS
        ],
        "defect_summary": [
            {
                "severity": "High",
                "count": sum(1 for d in MOCK_DEFECTS if d["severity"] == "High"),
            },
            {
                "severity": "Medium",
                "count": sum(1 for d in MOCK_DEFECTS if d["severity"] == "Medium"),
            },
            {
                "severity": "Low",
                "count": sum(1 for d in MOCK_DEFECTS if d["severity"] == "Low"),
            },
        ],
    }
    
    return report_data

def get_integration_status():
    """Return mock integration status."""
    return {
        "jira": random.choice([True, False]),
        "sharepoint": random.choice([True, False]),
        "alm": random.choice([True, False]),
        "watson": random.choice([True, False])
    }

def connect_integration(integration_type, credentials):
    """Mock function to connect to an integration."""
    # Simulate processing time
    time.sleep(1)
    
    # 80% chance of success
    success = random.random() < 0.8
    
    if success:
        return {
            "status": "connected",
            "message": f"Successfully connected to {integration_type}"
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to connect to {integration_type}. Please check credentials."
        }

def get_pending_tasks():
    """Return mock pending tasks."""
    return [
        {"id": "TASK-001", "type": "Review", "description": "Review suggested changes for TC-003", "priority": "High"},
        {"id": "TASK-002", "type": "Approve", "description": "Approve new test case TC-007", "priority": "Medium"},
        {"id": "TASK-003", "type": "Execute", "description": "Execute manual test TC-002", "priority": "Low"},
    ]

def get_recent_activity():
    """Return mock recent activity."""
    return [
        {"id": "ACT-001", "type": "Generation", "description": "Generated 3 test cases from REQ-001", "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()},
        {"id": "ACT-002", "type": "Execution", "description": "Executed test run RUN-002", "timestamp": (datetime.now() - timedelta(hours=3)).isoformat()},
        {"id": "ACT-003", "type": "Defect", "description": "Created defect DEF-002", "timestamp": (datetime.now() - timedelta(hours=5)).isoformat()},
    ]