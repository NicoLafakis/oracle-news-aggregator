import fs from 'fs'
import path from 'path'

interface Story {
  id: string
  title: string
  description: string
  content: string
  source: string
  source_url: string
  published_at: string
  category: string
  keywords?: string[]
}

interface DailyIndex {
  date: string
  total_stories: number
  by_category: Record<string, number>
  stories: Array<{
    id: string
    title: string
    category: string
    source: string
    published_at: string
  }>
}

/**
 * Get the path to the oracle stories directory
 * Works in both development and production (Vercel) environments
 */
function getStoriesBasePath(): string {
  // In production, files are in the project root
  // In development, we're in the web directory
  const possiblePaths = [
    path.join(process.cwd(), 'oracle', 'stories'),
    path.join(process.cwd(), '..', 'oracle', 'stories'),
  ]

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p
    }
  }

  // Default to first option
  return possiblePaths[0]
}

/**
 * Get available dates that have story data, sorted newest first
 */
function getAvailableDates(basePath: string, maxDays: number = 7): string[] {
  const dates: string[] = []

  try {
    const years = fs.readdirSync(basePath).filter(d => /^\d{4}$/.test(d)).sort().reverse()

    for (const year of years) {
      const yearPath = path.join(basePath, year)
      const months = fs.readdirSync(yearPath).filter(d => /^\d{2}$/.test(d)).sort().reverse()

      for (const month of months) {
        const monthPath = path.join(yearPath, month)
        const days = fs.readdirSync(monthPath).filter(d => /^\d{2}$/.test(d)).sort().reverse()

        for (const day of days) {
          dates.push(`${year}/${month}/${day}`)
          if (dates.length >= maxDays) {
            return dates
          }
        }
      }
    }
  } catch {
    console.error('Error reading story dates')
  }

  return dates
}

/**
 * Load the daily index for a specific date
 */
function loadDailyIndex(basePath: string, datePath: string): DailyIndex | null {
  const indexPath = path.join(basePath, datePath, 'index.json')

  try {
    if (fs.existsSync(indexPath)) {
      const content = fs.readFileSync(indexPath, 'utf-8')
      return JSON.parse(content)
    }
  } catch {
    console.error(`Error loading index for ${datePath}`)
  }

  return null
}

/**
 * Load full story details from a JSON file
 */
function loadStory(basePath: string, datePath: string, category: string, storyId: string): Story | null {
  const storyPath = path.join(basePath, datePath, category, `${storyId}.json`)

  try {
    if (fs.existsSync(storyPath)) {
      const content = fs.readFileSync(storyPath, 'utf-8')
      return JSON.parse(content)
    }
  } catch {
    console.error(`Error loading story ${storyId}`)
  }

  return null
}

/**
 * Format stories for inclusion in Claude's context
 */
function formatStoriesForContext(stories: Story[], date: string): string {
  if (stories.length === 0) return ''

  const groupedByCategory: Record<string, Story[]> = {}

  for (const story of stories) {
    const cat = story.category || 'uncategorized'
    if (!groupedByCategory[cat]) {
      groupedByCategory[cat] = []
    }
    groupedByCategory[cat].push(story)
  }

  let output = `## ${date}\n\n`

  for (const [category, categoryStories] of Object.entries(groupedByCategory)) {
    const categoryLabel = category.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    output += `### ${categoryLabel}\n\n`

    for (const story of categoryStories) {
      output += `**${story.title}**\n`
      if (story.description) {
        output += `${story.description}\n`
      }
      output += `*Source: ${story.source}*\n\n`
    }
  }

  return output
}

export interface RecentStoriesResult {
  formattedContext: string
  totalStories: number
  daysLoaded: number
}

/**
 * Load recent stories and format them for Claude's context
 * @param maxDays - Maximum number of days to look back (default: 3)
 * @param maxStoriesPerDay - Maximum stories to include per day (default: 50)
 */
export function loadRecentStories(maxDays: number = 3, maxStoriesPerDay: number = 50): RecentStoriesResult {
  const basePath = getStoriesBasePath()
  const dates = getAvailableDates(basePath, maxDays)

  if (dates.length === 0) {
    return {
      formattedContext: '',
      totalStories: 0,
      daysLoaded: 0
    }
  }

  let fullContext = `\n\n---\n\n# RECENT NEWS INTELLIGENCE\n\nThe following are recent news stories from The Oracle's aggregation system. Use these to inform your assessments with current events and emerging patterns.\n\n`

  let totalStories = 0

  for (const datePath of dates) {
    const index = loadDailyIndex(basePath, datePath)
    if (!index) continue

    const stories: Story[] = []
    let storiesLoaded = 0

    // Load stories from the index, prioritizing by category relevance
    for (const storyMeta of index.stories) {
      if (storiesLoaded >= maxStoriesPerDay) break

      const story = loadStory(basePath, datePath, storyMeta.category, storyMeta.id)
      if (story) {
        stories.push(story)
        storiesLoaded++
      }
    }

    if (stories.length > 0) {
      const dateFormatted = datePath.replace(/\//g, '-')
      fullContext += formatStoriesForContext(stories, dateFormatted)
      totalStories += stories.length
    }
  }

  if (totalStories > 0) {
    fullContext += `\n---\n\n*${totalStories} stories loaded from the last ${dates.length} day(s). Use these current events to inform your pattern recognition and assessments.*\n`
  }

  return {
    formattedContext: totalStories > 0 ? fullContext : '',
    totalStories,
    daysLoaded: dates.length
  }
}
