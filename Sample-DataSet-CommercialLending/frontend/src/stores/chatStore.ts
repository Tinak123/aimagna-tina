// Zustand store for chat messages and workflow state

import { create } from 'zustand';
import type { ChatMessage, WorkflowRun, ETLStep } from '../types';

interface ChatStore {
  messages: ChatMessage[];
  currentRun: WorkflowRun | null;
  etlSteps: ETLStep[];
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setCurrentRun: (run: WorkflowRun | null) => void;
  updateCurrentRun: (updates: Partial<WorkflowRun>) => void;
  updateETLStep: (stepName: string, status: ETLStep['status'], message?: string) => void;
  resetETLSteps: () => void;
  clearMessages: () => void;
}

const INITIAL_ETL_STEPS: ETLStep[] = [
  { name: 'download', label: 'Download from GCS', status: 'pending' },
  { name: 'profiler', label: 'Data Profiling', status: 'pending' },
  { name: 'staging', label: 'Staging to BigQuery', status: 'pending' },
  { name: 'mapper', label: 'Schema Mapping', status: 'pending' },
  { name: 'hitl', label: 'Human Approval', status: 'pending' },
  { name: 'create_tables', label: 'Create Target Tables', status: 'pending' },
  { name: 'transform', label: 'Generate Transforms', status: 'pending' },
  { name: 'execute', label: 'Execute Transforms', status: 'pending' },
  { name: 'validator', label: 'Data Validation', status: 'pending' },
  { name: 'feedback', label: 'Capture Feedback', status: 'pending' },
  { name: 'cleanup', label: 'Cleanup', status: 'pending' },
];

export const useChatStore = create<ChatStore>((set) => ({
  messages: [
    {
      id: 'welcome',
      type: 'agent',
      content: '👋 Welcome to AIMagna ETL Agent!\n\n🚀 **Start Pipeline** - Select a folder from your GCS bucket to run the ETL workflow\n📤 **Upload CSV** - Upload individual CSV files\n💬 **Query Data** - Ask questions about your transformed data\n\nClick "Start Pipeline" to begin!',
      timestamp: new Date(),
    },
  ],
  currentRun: null,
  etlSteps: [...INITIAL_ETL_STEPS],

  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
        },
      ],
    })),

  setCurrentRun: (run) => set({ currentRun: run }),

  updateCurrentRun: (updates) =>
    set((state) => ({
      currentRun: state.currentRun
        ? { ...state.currentRun, ...updates }
        : null,
    })),

  updateETLStep: (stepName, status, message) =>
    set((state) => ({
      etlSteps: state.etlSteps.map((step) =>
        step.name === stepName
          ? { ...step, status, message }
          : step
      ),
    })),

  resetETLSteps: () =>
    set({
      etlSteps: [...INITIAL_ETL_STEPS],
    }),

  clearMessages: () =>
    set({
      messages: [
        {
          id: 'welcome',
          type: 'agent',
          content: 'Chat cleared. Ready for a new session!',
          timestamp: new Date(),
        },
      ],
      etlSteps: [...INITIAL_ETL_STEPS],
    }),
}));
