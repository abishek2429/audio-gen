import React, { useEffect, useState } from "react";
import { Sliders, Clock } from "lucide-react";
import { apiClient } from "../services/apiClient";

interface NavbarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onTabChange }) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const checkHealth = () => {
      apiClient
        .getHealth()
        .then(() => {
          if (mounted) setIsHealthy(true);
        })
        .catch(() => {
          if (mounted) setIsHealthy(false);
        });
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { id: "studio", label: "Studio", icon: Sliders },
    { id: "history", label: "History", icon: Clock },
  ];

  return (
    <header
      style={{
        background: "var(--bg-panel)",
        borderBottom: "1px solid var(--border-subtle)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <div
        className="container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "58px",
        }}
      >
        {/* Brand / Logo */}
        <div
          onClick={() => onTabChange("studio")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "var(--radius-sm)",
              background: "var(--accent-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ffffff",
            }}
          >
            <Sliders size={15} />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ fontWeight: 700, fontSize: "1rem", letterSpacing: "-0.02em", color: "#ffffff" }}>
              IncuBrix
            </span>
            <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--accent-text)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Studio
            </span>
          </div>
        </div>

        {/* Minimal Navigation */}
        <nav style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id || (activeTab === "generate" && item.id === "studio") || (activeTab === "progress" && item.id === "studio");
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: isActive ? "var(--bg-panel-subtle)" : "transparent",
                  color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                  border: `1px solid ${isActive ? "var(--border-default)" : "transparent"}`,
                  padding: "6px 14px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.85rem",
                  fontWeight: isActive ? 600 : 500,
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                <Icon size={14} color={isActive ? "var(--accent-primary)" : "currentColor"} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System Status Pill */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              background: "var(--bg-canvas)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-full)",
              fontSize: "0.74rem",
              fontWeight: 500,
            }}
            title={isHealthy ? "Backend connected" : "Backend unreachable"}
          >
            <div
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor:
                  isHealthy === null
                    ? "var(--text-muted)"
                    : isHealthy
                    ? "var(--success)"
                    : "var(--danger)",
              }}
              className={isHealthy ? "" : "animate-pulse"}
            />
            <span style={{ color: "var(--text-secondary)" }}>
              {isHealthy === null ? "Connecting" : isHealthy ? "Online" : "Offline"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
