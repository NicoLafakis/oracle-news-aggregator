'use client'

import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function OraclePage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: userMessage }]
        })
      })

      if (!response.ok) {
        // Try to get the error message from the response
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }])
    } catch (error) {
      console.error('Error:', error)
      const errorMessage = error instanceof Error ? error.message : 'The threads are obscured. Please try again.'
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-oracle-gold/20 bg-black/30 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold oracle-glow text-oracle-gold text-center">
            THE ORACLE
          </h1>
          <p className="text-center text-gray-400 mt-2 text-sm">
            Foresight through pattern recognition
          </p>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="text-center py-20">
              <div className="text-6xl mb-6">🔮</div>
              <h2 className="text-xl text-oracle-gold mb-4">Ask The Oracle</h2>
              <p className="text-gray-400 max-w-md mx-auto mb-8">
                I do not predict the future. I reveal the patterns already in motion.
                Ask about trends, events, or what may come to pass.
              </p>
              <div className="grid gap-3 max-w-lg mx-auto">
                {[
                  "Will there be mass layoffs in tech over the next year?",
                  "What's the future of AI agents in the workplace?",
                  "Is the AI investment bubble going to burst?",
                ].map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(suggestion)}
                    className="text-left px-4 py-3 bg-black/30 border border-oracle-gold/20
                             rounded-lg hover:border-oracle-gold/50 hover:bg-black/50
                             transition-all text-sm text-gray-300"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, i) => (
                <div
                  key={i}
                  className={`message-enter ${
                    message.role === 'user' ? 'flex justify-end' : ''
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-oracle-gold/20 border border-oracle-gold/30'
                        : 'bg-black/40 border border-gray-700 oracle-message'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="message-enter">
                  <div className="bg-black/40 border border-gray-700 rounded-lg px-4 py-3 inline-block">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-oracle-gold rounded-full typing-dot"></div>
                      <div className="w-2 h-2 bg-oracle-gold rounded-full typing-dot"></div>
                      <div className="w-2 h-2 bg-oracle-gold rounded-full typing-dot"></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <footer className="border-t border-oracle-gold/20 bg-black/30 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the future..."
              rows={1}
              className="flex-1 bg-black/50 border border-oracle-gold/30 rounded-lg px-4 py-3
                       text-gray-100 placeholder-gray-500 resize-none
                       focus:outline-none focus:border-oracle-gold/60 focus:ring-1 focus:ring-oracle-gold/30"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-oracle-gold/20 border border-oracle-gold/50 rounded-lg
                       text-oracle-gold font-medium hover:bg-oracle-gold/30
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Ask
            </button>
          </div>
          <p className="text-center text-gray-500 text-xs mt-3">
            The Oracle illuminates probability, not certainty. Use wisdom in application.
          </p>
        </form>
      </footer>
    </div>
  )
}
