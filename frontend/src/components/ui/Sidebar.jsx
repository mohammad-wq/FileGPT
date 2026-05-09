import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { PanelLeft } from "lucide-react";

const SidebarContext = createContext(null);

export function SidebarProvider({ children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  const toggleSidebar = useCallback(() => setOpen(prev => !prev), []);

  // Keyboard shortcut (Cmd+B / Ctrl+B)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  return (
    <SidebarContext.Provider value={{ open, setOpen, toggleSidebar }}>
      <div className={`sidebar-wrapper ${open ? "sidebar-open" : "sidebar-collapsed"}`}>
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) throw new Error("useSidebar must be used within a SidebarProvider");
  return context;
}

export function Sidebar({ children }) {
  const { open } = useSidebar();
  return (
    <aside className={`sidebar-component ${open ? "expanded" : "collapsed"}`}>
      {children}
    </aside>
  );
}

export function SidebarHeader({ children }) {
  return <div className="sidebar-header-ui">{children}</div>;
}

export function SidebarContent({ children }) {
  return <div className="sidebar-content-ui">{children}</div>;
}

export function SidebarFooter({ children }) {
  return <div className="sidebar-footer-ui">{children}</div>;
}

export function SidebarTrigger() {
  const { toggleSidebar } = useSidebar();
  return (
    <button className="sidebar-trigger-ui" onClick={toggleSidebar} title="Toggle Sidebar (Ctrl+B)">
      <PanelLeft size={18} />
    </button>
  );
}

export function SidebarMenu({ children }) {
  return <nav className="sidebar-menu-ui">{children}</nav>;
}

export function SidebarMenuItem({ children, active, onClick, title }) {
  const { open } = useSidebar();
  return (
    <div 
      className={`sidebar-menu-item-ui ${active ? "active" : ""}`} 
      onClick={onClick}
      title={!open ? title : ""}
    >
      {children}
    </div>
  );
}
