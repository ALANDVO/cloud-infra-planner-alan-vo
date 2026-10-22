// frontend/src/api/types.ts
// Typed API contracts matching backend routes

export type Provider = 'terraform' | 'cloudformation' | 'arm';
export type Target = 'aws' | 'gcp' | 'azure';
export type Role = 'viewer' | 'operator' | 'admin';
export type GenerationStatus = 'pending' | 'completed' | 'failed';
export type Severity = 'error' | 'warning' | 'info';

export interface GenerateRequest {
  description: string;
  provider: Provider;
  target: Target;
  use_llm: boolean;
}

export interface ValidationIssue {
  severity: Severity;
  message: string;
  line?: number;
  column?: number;
  rule?: string;
}

export interface ValidateRequest {
  template: string;
  provider?: string;
  target?: string;
}

export interface ValidateResponse {
  valid: boolean;
  issues: ValidationIssue[];
  summary: string;
}

export interface ResourceCost {
  resource_type: string;
  resource_name: string;
  monthly_cost_usd: number;
  region: string;
  details?: Record<string, unknown>;
}

export interface EstimateRequest {
  template?: string;
  components?: string[];
  target: string;
  regions: number;
}

export interface EstimateResponse {
  total_monthly_usd: number;
  resources: ResourceCost[];
  breakdown_by_service: Record<string, number>;
  breakdown_by_region: Record<string, number>;
  assumptions: string[];
}

export interface Generation {
  id: number;
  description: string;
  provider: Provider;
  target: Target;
  template?: string;
  validation_notes?: string;
  cost_estimate_usd?: number;
  components: string[];
  status: GenerationStatus;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface GenerationListResponse {
  items: Generation[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name?: string;
  role: Role;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface CsrfResponse {
  csrf_token: string;
}

export interface DemoSetupResponse extends TokenResponse {}