// WebSocket hook for real-time workflow updates

import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import type { WorkflowUpdate } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export const useWebSocket = (runId: string | null, onMessage: (update: WorkflowUpdate) => void) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    // Create WebSocket connection
    const wsUrl = `${WS_URL}/ws/${runId}`;
    const socket = new WebSocket(wsUrl);

    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket connected:', runId);
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const update: WorkflowUpdate = JSON.parse(event.data);
        console.log('WebSocket message received:', update);
        onMessage(update);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
      }
    }, 30000);

    // Cleanup
    return () => {
      clearInterval(heartbeat);
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [runId, onMessage]);

  return { isConnected };
};
