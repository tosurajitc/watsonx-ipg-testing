import difflib
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple

def preprocess_text(text: str) -> str:
    """
    Preprocess text for comparison by converting to lowercase 
    and removing extra whitespace.
    
    Args:
        text (str): Input text to preprocess
    
    Returns:
        str: Preprocessed text
    """
    if not isinstance(text, str):
        return ""
    return " ".join(text.lower().split())

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings using difflib.
    
    Args:
        text1 (str): First text string
        text2 (str): Second text string
    
    Returns:
        float: Similarity score between 0 and 1
    """
    # Preprocess texts
    text1_processed = preprocess_text(text1)
    text2_processed = preprocess_text(text2)
    
    # Use SequenceMatcher for text similarity
    return difflib.SequenceMatcher(None, text1_processed, text2_processed).ratio()

def compare_test_cases(
    new_test_case: Dict[str, Any], 
    existing_test_cases: List[Dict[str, Any]], 
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Compare a new test case against existing test cases.
    
    Args:
        new_test_case (Dict): The new test case to compare
        existing_test_cases (List[Dict]): List of existing test cases
        similarity_threshold (float, optional): Threshold for match classification. Defaults to 0.7.
    
    Returns:
        List[Dict]: Matching test cases with similarity scores and match type
    """
    # Validate inputs
    if not new_test_case or not existing_test_cases:
        return []
    
    matches = []
    
    # Compare against each existing test case
    for existing_case in existing_test_cases:
        # Initialize similarity score tracking
        case_similarity_scores = {}
        
        # Compare key attributes 
        comparison_attributes = [
            'task_name', 
            'description', 
            'inputs', 
            'outputs', 
            'requirement_mapping'
        ]
        
        # Calculate similarity for each attribute
        for attr in comparison_attributes:
            # Safely get attributes, default to empty string if not found
            new_value = new_test_case.get(attr, '')
            existing_value = existing_case.get(attr, '')
            
            # Calculate text similarity
            similarity = calculate_text_similarity(
                str(new_value), 
                str(existing_value)
            )
            case_similarity_scores[attr] = similarity
        
        # Calculate overall similarity (average of attribute similarities)
        overall_similarity = np.mean(list(case_similarity_scores.values()))
        
        # Classify match type based on similarity
        if overall_similarity >= similarity_threshold:
            match_type = "exact" if overall_similarity >= 0.9 else "partial"
            
            matches.append({
                "existing_case_id": existing_case.get('task_id'),
                "similarity_score": overall_similarity,
                "match_type": match_type,
                "attribute_similarities": case_similarity_scores
            })
    
    # Sort matches by similarity score in descending order
    matches.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return matches

def load_test_cases_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Load test cases from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file
    
    Returns:
        List[Dict]: List of test cases as dictionaries
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Convert DataFrame to list of dictionaries
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading test cases from {file_path}: {e}")
        return []

def analyze_test_case_coverage(
    new_test_cases: List[Dict[str, Any]], 
    existing_test_cases: List[Dict[str, Any]], 
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Analyze coverage of new test cases against existing test cases.
    
    Args:
        new_test_cases (List[Dict]): New test cases to analyze
        existing_test_cases (List[Dict]): Existing test cases
        similarity_threshold (float, optional): Threshold for match classification. Defaults to 0.7.
    
    Returns:
        Dict: Coverage analysis results
    """
    coverage_results = {
        "total_new_cases": len(new_test_cases),
        "matched_cases": 0,
        "new_cases": 0,
        "matches": []
    }
    
    for new_case in new_test_cases:
        # Compare against existing test cases
        case_matches = compare_test_cases(
            new_case, 
            existing_test_cases, 
            similarity_threshold
        )
        
        # Update coverage results
        if case_matches:
            coverage_results['matched_cases'] += 1
            coverage_results['matches'].append({
                "new_case": new_case,
                "matches": case_matches
            })
        else:
            coverage_results['new_cases'] += 1
    
    return coverage_results

# Example usage and testing
if __name__ == "__main__":
    # Example of loading test cases and performing coverage analysis
    existing_cases = load_test_cases_from_csv('WBS.csv')
    
    # Simulate a new test case
    new_test_case = {
        "task_name": "User Login Test",
        "description": "Verify user can successfully log in to the system",
        "inputs": "Valid username and password",
        "outputs": "Successfully logged in to the system",
        "requirement_mapping": "Login functionality"
    }
    
    # Perform coverage analysis
    coverage_analysis = analyze_test_case_coverage(
        [new_test_case], 
        existing_cases
    )
    
    print("Coverage Analysis Results:")
    print(f"Total New Cases: {coverage_analysis['total_new_cases']}")
    print(f"Matched Cases: {coverage_analysis['matched_cases']}")
    print(f"New Cases: {coverage_analysis['new_cases']}")