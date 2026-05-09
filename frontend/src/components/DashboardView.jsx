import { useEffect, useState } from "react";
import apiClient from "../api/client";
import { Files, LoaderIcon, Database } from "lucide-react";
import { Skeleton } from "./ui/Skeleton";

export default function DashboardView({ stats }) {
  return (
    <div className="dashboard-view" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem', animation: 'fadeIn 0.5s ease-out' }}>
      <div className="dashboard-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div className="stat-label">Total Indexed Files</div>
            <Files size={20} color="var(--accent-primary)" opacity={0.6} />
          </div>
          <div className="stat-value">
            {stats?.db_stats ? (stats.db_stats.total_files || 0) : <Skeleton style={{ height: '36px', width: '80px', marginTop: '8px' }} />}
          </div>
          <div className="stat-meta">Across all watched folders</div>
        </div>
        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div className="stat-label">Pending Processing</div>
            <LoaderIcon size={20} color="var(--warning)" className="animate-spin" opacity={0.6} />
          </div>
          <div className="stat-value" style={{ color: 'var(--warning)' }}>
            {stats?.db_stats ? (
              (stats.db_stats.pending_embedding || 0) + (stats.db_stats.pending_summary || 0)
            ) : (
              <Skeleton style={{ height: '36px', width: '80px', marginTop: '8px' }} />
            )}
          </div>
          <div className="stat-meta">Embedding & Summarization</div>
        </div>
        <div className="stat-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div className="stat-label">Database Size</div>
            <Database size={20} color="var(--accent-primary)" opacity={0.6} />
          </div>
          <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>
            {stats?.db_stats ? (
              `${stats.db_stats.db_size_mb?.toFixed(2) || 0} MB`
            ) : (
              <Skeleton style={{ height: '36px', width: '120px', marginTop: '8px' }} />
            )}
          </div>
          <div className="stat-meta">SQLite + ChromaDB</div>
        </div>
      </div>

      <div className="dashboard-charts" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
        <div className="chart-container-premium">
          <h3 style={{ marginBottom: '1.5rem', fontSize: '1rem', opacity: 0.8 }}>Indexing Activity</h3>
          <div className="mock-chart" style={{ position: 'relative', height: '160px', width: '100%' }}>
            <svg viewBox="0 0 400 120" preserveAspectRatio="none" style={{ width: '100%', height: '100%', display: 'block' }}>
              <defs>
                <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-primary)" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="var(--accent-primary)" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path 
                d="M0,100 C50,20 150,20 200,60 C250,100 350,100 400,40 L400,120 L0,120 Z" 
                fill="url(#area-gradient)"
              />
              <path 
                d="M0,100 C50,20 150,20 200,60 C250,100 350,100 400,40" 
                fill="none" 
                stroke="var(--accent-primary)" 
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="chart-path"
              />
            </svg>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
            </div>
          </div>
        </div>

        <div className="chart-container-premium">
          <h3 style={{ marginBottom: '1.5rem', fontSize: '1rem', opacity: 0.8 }}>System Health</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="health-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                <span>Ollama (AI)</span>
                <span style={{ color: 'var(--success)' }}>98%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--bg-tertiary)', borderRadius: '3px' }}>
                <div style={{ width: '98%', height: '100%', background: 'var(--success)', borderRadius: '3px' }}></div>
              </div>
            </div>
            <div className="health-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                <span>Rust Monitor</span>
                <span style={{ color: 'var(--accent-primary)' }}>Active</span>
              </div>
              <div style={{ height: '6px', background: 'var(--bg-tertiary)', borderRadius: '3px' }}>
                <div style={{ width: '100%', height: '100%', background: 'var(--accent-primary)', borderRadius: '3px' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
