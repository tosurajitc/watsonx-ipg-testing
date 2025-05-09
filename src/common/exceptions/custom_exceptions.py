"""
Custom exceptions for the Watsonx IPG Testing project.

This module defines all custom exceptions used throughout the application to provide
clear error handling and meaningful error messages for various error scenarios.
"""


class WatsonxIPGError(Exception):
    """Base exception class for all Watsonx IPG Testing related errors."""
    def __init__(self, message="An error occurred in the Watsonx IPG Testing system"):
        self.message = message
        super().__init__(self.message)




# Repository Scanning Exceptions
class RepositoryScanError(WatsonxIPGError):
    """Base class for repository scanning related exceptions."""
    def __init__(self, message="Repository scanning operation failed"):
        super().__init__(message)


class RepositoryAccessError(RepositoryScanError):
    """Raised when there's an error accessing the repository."""
    def __init__(self, repository_name=None, reason=None, message=None):
        if message is None:
            base_msg = f"Failed to access repository: {repository_name}" if repository_name else "Repository access failed"
            message = f"{base_msg} - {reason}" if reason else base_msg
        super().__init__(message)
        self.repository_name = repository_name
        self.reason = reason


class RepositoryIndexingError(RepositoryScanError):
    """Raised when there's an error indexing repository contents."""
    def __init__(self, repository_name=None, indexing_type=None, message=None):
        if message is None:
            base_msg = f"Failed to index repository: {repository_name}" if repository_name else "Repository indexing failed"
            message = f"{base_msg} - {indexing_type} indexing" if indexing_type else base_msg
        super().__init__(message)
        self.repository_name = repository_name
        self.indexing_type = indexing_type


# Authentication Exceptions
class AuthenticationError(WatsonxIPGError):
    """Base class for authentication related exceptions."""
    def __init__(self, message="Authentication operation failed"):
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""
    def __init__(self, username=None, service=None, message=None):
        if message is None:
            base_msg = "Invalid credentials"
            if username:
                base_msg += f" for user: {username}"
            if service:
                base_msg += f" on service: {service}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.username = username
        self.service = service


class AuthorizationError(AuthenticationError):
    """Raised when user lacks required permissions."""
    def __init__(self, username=None, resource=None, required_permission=None, message=None):
        if message is None:
            base_msg = "Authorization denied"
            if username:
                base_msg += f" for user: {username}"
            if resource:
                base_msg += f" to access resource: {resource}"
            if required_permission:
                base_msg += f" - Required permission: {required_permission}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.username = username
        self.resource = resource
        self.required_permission = required_permission


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    def __init__(self, service=None, message=None):
        if message is None:
            base_msg = "Authentication token expired"
            if service:
                base_msg += f" for service: {service}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.service = service        


# Test Case Management Exceptions
class TestCaseError(WatsonxIPGError):
    """Base class for all test case related exceptions."""
    def __init__(self, message="An error occurred with test case management"):
        super().__init__(message)


class TestCaseNotFoundError(TestCaseError):
    """Raised when a test case is not found in the repository."""
    def __init__(self, test_case_id=None, message=None):
        if message is None:
            message = f"Test case not found: {test_case_id}" if test_case_id else "Test case not found"
        super().__init__(message)
        self.test_case_id = test_case_id


class TestCaseGenerationError(TestCaseError):
    """Raised when there's an error generating test cases from requirements or scenarios."""
    def __init__(self, source=None, message=None):
        if message is None:
            message = f"Failed to generate test case from source: {source}" if source else "Test case generation failed"
        super().__init__(message)
        self.source = source


class TestCaseValidationError(TestCaseError):
    """Raised when a test case fails validation checks."""
    def __init__(self, test_case_id=None, validation_errors=None, message=None):
        if message is None:
            message = f"Test case validation failed for {test_case_id}" if test_case_id else "Test case validation failed"
        super().__init__(message)
        self.test_case_id = test_case_id
        self.validation_errors = validation_errors or []


# Version Control Exceptions
class VersionControlError(WatsonxIPGError):
    """Base class for version control related exceptions."""
    def __init__(self, message="Version control operation failed"):
        super().__init__(message)


class InvalidVersionError(VersionControlError):
    """Raised when an invalid version is specified."""
    def __init__(self, version=None, message=None):
        if message is None:
            message = f"Invalid version specified: {version}" if version else "Invalid version specified"
        super().__init__(message)
        self.version = version


class VersionConflictError(VersionControlError):
    """Raised when there's a conflict during version updating."""
    def __init__(self, item_id=None, message=None):
        if message is None:
            message = f"Version conflict detected for item: {item_id}" if item_id else "Version conflict detected"
        super().__init__(message)
        self.item_id = item_id


# Metadata Exceptions
class MetadataError(WatsonxIPGError):
    """Base class for metadata related exceptions."""
    def __init__(self, message="Metadata operation failed"):
        super().__init__(message)


