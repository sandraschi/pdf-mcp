import { useStore } from "@/lib/store";
import { motion } from "framer-motion";
import { BookOpen, ChevronLeft, ChevronRight, FileText, LayoutDashboard, MessageSquare, Terminal, Workflow, Wrench } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workbench", label: "Workbench", icon: FileText },
  { to: "/pipeline", label: "Pipeline", icon: Workflow },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/skills", label: "Skills", icon: BookOpen },
  { to: "/logs", label: "Logs", icon: Terminal },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const backendOk = useStore((s) => s.backendOk);

  return (
    <motion.aside
      className="flex flex-col bg-zinc-900 border-r border-zinc-800 h-full overflow-hidden"
      animate={{ width: collapsed ? 60 : 240 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 h-14 border-b border-zinc-800">
        {!collapsed && <span className="font-bold text-amber-500 text-lg tracking-wide">pdf-mcp</span>}
        <button
          type="button"
          onClick={onToggle}
          className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          data-testid="sidebar-toggle"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="flex-1 py-2 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive ? "bg-amber-500/10 text-amber-500" : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
              }`
            }
            data-testid={`nav-${item.label.toLowerCase()}`}
          >
            <item.icon size={20} />
            {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-zinc-800 flex items-center gap-2">
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            backendOk === null ? "bg-zinc-500" : backendOk ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
          data-testid="backend-dot"
        />
        {!collapsed && (
          <span className="text-xs text-zinc-500">{backendOk === null ? "Connecting..." : backendOk ? "Connected" : "Offline"}</span>
        )}
      </div>
    </motion.aside>
  );
}
