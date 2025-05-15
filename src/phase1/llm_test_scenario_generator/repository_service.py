"""
Repository Service for Test Scenarios.

This module provides service functions for managing test scenarios in the database.
It handles operations like adding, retrieving, updating, and deleting test scenarios,
as well as various search and filtering capabilities.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.db import transaction
from .test_scenarios_model import TestScenario

# Configure logging
logger = logging.getLogger(__name__)


class TestScenarioRepositoryService:
    """Service class for handling test scenario repository operations."""

    @staticmethod
    def add_scenario(scenario_data: Dict[str, Any], created_by: Optional[str] = None) -> TestScenario:
        """
        Add a new test scenario to the repository.

        Args:
            scenario_data: Dictionary containing test scenario data
            created_by: Username of the creator (if available)

        Returns:
            The created TestScenario instance
        """
        try:
            # Extract required fields
            scenario_id = scenario_data.get('id')
            title = scenario_data.get('title')
            description = scenario_data.get('description')
            priority = scenario_data.get('priority', TestScenario.PRIORITY_MEDIUM)
            related_requirements = scenario_data.get('related_requirements')
            
            # Extract or set default for optional fields
            source = scenario_data.get('source', 'manual')
            llm_model = scenario_data.get('llm_model')
            source_details = scenario_data.get('source_details', {})
            
            # Validate required fields
            if not scenario_id or not title or not description:
                raise ValueError("Missing required fields: scenario_id, title, and description are required")
            
            # Normalize priority value
            if priority and isinstance(priority, str):
                priority = priority.capitalize()
                if priority not in [choice[0] for choice in TestScenario.PRIORITY_CHOICES]:
                    priority = TestScenario.PRIORITY_MEDIUM
            
            # Check if scenario with this ID already exists
            existing_scenario = TestScenarioRepositoryService.get_scenario_by_id(scenario_id)
            if existing_scenario:
                logger.warning(f"Scenario with ID {scenario_id} already exists. "
                              f"Using a different approach to add or update.")
                return TestScenarioRepositoryService.update_scenario(existing_scenario.id, scenario_data)
            
            # Create new scenario
            new_scenario = TestScenario(
                scenario_id=scenario_id,
                title=title,
                description=description,
                priority=priority,
                related_requirements=related_requirements,
                source=source,
                source_details=source_details,
                llm_model=llm_model,
                created_by=created_by,
                created_at=timezone.now()
            )
            new_scenario.save()
            
            logger.info(f"Successfully added new test scenario: {scenario_id}")
            return new_scenario
            
        except Exception as e:
            logger.error(f"Error adding test scenario: {str(e)}")
            raise

    @staticmethod
    def add_multiple_scenarios(scenarios_data: List[Dict[str, Any]], created_by: Optional[str] = None) -> List[TestScenario]:
        """
        Add multiple test scenarios to the repository in a single transaction.

        Args:
            scenarios_data: List of dictionaries containing test scenario data
            created_by: Username of the creator (if available)

        Returns:
            List of created TestScenario instances
        """
        created_scenarios = []
        
        try:
            with transaction.atomic():
                for scenario_data in scenarios_data:
                    scenario = TestScenarioRepositoryService.add_scenario(scenario_data, created_by)
                    created_scenarios.append(scenario)
                
            logger.info(f"Successfully added {len(created_scenarios)} test scenarios")
            return created_scenarios
            
        except Exception as e:
            logger.error(f"Error adding multiple test scenarios: {str(e)}")
            raise

    @staticmethod
    def get_scenario_by_id(scenario_id: str) -> Optional[TestScenario]:
        """
        Get a test scenario by its unique identifier.

        Args:
            scenario_id: The unique identifier of the scenario

        Returns:
            TestScenario instance if found, None otherwise
        """
        try:
            return TestScenario.objects.filter(scenario_id=scenario_id).first()
        except Exception as e:
            logger.error(f"Error retrieving test scenario {scenario_id}: {str(e)}")
            return None

    @staticmethod
    def get_all_scenarios(
        status: Optional[str] = None,
        priority: Optional[str] = None,
        source: Optional[str] = None,
        search_term: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        order_by: str = '-created_at'
    ) -> Dict[str, Any]:
        """
        Get test scenarios with optional filtering, pagination, and sorting.

        Args:
            status: Filter by status (optional)
            priority: Filter by priority (optional)
            source: Filter by source (optional)
            search_term: Search in title and description (optional)
            page: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 50)
            order_by: Field to order by (default: '-created_at')

        Returns:
            Dictionary with scenarios, total count, and pagination info
        """
        try:
            # Start with all scenarios
            queryset = TestScenario.objects.all()
            
            # Apply filters
            if status:
                queryset = queryset.filter(status=status)
            
            if priority:
                queryset = queryset.filter(priority=priority)
            
            if source:
                queryset = queryset.filter(source=source)
            
            if search_term:
                # Search in title, description, and ID
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(scenario_id__icontains=search_term)
                )
            
            # Count total before pagination
            total_count = queryset.count()
            
            # Apply sorting
            queryset = queryset.order_by(order_by)
            
            # Apply pagination
            start = (page - 1) * page_size
            end = start + page_size
            scenarios = list(queryset[start:end])
            
            return {
                'scenarios': scenarios,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end < total_count,
                'has_previous': page > 1
            }
            
        except Exception as e:
            logger.error(f"Error retrieving test scenarios: {str(e)}")
            return {
                'scenarios': [],
                'total_count': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'has_next': False,
                'has_previous': False
            }

    @staticmethod
    def update_scenario(scenario_id: Union[int, str], updated_data: Dict[str, Any]) -> Optional[TestScenario]:
        """
        Update an existing test scenario.

        Args:
            scenario_id: Database ID or scenario_id of the test scenario
            updated_data: Dictionary containing updated fields

        Returns:
            Updated TestScenario instance if successful, None otherwise
        """
        try:
            # Determine if ID is database ID or scenario_id
            if isinstance(scenario_id, int) or scenario_id.isdigit():
                scenario = TestScenario.objects.get(id=int(scenario_id))
            else:
                scenario = TestScenario.objects.get(scenario_id=scenario_id)
            
            # Update fields
            for field, value in updated_data.items():
                if hasattr(scenario, field) and field not in ['id', 'created_at']:
                    setattr(scenario, field, value)
            
            # Update the updated_at timestamp
            scenario.updated_at = timezone.now()
            scenario.save()
            
            logger.info(f"Successfully updated test scenario: {scenario.scenario_id}")
            return scenario
            
        except TestScenario.DoesNotExist:
            logger.error(f"Test scenario not found: {scenario_id}")
            return None
        except Exception as e:
            logger.error(f"Error updating test scenario {scenario_id}: {str(e)}")
            return None

    @staticmethod
    def delete_scenario(scenario_id: Union[int, str]) -> bool:
        """
        Delete a test scenario.

        Args:
            scenario_id: Database ID or scenario_id of the test scenario

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Determine if ID is database ID or scenario_id
            if isinstance(scenario_id, int) or scenario_id.isdigit():
                scenario = TestScenario.objects.get(id=int(scenario_id))
            else:
                scenario = TestScenario.objects.get(scenario_id=scenario_id)
            
            scenario_id_for_logging = scenario.scenario_id
            scenario.delete()
            
            logger.info(f"Successfully deleted test scenario: {scenario_id_for_logging}")
            return True
            
        except TestScenario.DoesNotExist:
            logger.error(f"Cannot delete test scenario - not found: {scenario_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting test scenario {scenario_id}: {str(e)}")
            return False

    @staticmethod
    def search_scenarios(query: str) -> List[TestScenario]:
        """
        Search for test scenarios matching the query.

        Args:
            query: Search query string

        Returns:
            List of matching TestScenario instances
        """
        try:
            return list(TestScenario.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(scenario_id__icontains=query) |
                Q(related_requirements__icontains=query)
            ).order_by('-created_at'))
            
        except Exception as e:
            logger.error(f"Error searching test scenarios with query '{query}': {str(e)}")
            return []

    @staticmethod
    def get_scenarios_by_requirement(requirement_id: str) -> List[TestScenario]:
        """
        Get test scenarios related to a specific requirement.

        Args:
            requirement_id: Requirement ID to search for

        Returns:
            List of related TestScenario instances
        """
        try:
            return list(TestScenario.objects.filter(
                related_requirements__icontains=requirement_id
            ).order_by('-created_at'))
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios for requirement {requirement_id}: {str(e)}")
            return []

    @staticmethod
    def get_scenarios_count_by_status() -> Dict[str, int]:
        """
        Get count of scenarios grouped by status.

        Returns:
            Dictionary with status as key and count as value
        """
        try:
            counts = {}
            for status_choice in TestScenario.STATUS_CHOICES:
                status = status_choice[0]
                count = TestScenario.objects.filter(status=status).count()
                counts[status] = count
            
            # Add total count
            counts['Total'] = TestScenario.objects.count()
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting scenario counts by status: {str(e)}")
            return {'Error': 0}

    @staticmethod
    def bulk_update_status(scenario_ids: List[Union[int, str]], new_status: str) -> int:
        """
        Update status for multiple scenarios at once.

        Args:
            scenario_ids: List of scenario IDs to update
            new_status: New status to set

        Returns:
            Number of scenarios updated
        """
        try:
            # Validate status
            if new_status not in [choice[0] for choice in TestScenario.STATUS_CHOICES]:
                raise ValueError(f"Invalid status: {new_status}")
            
            # Process each ID (can be database ID or scenario_id)
            updated_count = 0
            for sid in scenario_ids:
                result = TestScenarioRepositoryService.update_scenario(sid, {'status': new_status})
                if result:
                    updated_count += 1
            
            logger.info(f"Bulk updated {updated_count} scenarios to status: {new_status}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk status update: {str(e)}")
            return 0