import { useEffect, useState } from "react";
import apiClient from "../api/client";
import { Search, RefreshCw, FileText, CheckCircle2, Clock } from "lucide-react";
import { Skeleton } from "./ui/Skeleton";

export default function FilesView() {
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getIndexedFiles();
      setFiles(data.files || []);
    } catch (error) {
      console.error("Failed to fetch files", error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredFiles = files.filter(f => {
    const filePath = f.path || f.file_path || "";
    const summary = f.summary || "";
    return filePath.toLowerCase().includes(filter.toLowerCase()) ||
           summary.toLowerCase().includes(filter.toLowerCase());
  });

  return (
    <div className="files-view" style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column', animation: 'fadeIn 0.5s ease-out' }}>
      <div className="files-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '0.25rem' }}>Indexed Library</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Management and status of all indexed documents</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="Filter library..." 
              className="search-input"
              style={{ padding: '0.75rem 1rem 0.75rem 2.75rem', width: '320px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '12px', color: 'var(--text-primary)' }}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary" onClick={fetchFiles} disabled={isLoading} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: '12px', cursor: 'pointer', color: 'var(--text-primary)', fontWeight: 600 }}>
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
            Sync
          </button>
        </div>
      </div>

      <div className="files-table-container" style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-secondary)', borderRadius: '16px', border: '1px solid var(--border-color)', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
              <th style={{ padding: '1.25rem 1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Filename</th>
              <th style={{ padding: '1.25rem 1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Full Path</th>
              <th style={{ padding: '1.25rem 1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
              <th style={{ padding: '1.25rem 1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Indexed At</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1.25rem 1.5rem' }}><Skeleton style={{ height: '20px', width: '120px' }} /></td>
                  <td style={{ padding: '1.25rem 1.5rem' }}><Skeleton style={{ height: '20px', width: '200px' }} /></td>
                  <td style={{ padding: '1.25rem 1.5rem' }}><Skeleton style={{ height: '24px', width: '80px', borderRadius: '20px' }} /></td>
                  <td style={{ padding: '1.25rem 1.5rem' }}><Skeleton style={{ height: '20px', width: '100px' }} /></td>
                </tr>
              ))
            ) : filteredFiles.length > 0 ? (
              filteredFiles.map((file, idx) => {
                const fullPath = file.path || file.file_path || "";
                const filename = fullPath.split('/').pop();
                
                return (
                  <tr 
                    key={idx} 
                    onClick={() => apiClient.openExplorer(fullPath).catch(console.error)}
                    style={{ 
                      borderBottom: '1px solid var(--border-color)', 
                      transition: 'all 0.2s',
                      cursor: 'pointer'
                    }} 
                    className="clickable-table-row"
                  >
                    <td style={{ padding: '1.25rem 1.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <FileText size={18} color="var(--accent-primary)" />
                        <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>{filename}</span>
                      </div>
                    </td>
                    <td style={{ padding: '1.25rem 1.5rem' }}>
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', opacity: 0.8, fontFamily: 'monospace' }}>{fullPath}</span>
                    </td>
                    <td style={{ padding: '1.25rem 1.5rem' }}>
                      <span style={{ 
                        padding: '0.375rem 0.75rem', 
                        borderRadius: '20px', 
                        fontSize: '0.75rem', 
                        fontWeight: 600,
                        background: file.processing_status === 'completed' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                        color: file.processing_status === 'completed' ? 'var(--success)' : 'var(--warning)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.375rem'
                      }}>
                        {file.processing_status === 'completed' ? <CheckCircle2 size={12} /> : <Clock size={12} />}
                        {file.processing_status || 'indexed'}
                      </span>
                    </td>
                    <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {file.indexed_at ? new Date(file.indexed_at).toLocaleDateString() : 'Recent'}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="4" style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No indexed files found matching your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
