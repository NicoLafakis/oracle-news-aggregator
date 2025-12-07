import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'
import { ORACLE_SYSTEM_PROMPT } from '@/lib/oracle-context'

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
})

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json()

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: 'Messages array required' },
        { status: 400 }
      )
    }

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      system: ORACLE_SYSTEM_PROMPT,
      messages: messages.map((m: { role: string; content: string }) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })),
    })

    const content = response.content[0]
    if (content.type !== 'text') {
      throw new Error('Unexpected response type')
    }

    return NextResponse.json({ content: content.text })
  } catch (error) {
    console.error('Oracle API Error:', error)

    // Extract meaningful error message for debugging
    let errorMessage = 'Failed to consult The Oracle'
    let statusCode = 500

    if (error instanceof Error) {
      // Check for Anthropic API specific errors
      const err = error as Error & { status?: number; error?: { type?: string; message?: string } }

      if (err.status === 400 && err.error?.type === 'invalid_request_error') {
        // Token limit or request size error
        errorMessage = 'The knowledge web is too vast for a single query. Please try a more specific question.'
        statusCode = 400
      } else if (err.status === 401) {
        errorMessage = 'Oracle authentication failed. Please check API configuration.'
        statusCode = 401
      } else if (err.status === 429) {
        errorMessage = 'The Oracle is overwhelmed with requests. Please wait a moment and try again.'
        statusCode = 429
      } else if (err.message.includes('token') || err.message.includes('context length')) {
        errorMessage = 'The query exceeds the Oracle\'s capacity. Please ask a simpler question.'
        statusCode = 400
      } else {
        // Log the full error for debugging
        console.error('Full error details:', JSON.stringify(err, null, 2))
      }
    }

    return NextResponse.json(
      { error: errorMessage },
      { status: statusCode }
    )
  }
}
