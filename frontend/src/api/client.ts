// frontend/src/api/client.ts
// Typed API client with auth handling
/// <reference types="vite/client" />
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  GenerateRequest,
  Generation,
  GenerationListResponse,
  ValidateRequest,
  ValidateResponse,
  EstimateRequest,
  EstimateResponse,
  LoginRequest,
  TokenResponse,
  UserResponse,
  CsrfResponse,
  DemoSetupResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private csrfToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true, // for HttpOnly cookie
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        if (this.csrfToken && ['post', 'put', 'delete', 'patch'].includes(config.method || '')) {
          config.headers['X-CSRF-Token'] = this.csrfToken;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearAuth();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }

  setCsrfToken(token: string | null) {
    this.csrfToken = token;
    if (token) {
      localStorage.setItem('csrf_token', token);
    } else {
      localStorage.removeItem('csrf_token');
    }
  }

  loadStoredTokens() {
    this.accessToken = localStorage.getItem('access_token');
    this.csrfToken = localStorage.getItem('csrf_token');
  }

  clearAuth() {
    this.accessToken = null;
    this.csrfToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('csrf_token');
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/login', credentials);
    this.setAccessToken(response.data.access_token);
    await this.fetchCsrfToken();
    return response.data;
  }

  async demoSetup(): Promise<DemoSetupResponse> {
    const response = await this.client.post<DemoSetupResponse>('/auth/demo-setup');
    this.setAccessToken(response.data.access_token);
    await this.fetchCsrfToken();
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    this.clearAuth();
  }

  async getMe(): Promise<UserResponse> {
    const response = await this.client.get<UserResponse>('/auth/me');
    return response.data;
  }

  async fetchCsrfToken(): Promise<string> {
    const response = await this.client.get<CsrfResponse>('/auth/csrf');
    this.setCsrfToken(response.data.csrf_token);
    return response.data.csrf_token;
  }

  // Generate endpoints
  async generate(payload: GenerateRequest): Promise<Generation> {
    const response = await this.client.post<Generation>('/generate', payload);
    return response.data;
  }

  async listGenerations(params?: { page?: number; page_size?: number; status?: string }): Promise<GenerationListResponse> {
    const response = await this.client.get<GenerationListResponse>('/generate', { params });
    return response.data;
  }

  async getGeneration(id: number): Promise<Generation> {
    const response = await this.client.get<Generation>(`/generate/${id}`);
    return response.data;
  }

  async deleteGeneration(id: number): Promise<void> {
    await this.client.delete(`/generate/${id}`);
  }

  // Validate endpoint
  async validate(payload: ValidateRequest): Promise<ValidateResponse> {
    const response = await this.client.post<ValidateResponse>('/validate', payload);
    return response.data;
  }

  // Estimate endpoint
  async estimate(payload: EstimateRequest): Promise<EstimateResponse> {
    const response = await this.client.post<EstimateResponse>('/estimate', payload);
    return response.data;
  }

  // Health
  async health(): Promise<{ status: string; version: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const api = new ApiClient();