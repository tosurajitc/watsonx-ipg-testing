import React, { useState, useRef, useEffect } from 'react';
import { 
  FileText, 
  Upload, 
  Settings, 
  ChevronRight, 
  Download, 
  Database, 
  AlertCircle, 
  CheckCircle, 
  Loader,
  FilePlus,
  FileSearch,
  FileSpreadsheet,
  ExternalLink,
  MessageSquare,
  AlertTriangle,
  Archive,
  X,
  RefreshCw
} from 'lucide-react';
import axios from 'axios';

const TestCaseGeneration = () => {
  // State for active tab (Generate or Review)
  const [activeTab, setActiveTab] = useState('generate');
  
  // Generate Test Cases Tab States
  const [inputSource, setInputSource] = useState('requirements');
  const [selectedRequirements, setSelectedRequirements] = useState([]);
  const [directPrompt, setDirectPrompt] = useState('');
  const [format, setFormat] = useState('excel');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);
  const [generatedTestCases, setGeneratedTestCases] = useState([]);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [processAutomatically, setProcessAutomatically] = useState(false);
  const [testScenarios, setTestScenarios] = useState([]);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [detailLevel, setDetailLevel] = useState('medium');
  // Review & Refine Tab States
  const [testCaseFile, setTestCaseFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingError, setAnalyzingError] = useState(null);
  const [originalTestCase, setOriginalTestCase] = useState(null);
  const [refinedTestCase, setRefinedTestCase] = useState(null);
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [analysisResults, setAnalysisResults] = useState(null);
  
  // Refs
  const fileInputRef = useRef(null);
  
  // Handler for tab switching
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    resetStates(tab);
  };
  
  // Reset states when switching tabs
  const resetStates = (tab) => {
    if (tab === 'generate') {
      setSelectedRequirements([]);
      setDirectPrompt('');
      setGeneratedTestCases([]);
      setGenerationError(null);
      setProcessingStatus(null);
    } else {
      setTestCaseFile(null);
      setOriginalTestCase(null);
      setRefinedTestCase(null);
      setAiSuggestions([]);
      setAnalyzingError(null);
      setAnalysisResults(null);
    }
  };
  
  // Handle input source change
  const handleInputSourceChange = (source) => {
    setInputSource(source);
    setSelectedRequirements([]);
    setDirectPrompt('');
    
    if (source === 'requirements' && testScenarios.length === 0) {
      fetchTestScenarios();
    }
  };
  
  // Function to fetch test scenarios from the backend
  const fetchTestScenarios = async () => {
    setLoadingScenarios(true);
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      // Based on scenario_api_service.py endpoints
      const response = await axios.get(`${API_BASE_URL}/api/test-scenarios`);
      
      // Set the scenarios in state
      setTestScenarios(response.data.scenarios || []);
      return response.data.scenarios || [];
    } catch (error) {
      console.error('Error fetching test scenarios:', error);
      setGenerationError('Failed to load test scenarios. Please try again.');
      return [];
    } finally {
      setLoadingScenarios(false);
    }
  };
  
  // Load test scenarios when component mounts or when switching to generate tab
  useEffect(() => {
    if (activeTab === 'generate' && inputSource === 'requirements') {
      fetchTestScenarios();
    }
  }, [activeTab, inputSource]);
  
  // Handle scenario selection
  const handleRequirementSelect = (scenario) => {
    const isSelected = selectedRequirements.some(r => r.id === scenario.id);
    
    if (isSelected) {
      setSelectedRequirements(selectedRequirements.filter(r => r.id !== scenario.id));
    } else {
      setSelectedRequirements([...selectedRequirements, scenario]);
    }
  };
  
  // Handle test case generation
  const handleGenerateTestCases = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    setProcessingStatus('processing');
    
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      // Prepare request data
      let requestData;
      if (inputSource === 'requirements') {
        requestData = {
          scenarios: selectedRequirements.map(scenario => scenario.id),
          format: format
        };
      } else {
        requestData = {
          prompt: directPrompt,
          format: format
        };
      }
      
      // Call API to generate test cases
      const response = await axios.post(
        `${API_BASE_URL}/api/test-cases/generate`, 
        requestData
      );
      
      // Update state with generated test cases
      setGeneratedTestCases(response.data.test_cases || []);
      setProcessingStatus('success');
      
    } catch (error) {
      console.error('Error generating test cases:', error);
      setGenerationError(error.response?.data?.message || 'Failed to generate test cases');
      setProcessingStatus('error');
    } finally {
      setIsGenerating(false);
    }
  };
  
  // Handle Export to Excel
  const handleExportToExcel = async () => {
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      const response = await axios.post(
        `${API_BASE_URL}/api/test-cases/export-excel`,
        { test_cases: generatedTestCases },
        { responseType: 'blob' }
      );
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `test_cases_${new Date().toISOString().slice(0,10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Error exporting to Excel:', error);
      alert('Failed to export test cases to Excel');
    }
  };
  
  // Handle test case file upload
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    
    if (file) {
      // Validate file type
      const allowedTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ];
      
      if (!allowedTypes.includes(file.type)) {
        setAnalyzingError('Invalid file type. Please upload Excel or Word files.');
        return;
      }
      
      setTestCaseFile(file);
      setAnalyzingError(null);
    }
  };
  
  // Handle analyze and suggest refinements
  const handleAnalyzeTestCase = async () => {
    if (!testCaseFile) {
      setAnalyzingError('Please upload a test case file first');
      return;
    }
    
    setIsAnalyzing(true);
    setAnalyzingError(null);
    
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      // Create form data
      const formData = new FormData();
      formData.append('file', testCaseFile);
      
      const response = await axios.post(
        `${API_BASE_URL}/api/test-cases/analyze`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      // Update state with analysis results
      setAnalysisResults(response.data);
      setOriginalTestCase(response.data.original_test_case);
      setRefinedTestCase(response.data.refined_test_case);
      setAiSuggestions(response.data.suggestions || []);
      
    } catch (error) {
      console.error('Error analyzing test case:', error);
      setAnalyzingError(error.response?.data?.message || 'Failed to analyze test case');
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  // Handle accept suggestions
  const handleAcceptSuggestions = async () => {
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      await axios.post(`${API_BASE_URL}/api/test-cases/accept-suggestions`, {
        test_case_id: originalTestCase?.id,
        suggestions: aiSuggestions.filter(s => s.accepted)
      });
      
      alert('Suggestions accepted and test case updated successfully!');
      
    } catch (error) {
      console.error('Error accepting suggestions:', error);
      alert('Failed to accept suggestions');
    }
  };
  
  // Handle notification of test case owner
  const handleNotifyOwner = async () => {
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      await axios.post(`${API_BASE_URL}/api/test-cases/notify-owner`, {
        test_case_id: originalTestCase?.id,
        suggestions: aiSuggestions
      });
      
      alert('Owner has been notified of suggested changes!');
      
    } catch (error) {
      console.error('Error notifying owner:', error);
      alert('Failed to notify owner');
    }
  };
  
  // Handle marking test case as obsolete
  const handleMarkObsolete = async () => {
    if (!window.confirm('Are you sure you want to mark this test case as obsolete?')) {
      return;
    }
    
    try {
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      
      await axios.post(`${API_BASE_URL}/api/test-cases/mark-obsolete`, {
        test_case_id: originalTestCase?.id
      });
      
      alert('Test case has been marked as obsolete!');
      
    } catch (error) {
      console.error('Error marking as obsolete:', error);
      alert('Failed to mark test case as obsolete');
    }
  };
  
  // Handle discarding suggestions
  const handleDiscardSuggestions = () => {
    setRefinedTestCase(null);
    setAiSuggestions([]);
  };
  
  // Handle suggestion acceptance toggle
  const handleToggleSuggestion = (suggestionId) => {
    setAiSuggestions(aiSuggestions.map(suggestion => 
      suggestion.id === suggestionId 
        ? { ...suggestion, accepted: !suggestion.accepted }
        : suggestion
    ));
  };
  
  // Handle the next step (proceed to repository comparison)
  const handleNextStep = () => {
    if (processAutomatically) {
      // Trigger the next module automatically
      console.log('Automatically proceeding to Test Repository & Comparison Module');
      // Here you would implement the logic to pass the data to the next module
    } else {
      // Show confirmation dialog
      if (window.confirm('Do you want to proceed to test case repository comparison?')) {
        console.log('Manually proceeding to Test Repository & Comparison Module');
        // Here you would implement the logic to pass the data to the next module
      }
    }
  };
  
  // Render the Generate Test Cases tab
  const renderGenerateTab = () => (
    <div className="tab-content">
      <div className="input-section">
        <div className="section-title">
          <FilePlus size={20} />
          <h3>Test Case Source</h3>
        </div>
        
        <div className="input-source-tabs">
          <button 
            className={`source-tab ${inputSource === 'scenarios' ? 'active' : ''}`}
            onClick={() => handleInputSourceChange('scenarios')}
          >
            <FileText size={16} />
            <span>From Test Scenarios</span>
          </button>
          
          <button 
            className={`source-tab ${inputSource === 'prompt' ? 'active' : ''}`}
            onClick={() => handleInputSourceChange('prompt')}
          >
            <MessageSquare size={16} />
            <span>Direct Prompt</span>
          </button>
        </div>
        
        {inputSource === 'scenarios' ? (
          <div className="scenario-selector">
            <p className="section-description">
              Select test scenarios to generate detailed test cases from:
            </p>
            
            <div className="scenario-list">
              {loadingScenarios ? (
                <div className="loading-scenarios">
                  <Loader size={24} className="spinner" />
                  <p>Loading test scenarios...</p>
                </div>
              ) : availableScenarios.length > 0 ? (
                availableScenarios.map(scenario => (
                <div 
                  key={scenario.id} 
                  className={`scenario-item ${selectedScenarios.some(s => s.id === scenario.id) ? 'selected' : ''}`}
                  onClick={() => handleScenarioSelect(scenario)}
                >
                  <div className="checkbox">
                    {selectedScenarios.some(s => s.id === scenario.id) ? <CheckCircle size={16} /> : null}
                  </div>
                  <div className="scenario-content">
                    <h4>{scenario.id}: {scenario.title}</h4>
                    <p>{scenario.description}</p>
                  </div>
                </div>
              ))
              ) : (
                <div className="no-scenarios">
                  <AlertCircle size={24} />
                  <p>No test scenarios available. Please generate scenarios in the Requirements Ingestion module first.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="prompt-input">
            <p className="section-description">
              Enter a direct prompt to generate test cases:
            </p>
            
            <textarea
              className="prompt-textarea"
              placeholder="E.g., Generate login tests for admin user with both valid and invalid credentials"
              value={directPrompt}
              onChange={(e) => setDirectPrompt(e.target.value)}
            />
          </div>
        )}
      </div>
      
      <div className="configuration-section">
        <div className="section-title">
          <Settings size={20} />
          <h3>Configuration Options</h3>
        </div>
        
        <div className="config-grid">
          <div className="config-item">
            <label>Target Format:</label>
            <select 
              value={format}
              onChange={(e) => setFormat(e.target.value)}
            >
              <option value="excel">Excel</option>
              <option value="preview">Preview Only</option>
            </select>
          </div>
          
          <div className="config-item checkbox-item">
            <input
              type="checkbox"
              id="processAutomatically"
              checked={processAutomatically}
              onChange={(e) => setProcessAutomatically(e.target.checked)}
            />
            <label htmlFor="processAutomatically">Process automatically after generation</label>
          </div>
        </div>
        
        <div className="action-buttons">
          <button 
            className="generate-button"
            onClick={handleGenerateTestCases}
            disabled={isGenerating || 
              (inputSource === 'requirements' && selectedRequirements.length === 0) ||
              (inputSource === 'prompt' && !directPrompt.trim())}
          >
            {isGenerating ? (
              <>
                <Loader size={16} className="spinner" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <ChevronRight size={16} />
                <span>Generate Test Cases</span>
              </>
            )}
          </button>
        </div>
      </div>
      
      {processingStatus && (
        <div className={`status-message ${processingStatus}`}>
          {processingStatus === 'processing' && (
            <>
              <Loader size={20} className="spinner" />
              <span>Processing... AI is generating test cases</span>
            </>
          )}
          {processingStatus === 'success' && (
            <>
              <CheckCircle size={20} />
              <span>Test cases generated successfully!</span>
            </>
          )}
          {processingStatus === 'error' && (
            <>
              <AlertCircle size={20} />
              <span>{generationError || 'An error occurred while generating test cases'}</span>
            </>
          )}
        </div>
      )}
      
      {generatedTestCases.length > 0 && (
        <div className="results-section">
          <div className="section-title">
            <FileSpreadsheet size={20} />
            <h3>Generated Test Cases</h3>
          </div>
          
          <div className="test-cases-preview">
            <table className="test-cases-table">
              <thead>
                <tr>
                  <th>SUBJECT</th>
                  <th>TEST CASE</th>
                  <th>TEST CASE NUMBER</th>
                  <th>STEP NO</th>
                  <th>TEST STEP DESCRIPTION</th>
                  <th>EXPECTED RESULT</th>
                  {/* Not showing all columns for brevity in the preview */}
                </tr>
              </thead>
              <tbody>
                {generatedTestCases.map((testCase, index) => (
                  <tr key={index}>
                    <td>{testCase.SUBJECT}</td>
                    <td>{testCase["TEST CASE"]}</td>
                    <td>{testCase["TEST CASE NUMBER"]}</td>
                    <td>{testCase["STEP NO"]}</td>
                    <td>{testCase["TEST STEP DESCRIPTION"]}</td>
                    <td>{testCase["EXPECTED RESULT"]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="results-actions">
            <button 
              className="action-button export-button"
              onClick={handleExportToExcel}
            >
              <Download size={16} />
              <span>Export to Excel</span>
            </button>
            
            <button 
              className="action-button compare-button"
              onClick={handleNextStep}
            >
              <Database size={16} />
              <span>Compare with Repository</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
  
  // Render the Review & Refine tab
  const renderReviewTab = () => (
    <div className="tab-content">
      <div className="upload-section">
        <div className="section-title">
          <FileSearch size={20} />
          <h3>Upload Test Case for Review</h3>
        </div>
        
        <p className="section-description">
          Upload an existing test case file to analyze and suggest refinements:
        </p>
        
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept=".xlsx,.xls,.doc,.docx"
          className="hidden"
        />
        
        <div className="file-upload-container">
          <div 
            className="file-upload-area"
            onClick={() => fileInputRef.current.click()}
          >
            {testCaseFile ? (
              <>
                <FileText size={40} className="file-icon" />
                <span className="file-name">{testCaseFile.name}</span>
                <span className="file-size">
                  {(testCaseFile.size / 1024).toFixed(2)} KB
                </span>
              </>
            ) : (
              <>
                <Upload size={40} className="upload-icon" />
                <span className="upload-text">Drag & drop a file here or click to browse</span>
                <span className="upload-hint">Supported formats: Excel, Word</span>
              </>
            )}
          </div>
          
          {testCaseFile && (
            <button 
              className="change-file-btn"
              onClick={() => fileInputRef.current.click()}
            >
              Change File
            </button>
          )}
        </div>
        
        {analyzingError && (
          <div className="error-message">
            <AlertCircle size={16} />
            <span>{analyzingError}</span>
          </div>
        )}
        
        <div className="action-buttons">
          <button 
            className="analyze-button"
            onClick={handleAnalyzeTestCase}
            disabled={isAnalyzing || !testCaseFile}
          >
            {isAnalyzing ? (
              <>
                <Loader size={16} className="spinner" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <FileSearch size={16} />
                <span>Analyze & Suggest Refinements</span>
              </>
            )}
          </button>
        </div>
      </div>
      
      {originalTestCase && refinedTestCase && (
        <>
          <div className="comparison-section">
            <div className="section-title">
              <RefreshCw size={20} />
              <h3>Comparison View</h3>
            </div>
            
            <div className="comparison-container">
              <div className="comparison-column">
                <div className="column-header">
                  <h4>Original Test Case</h4>
                </div>
                <div className="test-case-view">
                  <table className="test-case-table">
                    <thead>
                      <tr>
                        <th>STEP NO</th>
                        <th>TEST STEP DESCRIPTION</th>
                        <th>EXPECTED RESULT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {originalTestCase.steps.map((step, index) => (
                        <tr key={index}>
                          <td>{step["STEP NO"]}</td>
                          <td>{step["TEST STEP DESCRIPTION"]}</td>
                          <td>{step["EXPECTED RESULT"]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              <div className="comparison-column">
                <div className="column-header">
                  <h4>Refined Test Case</h4>
                </div>
                <div className="test-case-view">
                  <table className="test-case-table">
                    <thead>
                      <tr>
                        <th>STEP NO</th>
                        <th>TEST STEP DESCRIPTION</th>
                        <th>EXPECTED RESULT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {refinedTestCase.steps.map((step, index) => {
                        const originalStep = originalTestCase.steps.find(
                          s => s["STEP NO"] === step["STEP NO"]
                        );
                        
                        const descChanged = originalStep && 
                          originalStep["TEST STEP DESCRIPTION"] !== step["TEST STEP DESCRIPTION"];
                        
                        const resultChanged = originalStep && 
                          originalStep["EXPECTED RESULT"] !== step["EXPECTED RESULT"];
                        
                        return (
                          <tr key={index}>
                            <td>{step["STEP NO"]}</td>
                            <td className={descChanged ? 'changed-cell' : ''}>
                              {step["TEST STEP DESCRIPTION"]}
                            </td>
                            <td className={resultChanged ? 'changed-cell' : ''}>
                              {step["EXPECTED RESULT"]}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
          
          <div className="suggestions-section">
            <div className="section-title">
              <MessageSquare size={20} />
              <h3>AI Suggestions</h3>
            </div>
            
            <div className="suggestions-list">
              {aiSuggestions.map((suggestion, index) => (
                <div key={index} className={`suggestion-item ${suggestion.accepted ? 'accepted' : ''}`}>
                  <div className="suggestion-header">
                    <div className="suggestion-type">
                      {suggestion.type === 'critical' ? (
                        <AlertCircle size={16} className="critical-icon" />
                      ) : suggestion.type === 'warning' ? (
                        <AlertTriangle size={16} className="warning-icon" />
                      ) : (
                        <MessageSquare size={16} className="info-icon" />
                      )}
                      <span>{suggestion.type}</span>
                    </div>
                    
                    <div className="suggestion-controls">
                      <button 
                        className={`toggle-button ${suggestion.accepted ? 'accepted' : ''}`}
                        onClick={() => handleToggleSuggestion(suggestion.id)}
                      >
                        {suggestion.accepted ? (
                          <>
                            <CheckCircle size={16} />
                            <span>Accepted</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle size={16} />
                            <span>Accept</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  <div className="suggestion-content">
                    <p className="suggestion-text">{suggestion.text}</p>
                    {suggestion.details && (
                      <p className="suggestion-details">{suggestion.details}</p>
                    )}
                  </div>
                  
                  {suggestion.changes && (
                    <div className="suggestion-changes">
                      <div className="change-item">
                        <div className="change-from">
                          <span className="label">From:</span>
                          <span className="value">{suggestion.changes.from}</span>
                        </div>
                        <div className="change-to">
                          <span className="label">To:</span>
                          <span className="value">{suggestion.changes.to}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            
            <div className="results-actions">
              <button 
                className="action-button accept-button"
                onClick={handleAcceptSuggestions}
                disabled={!aiSuggestions.some(s => s.accepted)}
              >
                <CheckCircle size={16} />
                <span>Accept Suggestions & Update</span>
              </button>
              
              <button 
                className="action-button notify-button"
                onClick={handleNotifyOwner}
              >
                <ExternalLink size={16} />
                <span>Notify Owner</span>
              </button>
              
              <button 
                className="action-button obsolete-button"
                onClick={handleMarkObsolete}
              >
                <Archive size={16} />
                <span>Mark as Obsolete</span>
              </button>
              
              <button 
                className="action-button discard-button"
                onClick={handleDiscardSuggestions}
              >
                <X size={16} />
                <span>Discard Suggestions</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
  
  return (
    <div className="test-case-generation-container">
      <div className="card">
        <div className="card-header">
          <h2>Test Case Generation & Refinement</h2>
          <p>Generate detailed test cases from requirements or refine existing test cases.</p>
        </div>
        
        <div className="tabs">
          <button 
            className={`tab-button ${activeTab === 'generate' ? 'active' : ''}`}
            onClick={() => handleTabChange('generate')}
          >
            <FilePlus size={18} />
            <span>Generate Test Cases</span>
          </button>
          
          <button 
            className={`tab-button ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => handleTabChange('review')}
          >
            <FileSearch size={18} />
            <span>Review & Refine</span>
          </button>
        </div>
        
        <div className="card-body">
          {activeTab === 'generate' ? renderGenerateTab() : renderReviewTab()}
        </div>
      </div>

      <style jsx>{`
        /* Global styles */
        .test-case-generation-container {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          max-width: 1000px;
          margin: 2rem auto;
          color: #333;
        }

        .card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
          overflow: hidden;
        }

        .card-header {
          padding: 24px 32px;
          background: linear-gradient(135deg, #2563eb, #3b82f6);
          color: white;
        }

        .card-header h2 {
          margin: 0 0 8px 0;
          font-size: 24px;
          font-weight: 600;
        }

        .card-header p {
          margin: 0;
          opacity: 0.9;
          font-size: 14px;
        }

        .card-body {
          padding: 24px 32px;
        }

        /* Tabs navigation */
        .tabs {
          display: flex;
          border-bottom: 1px solid #e2e8f0;
          background-color: #f8fafc;
        }

        .tab-button {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 16px;
          background-color: transparent;
          border: none;
          border-bottom: 3px solid transparent;
          color: #64748b;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .tab-button:hover {
          background-color: #f1f5f9;
          color: #3b82f6;
        }

        .tab-button.active {
          color: #3b82f6;
          border-bottom-color: #3b82f6;
          background-color: white;
        }

        /* Tab content */
        .tab-content {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        /* Section styling */
        .section-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 16px;
          color: #1e3a8a;
        }

        .section-title h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .section-description {
          margin-bottom: 16px;
          color: #64748b;
          font-size: 14px;
        }

        /* Input source tabs */
        .input-source-tabs {
          display: flex;
          margin-bottom: 16px;
          border-bottom: 1px solid #e2e8f0;
        }

        .source-tab {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          background-color: transparent;
          border: none;
          border-bottom: 2px solid transparent;
          color: #64748b;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .source-tab:hover {
          background-color: #f8fafc;
          color: #3b82f6;
        }

        .source-tab.active {
          color: #3b82f6;
          border-bottom-color: #3b82f6;
        }

        /* Scenario selector */
        .scenario-list {
          max-height: 300px;
          overflow-y: auto;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
        }

        .scenario-item {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 12px 16px;
          border-bottom: 1px solid #e2e8f0;
          cursor: pointer;
          transition: background-color 0.2s ease;
        }

        .scenario-item:last-child {
          border-bottom: none;
        }

        .scenario-item:hover {
          background-color: #f8fafc;
        }

        .scenario-item.selected {
          background-color: #e0f2fe;
        }

        .checkbox {
          width: 20px;
          height: 20px;
          border: 2px solid #cbd5e1;
          border-radius: 4px;
          margin-top: 2px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #3b82f6;
        }

        .scenario-item.selected .checkbox {
          border-color: #3b82f6;
        }

        .scenario-content h4 {
          margin: 0 0 4px 0;
          font-size: 16px;
          font-weight: 500;
        }

        .scenario-content p {
          margin: 0;
          font-size: 14px;
          color: #64748b;
        }
        
        .loading-scenarios, .no-scenarios {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          text-align: center;
          color: #64748b;
        }
        
        .loading-scenarios .spinner {
          margin-bottom: 16px;
          color: #3b82f6;
        }
        
        .no-scenarios svg {
          margin-bottom: 16px;
          color: #f59e0b;
        }
        
        .loading-scenarios p, .no-scenarios p {
          margin: 0;
          font-size: 14px;
        }

        /* Prompt input */
        .prompt-textarea {
          width: 100%;
          min-height: 120px;
          padding: 12px;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          font-family: inherit;
          font-size: 14px;
          resize: vertical;
          transition: border-color 0.2s ease;
        }

        .prompt-textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }

        /* Configuration section */
        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .config-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .config-item label {
          font-size: 14px;
          font-weight: 500;
          color: #334155;
        }

        .config-item select {
          padding: 8px 12px;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          font-size: 14px;
          transition: all 0.2s ease;
        }

        .config-item select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }

        .checkbox-item {
          flex-direction: row;
          align-items: center;
        }

        .checkbox-item input[type="checkbox"] {
          margin-right: 8px;
        }

        /* Action buttons */
        .action-buttons {
          display: flex;
          justify-content: center;
          margin-top: 20px;
        }

        .generate-button, .analyze-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px 24px;
          background: linear-gradient(135deg, #2563eb, #3b82f6);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .generate-button:hover, .analyze-button:hover {
          background: linear-gradient(135deg, #1d4ed8, #2563eb);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }

        .generate-button:active, .analyze-button:active {
          transform: translateY(0);
        }

        .generate-button:disabled, .analyze-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }

        /* Status message */
        .status-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 16px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
        }

        .status-message.processing {
          background-color: #f0f9ff;
          color: #0284c7;
        }

        .status-message.success {
          background-color: #f0fdf4;
          color: #16a34a;
        }

        .status-message.error {
          background-color: #fef2f2;
          color: #dc2626;
        }

        .spinner {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        /* Test Cases Preview */
        .test-cases-preview {
          max-height: 400px;
          overflow-y: auto;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          margin-bottom: 20px;
        }

        .test-cases-table {
          width: 100%;
          border-collapse: collapse;
        }

        .test-cases-table th {
          position: sticky;
          top: 0;
          background-color: #f8fafc;
          padding: 12px 16px;
          text-align: left;
          font-weight: 500;
          color: #334155;
          border-bottom: 1px solid #e2e8f0;
        }

        .test-cases-table td {
          padding: 12px 16px;
          border-bottom: 1px solid #e2e8f0;
          font-size: 14px;
        }

        .test-cases-table tr:last-child td {
          border-bottom: none;
        }

        /* Results actions */
        .results-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 20px;
        }

        .action-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 10px 20px;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          border: 1px solid transparent;
        }

        .export-button {
          background-color: #f0fdf4;
          color: #16a34a;
          border-color: #bbf7d0;
        }

        .export-button:hover {
          background-color: #dcfce7;
        }

        .compare-button {
          background-color: #f0f9ff;
          color: #0284c7;
          border-color: #bae6fd;
        }

        .compare-button:hover {
          background-color: #e0f2fe;
        }

        .accept-button {
          background-color: #f0fdf4;
          color: #16a34a;
          border-color: #bbf7d0;
        }

        .accept-button:hover {
          background-color: #dcfce7;
        }

        .notify-button {
          background-color: #f0f9ff;
          color: #0284c7;
          border-color: #bae6fd;
        }

        .notify-button:hover {
          background-color: #e0f2fe;
        }

        .obsolete-button {
          background-color: #fff7ed;
          color: #c2410c;
          border-color: #fed7aa;
        }

        .obsolete-button:hover {
          background-color: #ffedd5;
        }

        .discard-button {
          background-color: #f1f5f9;
          color: #64748b;
          border-color: #e2e8f0;
        }

        .discard-button:hover {
          background-color: #e2e8f0;
        }

        /* File upload */
        .file-upload-container {
          margin-bottom: 20px;
        }

        .file-upload-area {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 180px;
          border: 2px dashed #cbd5e1;
          border-radius: 8px;
          background-color: #f8fafc;
          cursor: pointer;
          transition: all 0.2s ease;
          padding: 20px;
        }

        .file-upload-area:hover {
          border-color: #3b82f6;
          background-color: #f0f9ff;
        }

        .upload-icon, .file-icon {
          margin-bottom: 16px;
          color: #64748b;
        }

        .upload-text {
          font-size: 16px;
          font-weight: 500;
          margin-bottom: 8px;
          color: #334155;
        }

        .upload-hint {
          font-size: 12px;
          color: #64748b;
        }

        .file-name {
          font-size: 16px;
          font-weight: 500;
          margin-bottom: 8px;
          color: #334155;
          max-width: 400px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .file-size {
          font-size: 12px;
          color: #64748b;
        }

        .change-file-btn {
          display: block;
          margin: 10px auto 0;
          padding: 8px 16px;
          background-color: #f1f5f9;
          border: 1px solid #cbd5e1;
          border-radius: 4px;
          color: #334155;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .change-file-btn:hover {
          background-color: #e2e8f0;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          color: #dc2626;
          font-size: 14px;
        }

        /* Comparison View */
        .comparison-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-bottom: 20px;
        }

        .comparison-column {
          display: flex;
          flex-direction: column;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          overflow: hidden;
        }

        .column-header {
          padding: 12px 16px;
          background-color: #f8fafc;
          border-bottom: 1px solid #e2e8f0;
        }

        .column-header h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 500;
          color: #334155;
        }

        .test-case-view {
          max-height: 300px;
          overflow-y: auto;
        }

        .test-case-table {
          width: 100%;
          border-collapse: collapse;
        }

        .test-case-table th {
          position: sticky;
          top: 0;
          background-color: #f8fafc;
          padding: 10px 16px;
          text-align: left;
          font-weight: 500;
          color: #334155;
          border-bottom: 1px solid #e2e8f0;
        }

        .test-case-table td {
          padding: 10px 16px;
          border-bottom: 1px solid #e2e8f0;
          font-size: 14px;
        }

        .test-case-table tr:last-child td {
          border-bottom: none;
        }

        .changed-cell {
          background-color: #e0f2fe;
          position: relative;
        }

        .changed-cell::before {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 3px;
          background-color: #3b82f6;
        }

        /* Suggestions Section */
        .suggestions-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 20px;
        }

        .suggestion-item {
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          overflow: hidden;
          transition: all 0.2s ease;
        }

        .suggestion-item.accepted {
          border-color: #bbf7d0;
          background-color: #f0fdf4;
        }

        .suggestion-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background-color: #f8fafc;
          border-bottom: 1px solid #e2e8f0;
        }

        .suggestion-item.accepted .suggestion-header {
          background-color: #dcfce7;
          border-bottom-color: #bbf7d0;
        }

        .suggestion-type {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;
          font-size: 14px;
        }

        .critical-icon {
          color: #dc2626;
        }

        .warning-icon {
          color: #eab308;
        }

        .info-icon {
          color: #3b82f6;
        }

        .suggestion-controls {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .toggle-button {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 14px;
          font-weight: 500;
          background-color: #f1f5f9;
          border: 1px solid #cbd5e1;
          color: #334155;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .toggle-button:hover {
          background-color: #e2e8f0;
        }

        .toggle-button.accepted {
          background-color: #dcfce7;
          border-color: #bbf7d0;
          color: #16a34a;
        }

        .suggestion-content {
          padding: 16px;
        }

        .suggestion-text {
          margin: 0 0 8px 0;
          font-size: 14px;
        }

        .suggestion-details {
          margin: 0;
          font-size: 13px;
          color: #64748b;
        }

        .suggestion-changes {
          padding: 0 16px 16px;
        }

        .change-item {
          padding: 12px;
          background-color: #f8fafc;
          border-radius: 6px;
          font-size: 14px;
        }

        .change-from, .change-to {
          display: flex;
          margin-bottom: 8px;
        }

        .change-to {
          margin-bottom: 0;
        }

        .label {
          width: 50px;
          font-weight: 500;
        }

        .value {
          flex: 1;
        }

        /* Hidden class for file input */
        .hidden {
          display: none;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
          .test-case-generation-container {
            margin: 1rem;
          }

          .card-header, .card-body {
            padding: 16px 20px;
          }

          .config-grid {
            grid-template-columns: 1fr;
          }

          .comparison-container {
            grid-template-columns: 1fr;
          }

          .results-actions {
            flex-direction: column;
          }

          .action-button {
            width: 100%;
          }

          .tab-button span {
            display: none;
          }

          .tab-button {
            padding: 12px;
          }
        }
      `}</style>
    </div>
  );
};

export default TestCaseGeneration;