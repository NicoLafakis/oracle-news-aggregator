const fs = require('fs')
const path = require('path')

// Paths
const nodesDir = path.join(__dirname, '..', '..', 'oracle', 'oracle-nodes')
const systemPromptPath = path.join(__dirname, '..', '..', 'oracle', 'ORACLE_SYSTEM_PROMPT.md')
const outputPath = path.join(__dirname, '..', 'lib', 'oracle-context.ts')

// Maximum size for the system prompt (characters) - keep well under token limits
const MAX_CONTEXT_SIZE = 100000 // ~25k tokens max

// Read the system prompt
let systemPrompt = ''
if (fs.existsSync(systemPromptPath)) {
  systemPrompt = fs.readFileSync(systemPromptPath, 'utf-8')
  console.log('Loaded system prompt')
} else {
  console.warn('Warning: System prompt not found at', systemPromptPath)
}

// Read all node files and extract event summaries
let eventIndex = []
let eventCount = 0

if (fs.existsSync(nodesDir)) {
  const files = fs.readdirSync(nodesDir)
    .filter(f => f.endsWith('.md') && f.startsWith('node_'))
    .sort()

  for (const file of files) {
    const filePath = path.join(nodesDir, file)
    // Skip if it's a directory
    if (fs.statSync(filePath).isDirectory()) continue

    const content = fs.readFileSync(filePath, 'utf-8')

    // Extract title from content (removing any N### prefix)
    const titleMatch = content.match(/^#\s*(?:Node\s+N\d+:\s*)?(.+?)(?:\s*[-–—]\s*|\n)/m)

    if (titleMatch) {
      // Clean up the title - remove any remaining node references
      let title = titleMatch[1].trim()
      title = title.replace(/^Node\s+N\d+:\s*/i, '')

      eventIndex.push({
        title: title,
        file: file
      })
    }
    eventCount++
  }
  console.log(`Indexed ${eventCount} tracked events`)
} else {
  console.warn('Warning: Events directory not found at', nodesDir)
}

// Create a compact event summary for the system prompt (just titles, no IDs)
const eventSummary = eventIndex
  .slice(0, 50) // Include up to 50 key events in the summary
  .map(e => `- ${e.title}`)
  .join('\n')

// Combine into compact context
const fullContext = `${systemPrompt}

---

# KNOWLEDGE BASE (${eventCount} tracked events)

Your knowledge web includes documented events and their ripple effects. Key events you can draw upon:

${eventSummary}

---

Remember: You are The Oracle. Use your analytical principles to identify patterns and assess probabilities. When discussing events, describe them naturally by their content—never reference internal identifiers or codes. Walk users through the ripple effects and help them understand the connections.
`

// Verify size is within limits
if (fullContext.length > MAX_CONTEXT_SIZE) {
  console.warn(`Warning: Context size (${fullContext.length}) exceeds recommended maximum (${MAX_CONTEXT_SIZE})`)
}

// Ensure lib directory exists
const libDir = path.dirname(outputPath)
if (!fs.existsSync(libDir)) {
  fs.mkdirSync(libDir, { recursive: true })
}

// Write as TypeScript module
const tsContent = `// Auto-generated Oracle context - DO NOT EDIT
// Generated at: ${new Date().toISOString()}
// Events loaded: ${eventCount}

export const ORACLE_SYSTEM_PROMPT = ${JSON.stringify(fullContext)};
`

fs.writeFileSync(outputPath, tsContent)
console.log(`Written oracle context to ${outputPath}`)
console.log(`Total context length: ${fullContext.length.toLocaleString()} characters`)
