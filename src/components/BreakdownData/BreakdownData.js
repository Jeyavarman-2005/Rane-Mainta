import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import { 
  FiSearch, FiFilter, FiDownload, FiRefreshCw, FiChevronDown, 
  FiChevronUp, FiChevronLeft, FiChevronRight, FiX, FiCheck
} from 'react-icons/fi';
import './BreakdownData.css';

const BreakdownData = ({ plant }) => {
  // State management
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [inputFilters, setInputFilters] = useState({
  MachineName: '',
  StartDate: '',
  ShiftName: '',
  ModuleName: '',
  ShopName: '',
  LineName: ''
});

const [appliedFilters, setAppliedFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: 'StartDate', direction: 'desc' });
  const [uniqueValues, setUniqueValues] = useState({
    MachineName: [],
    ShiftName: [],
    ModuleName: [],
    ShopName: [],
    LineName: []
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [searchDropdown, setSearchDropdown] = useState({ field: '', results: [] });
  const [selectedColumns, setSelectedColumns] = useState([
  'MachineName', 'ProblemType', 'Breakdowntype', 'StartDate', 
  'Minutes', 'ActualReason', 'SapStatus', 'ShiftName', 'ShopName', 'ModuleName'
]);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  
  const itemsPerPage = 20;
  const dropdownRef = {
  MachineName: useRef(null),
  ShiftName: useRef(null),
  ModuleName: useRef(null),
  ShopName: useRef(null),
  LineName: useRef(null)
};
  const tableContainerRef = useRef(null);

  // Fetch data from API
  const fetchData = async () => {
  setLoading(true);
  setError(null);
  try {
    let endpoint = 'http://localhost:8001/api/breakdown-data';
    if (plant !== 'master') {
      endpoint = `http://localhost:8001/api/breakdown-data/${plant}`;
    }

    const response = await axios.get(endpoint);
    setData(response.data);
  } catch (err) {
    setError(err.message);
    console.error('Error fetching data:', err);
  } finally {
    setLoading(false);
  }
};

// Update the useEffect hook to just call fetchData
useEffect(() => {
  fetchData();
}, [plant]);

  // Extract unique values for filters
  useEffect(() => {
    if (data.length > 0) {
      setUniqueValues({
        MachineName: [...new Set(data.map(item => item.MachineName))].filter(Boolean).sort(),
        ShiftName: [...new Set(data.map(item => item.ShiftName))].filter(Boolean).sort(),
        ModuleName: [...new Set(data.map(item => item.ModuleName))].filter(Boolean).sort(),
        ShopName: [...new Set(data.map(item => item.ShopName))].filter(Boolean).sort(),
        LineName: [...new Set(data.map(item => item.LineName))].filter(Boolean).sort()
      });
    }
  }, [data]);

  // Apply filters when they change
  useEffect(() => {
    applyFilters();
  }, [data, searchTerm, appliedFilters, sortConfig]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Infinite scroll handler
  useEffect(() => {
    const tableContainer = tableContainerRef.current;
    if (!tableContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = tableContainer;
      if (scrollHeight - (scrollTop + clientHeight) < 50 && currentPage * itemsPerPage < filteredData.length) {
        setCurrentPage(prev => prev + 1);
      }
    };

    tableContainer.addEventListener('scroll', handleScroll);
    return () => tableContainer.removeEventListener('scroll', handleScroll);
  }, [currentPage, filteredData.length]);

  const handleInputChange = (field, value) => {
  setInputFilters(prev => ({ ...prev, [field]: value }));

  // Only perform dropdown logic if field is in uniqueValues
  if (!uniqueValues[field]) return;

  if (value) {
    setActiveDropdown(field);
    const results = uniqueValues[field]
      .filter(item => item.toLowerCase().includes(value.toLowerCase()))
      .slice(0, 10);
    setSearchDropdown({ field, results });
  } else {
    setActiveDropdown(null);
  }
};


  const handleSelectItem = (field, value) => {
    setInputFilters(prev => ({ ...prev, [field]: value }));
    setAppliedFilters(prev => ({ ...prev, [field]: value }));
    setActiveDropdown(null);
  };

  const applyAllFilters = () => {
    const newFilters = Object.fromEntries(
      Object.entries(inputFilters).filter(([_, value]) => value)
    );
    setAppliedFilters(newFilters);
  };

  const resetAllFilters = () => {
    setInputFilters({
      MachineName: '',
      StartDate: '',
      ShiftName: '',
      ModuleName: '',
      ShopName: '',
      LineName: ''
    });
    setAppliedFilters({});
    setActiveDropdown(null);
    setSearchTerm('');
  };

  const applyFilters = () => {
    let result = [...data];
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(item => 
        Object.values(item).some(
          val => val && val.toString().toLowerCase().includes(term)
      ));
    }
    
    Object.entries(appliedFilters).forEach(([key, value]) => {
      if (value) {
        if (key === 'StartDate') {
          const filterDate = new Date(value).toDateString();
          result = result.filter(item => {
            const itemDate = item.StartDate ? new Date(item.StartDate).toDateString() : '';
            return itemDate === filterDate;
          });
        } else {
          result = result.filter(item => item[key] === value);
        }
      }
    });
    
    if (sortConfig.key) {
      result.sort((a, b) => {
        if (sortConfig.key === 'StartDate') {
          const dateA = a.StartDate ? new Date(a.StartDate) : new Date(0);
          const dateB = b.StartDate ? new Date(b.StartDate) : new Date(0);
          return sortConfig.direction === 'asc' ? dateA - dateB : dateB - dateA;
        } else {
          if (a[sortConfig.key] < b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? -1 : 1;
          }
          if (a[sortConfig.key] > b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? 1 : -1;
          }
          return 0;
        }
      });
    }
    
    setFilteredData(result);
    setCurrentPage(1);
  };

  const exportToExcel = () => {
    const ws = XLSX.utils.json_to_sheet(filteredData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "BreakdownData");
    XLSX.writeFile(wb, `BreakdownData_${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateString;
    }
  };

  const formatDuration = (minutes) => {
    if (!minutes) return '0m';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  // Calculate metrics
  const totalRecords = filteredData.length;
  const totalDowntime = Math.round(filteredData.reduce((sum, item) => sum + ((parseInt(item.Minutes) || 0) / 60 * 10), 0) / 10);
  const uniqueMachines = [...new Set(filteredData.map(item => item.MachineName))].filter(Boolean).length;
  const problemTypes = [...new Set(filteredData.map(item => item.ProblemType))].filter(Boolean).length;

  // Column selector functions
  const toggleColumn = (column) => {
    if (selectedColumns.includes(column)) {
      setSelectedColumns(selectedColumns.filter(c => c !== column));
    } else {
      setSelectedColumns([...selectedColumns, column]);
    }
  };

  const handleSort = (key) => {
    setSortConfig({
      key,
      direction: 
        sortConfig.key === key && sortConfig.direction === 'asc' 
          ? 'desc' 
          : 'asc'
    });
  };

  const getSortClass = (key) => {
    return sortConfig.key === key ? `sorted ${sortConfig.direction}` : '';
  };

  const renderSortIcon = (key) => {
    return sortConfig.key === key ? (
      <span className="sort-icon">
        {sortConfig.direction === 'asc' ? '↑' : '↓'}
      </span>
    ) : null;
  };

  const columnDisplayNames = {
  Unique_ID_No: 'ID',
  Type_id: 'Type ID',
  ProblemType: 'Problem Type',
  PlantName: 'Plant',
  ShopName: 'Shop',
  ModuleName: 'Module',
  LineName: 'Line',
  MachineName: 'Machine',
  Servicetype: 'Service Type',
  SapMachnCode: 'SAP Code',
  ShiftName: 'Shift',
  StartDate: 'Start Date',
  StartTime: 'Start Time',
  EndDate: 'End Date',
  EndTime: 'End Time',
  Minutes: 'Duration (min)',
  Hours: 'Hours',
  ClosureReason: 'Closure Reason',
  ActualReason: 'Actual Reason',
  Breakdowntype: 'Breakdown Type',
  SapStatus: 'Status',
  SubGroup: 'Sub Group',
  Phenomena: 'Phenomena',
  Loto: 'LOTO',
  Vendor: 'Vendor',
  Material: 'Material',
  Reason: 'Reason',
  details: 'Details'
};

  if (loading) {
    return (
      <div className="breakdown-container loading">
        <div className="loading-spinner"></div>
        <p>Loading breakdown data...</p>
      </div>
    );
  }

  if (error) {
  return (
    <div className="breakdown-container error">
      <div className="error-icon">!</div>
      <p>Error loading data: {error}</p>
      <button onClick={fetchData} className="retry-button">
        <FiRefreshCw /> Retry
      </button>
    </div>
  );
}

 return (
    <div className="breakdown-container">
      <div className="dashboard-header">
        <h1>Machine Breakdown Dashboard - Plant {plant}</h1>
        
        <div className="metrics-container">
          <div className="metric-card">
            <div className="metric-value">{totalRecords}</div>
            <div className="metric-label">Total Records</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{totalDowntime}h</div>
            <div className="metric-label">Total Downtime</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{uniqueMachines}</div>
            <div className="metric-label">Unique Machines</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{problemTypes}</div>
            <div className="metric-label">Problem Types</div>
          </div>
        </div>
      </div>
      
      <div className="controls-section">
        <div className="search-box">
          <FiSearch className="search-icon" />
          <input
            type="text"
            placeholder="Search across all fields..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="action-buttons">
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`filter-toggle ${showFilters ? 'active' : ''}`}
          >
            <FiFilter /> {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>
          <button onClick={fetchData} className="action-button refresh">
            <FiRefreshCw /> Refresh
          </button>
          <button onClick={exportToExcel} className="action-button export">
            <FiDownload /> Export
          </button>
          <button 
            onClick={() => setShowColumnSelector(!showColumnSelector)}
            className="action-button columns"
          >
            Columns
          </button>
        </div>
      </div>
      
      {showFilters && (
  <div className="filters-panel">
    <div className="filter-row">
      {/* Machine Name Filter */}
      <div className="filter-group">
        <label>Machine Name</label>
        <div className="dropdown-container" ref={dropdownRef}>
          <input
            type="text"
            placeholder="Search machine..."
            value={inputFilters.MachineName}
            onChange={(e) => handleInputChange('MachineName', e.target.value)}
            onFocus={() => handleInputChange('MachineName', inputFilters.MachineName)}
          />
          {activeDropdown === 'MachineName' && (
            <div className="dropdown-menu">
              {searchDropdown.results.length > 0 ? (
                searchDropdown.results.map((item, index) => (
                  <div 
                    key={index}
                    className="dropdown-item"
                    onClick={() => handleSelectItem('MachineName', item)}
                  >
                    {item}
                  </div>
                ))
              ) : (
                <div className="dropdown-item no-results">No matches found</div>
              )}
            </div>
          )}
        </div>
      </div>
            
            <div className="filter-group">
        <label>Date</label>
        <input
          type="date"
          value={inputFilters.StartDate}
          onChange={(e) => {
            handleInputChange('StartDate', e.target.value);
            setAppliedFilters(prev => ({ ...prev, StartDate: e.target.value }));
          }}
        />
      </div>
                        
              <div className="filter-group">
                <label>Shift</label>
                <div className="dropdown-container" ref={dropdownRef}>
                  <input
                    type="text"
                    placeholder="Search shift..."
                    value={inputFilters.ShiftName}
                    onChange={(e) => handleInputChange('ShiftName', e.target.value)}
                    onFocus={() => handleInputChange('ShiftName', inputFilters.ShiftName)}
                  />
                  {activeDropdown === 'ShiftName' && (
                    <div className="dropdown-menu">
                      {searchDropdown.results.length > 0 ? (
                        searchDropdown.results.map((item, index) => (
                          <div
                            key={index}
                            className="dropdown-item"
                            onClick={() => handleSelectItem('ShiftName', item)}
                          >
                            {item}
                          </div>
                        ))
                      ) : (
                        <div className="dropdown-item no-results">No matches found</div>
                      )}
                    </div>
                  )}
                </div>
                  </div>
                </div>
          
           <div className="filter-row">
      {/* Module Filter */}
      <div className="filter-group">
        <label>Module</label>
        <div className="dropdown-container">
          <input
            type="text"
            placeholder="Search module..."
            value={inputFilters.ModuleName}
            onChange={(e) => handleInputChange('ModuleName', e.target.value)}
            onFocus={() => handleInputChange('ModuleName', inputFilters.ModuleName)}
          />
          {activeDropdown === 'ModuleName' && (
            <div className="dropdown-menu">
              {searchDropdown.results.length > 0 ? (
                searchDropdown.results.map((item, index) => (
                  <div 
                    key={index}
                    className="dropdown-item"
                    onClick={() => handleSelectItem('ModuleName', item)}
                  >
                    {item}
                  </div>
                ))
              ) : (
                <div className="dropdown-item no-results">No matches found</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Shop Filter */}
      <div className="filter-group">
        <label>Shop</label>
        <div className="dropdown-container">
          <input
            type="text"
            placeholder="Search shop..."
            value={inputFilters.ShopName}
            onChange={(e) => handleInputChange('ShopName', e.target.value)}
            onFocus={() => handleInputChange('ShopName', inputFilters.ShopName)}
          />
          {activeDropdown === 'ShopName' && (
            <div className="dropdown-menu">
              {searchDropdown.results.length > 0 ? (
                searchDropdown.results.map((item, index) => (
                  <div 
                    key={index}
                    className="dropdown-item"
                    onClick={() => handleSelectItem('ShopName', item)}
                  >
                    {item}
                  </div>
                ))
              ) : (
                <div className="dropdown-item no-results">No matches found</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Line Filter */}
      <div className="filter-group">
        <label>Line</label>
        <div className="dropdown-container">
          <input
            type="text"
            placeholder="Search line..."
            value={inputFilters.LineName}
            onChange={(e) => handleInputChange('LineName', e.target.value)}
            onFocus={() => handleInputChange('LineName', inputFilters.LineName)}
          />
          {activeDropdown === 'LineName' && (
            <div className="dropdown-menu">
              {searchDropdown.results.length > 0 ? (
                searchDropdown.results.map((item, index) => (
                  <div 
                    key={index}
                    className="dropdown-item"
                    onClick={() => handleSelectItem('LineName', item)}
                  >
                    {item}
                  </div>
                ))
              ) : (
                <div className="dropdown-item no-results">No matches found</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>

    <div className="filter-actions">
      <button onClick={resetAllFilters} className="reset-button">
        Reset All Filters
      </button>
      <button onClick={applyAllFilters} className="apply-button">
        <FiCheck /> Apply Filters
      </button>
    </div>
  </div>
)}
      
      <div className="data-table-container" ref={tableContainerRef}>
        <table className="data-table">
          <thead>
            <tr>
              {selectedColumns.includes('MachineName') && (
                <th 
                  onClick={() => handleSort('MachineName')}
                  className={getSortClass('MachineName')}
                >
                  Machine {renderSortIcon('MachineName')}
                </th>
              )}
              {selectedColumns.includes('ProblemType') && (
                <th 
                  onClick={() => handleSort('ProblemType')}
                  className={getSortClass('ProblemType')}
                >
                  Problem Type {renderSortIcon('ProblemType')}
                </th>
              )}
              {selectedColumns.includes('Breakdowntype') && (
                <th 
                  onClick={() => handleSort('Breakdowntype')}
                  className={getSortClass('Breakdowntype')}
                >
                  Breakdown Type {renderSortIcon('Breakdowntype')}
                </th>
              )}
              {selectedColumns.includes('StartDate') && (
                <th 
                  onClick={() => handleSort('StartDate')}
                  className={getSortClass('StartDate')}
                >
                  Start Time {renderSortIcon('StartDate')}
                </th>
              )}
              {selectedColumns.includes('Minutes') && (
                <th 
                  onClick={() => handleSort('Minutes')}
                  className={getSortClass('Minutes')}
                >
                  Duration {renderSortIcon('Minutes')}
                </th>
              )}
              {selectedColumns.includes('ActualReason') && (
                <th 
                  onClick={() => handleSort('ActualReason')}
                  className={getSortClass('ActualReason')}
                >
                  Actual Reason {renderSortIcon('ActualReason')}
                </th>
              )}
              {selectedColumns.includes('SapStatus') && (
                <th 
                  onClick={() => handleSort('SapStatus')}
                  className={getSortClass('SapStatus')}
                >
                  Status {renderSortIcon('SapStatus')}
                </th>
              )}
              {selectedColumns.includes('ShiftName') && (
                <th 
                  onClick={() => handleSort('ShiftName')}
                  className={getSortClass('ShiftName')}
                >
                  Shift {renderSortIcon('ShiftName')}
                </th>
              )}
              {selectedColumns.includes('ShopName') && (
                <th 
                  onClick={() => handleSort('ShopName')}
                  className={getSortClass('ShopName')}
                >
                  Shop {renderSortIcon('ShopName')}
                </th>
              )}
              {selectedColumns.includes('ModuleName') && (
                <th 
                  onClick={() => handleSort('ModuleName')}
                  className={getSortClass('ModuleName')}
                >
                  Module {renderSortIcon('ModuleName')}
                </th>
              )}
              {selectedColumns.includes('LineName') && (
                <th 
                  onClick={() => handleSort('LineName')}
                  className={getSortClass('LineName')}
                >
                  Line {renderSortIcon('LineName')}
                </th>
              )}
              {selectedColumns.includes('PlantName') && (
                <th 
                  onClick={() => handleSort('PlantName')}
                  className={getSortClass('PlantName')}
                >
                  Plant {renderSortIcon('PlantName')}
                </th>
              )}
              {selectedColumns.includes('Servicetype') && (
                <th 
                  onClick={() => handleSort('Servicetype')}
                  className={getSortClass('Servicetype')}
                >
                  Service Type {renderSortIcon('Servicetype')}
                </th>
              )}
              {selectedColumns.includes('SapMachnCode') && (
                <th 
                  onClick={() => handleSort('SapMachnCode')}
                  className={getSortClass('SapMachnCode')}
                >
                  SAP Code {renderSortIcon('SapMachnCode')}
                </th>
              )}
              {selectedColumns.includes('EndDate') && (
                <th 
                  onClick={() => handleSort('EndDate')}
                  className={getSortClass('EndDate')}
                >
                  End Time {renderSortIcon('EndDate')}
                </th>
              )}
              {selectedColumns.includes('ClosureReason') && (
                <th 
                  onClick={() => handleSort('ClosureReason')}
                  className={getSortClass('ClosureReason')}
                >
                  Closure Reason {renderSortIcon('ClosureReason')}
                </th>
              )}
              {selectedColumns.includes('SubGroup') && (
                <th 
                  onClick={() => handleSort('SubGroup')}
                  className={getSortClass('SubGroup')}
                >
                  Sub Group {renderSortIcon('SubGroup')}
                </th>
              )}
              {selectedColumns.includes('Phenomena') && (
                <th 
                  onClick={() => handleSort('Phenomena')}
                  className={getSortClass('Phenomena')}
                >
                  Phenomena {renderSortIcon('Phenomena')}
                </th>
              )}
              {selectedColumns.includes('Loto') && (
                <th 
                  onClick={() => handleSort('Loto')}
                  className={getSortClass('Loto')}
                >
                  LOTO {renderSortIcon('Loto')}
                </th>
              )}
              {selectedColumns.includes('Vendor') && (
                <th 
                  onClick={() => handleSort('Vendor')}
                  className={getSortClass('Vendor')}
                >
                  Vendor {renderSortIcon('Vendor')}
                </th>
              )}
              {selectedColumns.includes('Material') && (
                <th 
                  onClick={() => handleSort('Material')}
                  className={getSortClass('Material')}
                >
                  Material {renderSortIcon('Material')}
                </th>
              )}
              {selectedColumns.includes('Reason') && (
                <th 
                  onClick={() => handleSort('Reason')}
                  className={getSortClass('Reason')}
                >
                  Reason {renderSortIcon('Reason')}
                </th>
              )}
              {selectedColumns.includes('details') && (
                <th 
                  onClick={() => handleSort('details')}
                  className={getSortClass('details')}
                >
                  Details {renderSortIcon('details')}
                </th>
              )}
              {selectedColumns.includes('Unique_ID_No') && (
                <th 
                  onClick={() => handleSort('Unique_ID_No')}
                  className={getSortClass('Unique_ID_No')}
                >
                  ID {renderSortIcon('Unique_ID_No')}
                </th>
              )}
              {selectedColumns.includes('Type_id') && (
                <th 
                  onClick={() => handleSort('Type_id')}
                  className={getSortClass('Type_id')}
                >
                  Type ID {renderSortIcon('Type_id')}
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {filteredData.slice(0, currentPage * itemsPerPage).map((item, index) => (
              <tr key={item.Unique_ID_No || index}>
                {selectedColumns.includes('MachineName') && (
                  <td>{item.MachineName}</td>
                )}
                {selectedColumns.includes('ProblemType') && (
                  <td>{item.ProblemType}</td>
                )}
                {selectedColumns.includes('Breakdowntype') && (
                  <td>
                    <span className={`breakdown-tag ${item.Breakdowntype?.toLowerCase().replace(/\s+/g, '-') || 'other'}`}>
                      {item.Breakdowntype}
                    </span>
                  </td>
                )}
                {selectedColumns.includes('StartDate') && (
                  <td>{formatDate(item.StartDate)}</td>
                )}
                {selectedColumns.includes('Minutes') && (
                  <td>{formatDuration(item.Minutes)}</td>
                )}
                {selectedColumns.includes('ActualReason') && (
                  <td className="reason-cell">
                    <div className="reason-content">{item.ActualReason}</div>
                  </td>
                )}
                {selectedColumns.includes('SapStatus') && (
                  <td>
                    <span className={`status-badge ${item.SapStatus === 'Y' ? 'resolved' : 'pending'}`}>
                      {item.SapStatus === 'Y' ? 'Resolved' : 'Pending'}
                    </span>
                  </td>
                )}
                {selectedColumns.includes('ShiftName') && (
                  <td>{item.ShiftName}</td>
                )}
                {selectedColumns.includes('PlantName') && (
                  <td>{item.PlantName}</td>
                )}
                {selectedColumns.includes('ShopName') && (
                  <td>{item.ShopName}</td>
                )}
                {selectedColumns.includes('ModuleName') && (
                  <td>{item.ModuleName}</td>
                )}
                {selectedColumns.includes('LineName') && (
                  <td>{item.LineName}</td>
                )}
                {selectedColumns.includes('Servicetype') && (
                  <td>{item.Servicetype}</td>
                )}
                {selectedColumns.includes('SapMachnCode') && (
                  <td>{item.SapMachnCode}</td>
                )}
                {selectedColumns.includes('EndDate') && (
                  <td>{formatDate(item.EndDate)}</td>
                )}
                {selectedColumns.includes('ClosureReason') && (
                  <td>{item.ClosureReason}</td>
                )}
                {selectedColumns.includes('SubGroup') && (
                  <td>{item.SubGroup}</td>
                )}
                {selectedColumns.includes('Phenomena') && (
                  <td>{item.Phenomena}</td>
                )}
                {selectedColumns.includes('Loto') && (
                  <td>{item.Loto}</td>
                )}
                {selectedColumns.includes('Vendor') && (
                  <td>{item.Vendor}</td>
                )}
                {selectedColumns.includes('Material') && (
                  <td>{item.Material}</td>
                )}
                {selectedColumns.includes('Reason') && (
                  <td>{item.Reason}</td>
                )}
                {selectedColumns.includes('details') && (
                  <td>{item.details}</td>
                )}
                {selectedColumns.includes('Unique_ID_No') && (
                  <td>{item.Unique_ID_No}</td>
                )}
                {selectedColumns.includes('Type_id') && (
                  <td>{item.Type_id}</td>
                )}
              </tr>
            ))}
            {filteredData.length === 0 && (
              <tr>
                <td colSpan={selectedColumns.length} className="no-results">
                  No matching records found. Try adjusting your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {showColumnSelector && (
        <div className="column-selector-overlay">
          <div className="column-selector">
            <div className="selector-header">
              <h3>Select Columns</h3>
              <button 
                onClick={() => setShowColumnSelector(false)}
                className="close-button"
              >
                <FiX />
              </button>
            </div>
            <div className="columns-list">
              {Object.keys(columnDisplayNames).map(column => (
                <div key={column} className="column-item">
                  <input
                    type="checkbox"
                    id={`col-${column}`}
                    checked={selectedColumns.includes(column)}
                    onChange={() => toggleColumn(column)}
                  />
                  <label htmlFor={`col-${column}`}>
                    {columnDisplayNames[column] || column}
                  </label>
                </div>
              ))}
            </div>
            <div className="selector-actions">
              <button 
                onClick={() => setSelectedColumns(Object.keys(columnDisplayNames))}
                className="action-button select-all"
              >
                Select All
              </button>
              <button 
                onClick={() => setSelectedColumns([])}
                className="action-button select-none"
              >
                Select None
              </button>
              <button 
                onClick={() => setShowColumnSelector(false)}
                className="action-button apply"
              >
                Apply
              </button>
              <button 
                className="scroll-down-button"
                onClick={() => {
                  tableContainerRef.current?.scrollTo({
                    top: tableContainerRef.current.scrollHeight,
                    behavior: 'smooth'
                  });
                }}
              >
                <FiChevronDown /> Scroll Down
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BreakdownData;