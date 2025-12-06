import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'The Oracle | Foresight Through Pattern Recognition',
  description: 'An analytical intelligence that synthesizes global events into actionable foresight.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased text-gray-100">
        {children}
      </body>
    </html>
  )
}
