import React, { useState, useRef } from 'react';
import { Upload, Edit, Database, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import axios from 'axios';

const RequirementsIngestion = () => {
  // State management for different input methods
  const [inputMethod, setInputMethod] = useState('manual');
  const [manualInput, setManualInput] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [jiraConfig, setJiraConfig] = useState({
    url: '',
    projectKey: '',
    apiToken: ''
  });

  // State for processing and validation
  const [processingStatus, setProcessingStatus] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  // Reference for file input
  const fileInputRef = useRef(null);

  // Handler for input method selection
  const handleInputMethodChange = (method) => {
    setInputMethod(method);
    // Reset states when changing method
    setManualInput('');
    setUploadedFile(null);
    setJiraConfig({ url: '', projectKey: '', apiToken: '' });
    setProcessingStatus(null);
    setValidationErrors({});
  };

  // File upload handlers
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    
    // Validate file type
    const allowedTypes = [
      'application/msword', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/pdf',
      'text/plain'
    ];

    if (file) {
      if (!allowedTypes.includes(file.type)) {
        setValidationErrors({
          file: 'Unsupported file type. Please upload Word, Excel, PDF, or Text files.'
        });
        return;
      }

      // Check file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setValidationErrors({
          file: 'File size exceeds 10MB limit.'
        });
        return;
      }

      setUploadedFile(file);
      setValidationErrors({});
    }
  };

  // JIRA configuration handlers
  const handleJiraConfigChange = (e) => {
    const { name, value } = e.target;
    setJiraConfig(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Validation methods
  const validateInput = () => {
    const errors = {};

    switch (inputMethod) {
      case 'manual':
        if (!manualInput.trim()) {
          errors.manual = 'Requirements text cannot be empty';
        }
        break;
      case 'file':
        if (!uploadedFile) {
          errors.file = 'Please upload a file';
        }
        break;
      case 'jira':
        if (!jiraConfig.url.trim()) {
          errors.url = 'JIRA URL is required';
        }
        if (!jiraConfig.projectKey.trim()) {
          errors.projectKey = 'Project Key is required';
        }
        if (!jiraConfig.apiToken.trim()) {
          errors.apiToken = 'API Token is required';
        }
        break;
      default:
        break;
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Process requirements
  const processRequirements = async () => {
    // Validate input first
    if (!validateInput()) return;

    setProcessingStatus('processing');

    try {
      let processedData;
      const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

      switch (inputMethod) {
        case 'manual':
          processedData = await axios.post(`${API_BASE_URL}/requirements/manual-input`, 
            { requirements_text: manualInput },
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          break;
        case 'file':
          const formData = new FormData();
          formData.append('file', uploadedFile);
          processedData = await axios.post(`${API_BASE_URL}/requirements/file-upload`, 
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          break;
        case 'jira':
          const jiraFormData = new FormData();
          jiraFormData.append('url', jiraConfig.url);
          jiraFormData.append('project_key', jiraConfig.projectKey);
          jiraFormData.append('api_token', jiraConfig.apiToken);
          processedData = await axios.post(`${API_BASE_URL}/requirements/jira-requirements`, 
            jiraFormData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          break;
        default:
          throw new Error('Invalid input method');
      }

      setProcessingStatus('success');
      console.log(processedData.data);
    } catch (error) {
      setProcessingStatus('error');
      setValidationErrors({ 
        processing: error.response?.data?.detail || 'Failed to process requirements' 
      });
    }
  };

  // Render input method selection
  const renderInputMethodSelector = () => (
    <div className="input-method-tabs">
      <button
        onClick={() => handleInputMethodChange('manual')}
        className={`tab-button ${inputMethod === 'manual' ? 'active' : ''}`}
      >
        <Edit size={18} />
        <span>Manual Input</span>
      </button>
      <button
        onClick={() => handleInputMethodChange('file')}
        className={`tab-button ${inputMethod === 'file' ? 'active' : ''}`}
      >
        <Upload size={18} />
        <span>File Upload</span>
      </button>
      <button
        onClick={() => handleInputMethodChange('jira')}
        className={`tab-button ${inputMethod === 'jira' ? 'active' : ''}`}
      >
        <Database size={18} />
        <span>JIRA Connection</span>
      </button>
    </div>
  );

  // Render specific input method form
  const renderInputMethodForm = () => {
    switch (inputMethod) {
      case 'manual':
        return (
          <div className="input-container">
            <div className="form-title">
              <Edit size={20} />
              <h3>Enter Requirements Text</h3>
            </div>
            <div className="form-description">
              Type or paste your requirements directly into the text area below.
            </div>
            <textarea
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Enter user stories, requirements, or business cases here..."
              className="input-textarea"
            />
            {validationErrors.manual && (
              <p className="error-message">{validationErrors.manual}</p>
            )}
          </div>
        );
      
      case 'file':
        return (
          <div className="input-container">
            <div className="form-title">
              <Upload size={20} />
              <h3>Upload Requirements Document</h3>
            </div>
            <div className="form-description">
              Upload Word, Excel, PDF, or Text files containing your requirements.
            </div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".doc,.docx,.xls,.xlsx,.pdf,.txt"
              className="hidden"
            />
            <div className="file-upload-container">
              <div className="file-upload-area" onClick={() => fileInputRef.current.click()}>
                {uploadedFile ? (
                  <>
                    <FileText size={40} className="file-icon" />
                    <span className="file-name">{uploadedFile.name}</span>
                    <span className="file-size">
                      {(uploadedFile.size / 1024).toFixed(2)} KB
                    </span>
                  </>
                ) : (
                  <>
                    <Upload size={40} className="upload-icon" />
                    <span className="upload-text">Drag & drop a file here or click to browse</span>
                    <span className="upload-hint">Supported formats: Word, Excel, PDF, Text</span>
                  </>
                )}
              </div>
              {uploadedFile && (
                <button 
                  className="change-file-btn"
                  onClick={() => fileInputRef.current.click()}
                >
                  Change File
                </button>
              )}
            </div>
            {validationErrors.file && (
              <p className="error-message">{validationErrors.file}</p>
            )}
          </div>
        );
      
      case 'jira':
        return (
          <div className="input-container">
            <div className="form-title">
              <Database size={20} />
              <h3>Connect to JIRA</h3>
            </div>
            <div className="form-description">
              Connect to your JIRA account to import requirements directly.
            </div>
            <div className="jira-form">
              <div className="form-group">
                <label>JIRA URL</label>
                <input
                  type="text"
                  name="url"
                  value={jiraConfig.url}
                  onChange={handleJiraConfigChange}
                  placeholder="e.g., https://yourcompany.atlassian.net"
                  className="input-field"
                />
                {validationErrors.url && (
                  <p className="error-message">{validationErrors.url}</p>
                )}
              </div>
              
              <div className="form-group">
                <label>Project Key</label>
                <input
                  type="text"
                  name="projectKey"
                  value={jiraConfig.projectKey}
                  onChange={handleJiraConfigChange}
                  placeholder="e.g., TEST"
                  className="input-field"
                />
                {validationErrors.projectKey && (
                  <p className="error-message">{validationErrors.projectKey}</p>
                )}
              </div>
              
              <div className="form-group">
                <label>API Token</label>
                <input
                  type="password"
                  name="apiToken"
                  value={jiraConfig.apiToken}
                  onChange={handleJiraConfigChange}
                  placeholder="Your JIRA API token"
                  className="input-field"
                />
                {validationErrors.apiToken && (
                  <p className="error-message">{validationErrors.apiToken}</p>
                )}
              </div>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  // Render processing status
  const renderProcessingStatus = () => {
    if (!processingStatus) return null;

    switch (processingStatus) {
      case 'processing':
        return (
          <div className="status-message processing">
            <Loader size={20} className="spinner" />
            <span>Processing requirements...</span>
          </div>
        );
      case 'success':
        return (
          <div className="status-message success">
            <CheckCircle size={20} />
            <span>Requirements processed successfully!</span>
          </div>
        );
      case 'error':
        return (
          <div className="status-message error">
            <AlertCircle size={20} />
            <span>{validationErrors.processing || 'Failed to process requirements'}</span>
          </div>
        );
      default:
        return null;
    }
  };

  // Main render method
  return (
    <div className="requirements-ingestion-container">
      <div className="card">
        <div className="card-header">
          <h2>Requirements Ingestion</h2>
          <p>Import your requirements using one of the methods below.</p>
        </div>
        
        {renderInputMethodSelector()}
        
        <div className="card-body">
          {renderInputMethodForm()}
        </div>
        
        <div className="card-footer">
          <button
            onClick={processRequirements}
            className="process-button"
            disabled={processingStatus === 'processing'}
          >
            {processingStatus === 'processing' ? (
              <>
                <Loader size={16} className="spinner" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span>Process Requirements</span>
              </>
            )}
          </button>
          
          {renderProcessingStatus()}
        </div>
      </div>

      <style jsx>{`
        /* Global styles */
        .requirements-ingestion-container {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          max-width: 800px;
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

        .card-footer {
          padding: 24px 32px;
          background-color: #f8fafc;
          border-top: 1px solid #e2e8f0;
        }

        /* Input method tabs */
        .input-method-tabs {
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

        /* Form elements */
        .input-container {
          margin-bottom: 20px;
        }

        .form-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
          color: #1e3a8a;
        }

        .form-title h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .form-description {
          margin-bottom: 20px;
          color: #64748b;
          font-size: 14px;
        }

        .input-textarea {
          width: 100%;
          min-height: 200px;
          padding: 12px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-family: inherit;
          font-size: 14px;
          resize: vertical;
          transition: border-color 0.2s ease;
        }

        .input-textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }

        .file-upload-container {
          margin-bottom: 20px;
        }

        .file-upload-area {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 200px;
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

        .jira-form {
          display: grid;
          gap: 20px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .form-group label {
          font-size: 14px;
          font-weight: 500;
          color: #334155;
        }

        .input-field {
          padding: 10px 12px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 14px;
          transition: all 0.2s ease;
        }

        .input-field:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }

        .error-message {
          margin-top: 6px;
          font-size: 12px;
          color: #dc2626;
        }

        /* Process button */
        .process-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          width: 100%;
          padding: 12px;
          background: linear-gradient(135deg, #2563eb, #3b82f6);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .process-button:hover {
          background: linear-gradient(135deg, #1d4ed8, #2563eb);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }

        .process-button:active {
          transform: translateY(0);
        }

        .process-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }

        /* Status messages */
        .status-message {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 16px;
          padding: 12px;
          border-radius: 6px;
          font-size: 14px;
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

        /* Responsive adjustments */
        @media (max-width: 768px) {
          .requirements-ingestion-container {
            margin: 1rem;
          }

          .card-header, .card-body, .card-footer {
            padding: 16px 20px;
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

export default RequirementsIngestion;