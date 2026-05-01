import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata = {
  title: 'TenzorX — Kirana Credit Intelligence',
  description: 'Remote cash flow underwriting for kirana stores using Vision & Geo Intelligence. A credit bureau for the physical world.',
  keywords: 'kirana, underwriting, NBFC, AI, credit scoring, fintech',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏪</text></svg>" />
      </head>
      <body className="bg-surface-0 text-white antialiased">
        {children}
      </body>
    </html>
  );
}
