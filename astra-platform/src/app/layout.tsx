import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { GlobalClientContainer } from '@/components/layout/GlobalClientContainer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ASTRA — Stellar Intelligence Platform',
  description:
    'Automated Stellar Transient Recognition & Analysis. A scientific ML platform for TESS photometric variability classification.',
  keywords: ['astronomy', 'machine learning', 'stellar classification', 'TESS', 'photometry'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={inter.className} style={{ background: '#05070B' }}>
        <Providers>
          <GlobalClientContainer>{children}</GlobalClientContainer>
        </Providers>
      </body>
    </html>
  );
}
