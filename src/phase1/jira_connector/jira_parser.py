import json
from typing import List, Dict

class JiraParser:
    def __init__(self, raw_data: dict):
        self.raw_data = raw_data

    def parse(self) -> List[Dict]:
        """
        Parses raw JIRA JSON data into a standardized structure for test scenario generation.

        Returns:
            List[Dict]: A list of standardized requirement records.
        """
        standardized_records = []

        issues = self.raw_data.get('issues', [])
        for issue in issues:
            fields = issue.get('fields', {})

            record = {
                "issue_key": issue.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "status": fields.get("status", {}).get("name"),
                "labels": fields.get("labels", []),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "reporter": fields.get("reporter", {}).get("displayName"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "custom_fields": self.extract_custom_fields(fields)
            }

            standardized_records.append(record)

        return standardized_records

    def extract_custom_fields(self, fields: dict) -> Dict:
        """
        Extract custom fields if needed.
        Extend this based on your JIRA configuration.

        Args:
            fields (dict): The fields part of JIRA issue.

        Returns:
            Dict: Custom fields extracted.
        """
        custom_data = {}

        # Example: If your JIRA has custom fields like "Acceptance Criteria" or "Business Requirement"
        # To be updated as per the actual fields.
        if "customfield_10030" in fields:  # Change this ID to your custom field ID
            custom_data["acceptance_criteria"] = fields["customfield_10030"]

        return custom_data
