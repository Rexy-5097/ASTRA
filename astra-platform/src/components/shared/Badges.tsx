import { cn, CLASS_LABELS, CLASS_BADGE_STYLE } from '@/lib/utils';
import type { AstraClass, PeriodSource } from '@/lib/types';

export function ClassBadge({ cls }: { cls: AstraClass }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium',
        CLASS_BADGE_STYLE[cls],
      )}
    >
      {CLASS_LABELS[cls]}
    </span>
  );
}

export function PeriodSourceBadge({ source }: { source: PeriodSource }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border',
        source === 'catalog'
          ? 'bg-green-500/10 text-green-400 border-green-500/30'
          : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
      )}
    >
      {source === 'catalog' ? 'Catalog' : 'BLS'}
    </span>
  );
}

export function SplitBadge({ split }: { split: string }) {
  const styles: Record<string, string> = {
    train: 'bg-blue-500/10 text-blue-400 border border-blue-500/30',
    val: 'bg-purple-500/10 text-purple-400 border border-purple-500/30',
    test: 'bg-orange-500/10 text-orange-400 border border-orange-500/30',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium',
        styles[split] ?? 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/30',
      )}
    >
      {split}
    </span>
  );
}

export function StatusBadge({ status }: { status: 'PASS' | 'FAIL' | 'WARN' }) {
  const styles = {
    PASS: 'bg-green-500/10 text-green-400 border-green-500/30',
    FAIL: 'bg-red-500/10 text-red-400 border-red-500/30',
    WARN: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border',
        styles[status],
      )}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full',
          status === 'PASS' ? 'bg-green-400' : status === 'FAIL' ? 'bg-red-400' : 'bg-yellow-400',
        )}
      />
      {status}
    </span>
  );
}
