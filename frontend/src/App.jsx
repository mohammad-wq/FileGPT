import { useState, useEffect, useRef } from "react";
import "./App.css";
import "./components/components.css";
import apiClient from "./api/client";
import toast from "./utils/toast";
import OrganizationApprovalModal from "./components/OrganizationApprovalModal";
import DashboardView from "./components/DashboardView";
import FilesView from "./components/FilesView";
import ChatView from "./components/ChatView";
import { parseDestinationPath, parseCategoryDescription } from "./utils/pathUtils";
import { 
  SidebarProvider, 
  Sidebar, 
  SidebarHeader, 
  SidebarContent, 
  SidebarFooter, 
  SidebarTrigger, 
  SidebarMenu, 
  SidebarMenuItem,
  useSidebar
} from "./components/ui/Sidebar";

import { LayoutDashboard, MessageSquare, Files, Settings, FolderClosed, File, FileIcon, FilesIcon, MessageCircleX, MessageCircleCodeIcon, MessageCircleIcon, MessageCircleDashed, LucideMessageCircle, MessageSquareXIcon, MessageSquareCheckIcon, MessageSquareIcon } from "lucide-react";

function AppContent() {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("offline");
  const [stats, setStats] = useState(null);
  const [organizationPlan, setOrganizationPlan] = useState(null);
  const [currentView, setCurrentView] = useState("dashboard");
  const messagesEndRef = useRef(null);
  const [showAllFilesIdx, setShowAllFilesIdx] = useState(null); 
  const abortControllerRef = useRef(null);
  const { open: sidebarOpen } = useSidebar();

  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkBackendStatus = async () => {
    try {
      const response = await apiClient.checkHealth();
      setBackendStatus("online");
      if (response.stats) setStats(response.stats);
    } catch (error) {
      setBackendStatus("offline");
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    
    const currentQuery = query.trim();
    setMessages((prev) => [...prev, { role: "user", content: currentQuery }]);
    setQuery("");
    setIsLoading(true);

    // Create new abort controller
    abortControllerRef.current = new AbortController();
    
    try {
      // Intent parsing and routing
      const lowerQuery = currentQuery.toLowerCase();
      if (lowerQuery.includes("organize") || lowerQuery.includes("move")) {
        const dest = parseDestinationPath(currentQuery);
        const cat = parseCategoryDescription(currentQuery);
        const resp = await apiClient.categorize(cat, null, 100, { signal: abortControllerRef.current.signal });
        const plan = {
          category: cat,
          destinationFolder: dest || `Desktop/${cat}`,
          files: (resp.results || []).map(r => ({ path: r.file_path, summary: r.summary })),
        };
        setMessages(prev => [...prev, { role: "assistant", content: "Review plan:", type: "organize-plan", plan }]);
      } else {
        let currentAnswer = "";
        setMessages(prev => [...prev, { role: "assistant", content: "" }]);
        
        await apiClient.askStream(currentQuery, 5, null, (chunk) => {
          if (chunk.type === "text") {
            if (chunk.replace) {
              currentAnswer = chunk.content;
            } else {
              currentAnswer += chunk.content;
            }
            setMessages(prev => {
              const newMessages = [...prev];
              const lastIdx = newMessages.length - 1;
              newMessages[lastIdx] = { ...newMessages[lastIdx], content: currentAnswer };
              return newMessages;
            });
          } else if (chunk.type === "metadata") {
            setMessages(prev => {
              const newMessages = [...prev];
              const lastIdx = newMessages.length - 1;
              const updatedMsg = { ...newMessages[lastIdx], ...chunk.content };
              
              // Compatibility: map sources to files if needed
              if (updatedMsg.sources && !updatedMsg.files) {
                updatedMsg.files = updatedMsg.sources;
              }
              
              newMessages[lastIdx] = updatedMsg;
              return newMessages;
            });
          }
        }, { signal: abortControllerRef.current.signal });
      }
    } catch (error) {
      if (error.name === 'AbortError' || error.message === 'canceled') {
        setMessages(prev => [...prev, { role: "assistant", content: "_Request cancelled._", isSystem: true }]);
      } else {
        const errorMsg = typeof error.message === 'string' ? error.message : JSON.stringify(error.message);
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${errorMsg}`, error: true }]);
      }
    } finally { 
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopPrompt = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <>
      <Sidebar>
        <SidebarHeader>
          <div className="sidebar-logo">
            <FolderClosed size={24} color="var(--accent-primary)" fill="rgba(59, 130, 246, 0.2)" />
            {sidebarOpen && <h1 style={{ fontSize: '1.125rem', fontWeight: 800 }}>FileGPT</h1>}
          </div>
        </SidebarHeader>
        
        <SidebarContent>
          <SidebarMenu>
            <SidebarMenuItem 
              active={currentView === "dashboard"} 
              onClick={() => setCurrentView("dashboard")}
              title="Dashboard"
            >
              <LayoutDashboard size={20} /> {sidebarOpen && <span>Dashboard</span>}
            </SidebarMenuItem>
            <SidebarMenuItem 
              active={currentView === "chat"} 
              onClick={() => setCurrentView("chat")}
              title="Chat"
            >
              <MessageSquareIcon size={20} /> {sidebarOpen && <span>AI Assistant</span>}
            </SidebarMenuItem>
            <SidebarMenuItem 
              active={currentView === "files"} 
              onClick={() => setCurrentView("files")}
              title="Files"
            >
              <Files size={20} /> {sidebarOpen && <span>Library</span>}
            </SidebarMenuItem>
            <SidebarMenuItem 
              active={currentView === "settings"} 
              onClick={() => setCurrentView("settings")}
              title="Settings"
            >
              <Settings size={20} /> {sidebarOpen && <span>Settings</span>}
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarContent>

        <SidebarFooter>
          <div className="status-badge-sidebar" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className={`status-dot ${backendStatus}`} style={{ width: 8, height: 8, borderRadius: '50%', background: backendStatus === 'online' ? 'var(--success)' : 'var(--error)', boxShadow: backendStatus === 'online' ? '0 0 8px var(--success)' : 'none' }}></span>
            {sidebarOpen && <span style={{ fontSize: '0.75rem', fontWeight: 600, opacity: 0.8, letterSpacing: '0.02em' }}>{backendStatus === 'online' ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}</span>}
          </div>
        </SidebarFooter>
      </Sidebar>

      <main className="main-content">
        <header className="top-bar">
          <SidebarTrigger />
          <div className="top-bar-title">
            {currentView === 'dashboard' && 'System Overview'}
            {currentView === 'chat' && 'AI Assistant & Semantic Search'}
            {currentView === 'files' && 'Indexed Library'}
            {currentView === 'settings' && 'Configuration'}
          </div>
          <div style={{ marginLeft: 'auto' }}>
            {stats && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.6 }}>
                <FileIcon size={14} color="var(--text-secondary)" />
                <span style={{ fontSize: '0.75rem' }}>{stats.db_stats?.total_files || 0} indexed</span>
              </div>
            )}
          </div>
        </header>

        <div style={{ flex: 1, overflow: 'hidden' }}>
          {currentView === "dashboard" && <DashboardView stats={stats} />}
          {currentView === "chat" && (
            <ChatView 
              messages={messages} 
              handleSendMessage={handleSendMessage} 
              handleStopPrompt={handleStopPrompt}
              query={query} 
              setQuery={setQuery} 
              isLoading={isLoading} 
              backendStatus={backendStatus}
              handleKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(e); } }}
              setOrganizationPlan={setOrganizationPlan}
              showAllFilesIdx={showAllFilesIdx}
              setShowAllFilesIdx={setShowAllFilesIdx}
              messagesEndRef={messagesEndRef}
            />
          )}
          {currentView === "files" && <FilesView />}
          {currentView === "settings" && <div style={{ padding: '2rem', opacity: 0.5 }}>Settings coming soon...</div>}
        </div>
      </main>

      {organizationPlan && (
        <OrganizationApprovalModal 
          plan={organizationPlan} 
          onAccept={() => { setOrganizationPlan(null); toast.success("Organized!"); }} 
          onReject={() => setOrganizationPlan(null)} 
        />
      )}
    </>
  );
}

export default function App() {
  return (
    <SidebarProvider>
      <AppContent />
    </SidebarProvider>
  );
}
