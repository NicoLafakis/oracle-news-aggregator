import Anthropic from '@anthropic-ai/sdk'
import { NextRequest } from 'next/server'
import { ORACLE_SYSTEM_PROMPT } from '@/lib/oracle-context'

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
})

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json()

    if (!messages || !Array.isArray(messages)) {
      return new Response(
        JSON.stringify({ error: 'Messages array required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Create streaming response
    const stream = await anthropic.messages.stream({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      system: ORACLE_SYSTEM_PROMPT,
      messages: messages.map((m: { role: string; content: string }) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })),
    })

    // Create a ReadableStream that emits Server-Sent Events
    const encoder = new TextEncoder()
    const readableStream = new ReadableStream({
      async start(controller) {
        try {
          for await (const event of stream) {
            if (event.type === 'content_block_delta') {
              const delta = event.delta
              if ('text' in delta) {
                // Send the text chunk as an SSE event
                const sseMessage = `data: ${JSON.stringify({ text: delta.text })}\n\n`
                controller.enqueue(encoder.encode(sseMessage))
              }
            }
          }
          // Send completion event
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        } catch (error) {
          console.error('Stream error:', error)
          const errorMessage = getErrorMessage(error)
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: errorMessage })}\n\n`))
          controller.close()
        }
      },
    })

    return new Response(readableStream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  } catch (error) {
    console.error('Oracle API Error:', error)
    const errorMessage = getErrorMessage(error)
    const statusCode = getStatusCode(error)

    return new Response(
      JSON.stringify({ error: errorMessage }),
      { status: statusCode, headers: { 'Content-Type': 'application/json' } }
    )
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    const err = error as Error & { status?: number; error?: { type?: string; message?: string } }

    if (err.status === 400 && err.error?.type === 'invalid_request_error') {
      return 'The knowledge web is too vast for a single query. Please try a more specific question.'
    } else if (err.status === 401) {
      return 'Oracle authentication failed. Please check API configuration.'
    } else if (err.status === 429) {
      return 'The Oracle is overwhelmed with requests. Please wait a moment and try again.'
    } else if (err.message.includes('token') || err.message.includes('context length')) {
      return 'The query exceeds the Oracle\'s capacity. Please ask a simpler question.'
    }
  }
  return 'Failed to consult The Oracle'
}

function getStatusCode(error: unknown): number {
  if (error instanceof Error) {
    const err = error as Error & { status?: number; error?: { type?: string } }
    if (err.status === 400 && err.error?.type === 'invalid_request_error') return 400
    if (err.status === 401) return 401
    if (err.status === 429) return 429
  }
  return 500
}
