import React, { useState } from 'react';
import RequirementsIngestion from './components/Requirements/RequirementsIngestion';
import TestCaseGeneration from './components/TestCases/TestCaseGeneration';

function App() {
  const [activeModule, setActiveModule] = useState('requirements');

  return (
    <div className="App">
      <div className="module-selector">
        <button 
          className={`module-button ${activeModule === 'requirements' ? 'active' : ''}`}
          onClick={() => setActiveModule('requirements')}
        >
          Requirements Ingestion
        </button>
        <button 
          className={`module-button ${activeModule === 'testcases' ? 'active' : ''}`}
          onClick={() => setActiveModule('testcases')}
        >
          Test Case Generation
        </button>
      </div>
      
      {activeModule === 'requirements' ? (
        <RequirementsIngestion />
      ) : (
        <TestCaseGeneration />
      )}

      <style jsx>{`
        .App {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        
        .module-selector {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
        }
        
        .module-button {
          padding: 10px 20px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          background-color: #f8fafc;
          color: #64748b;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .module-button:hover {
          background-color: #f1f5f9;
          color: #3b82f6;
        }
        
        .module-button.active {
          background-color: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }
      `}</style>
    </div>
  );
}

export default App;