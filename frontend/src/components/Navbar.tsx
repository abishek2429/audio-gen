import React, { useEffect, useState } from "react";
import { Music, Activity, Layers, FileJson, Clock, PlusCircle } from "lucide-react";
import { apiClient } from "../services/apiClient";

interface NavbarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onTabChange }) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const checkHealth = () => {
      apiClient
        .getHealth()
        .then(() => setIsHealthy(true))
        .catch(() => setIsHealthy(false));
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Activity },
    { id: "generate", label: "Create Music", icon: PlusCircle },
    { id: "studio", label: "Audio Studio", icon: Layers },
    { id: "manifest", label: "Manifest Viewer", icon: FileJson },
    { id: "history", label: "Job History", icon: Clock },
  ];

  return (
    <header
      style={{
        background: "rgba(10, 14, 23, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--border-subtle)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <div
        className="container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "68px",
          gap: "16px",
        }}
      >
        {/* Brand / Logo */}
        <div
          onClick={() => onTabChange("dashboard")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "10px",
              background: "var(--accent-gradient)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 16px rgba(139, 92, 246, 0.4)",
            }}
          >
            <Music size={20} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "1.1rem", letterSpacing: "-0.02em", color: "#fff" }}>
              Incu<span style={{ color: "var(--accent-secondary)" }}>Brix</span>
            </div>
            <div style={{ fontSize: "0.68rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              AI Music Engine
            </div>
          </div>
        </div>

        {/* Nav Tabs */}
        <nav style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  background: isActive ? "rgba(139, 92, 246, 0.15)" : "transparent",
                  color: isActive ? "#fff" : "var(--text-muted)",
                  border: `1px solid ${isActive ? "rgba(139, 92, 246, 0.35)" : "transparent"}`,
                  padding: "8px 14px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.85rem",
                  fontWeight: isActive ? 600 : 500,
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <Icon size={16} color={isActive ? "var(--accent-secondary)" : "currentColor"} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Live Backend Status Indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 11px",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-full)",
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor:
                  isHealthy === null
                    ? "var(--text-dim)"
                    : isHealthy
                    ? "var(--success)"
                    : "var(--danger)",
                boxShadow: isHealthy ? "0 0 8px var(--success)" : "none",
              }}
            />
            <span style={{ color: "var(--text-muted)" }}>
              {isHealthy === null ? "Connecting..." : isHealthy ? "API Online" : "API Offline"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
