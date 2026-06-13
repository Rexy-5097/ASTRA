'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Search,
  BarChart2,
  Database,
  GitBranch,
  Globe,
  Cpu,
  FlaskConical,
  Clapperboard,
  ChevronLeft,
  ChevronRight,
  Satellite,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAstraStore } from '@/lib/store';
import { motion } from 'framer-motion';

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Mission Control', short: 'MC' },
  { href: '/search', icon: Search, label: 'Target Search', short: 'SRC' },
  { href: '/analysis', icon: BarChart2, label: 'Light Curve Analysis', short: 'LCA' },
  { href: '/dataset', icon: Database, label: 'Dataset Intelligence', short: 'DST' },
  { href: '/model', icon: Cpu, label: 'Model Operations', short: 'MLO' },
  { href: '/research', icon: FlaskConical, label: 'Research Findings', short: 'RES' },
  { href: '/mission-replay', icon: Clapperboard, label: 'Mission Replay', short: 'RPL' },
  { href: '/osint', icon: Globe, label: 'Space OSINT', short: 'OSI' },
  { href: '/visualization', icon: GitBranch, label: '3D Visualization', short: '3DV' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen } = useAstraStore();

  return (
    <aside
      className={cn(
        'flex flex-col h-screen border-r transition-all duration-200 shrink-0 astra-glass relative z-10',
        sidebarOpen ? 'w-52' : 'w-12',
      )}
      style={{ borderColor: 'rgba(255, 255, 255, 0.08)' }}
    >
      {/* Logo */}
      <div
        className={cn(
          'flex items-center border-b border-white/5 h-12 shrink-0 overflow-hidden',
          sidebarOpen ? 'px-3 gap-2' : 'px-0 justify-center',
        )}
      >
        <Satellite className="w-4 h-4 text-[#6EA8FE] shrink-0" />
        {sidebarOpen && (
          <div className="flex flex-col overflow-hidden">
            <span className="text-[#D7DEE7] font-semibold text-sm leading-none tracking-wide">
              ASTRA
            </span>
            <span className="text-[#8B97A7] text-[10px] leading-none mt-0.5">
              Stellar Intelligence
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map((item, idx) => {
          const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <motion.div
              key={item.href}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03, duration: 0.3 }}
            >
              <Link
                href={item.href}
                title={item.label}
                className={cn(
                  'flex items-center h-9 text-[0.8125rem] transition-colors relative',
                  sidebarOpen ? 'px-3 gap-2.5' : 'justify-center px-0',
                  isActive
                    ? 'text-[#6EA8FE] bg-[#1D3A6B]/30'
                    : 'text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-white/5',
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1 bottom-1 w-0.5 rounded-r bg-[#6EA8FE]" />
                )}
                <Icon className="w-4 h-4 shrink-0" />
                {sidebarOpen && (
                  <span className="truncate">{item.label}</span>
                )}
                {!sidebarOpen && (
                  <span className="sr-only">{item.label}</span>
                )}
              </Link>
            </motion.div>
          );
        })}
      </nav>

      {/* System status */}
      {sidebarOpen && (
        <div className="border-t border-white/5 px-3 py-2">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#56D364] animate-pulse" />
            <span className="text-[10px] text-[#8B97A7] uppercase tracking-widest font-semibold">Operational</span>
          </div>
          <p className="text-[10px] text-[#5A6878] mt-0.5 font-mono">
            Phase 8 · Verified
          </p>
        </div>
      )}

      {/* Toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="flex items-center justify-center h-9 border-t border-white/5 text-[#5A6878] hover:text-[#8B97A7] transition-colors"
        aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {sidebarOpen ? (
          <ChevronLeft className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
      </button>
    </aside>
  );
}
