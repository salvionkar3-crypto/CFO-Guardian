"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Shield,
  Activity,
  Database,
  CreditCard,
  RefreshCw,
  LogIn,
  LogOut,
  Building,
  Sparkles,
  Bell,
  Check,
  CheckCheck,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { SystemHealth, TokenResponse, NotificationItem } from "@/types";
import { api } from "@/lib/api";

interface HeaderProps {
  health: SystemHealth | null;
  loading: boolean;
  onRefresh: () => void;
  authData: TokenResponse | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  onOpenChat?: () => void;
  onSelectDecision?: (decisionId: number) => void;
  onNavigateToSecurity?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  loading,
  onRefresh,
  authData,
  onOpenAuth,
  onLogout,
  onOpenChat,
  onSelectDecision,
  onNavigateToSecurity,
}) => {
  const isHealthy = health?.status === "healthy";
  const dbConnected = health?.database?.status === "connected";
  const paypalReady = health?.paypal?.status === "ready";

  // Notifications State
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isLoadingNotifs, setIsLoadingNotifs] = useState(false);
  const notifDropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotificationData = useCallback(async () => {
    if (!authData) return;
    try {
      const [countRes, listRes] = await Promise.all([
        api.getUnreadNotificationCount(),
        api.getNotifications({ limit: 15 }),
      ]);
      setUnreadCount(countRes.unread_count);
      setNotifications(listRes);
    } catch {
      // Background telemetry fails silently if unauthorized
    }
  }, [authData]);

  useEffect(() => {
    fetchNotificationData();
    const interval = setInterval(fetchNotificationData, 15000); // 15-second polling for live alerts
    return () => clearInterval(interval);
  }, [fetchNotificationData]);

  // Click outside listener for dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifDropdownRef.current && !notifDropdownRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkAsRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark notification read", err);
    }
  };

  const handleMarkAllRead = async () => {
    setIsLoadingNotifs(true);
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all notifications read", err);
    } finally {
      setIsLoadingNotifs(false);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-950/80 text-rose-300 border-rose-800";
      case "HIGH":
        return "bg-amber-950/80 text-amber-300 border-amber-800";
      case "MEDIUM":
        return "bg-blue-950/80 text-blue-300 border-blue-800";
      case "LOW":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">GUARDIAN CFO</h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                v{health?.version || "1.0.0"}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">The AI CFO That Thinks Before It Pays</p>
          </div>
        </div>

        {/* Center/Right: Telemetry & Auth Profile */}
        <div className="flex items-center flex-wrap gap-2 text-xs">
          {/* Backend Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Activity className={`h-3.5 w-3.5 ${isHealthy ? "text-emerald-400 animate-pulse" : "text-amber-400"}`} />
            <span>FastAPI:</span>
            <span className={`font-semibold ${isHealthy ? "text-emerald-400" : "text-amber-400"}`}>
              {isHealthy ? "Online" : "Connecting..."}
            </span>
          </div>

          {/* Database */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Database className={`h-3.5 w-3.5 ${dbConnected ? "text-emerald-400" : "text-rose-400"}`} />
            <span>DB:</span>
            <span className={`font-semibold ${dbConnected ? "text-emerald-400" : "text-rose-400"}`}>
              {health?.database?.type?.toUpperCase() || "Checking"}
            </span>
          </div>

          {/* PayPal Sandbox Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <CreditCard className={`h-3.5 w-3.5 ${paypalReady ? "text-cyan-400" : "text-amber-400"}`} />
            <span>PayPal Sandbox:</span>
            <span className={`font-semibold ${paypalReady ? "text-cyan-400" : "text-amber-400"}`}>
              {paypalReady ? "Ready" : "Config Needed"}
            </span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition disabled:opacity-50"
            title="Refresh analytics and telemetry"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          {/* AI CFO Chat Trigger */}
          {onOpenChat && (
            <button
              onClick={onOpenChat}
              className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600/90 to-blue-600/90 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 transition shadow-sm"
              title="Open AI CFO consultation drawer"
            >
              <Sparkles className="h-3.5 w-3.5 text-cyan-200 animate-pulse" />
              <span>AI CFO Chat</span>
            </button>
          )}

          {/* Notification Bell Dropdown */}
          {authData && (
            <div className="relative" ref={notifDropdownRef}>
              <button
                onClick={() => setIsNotifOpen(!isNotifOpen)}
                className="relative p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition border border-slate-800"
                title="Notifications & Security Alerts"
              >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-4 min-w-[16px] px-1 bg-rose-600 text-white font-mono font-bold text-[9px] rounded-full flex items-center justify-center shadow-lg animate-pulse">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {isNotifOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in-50 slide-in-from-top-2">
                  <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/60">
                    <div className="flex items-center gap-2">
                      <Bell className="h-4 w-4 text-cyan-400" />
                      <span className="text-xs font-bold text-white">Notifications & Alerts</span>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800">
                          {unreadCount} new
                        </span>
                      )}
                    </div>

                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        disabled={isLoadingNotifs}
                        className="text-[11px] font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition"
                      >
                        <CheckCheck className="h-3 w-3" />
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                    {notifications.length === 0 ? (
                      <div className="py-8 text-center text-xs text-slate-500">
                        No notifications recorded yet.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`p-3 transition text-xs flex flex-col gap-1.5 ${
                            n.is_read ? "bg-slate-950/60 opacity-80" : "bg-slate-900/40"
                          } hover:bg-slate-900/90`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span
                              className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${getSeverityBadge(
                                n.severity
                              )}`}
                            >
                              {n.severity}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500">
                              {new Date(n.created_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>

                          <div className="font-semibold text-white leading-tight">
                            {n.title}
                          </div>

                          <p className="text-[11px] text-slate-400 leading-snug">
                            {n.message}
                          </p>

                          <div className="flex items-center justify-between pt-1 border-t border-slate-900">
                            {n.payment_draft_id ? (
                              <button
                                onClick={() => {
                                  setIsNotifOpen(false);
                                  if (onSelectDecision && n.payment_draft_id) {
                                    onSelectDecision(n.payment_draft_id);
                                  }
                                }}
                                className="text-[11px] text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
                              >
                                View Draft #{n.payment_draft_id}
                                <ArrowRight className="h-2.5 w-2.5" />
                              </button>
                            ) : (
                              <span />
                            )}

                            {!n.is_read && (
                              <button
                                onClick={() => handleMarkAsRead(n.id)}
                                className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-0.5"
                              >
                                <Check className="h-2.5 w-2.5" />
                                Mark read
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {onNavigateToSecurity && (
                    <div className="p-2.5 bg-slate-900/80 border-t border-slate-800 text-center">
                      <button
                        onClick={() => {
                          setIsNotifOpen(false);
                          onNavigateToSecurity();
                        }}
                        className="text-[11px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center justify-center gap-1.5 w-full"
                      >
                        Open Security Activity & Audit Center
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* User Auth Section */}
          <div className="border-l border-slate-800 pl-2 ml-1 flex items-center gap-2">
            {authData ? (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 bg-slate-900 border border-cyan-800/80 px-2.5 py-1 rounded-lg">
                  <Building className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="font-semibold text-white truncate max-w-[140px]">
                    {authData.business.name}
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.2 rounded border border-cyan-800">
                    {authData.user.role}
                  </span>
                  {(authData.user.email.includes("demo") || authData.business.name.includes("Acme")) && (
                    <span className="text-[9px] font-mono font-bold text-amber-300 bg-amber-950/90 px-1.5 py-0.5 rounded border border-amber-600/70 shadow-sm animate-pulse">
                      DEMO MODE
                    </span>
                  )}
                </div>

                <button
                  onClick={onLogout}
                  className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-rose-950/60 hover:border-rose-800 border border-slate-700 text-slate-300 hover:text-rose-300 text-xs flex items-center gap-1 transition"
                  title="Sign Out"
                >
                  <LogOut className="h-3 w-3" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuth}
                className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 transition shadow"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Sign In / Demo</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
