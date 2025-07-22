import React from 'react';

const MachineHistoryResponse = ({ data }) => {
  return (
    <div className="machine-history-response">
      {/* Header */}
      <h3 className="machine-header">
        🖥️ {data.machine} 
        {data.sap_code && <span> (SAP: {data.sap_code})</span>}
      </h3>
      
      {/* Top Problems */}
      <div className="top-problems">
        <h4>🔝 Top Problems:</h4>
        <ul>
          {data.top_problems.map(([problem, count], index) => (
            <li key={index}>
              {problem} <span className="count">({count} times)</span>
            </li>
          ))}
        </ul>
      </div>
      
      {/* Breakdown Table */}
      <div className="breakdown-table">
        <h4>📅 Latest Breakdowns:</h4>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Problem</th>
              <th>Downtime (min)</th>
              <th>Solution</th>
            </tr>
          </thead>
          <tbody>
            {data.breakdowns.map((row, index) => (
              <tr key={index}>
                <td>{row.date.split('  ')[0]}</td> {/* Show only date */}
                <td>{row.problem}</td>
                <td className="downtime">{row.downtime}</td>
                <td>{row.solution || 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MachineHistoryResponse;