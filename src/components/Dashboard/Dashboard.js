import React from 'react';
import { 
  BsDatabase, BsLightningFill 
} from 'react-icons/bs';
import { 
  MdOutlineSupport 
} from 'react-icons/md';
import { TbChartArcs } from 'react-icons/tb';
import './Dashboard.css';

const Dashboard = () => {
  return (
    <div className="dashboard-tab">
      <h3>Maintenance Dashboard</h3>
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3><BsDatabase /> Total Machines</h3>
          <p>1,247</p>
        </div>
        <div className="dashboard-card">
          <h3><TbChartArcs /> MTBF</h3>
          <p>142 hours</p>
        </div>
        <div className="dashboard-card">
          <h3><MdOutlineSupport /> Active Issues</h3>
          <p>23</p>
        </div>
        <div className="dashboard-card">
          <h3><BsLightningFill /> Breakdowns Today</h3>
          <p>4</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;