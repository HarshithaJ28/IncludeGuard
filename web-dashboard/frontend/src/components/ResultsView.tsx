import { Download, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { api } from '../api';
import type { JobStatus } from '../api';
import { useState, useEffect } from 'react';

interface ResultsViewProps {
  jobStatus: JobStatus;
  onReset: () => void;
}

export default function ResultsView({ jobStatus, onReset }: ResultsViewProps) {
  const result = jobStatus.result;
  const [isDark, setIsDark] = useState(false);
  const [activeSection, setActiveSection] = useState('overview');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setIsDark(savedTheme === 'dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = !isDark;
    setIsDark(newTheme);
    localStorage.setItem('theme', newTheme ? 'dark' : 'light');
  };

  if (!result) {
    return (
      <div style={{ 
        background: '#ffffff', 
        borderRadius: '16px', 
        padding: '32px', 
        textAlign: 'center',
        border: '1px solid #e2e8f0'
      }}>
        <AlertTriangle style={{ width: '64px', height: '64px', color: '#f59e0b', margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>No Results Available</h2>
        <p style={{ color: '#64748b', marginBottom: '24px' }}>The analysis completed but no results were returned.</p>
        <button
          onClick={onReset}
          style={{
            background: '#8b5cf6',
            color: 'white',
            fontWeight: '600',
            padding: '12px 24px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  const scrollToSection = (sectionId: string) => {
    setActiveSection(sectionId);
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Prepare chart data
  const fileCostData = result.top_opportunities
    .reduce((acc: any[], opp) => {
      const existing = acc.find(f => f.name === opp.file);
      if (existing) {
        existing.value += opp.cost;
      } else {
        acc.push({ name: opp.file, value: opp.cost });
      }
      return acc;
    }, [])
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  const wasteData = result.top_opportunities
    .reduce((acc: any[], opp) => {
      const existing = acc.find(f => f.file === opp.file);
      if (existing) {
        existing.waste += opp.cost;
      } else {
        acc.push({ file: opp.file, waste: opp.cost });
      }
      return acc;
    }, [])
    .sort((a, b) => b.waste - a.waste)
    .slice(0, 6);

  const pieColors = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#e9d5ff', '#f3e8ff'];

  const styles = {
    bgLight: isDark ? '#0f172a' : '#f8fafc',
    bgWhite: isDark ? '#1e293b' : '#ffffff',
    textDark: isDark ? '#f1f5f9' : '#1e293b',
    textGray: isDark ? '#94a3b8' : '#64748b',
    border: isDark ? '#334155' : '#e2e8f0',
  };

  return (
    <>
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        html {
          scroll-behavior: smooth;
        }
        
        body {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .fade-in {
          animation: fadeInUp 0.5s ease;
        }
        
        .card {
          animation: fadeInUp 0.6s ease;
        }
        
        .metric-card {
          transition: all 0.3s;
        }
        
        .metric-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 20px rgba(139,92,246,0.15);
        }
        
        .nav-item {
          transition: all 0.2s;
        }
        
        .cost-high {
          color: #ef4444;
          font-weight: 600;
        }
        
        .cost-medium {
          color: #f59e0b;
          font-weight: 600;
        }
        
        .cost-low {
          color: #10b981;
          font-weight: 500;
        }
        
        table {
          width: 100%;
          border-collapse: collapse;
        }
        
        thead {
          background: ${styles.bgLight};
        }
        
        th {
          padding: 12px 16px;
          text-align: left;
          color: ${styles.textGray};
          font-weight: 600;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        td {
          padding: 14px 16px;
          border-top: 1px solid ${styles.border};
          color: ${styles.textDark};
          font-size: 14px;
        }
        
        tbody tr {
          transition: background 0.2s;
        }
        
        tbody tr:hover {
          background: ${styles.bgLight};
        }
        
        code {
          background: ${styles.bgLight};
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Fira Code', 'Courier New', monospace;
          color: #6366f1;
          font-size: 13.5px;
          font-weight: 500;
        }
      `}</style>

      <div style={{ display: 'flex', background: styles.bgLight, minHeight: '100vh' }}>
        {/* Sidebar */}
        <div style={{
          position: 'fixed',
          left: 0,
          top: 0,
          width: '200px',
          height: '100vh',
          background: 'linear-gradient(180deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%)',
          padding: '24px 16px',
          boxShadow: '2px 0 12px rgba(0,0,0,0.1)',
          zIndex: 1000,
        }}>
          <div style={{
            color: 'white',
            fontSize: '17.6px',
            fontWeight: 700,
            marginBottom: '32px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <i className="fas fa-shield-halved"></i>
            <span>IncludeGuard</span>
          </div>

          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <a
              href="#overview"
              onClick={(e) => {
                e.preventDefault();
                scrollToSection('overview');
              }}
              className="nav-item"
              style={{
                color: activeSection === 'overview' ? 'white' : 'rgba(255,255,255,0.8)',
                padding: '8px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '13.6px',
                textDecoration: 'none',
                background: activeSection === 'overview' ? 'rgba(255,255,255,0.2)' : 'transparent',
                fontWeight: activeSection === 'overview' ? 600 : 400,
              }}
            >
              <i className="fas fa-chart-line" style={{ width: '16px' }}></i>
              Overview
            </a>
            <a
              href="#opportunities"
              onClick={(e) => {
                e.preventDefault();
                scrollToSection('opportunities');
              }}
              className="nav-item"
              style={{
                color: activeSection === 'opportunities' ? 'white' : 'rgba(255,255,255,0.8)',
                padding: '8px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '13.6px',
                textDecoration: 'none',
                background: activeSection === 'opportunities' ? 'rgba(255,255,255,0.2)' : 'transparent',
                fontWeight: activeSection === 'opportunities' ? 600 : 400,
              }}
            >
              <i className="fas fa-lightbulb" style={{ width: '16px' }}></i>
              Opportunities
            </a>
            {result.pch_recommendations && result.pch_recommendations.length > 0 && (
              <a
                href="#pch"
                onClick={(e) => {
                  e.preventDefault();
                  scrollToSection('pch');
                }}
                className="nav-item"
                style={{
                  color: activeSection === 'pch' ? 'white' : 'rgba(255,255,255,0.8)',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '13.6px',
                  textDecoration: 'none',
                  background: activeSection === 'pch' ? 'rgba(255,255,255,0.2)' : 'transparent',
                  fontWeight: activeSection === 'pch' ? 600 : 400,
                }}
              >
                <i className="fas fa-layer-group" style={{ width: '16px' }}></i>
                PCH
              </a>
            )}
          </nav>

          <div style={{
            position: 'absolute',
            bottom: '24px',
            left: '16px',
            right: '16px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(255,255,255,0.1)',
          }}>
            <button
              onClick={toggleTheme}
              style={{
                width: '100%',
                padding: '8px',
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: 'white',
                borderRadius: '8px',
                cursor: 'pointer',
                fontFamily: 'Inter, sans-serif',
                fontSize: '12.8px',
                marginBottom: '8px',
              }}
            >
              <i className="fas fa-moon" style={{ marginRight: '8px' }}></i>
              Toggle Dark Mode
            </button>
            <button
              onClick={onReset}
              style={{
                width: '100%',
                padding: '8px',
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: 'white',
                borderRadius: '8px',
                cursor: 'pointer',
                fontFamily: 'Inter, sans-serif',
                fontSize: '12.8px',
              }}
            >
              <i className="fas fa-arrow-left" style={{ marginRight: '8px' }}></i>
              New Analysis
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ marginLeft: '200px', flex: 1, padding: '32px', minHeight: '100vh' }}>
          {/* Overview Section */}
          <div id="overview" className="fade-in">
            <div style={{ marginBottom: '32px' }}>
              <h1 style={{
                fontSize: '24px',
                color: styles.textDark,
                marginBottom: '4px',
                fontWeight: 700,
              }}>
                C++ Include Analysis
              </h1>
              <p style={{ color: styles.textGray, fontSize: '13.6px' }}>
                Comprehensive analysis of header dependencies and build optimization opportunities
              </p>
            </div>

            {/* Metrics Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '20px',
              marginBottom: '32px',
            }}>
              <MetricCard
                icon="fas fa-folder-open"
                label="Files Analyzed"
                value={result.total_files.toString()}
                styles={styles}
              />
              <MetricCard
                icon="fas fa-link"
                label="Total Includes"
                value={result.top_opportunities.length.toString()}
                styles={styles}
              />
              <MetricCard
                icon="fas fa-clock"
                label="Total Cost"
                value={result.total_cost.toLocaleString()}
                styles={styles}
              />
              <MetricCard
                icon="fas fa-trash-can"
                label="Wasted Cost"
                value={result.wasted_cost.toLocaleString()}
                valueColor="#ef4444"
                styles={styles}
              />
              <MetricCard
                icon="fas fa-percentage"
                label="Waste Percentage"
                value={`${result.waste_percentage.toFixed(1)}%`}
                valueColor="#f59e0b"
                styles={styles}
              />
            </div>

            {/* Charts Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
              <div className="card" style={{
                background: styles.bgWhite,
                padding: '24px',
                borderRadius: '16px',
                border: `1px solid ${styles.border}`,
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}>
                <h2 style={{
                  fontSize: '16px',
                  color: styles.textDark,
                  marginBottom: '16px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}>
                  <i className="fas fa-chart-bar"></i>
                  Cost Distribution
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={fileCostData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name}: ${((entry.value / result.total_cost) * 100).toFixed(1)}%`}
                      outerRadius={90}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {fileCostData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: styles.bgWhite,
                        border: `1px solid ${styles.border}`,
                        borderRadius: '8px',
                        color: styles.textDark,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="card" style={{
                background: styles.bgWhite,
                padding: '24px',
                borderRadius: '16px',
                border: `1px solid ${styles.border}`,
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}>
                <h2 style={{
                  fontSize: '16px',
                  color: styles.textDark,
                  marginBottom: '16px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}>
                  <i className="fas fa-trash"></i>
                  Wasted Cost by File
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={wasteData}>
                    <XAxis
                      dataKey="file"
                      angle={-45}
                      textAnchor="end"
                      height={120}
                      stroke={styles.textGray}
                      style={{ fontSize: '11px' }}
                    />
                    <YAxis stroke={styles.textGray} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: styles.bgWhite,
                        border: `1px solid ${styles.border}`,
                        borderRadius: '8px',
                        color: styles.textDark,
                      }}
                    />
                    <Bar dataKey="waste" fill="#ef4444" name="Wasted Cost" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Top Optimization Opportunities */}
          <div id="opportunities" className="card" style={{
            background: styles.bgWhite,
            borderRadius: '16px',
            border: `1px solid ${styles.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            padding: '24px',
            marginBottom: '24px',
          }}>
            <h2 style={{
              fontSize: '16px',
              color: styles.textDark,
              marginBottom: '8px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <i className="fas fa-lightbulb"></i>
              Top Optimization Opportunities
            </h2>
            <p style={{ color: styles.textGray, marginBottom: '16px', fontSize: '14.4px' }}>
              Remove these unused includes to reduce build time
            </p>

            {result.top_opportunities && result.top_opportunities.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>File</th>
                    <th>Unused Header</th>
                    <th>Estimated Cost</th>
                    <th>Line</th>
                  </tr>
                </thead>
                <tbody>
                  {result.top_opportunities.slice(0, 15).map((opp, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td>
                        <code style={{ fontFamily: "'Fira Code', monospace", fontSize: '13.6px' }}>
                          {opp.file}
                        </code>
                      </td>
                      <td>
                        <code style={{ fontFamily: "'Fira Code', monospace", fontSize: '13.6px' }}>
                          {opp.header}
                        </code>
                      </td>
                      <td className={opp.cost >= 1200 ? 'cost-medium' : ''}>
                        {opp.cost.toLocaleString()}
                      </td>
                      <td>{opp.line}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ textAlign: 'center', padding: '32px', color: styles.textGray }}>
                No unused includes detected
              </div>
            )}
          </div>

          {/* PCH Recommendations */}
          {result.pch_recommendations && result.pch_recommendations.length > 0 && (
            <div id="pch" className="card" style={{
              background: styles.bgWhite,
              borderRadius: '16px',
              border: `1px solid ${styles.border}`,
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              padding: '24px',
              marginBottom: '24px',
            }}>
              <h2 style={{
                fontSize: '16px',
                color: styles.textDark,
                marginBottom: '8px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                <i className="fas fa-layer-group"></i>
                Precompiled Header (PCH) Recommendations
              </h2>
              <p style={{ color: styles.textGray, marginBottom: '16px', fontSize: '14.4px' }}>
                These headers are used frequently and expensive to compile - consider adding them to a precompiled header
              </p>

              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Header</th>
                    <th>Used By</th>
                    <th>Cost</th>
                    <th>PCH Score</th>
                    <th>Est. Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {result.pch_recommendations.slice(0, 10).map((rec, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td>
                        <code style={{ fontFamily: "'Fira Code', monospace", fontSize: '13.6px' }}>
                          {rec.header}
                        </code>
                      </td>
                      <td>{rec.used_by} files</td>
                      <td className="cost-medium">{rec.cost.toLocaleString()}</td>
                      <td className="cost-medium">{(rec.cost * rec.used_by).toLocaleString()}</td>
                      <td style={{ color: '#10b981', fontWeight: 600 }}>
                        {rec.savings.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Download Button */}
          <div style={{ display: 'flex', gap: '16px' }}>
            <a
              href={api.getReportUrl(jobStatus.job_id)}
              download
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                background: '#8b5cf6',
                color: 'white',
                fontWeight: '600',
                padding: '16px 24px',
                borderRadius: '8px',
                textDecoration: 'none',
                transition: 'background 0.2s',
              }}
            >
              <Download style={{ width: '20px', height: '20px' }} />
              <span>Download Full HTML Report</span>
            </a>
          </div>
        </div>
      </div>
    </>
  );
}

interface MetricCardProps {
  icon: string;
  label: string;
  value: string;
  valueColor?: string;
  styles: any;
}

function MetricCard({ icon, label, value, valueColor, styles }: MetricCardProps) {
  return (
    <div className="metric-card" style={{
      background: styles.bgWhite,
      padding: '16px',
      borderRadius: '12px',
      border: `1px solid ${styles.border}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        background: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
        borderRadius: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '12px',
        color: 'white',
        fontSize: '19.2px',
      }}>
        <i className={icon}></i>
      </div>
      <div style={{
        color: styles.textGray,
        fontSize: '12px',
        marginBottom: '4px',
        fontWeight: 500,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '24px',
        color: valueColor || styles.textDark,
        fontWeight: 700,
      }}>
        {value}
      </div>
    </div>
  );
}
