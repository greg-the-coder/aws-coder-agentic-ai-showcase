import type { WorkatoRecipeStatus, WorkatoConnection } from '../types';

// ─── Mock Data ───────────────────────────────────────────────────────────────

const mockRecipes: WorkatoRecipeStatus[] = [
  {
    recipe_id: 'rec-001',
    name: "Moody's Daily Credit Sync",
    status: 'active',
    last_run: '2025-01-15T06:00:00Z',
    next_run: '2025-01-15T12:00:00Z',
    success_count: 1842,
    error_count: 3,
    avg_duration_ms: 4520,
  },
  {
    recipe_id: 'rec-002',
    name: 'Alert Distribution Pipeline',
    status: 'active',
    last_run: '2025-01-15T08:32:00Z',
    next_run: '2025-01-15T08:33:00Z',
    success_count: 956,
    error_count: 0,
    avg_duration_ms: 1230,
  },
  {
    recipe_id: 'rec-003',
    name: 'Holdings Reconciliation (Nightly)',
    status: 'active',
    last_run: '2025-01-15T02:00:00Z',
    next_run: '2025-01-16T02:00:00Z',
    success_count: 365,
    error_count: 2,
    avg_duration_ms: 18700,
  },
];

const mockConnections: WorkatoConnection[] = [
  { id: 'conn-001', name: "Moody's CreditView API", provider: 'HTTP (OAuth2)', status: 'connected', last_tested: '2025-01-15T08:00:00Z' },
  { id: 'conn-002', name: 'Amazon S3 — Data Lake', provider: 'AWS S3', status: 'connected', last_tested: '2025-01-15T06:01:00Z' },
  { id: 'conn-003', name: 'Amazon SNS — Alerts', provider: 'AWS SNS', status: 'connected', last_tested: '2025-01-15T08:32:00Z' },
  { id: 'conn-004', name: 'Internal OMS (REST)', provider: 'HTTP', status: 'disconnected', last_tested: '2025-01-14T22:00:00Z' },
];

const mockRunHistory = [
  { id: 'run-010', recipe: "Moody's Daily Credit Sync", status: 'success' as const, started: '2025-01-15T06:00:00Z', duration_ms: 4320, records: 48 },
  { id: 'run-009', recipe: 'Alert Distribution Pipeline', status: 'success' as const, started: '2025-01-15T05:45:00Z', duration_ms: 890, records: 3 },
  { id: 'run-008', recipe: 'Holdings Reconciliation (Nightly)', status: 'success' as const, started: '2025-01-15T02:00:00Z', duration_ms: 19200, records: 1245 },
  { id: 'run-007', recipe: "Moody's Daily Credit Sync", status: 'success' as const, started: '2025-01-15T00:00:00Z', duration_ms: 4780, records: 48 },
  { id: 'run-006', recipe: 'Alert Distribution Pipeline', status: 'error' as const, started: '2025-01-14T23:12:00Z', duration_ms: 340, records: 0 },
  { id: 'run-005', recipe: "Moody's Daily Credit Sync", status: 'success' as const, started: '2025-01-14T18:00:00Z', duration_ms: 4150, records: 48 },
];

// ─── Mock Client ─────────────────────────────────────────────────────────────

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function getRecipes(): Promise<WorkatoRecipeStatus[]> {
  await delay(300);
  return [...mockRecipes];
}

export async function triggerRecipe(recipeId: string): Promise<{ success: boolean; run_id: string }> {
  await delay(800);
  return { success: true, run_id: `run-${Date.now()}` };
}

export async function getRecipeStatus(recipeId: string): Promise<WorkatoRecipeStatus | undefined> {
  await delay(200);
  return mockRecipes.find((r) => r.recipe_id === recipeId);
}

export async function getConnections(): Promise<WorkatoConnection[]> {
  await delay(250);
  return [...mockConnections];
}

export async function getRunHistory() {
  await delay(300);
  return [...mockRunHistory];
}

export async function simulateWebhook(): Promise<{ event: string; processed: boolean }> {
  await delay(600);
  return { event: 'outlook_change', processed: true };
}