class MetadataNotFoundError(MetadataError):
    """Raised when metadata for a specific item is not found."""
    def __init__(self, item_id=None, message=None):
        if message is None:
            message = f"Metadata not found for item: {item_id}" if item_id else "Metadata not found"
        super().__init__(message)
        self.item_id = item_id


class MetadataValidationError(MetadataError):
    """Raised when metadata fails validation."""
    def __init__(self, item_id=None, validation_errors=None, message=None):
        if message is None:
            message = f"Metadata validation failed for item: {item_id}" if item_id else "Metadata validation failed"
        super().__init__(message)
        self.item_id = item_id
        self.validation_errors = validation_errors or []


# Template Exceptions
class TemplateError(WatsonxIPGError):
    """Base class for template related exceptions."""
    def __init__(self, message="Template operation failed"):
        super().__init__(message)


class TemplateNotFoundError(TemplateError):
    """Raised when a required template is not found."""
    def __init__(self, template_name=None, message=None):
        if message is None:
            message = f"Template not found: {template_name}" if template_name else "Template not found"
        super().__init__(message)
        self.template_name = template_name


class TemplateRenderingError(TemplateError):
    """Raised when there's an error rendering a template."""
    def __init__(self, template_name=None, reason=None, message=None):
        if message is None:
            base_msg = f"Failed to render template: {template_name}" if template_name else "Template rendering failed"
            message = f"{base_msg} - {reason}" if reason else base_msg
        super().__init__(message)
        self.template_name = template_name
        self.reason = reason


# Scenario Generation Exceptions
class ScenarioError(WatsonxIPGError):
    """Base class for scenario related exceptions."""
    def __init__(self, message="Scenario operation failed"):
        super().__init__(message)


class ScenarioValidationError(ScenarioError):
    """Raised when a generated scenario fails validation."""
    def __init__(self, scenario_id=None, validation_errors=None, message=None):
        if message is None:
            message = f"Scenario validation failed for {scenario_id}" if scenario_id else "Scenario validation failed"
        super().__init__(message)
        self.scenario_id = scenario_id
        self.validation_errors = validation_errors or []


class ScenarioGenerationError(ScenarioError):
    """Raised when there's an error generating scenarios from requirements."""
    def __init__(self, source=None, message=None):
        if message is None:
            message = f"Failed to generate scenario from source: {source}" if source else "Scenario generation failed"
        super().__init__(message)
        self.source = source


# Database Exceptions
class DatabaseError(WatsonxIPGError):
    """Base class for database related exceptions."""
    def __init__(self, message="Database operation failed"):
        super().__init__(message)


class DatabaseConnectionError(DatabaseError):
    """Raised when there's an error connecting to the database."""
    def __init__(self, db_name=None, message=None):
        if message is None:
            message = f"Failed to connect to database: {db_name}" if db_name else "Database connection failed"
        super().__init__(message)
        self.db_name = db_name


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""
    def __init__(self, query=None, message=None):
        if message is None:
            message = "Database query failed"
        super().__init__(message)
        self.query = query


# Schema Validation Exceptions
class SchemaError(WatsonxIPGError):
    """Base class for schema related exceptions."""
    def __init__(self, message="Schema operation failed"):
        super().__init__(message)


class SchemaValidationError(SchemaError):
    """Raised when data fails schema validation."""
    def __init__(self, schema_name=None, validation_errors=None, message=None):
        if message is None:
            message = f"Data validation failed against schema: {schema_name}" if schema_name else "Schema validation failed"
        super().__init__(message)
        self.schema_name = schema_name
        self.validation_errors = validation_errors or []


# Integration Exceptions
class IntegrationError(WatsonxIPGError):
    """Base class for integration related exceptions."""
    def __init__(self, message="Integration operation failed"):
        super().__init__(message)


class JiraIntegrationError(IntegrationError):
    """Raised when there's an error with Jira integration."""
    def __init__(self, operation=None, message=None):
        if message is None:
            message = f"Jira integration error during {operation}" if operation else "Jira integration error"
        super().__init__(message)
        self.operation = operation


class SharePointIntegrationError(IntegrationError):
    """Raised when there's an error with SharePoint integration."""
    def __init__(self, operation=None, message=None):
        if message is None:
            message = f"SharePoint integration error during {operation}" if operation else "SharePoint integration error"
        super().__init__(message)
        self.operation = operation


class ALMIntegrationError(IntegrationError):
    """Raised when there's an error with ALM integration."""
    def __init__(self, operation=None, message=None):
        if message is None:
            message = f"ALM integration error during {operation}" if operation else "ALM integration error"
        super().__init__(message)
        self.operation = operation


class RPAIntegrationError(IntegrationError):
    """Raised when there's an error with RPA integration."""
    def __init__(self, operation=None, message=None):
        if message is None:
            message = f"RPA integration error during {operation}" if operation else "RPA integration error"
        super().__init__(message)
        self.operation = operation


# Test Execution Exceptions
class ExecutionError(WatsonxIPGError):
    """Base class for test execution related exceptions."""
    def __init__(self, message="Test execution operation failed"):
        super().__init__(message)

