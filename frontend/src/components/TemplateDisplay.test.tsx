// frontend/src/components/TemplateDisplay.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateDisplay } from './TemplateDisplay';
import { vi, describe, it, expect } from 'vitest';

vi.mock('../api/client', () => ({
  api: {
    validate: vi.fn(),
    estimate: vi.fn(),
  },
}));

const mockGeneration = {
  id: 1,
  description: 'Test generation',
  provider: 'terraform' as const,
  target: 'aws' as const,
  template: 'resource "aws_instance" "web" {\n  ami = "ami-123"\n  instance_type = "t3.micro"\n}',
  validation_notes: 'Validation passed',
  cost_estimate_usd: 150,
  components: ['network', 'compute'],
  status: 'completed' as const,
  error_message: undefined,
  created_at: '2024-01-15T10:30:00Z',
  completed_at: '2024-01-15T10:31:00Z',
};

describe('TemplateDisplay', () => {
  it('renders template with syntax highlighting', () => {
    render(<TemplateDisplay generation={mockGeneration} />);

    expect(screen.getByText(/terraform/i)).toBeInTheDocument();
    expect(screen.getAllByText(/aws/i)).toHaveLength(2);
    expect(screen.getAllByText(/completed/i)).toHaveLength(2);
    expect(screen.getByText(/aws_instance/)).toBeInTheDocument();
  });

  it('shows validation notes when present', () => {
    render(<TemplateDisplay generation={mockGeneration} />);

    expect(screen.getByText(/validation notes/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/validation notes/i));
    expect(screen.getByText(/validation passed/i)).toBeInTheDocument();
  });

  it('shows components list', () => {
    render(<TemplateDisplay generation={mockGeneration} />);

    expect(screen.getByText(/detected components/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/detected components/i));
    expect(screen.getByText(/network/)).toBeInTheDocument();
    expect(screen.getByText(/compute/)).toBeInTheDocument();
  });

  it('shows cost estimate when available', () => {
    render(<TemplateDisplay generation={mockGeneration} />);

    expect(screen.getByText(/est. monthly cost: \$150/i)).toBeInTheDocument();
  });

  it('renders empty state when no template', () => {
    const genNoTemplate = { ...mockGeneration, template: undefined, error_message: 'Failed to generate' };
    render(<TemplateDisplay generation={genNoTemplate} />);

    expect(screen.getByText(/no template/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to generate/i)).toBeInTheDocument();
  });

  it('calls onValidate callback', () => {
    const onValidate = vi.fn();
    render(<TemplateDisplay generation={mockGeneration} onValidate={onValidate} />);

    fireEvent.click(screen.getByRole('button', { name: /validate/i }));
    expect(onValidate).toHaveBeenCalled();
  });

  it('calls onEstimate callback', () => {
    const onEstimate = vi.fn();
    render(<TemplateDisplay generation={mockGeneration} onEstimate={onEstimate} />);

    fireEvent.click(screen.getByRole('button', { name: /estimate cost/i }));
    expect(onEstimate).toHaveBeenCalled();
  });

  it('calls onExport callback', () => {
    const onExport = vi.fn();
    render(<TemplateDisplay generation={mockGeneration} onExport={onExport} />);

    fireEvent.click(screen.getByRole('button', { name: /export/i }));
    expect(onExport).toHaveBeenCalled();
  });
});