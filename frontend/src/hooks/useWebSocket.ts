import { useState, useEffect, useCallback, useRef } from "react";

const WS_BASE = import.meta.env.VITE_WS_BASE ?? "ws://localhost:8050";

export type NotificationSeverity = "info" | "warning" | "error" | "success";

export type Notification = {
  id: string;
  type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  severity: NotificationSeverity;
  action_url?: string;
  timestamp: string;
  read: boolean;
};

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

type WebSocketMessage = {
  type: string;
  [key: string]: unknown;
};

type UseWebSocketOptions = {
  userId?: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onNotification?: (notification: Notification) => void;
};

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    userId = "anonymous",
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    onNotification,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Calculate unread count
  useEffect(() => {
    setUnreadCount(notifications.filter((n) => !n.read).length);
  }, [notifications]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus("connecting");
    
    try {
      const ws = new WebSocket(`${WS_BASE}/ws/notifications`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected, sending auth...");
        // Send auth message
        ws.send(JSON.stringify({
          type: "auth",
          user_id: userId,
          // In production, include JWT token here
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          
          switch (data.type) {
            case "connected":
              setStatus("connected");
              reconnectAttemptsRef.current = 0;
              console.log("WebSocket authenticated:", data);
              break;
            
            case "deadline_alert":
            case "deadline_overdue":
            case "workflow_change":
            case "ai_escalation":
            case "offer_received":
            case "offer_response":
            case "document_uploaded":
            case "case_update":
            case "system": {
              const notification = data as unknown as Notification;
              setNotifications((prev) => [notification, ...prev.slice(0, 99)]);
              onNotification?.(notification);
              break;
            }
            
            case "error":
              console.error("WebSocket error:", data.message);
              break;
            
            case "ping":
              ws.send(JSON.stringify({ type: "pong" }));
              break;
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setStatus("error");
      };

      ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        setStatus("disconnected");
        wsRef.current = null;

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Reconnecting in ${reconnectInterval}ms (attempt ${reconnectAttemptsRef.current})`);
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };
    } catch (e) {
      console.error("Failed to create WebSocket:", e);
      setStatus("error");
    }
  }, [userId, reconnectInterval, maxReconnectAttempts, onNotification]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setStatus("disconnected");
  }, []);

  // Subscribe to topics
  const subscribe = useCallback((topics: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "subscribe",
        topics,
      }));
    }
  }, []);

  // Unsubscribe from topics
  const unsubscribe = useCallback((topics: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "unsubscribe",
        topics,
      }));
    }
  }, []);

  // Mark notification as read
  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
    );
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "ack",
        notification_id: notificationId,
      }));
    }
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  // Clear notifications
  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    status,
    notifications,
    unreadCount,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  };
}
