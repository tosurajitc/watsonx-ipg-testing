import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import re

class TestCoverageGapAnalyzer:
    """
    Analyzes gaps in test case coverage across requirements
    """
    def __init__(self, requirements_file: str = None, test_cases_file: str = None):
        """
        Initialize the Gap Analyzer with optional requirements and test cases files
        
        Args:
            requirements_file (str, optional): Path to requirements CSV file
            test_cases_file (str, optional): Path to test cases CSV file
        """
        self.requirements = self._load_requirements(requirements_file) if requirements_file else []
        self.test_cases = self._load_test_cases(test_cases_file) if test_cases_file else []
    
    def _load_requirements(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load requirements from a CSV file
        
        Args:
            file_path (str): Path to the requirements CSV file
        
        Returns:
            List[Dict[str, Any]]: List of requirements
        """
        try:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error loading requirements from {file_path}: {e}")
            return []
    
    def _load_test_cases(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from a CSV file
        
        Args:
            file_path (str): Path to the test cases CSV file
        
        Returns:
            List[Dict[str, Any]]: List of test cases
        """
        try:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error loading test cases from {file_path}: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text
        
        Args:
            text (str): Input text to extract keywords from
        
        Returns:
            List[str]: List of extracted keywords
        """
        if not isinstance(text, str):
            return []
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Remove common stop words
        stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
        
        # Split into words and filter out stop words
        keywords = [word for word in text.split() if word not in stop_words]
        
        return keywords
    
    def calculate_requirement_coverage(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate coverage for a specific requirement
        
        Args:
            requirement (Dict[str, Any]): Requirement to analyze
        
        Returns:
            Dict[str, Any]: Coverage analysis for the requirement
        """
        # Extract requirement keywords
        req_keywords = set(self._extract_keywords(
            f"{requirement.get('description', '')} {requirement.get('task_name', '')}"
        ))
        
        # Find matching test cases
        matching_test_cases = []
        for test_case in self.test_cases:
            # Extract test case keywords
            test_keywords = set(self._extract_keywords(
                f"{test_case.get('description', '')} {test_case.get('task_name', '')}"
            ))
            
            # Calculate keyword overlap
            overlap = len(req_keywords.intersection(test_keywords))
            coverage_percentage = (overlap / len(req_keywords)) * 100 if req_keywords else 0
            
            if coverage_percentage > 0:
                matching_test_cases.append({
                    'test_case_id': test_case.get('task_id'),
                    'test_case_name': test_case.get('task_name'),
                    'coverage_percentage': round(coverage_percentage, 2)
                })
        
        return {
            'requirement_id': requirement.get('task_id'),
            'requirement_name': requirement.get('task_name'),
            'matching_test_cases': matching_test_cases,
            'total_coverage': len(matching_test_cases),
            'coverage_percentage': round(
                (len(matching_test_cases) / len(self.test_cases)) * 100 if self.test_cases else 0, 
                2
            )
        }
    
    def analyze_overall_coverage(self) -> Dict[str, Any]:
        """
        Perform comprehensive coverage analysis across all requirements
        
        Returns:
            Dict[str, Any]: Overall coverage analysis report
        """
        coverage_results = {
            'total_requirements': len(self.requirements),
            'total_test_cases': len(self.test_cases),
            'requirements_coverage': []
        }
        
        # Analyze coverage for each requirement
        uncovered_requirements = []
        partially_covered_requirements = []
        fully_covered_requirements = []
        
        for requirement in self.requirements:
            req_coverage = self.calculate_requirement_coverage(requirement)
            coverage_results['requirements_coverage'].append(req_coverage)
            
            # Classify requirements based on coverage
            if req_coverage['total_coverage'] == 0:
                uncovered_requirements.append(requirement)
            elif req_coverage['coverage_percentage'] < 50:
                partially_covered_requirements.append(requirement)
            else:
                fully_covered_requirements.append(requirement)
        
        # Calculate summary statistics
        coverage_results.update({
            'uncovered_requirements': len(uncovered_requirements),
            'partially_covered_requirements': len(partially_covered_requirements),
            'fully_covered_requirements': len(fully_covered_requirements),
            'overall_coverage_percentage': round(
                (len(fully_covered_requirements) / len(self.requirements)) * 100, 
                2
            )
        })
        
        return coverage_results
    
    def generate_gap_recommendations(self) -> Dict[str, Any]:
        """
        Generate recommendations for addressing test coverage gaps
        
        Returns:
            Dict[str, Any]: Recommendations for improving test coverage
        """
        # Perform overall coverage analysis
        coverage_analysis = self.analyze_overall_coverage()
        
        recommendations = {
            'total_recommendations': 0,
            'recommendations_list': []
        }
        
        # Focus on uncovered and partially covered requirements
        for requirement in self.requirements:
            coverage = next(
                (rc for rc in coverage_analysis['requirements_coverage'] 
                 if rc['requirement_id'] == requirement.get('task_id')), 
                None
            )
            
            if not coverage or coverage['total_coverage'] < 1:
                recommendations['recommendations_list'].append({
                    'requirement_id': requirement.get('task_id'),
                    'requirement_name': requirement.get('task_name'),
                    'recommendation_type': 'create_new_test_case',
                    'rationale': 'No test cases cover this requirement',
                    'severity': 'high'
                })
            elif coverage['coverage_percentage'] < 50:
                recommendations['recommendations_list'].append({
                    'requirement_id': requirement.get('task_id'),
                    'requirement_name': requirement.get('task_name'),
                    'recommendation_type': 'enhance_test_coverage',
                    'rationale': f'Partial coverage ({coverage["coverage_percentage"]}%)',
                    'severity': 'medium'
                })
        
        recommendations['total_recommendations'] = len(recommendations['recommendations_list'])
        
        return recommendations

# Example usage
if __name__ == "__main__":
    # Example of using the Gap Analyzer
    gap_analyzer = TestCoverageGapAnalyzer(
        requirements_file='requirements.csv',  # Replace with actual file path
        test_cases_file='WBS.csv'  # Replace with actual file path
    )
    
    # Analyze overall coverage
    coverage_analysis = gap_analyzer.analyze_overall_coverage()
    print("Overall Coverage Analysis:")
    print(coverage_analysis)
    
    # Generate gap recommendations
    gap_recommendations = gap_analyzer.generate_gap_recommendations()
    print("\nGap Recommendations:")
    print(gap_recommendations)