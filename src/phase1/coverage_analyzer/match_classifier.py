from typing import Dict, List, Any
import pandas as pd
import numpy as np

class TestCaseMatchClassifier:
    """
    Classifier for test case matches with advanced categorization and scoring
    """
    def __init__(self, similarity_thresholds: Dict[str, float] = None):
        """
        Initialize the classifier with configurable similarity thresholds
        
        Args:
            similarity_thresholds (Dict[str, float], optional): Custom thresholds for match classification
        """
        # Default thresholds if not provided
        self.thresholds = similarity_thresholds or {
            'exact_match': 0.9,
            'partial_match': 0.7,
            'minimal_match': 0.5
        }
    
    def classify_match(self, match_details: Dict[str, Any]) -> str:
        """
        Classify the type of match based on similarity scores
        
        Args:
            match_details (Dict[str, Any]): Details of the match including similarity scores
        
        Returns:
            str: Match classification type
        """
        overall_similarity = match_details.get('similarity_score', 0)
        
        if overall_similarity >= self.thresholds['exact_match']:
            return 'exact_match'
        elif overall_similarity >= self.thresholds['partial_match']:
            return 'partial_match'
        elif overall_similarity >= self.thresholds['minimal_match']:
            return 'minimal_match'
        else:
            return 'no_match'
    
    def generate_match_recommendations(
        self, 
        new_test_case: Dict[str, Any], 
        matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate detailed recommendations based on match results
        
        Args:
            new_test_case (Dict[str, Any]): The new test case being analyzed
            matches (List[Dict[str, Any]]): List of matches found
        
        Returns:
            Dict[str, Any]: Recommendations for handling the test case
        """
        if not matches:
            return {
                'recommendation': 'create_new',
                'rationale': 'No similar test cases found in repository',
                'action': 'Upload as new test case'
            }
        
        # Get the best match
        best_match = matches[0]
        match_type = self.classify_match(best_match)
        
        recommendations = {
            'best_match_id': best_match.get('existing_case_id'),
            'similarity_score': best_match.get('similarity_score', 0),
            'match_type': match_type
        }
        
        # Provide specific recommendations based on match type
        if match_type == 'exact_match':
            recommendations.update({
                'recommendation': 'skip_duplicate',
                'rationale': 'Identical test case already exists',
                'action': 'Do not create duplicate'
            })
        elif match_type == 'partial_match':
            recommendations.update({
                'recommendation': 'modify_existing',
                'rationale': 'Similar test case exists with potential improvements',
                'action': 'Review and update existing test case',
                'attribute_differences': best_match.get('attribute_similarities', {})
            })
        elif match_type == 'minimal_match':
            recommendations.update({
                'recommendation': 'create_variation',
                'rationale': 'Loosely related test case found, but significant differences exist',
                'action': 'Create new test case with references to existing case'
            })
        else:
            recommendations.update({
                'recommendation': 'create_new',
                'rationale': 'No sufficiently similar test cases found',
                'action': 'Upload as new test case'
            })
        
        return recommendations
    
    def generate_coverage_report(
        self, 
        new_test_cases: List[Dict[str, Any]], 
        existing_test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive coverage report
        
        Args:
            new_test_cases (List[Dict[str, Any]]): New test cases to analyze
            existing_test_cases (List[Dict[str, Any]]): Existing test cases
        
        Returns:
            Dict[str, Any]: Detailed coverage analysis report
        """
        coverage_report = {
            'total_new_cases': len(new_test_cases),
            'match_breakdown': {
                'exact_match': 0,
                'partial_match': 0,
                'minimal_match': 0,
                'no_match': 0
            },
            'detailed_matches': []
        }
        
        # Simple similarity comparison function (can be replaced with more sophisticated method)
        def calculate_similarity(case1, case2):
            # Compare key attributes
            attributes = ['task_name', 'description', 'inputs', 'outputs']
            similarities = []
            
            for attr in attributes:
                val1 = str(case1.get(attr, '')).lower()
                val2 = str(case2.get(attr, '')).lower()
                similarity = len(set(val1.split()) & set(val2.split())) / len(set(val1.split()) | set(val2.split()))
                similarities.append(similarity)
            
            return np.mean(similarities)
        
        # Analyze each new test case
        for new_case in new_test_cases:
            # Find matches among existing test cases
            matches = []
            for existing_case in existing_test_cases:
                similarity = calculate_similarity(new_case, existing_case)
                if similarity > 0:
                    matches.append({
                        'existing_case_id': existing_case.get('task_id'),
                        'similarity_score': similarity
                    })
            
            # Sort matches by similarity
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Classify the best match
            if matches:
                best_match = matches[0]
                match_type = self.classify_match(best_match)
                
                # Update match breakdown
                coverage_report['match_breakdown'][match_type] += 1
                
                # Store detailed match information
                coverage_report['detailed_matches'].append({
                    'new_case': new_case,
                    'best_match': best_match,
                    'match_type': match_type
                })
            else:
                # No match found
                coverage_report['match_breakdown']['no_match'] += 1
        
        return coverage_report

# Example usage
if __name__ == "__main__":
    # Sample test data
    new_test_cases = [
        {
            "task_name": "User Login Test",
            "description": "Verify user can successfully log in to the system",
            "inputs": "Valid username and password",
            "outputs": "Successfully logged in to the system"
        }
    ]
    
    existing_test_cases = [
        {
            "task_id": "TC001",
            "task_name": "User Authentication Test",
            "description": "Test login functionality for different user roles",
            "inputs": "Various user credentials",
            "outputs": "Correct access permissions"
        }
    ]
    
    # Initialize classifier
    classifier = TestCaseMatchClassifier()
    
    # Generate coverage report
    coverage_report = classifier.generate_coverage_report(
        new_test_cases, 
        existing_test_cases
    )
    
    print("Coverage Report:")
    print(coverage_report)