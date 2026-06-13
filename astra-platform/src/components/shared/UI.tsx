import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  mono?: boolean;
  accent?: boolean;
  accentColor?: string;
  className?: string;
}

export function MetricCard({
  label,
  value,
  sub,
  mono = false,
  accent = false,
  accentColor,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'p-4 rounded border astra-glass astra-glass-hover',
        className,
      )}
    >
      <p className="text-[0.6875rem] uppercase tracking-[0.08em] text-[#8B97A7] mb-1.5 leading-none">
        {label}
      </p>
      <p
        className={cn(
          'leading-none font-semibold',
          mono ? 'font-mono text-xl' : 'text-xl',
          accentColor ? accentColor : (accent ? 'text-[#6EA8FE]' : 'text-[#D7DEE7]'),
        )}
      >
        {value}
      </p>
      {sub && (
        <p className="text-[0.6875rem] text-[#5A6878] mt-1.5 font-mono leading-none">{sub}</p>
      )}
    </div>
  );
}

interface SectionHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function SectionHeader({ title, description, children }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-[0.9375rem] font-semibold text-[#D7DEE7]">{title}</h2>
        {description && (
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

interface PanelProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  headerRight?: React.ReactNode;
}

export function Panel({ title, subtitle, children, className, headerRight }: PanelProps) {
  return (
    <div
      className={cn('rounded border astra-glass', className)}
    >
      {title && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <div>
            <p className="text-[0.8125rem] font-medium text-[#D7DEE7]">{title}</p>
            {subtitle && (
              <p className="text-[0.6875rem] text-[#8B97A7] mt-0.5">{subtitle}</p>
            )}
          </div>
          {headerRight}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function DataRow({ label, value, mono = false }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between py-2 border-b border-[#1A2430] last:border-0">
      <span className="text-[0.75rem] text-[#8B97A7]">{label}</span>
      <span
        className={cn(
          'text-[0.8125rem] text-[#D7DEE7]',
          mono && 'font-mono',
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function ConfidenceBar({
  value,
  max = 1,
  color,
  label,
}: {
  value: number;
  max?: number;
  color?: string;
  label?: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  const barColor = color ?? (pct >= 85 ? '#56D364' : pct >= 70 ? '#6EA8FE' : pct >= 55 ? '#D29922' : '#F85149');
  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between mb-1">
          <span className="text-[0.6875rem] text-[#8B97A7]">{label}</span>
          <span className="text-[0.6875rem] font-mono text-[#D7DEE7]">
            {(value * 100).toFixed(1)}%
          </span>
        </div>
      )}
      <div className="h-1.5 bg-[#1A2430] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
    </div>
  );
}

export function HashBadge({ hash, label }: { hash: string; label?: string }) {
  return (
    <div className="inline-flex flex-col gap-0.5">
      {label && <span className="text-[10px] text-[#8B97A7] uppercase tracking-wider">{label}</span>}
      <span
        className="font-mono text-[0.75rem] text-[#6EA8FE] px-2 py-0.5 rounded border border-[#1D3A6B] bg-[#1D3A6B]/20"
        title={hash}
      >
        {hash.slice(0, 8)}…{hash.slice(-6)}
      </span>
    </div>
  );
}

export function EmptyState({ message, sub }: { message: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-[#8B97A7] text-sm">{message}</p>
      {sub && <p className="text-[#5A6878] text-xs mt-1">{sub}</p>}
    </div>
  );
}

export function LoadingRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <tr key={i}>
          {Array.from({ length: 6 }, (__, j) => (
            <td key={j} className="px-4 py-2.5">
              <div className="h-3.5 rounded bg-[#1A2430] animate-pulse" style={{ width: `${60 + ((i * 7 + j * 13) % 40)}%` }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
