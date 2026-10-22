// frontend/src/components/GenerateForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GenerateForm } from './GenerateForm';
import { useAuth } from '../hooks/useAuth';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../hooks/useAuth');
vi.mock('../api/client', () => ({
  api: {
    generate: vi.fn(),
    isAuthenticated: vi.fn(() => true),
    loadStoredTokens: vi.fn(),
  },
}));

const mockUseAuth = useAuth as unknown as ReturnType<typeof vi.fn>;
const mockApi = await import('../api/client');

function renderWithRouter() {
  return render(
    <BrowserRouter>
      <GenerateForm />
    </BrowserRouter>
  );
}

describe('GenerateForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { id: 1, email: 'operator@example.com', role: 'operator', is_active: true, full_name: null },
      isAuthenticated: true,
      isOperator: true,
      loading: false,
      error: null,
      login: vi.fn(),
      demoLogin: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn(() => true),
    });
  });

  it('renders form with all fields', () => {
    renderWithRouter();

    expect(screen.getByLabelText(/infrastructure description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/provider/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cloud target/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/use llm advisory/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate template/i })).toBeInTheDocument();
  });

  it('shows error for empty description', async () => {
    renderWithRouter();

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/description is required/i)).toBeInTheDocument();
    });
  });

  it('shows error for too short description', async () => {
    renderWithRouter();

    const textarea = screen.getByLabelText(/infrastructure description/i);
    fireEvent.change(textarea, { target: { value: 'short' } });

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
    });
  });

  it('calls api.generate on valid submit', async () => {
    const mockGenerate = vi.fn().mockResolvedValue({ id: 42, description: 'test', provider: 'terraform', target: 'aws', template: 'test', status: 'completed' });
    mockApi.api.generate = mockGenerate;

    renderWithRouter();

    const textarea = screen.getByLabelText(/infrastructure description/i);
    fireEvent.change(textarea, { target: { value: 'A web app with load balancer and database' } });

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith({
        description: 'A web app with load balancer and database',
        provider: 'terraform',
        target: 'aws',
        use_llm: true,
      });
    });
  });

  it('shows success banner on successful generation', async () => {
    const mockGenerate = vi.fn().mockResolvedValue({ id: 42, description: 'test', provider: 'terraform', target: 'aws', template: 'test', status: 'completed' });
    mockApi.api.generate = mockGenerate;

    renderWithRouter();

    const textarea = screen.getByLabelText(/infrastructure description/i);
    fireEvent.change(textarea, { target: { value: 'A web app with load balancer and database' } });

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/template generated successfully/i)).toBeInTheDocument();
      expect(screen.getByText(/generation id: 42/i)).toBeInTheDocument();
    });
  });

  it('shows error when generation fails', async () => {
    const mockGenerate = vi.fn().mockRejectedValue(new Error('API Error'));
    mockApi.api.generate = mockGenerate;

    renderWithRouter();

    const textarea = screen.getByLabelText(/infrastructure description/i);
    fireEvent.change(textarea, { target: { value: 'A web app with load balancer and database' } });

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/api error/i)).toBeInTheDocument();
    });
  });

  it('disables submit while loading', async () => {
    let resolveGenerate: (value: unknown) => void;
    const mockGenerate = vi.fn().mockImplementation(() => new Promise((resolve) => { resolveGenerate = resolve; }));
    mockApi.api.generate = mockGenerate;

    renderWithRouter();

    const textarea = screen.getByLabelText(/infrastructure description/i);
    fireEvent.change(textarea, { target: { value: 'A web app with load balancer and database' } });

    const submitBtn = screen.getByRole('button', { name: /generate template/i });
    fireEvent.click(submitBtn);

    expect(submitBtn).toBeDisabled();
    expect(screen.getByText(/generating\.\.\./i)).toBeInTheDocument();

    resolveGenerate!({ id: 42, description: 'test', provider: 'terraform', target: 'aws', template: 'test', status: 'completed' });
    await waitFor(() => {
      expect(submitBtn).not.toBeDisabled();
    });
  });

  it('shows example descriptions', () => {
    renderWithRouter();

    const details = screen.getByText(/example descriptions/i).closest('details');
    expect(details).toBeInTheDocument();

    fireEvent.click(screen.getByText(/example descriptions/i));

    expect(screen.getByText(/highly available 3-tier web app/i)).toBeInTheDocument();
    expect(screen.getByText(/serverless api with lambda/i)).toBeInTheDocument();
  });
});