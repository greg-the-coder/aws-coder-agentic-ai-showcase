import type { AgentResponse, ChatSession } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';
const BASE_URL = `${API_URL}/v1`;

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } catch (err) {
    console.warn(`API request failed: ${url}`, err);
    throw err;
  }
}

export async function submitQuery(sessionId: string, message: string): Promise<AgentResponse> {
  return request<AgentResponse>(`${BASE_URL}/query`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export async function getSession(sessionId: string): Promise<ChatSession> {
  return request<ChatSession>(`${BASE_URL}/sessions/${sessionId}`);
}

export async function getHealth(): Promise<{ status: string; version: string }> {
  return request(`${BASE_URL}/health`);
}

export async function generateReport(params: {
  operators: string[];
  sections: string[];
  format: 'pdf' | 'markdown';
}): Promise<{ report_url: string }> {
  return request(`${BASE_URL}/reports/generate`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function submitFeedback(
  traceId: string,
  feedback: 'up' | 'down'
): Promise<{ success: boolean }> {
  return request(`/api/mock/arize/traces/${traceId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  });
}