# Add to src/common/exceptions/custom_exceptions.py
class LLMConnectionError(Exception):
    """Exception raised when there's an error connecting to the LLM API."""
    pass

class LLMResponseError(Exception):
    """Exception raised when there's an error parsing the LLM response."""
    pass


class TestExecutionFailedError(ExecutionError):
    """Raised when a test execution fails."""
    def __init__(self, test_case_id=None, step=None, message=None):
        if message is None:
            msg = f"Test execution failed for test case: {test_case_id}"
            if step:
                msg += f" at step: {step}"
            message = msg
        super().__init__(message)
        self.test_case_id = test_case_id
        self.step = step


class TestDataError(ExecutionError):
    """Raised when there's an issue with test data."""
    def __init__(self, test_case_id=None, data_issue=None, message=None):
        if message is None:
            base_msg = f"Test data issue for test case: {test_case_id}" if test_case_id else "Test data issue"
            message = f"{base_msg} - {data_issue}" if data_issue else base_msg
        super().__init__(message)
        self.test_case_id = test_case_id
        self.data_issue = data_issue


# LLM (Watsonx) Related Exceptions
class LLMError(WatsonxIPGError):
    """Base class for LLM related exceptions."""
    def __init__(self, message="LLM operation failed"):
        super().__init__(message)


class LLMConnectionError(LLMError):
    """Raised when there's an error connecting to the LLM service."""
    def __init__(self, service_name=None, message=None):
        if message is None:
            message = f"Failed to connect to LLM service: {service_name}" if service_name else "LLM connection failed"
        super().__init__(message)
        self.service_name = service_name


class LLMResponseError(LLMError):
    """Raised when there's an error in the LLM response."""
    def __init__(self, prompt_id=None, message=None):
        if message is None:
            message = f"Error in LLM response for prompt: {prompt_id}" if prompt_id else "Error in LLM response"
        super().__init__(message)
        self.prompt_id = prompt_id


# Configuration Exceptions
class ConfigurationError(WatsonxIPGError):
    """Base class for configuration related exceptions."""
    def __init__(self, message="Configuration operation failed"):
        super().__init__(message)


class ConfigurationFileError(ConfigurationError):
    """Raised when there's an error with a configuration file."""
    def __init__(self, config_file=None, message=None):
        if message is None:
            message = f"Error with configuration file: {config_file}" if config_file else "Configuration file error"
        super().__init__(message)
        self.config_file = config_file


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    def __init__(self, config_section=None, validation_errors=None, message=None):
        if message is None:
            message = f"Configuration validation failed for section: {config_section}" if config_section else "Configuration validation failed"
        super().__init__(message)
        self.config_section = config_section
        self.validation_errors = validation_errors or []




# Test Case Formatting Exceptions
class TestCaseFormatError(WatsonxIPGError):
    """Base class for test case formatting related exceptions."""
    def __init__(self, message="Test case formatting operation failed"):
        super().__init__(message)


class TestCaseFormatInvalidError(TestCaseFormatError):
    """Raised when a test case fails to meet required formatting standards."""
    def __init__(self, test_case_id=None, format_issues=None, message=None):
        if message is None:
            base_msg = f"Invalid test case format for case: {test_case_id}" if test_case_id else "Invalid test case format"
            if format_issues:
                base_msg += f" - Issues: {', '.join(format_issues)}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.test_case_id = test_case_id
        self.format_issues = format_issues or []


class TestCaseTemplateError(TestCaseFormatError):
    """Raised when there's an issue with test case template compatibility."""
    def __init__(self, template_name=None, reason=None, message=None):
        if message is None:
            base_msg = f"Test case template error: {template_name}" if template_name else "Test case template error"
            if reason:
                base_msg += f" - {reason}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.template_name = template_name
        self.reason = reason


# Refinement Rule Exceptions
class RefinementRuleError(WatsonxIPGError):
    """Base class for test case refinement rule related exceptions."""
    def __init__(self, message="Test case refinement rule operation failed"):
        super().__init__(message)


class RefinementRuleValidationError(RefinementRuleError):
    """Raised when a refinement rule fails validation."""
    def __init__(self, rule_id=None, validation_errors=None, message=None):
        if message is None:
            base_msg = f"Invalid refinement rule: {rule_id}" if rule_id else "Refinement rule validation failed"
            if validation_errors:
                base_msg += f" - Errors: {', '.join(validation_errors)}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.rule_id = rule_id
        self.validation_errors = validation_errors or []


class RefinementRuleConflictError(RefinementRuleError):
    """Raised when refinement rules conflict with each other."""
    def __init__(self, conflicting_rules=None, message=None):
        if message is None:
            base_msg = "Conflicting refinement rules detected"
            if conflicting_rules:
                base_msg += f" - Conflicts: {', '.join(conflicting_rules)}"
        else:
            base_msg = message
        super().__init__(base_msg)
        self.conflicting_rules = conflicting_rules or []        