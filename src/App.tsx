import { BrowserRouter as Router, Routes, Route, Link, useLocation } from "react-router-dom";
import { Home, HardDrive, Box, Activity } from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import Snapshots from "@/pages/Snapshots";
import Storage from "@/pages/Storage";
import Containers from "@/pages/Containers";

function Sidebar() {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Dashboard", icon: Home },
    { path: "/snapshots", label: "Snapshots", icon: Activity },
    { path: "/storage", label: "Storage", icon: HardDrive },
    { path: "/containers", label: "Containers", icon: Box },
  ];

  return (
    <div className="w-64 bg-white h-screen border-r border-slate-200 fixed left-0 top-0 shadow-xl">
      <div className="p-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-sky-500 to-violet-500 bg-clip-text text-transparent">
          NAS Manager
        </h1>
      </div>
      <nav className="px-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive
                  ? "bg-gradient-to-r from-sky-500 to-violet-500 text-white shadow-lg"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <Sidebar />
        <div className="ml-64">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/snapshots" element={<Snapshots />} />
            <Route path="/storage" element={<Storage />} />
            <Route path="/containers" element={<Containers />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}
