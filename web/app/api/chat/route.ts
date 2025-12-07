import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'
import { ORACLE_SYSTEM_PROMPT } from '@/lib/oracle-context'
import { loadRecentStories } from '@/lib/story-loader'

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
})

// Cache for recent stories to avoid reading files on every request
let storiesCache: { context: string; timestamp: number } | null = null
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

function getEnhancedSystemPrompt(): string {
  const now = Date.now()

  // Check if cache is valid
  if (storiesCache && (now - storiesCache.timestamp) < CACHE_TTL) {
    return ORACLE_SYSTEM_PROMPT + storiesCache.context
  }

  // Load fresh stories
  try {
    const { formattedContext, totalStories, daysLoaded } = loadRecentStories(3, 50)

    if (totalStories > 0) {
      console.log(`Oracle: Loaded ${totalStories} stories from ${daysLoaded} days`)
      storiesCache = {
        context: formattedContext,
        timestamp: now
      }
      return ORACLE_SYSTEM_PROMPT + formattedContext
    }
  } catch (error) {
    console.error('Error loading recent stories:', error)
  }

  // Fallback to base prompt if no stories
  return ORACLE_SYSTEM_PROMPT
}

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json()

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: 'Messages array required' },
        { status: 400 }
      )
    }

    const systemPrompt = getEnhancedSystemPrompt()

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      system: systemPrompt,
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
    return NextResponse.json(
      { error: 'Failed to consult The Oracle' },
      { status: 500 }
    )
  }
}
