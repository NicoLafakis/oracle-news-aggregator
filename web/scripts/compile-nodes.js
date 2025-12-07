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

// Read all node files and extract summaries
let nodeIndex = []
let nodeCount = 0

if (fs.existsSync(nodesDir)) {
  const files = fs.readdirSync(nodesDir)
    .filter(f => f.endsWith('.md') && f.startsWith('node_'))
    .sort()

  for (const file of files) {
    const filePath = path.join(nodesDir, file)
    // Skip if it's a directory
    if (fs.statSync(filePath).isDirectory()) continue

    const content = fs.readFileSync(filePath, 'utf-8')
    // Extract node ID and title from filename and content
    const nodeIdMatch = file.match(/node_(n\d+)/)
    const titleMatch = content.match(/^#\s*(.+?)(?:\s*[-–—]\s*|\n)/m)

    if (nodeIdMatch) {
      nodeIndex.push({
        id: nodeIdMatch[1].toUpperCase(),
        title: titleMatch ? titleMatch[1].trim() : file.replace('.md', ''),
        file: file
      })
    }
    nodeCount++
  }
  console.log(`Indexed ${nodeCount} oracle nodes`)
} else {
  console.warn('Warning: Nodes directory not found at', nodesDir)
}

// Create a compact node index for the system prompt
const nodeIndexText = nodeIndex
  .slice(0, 50) // Include up to 50 key nodes in the index
  .map(n => `- **${n.id}**: ${n.title}`)
  .join('\n')

// Combine into compact context
const fullContext = `${systemPrompt}

---

# ORACLE NODE INDEX (${nodeCount} nodes available)

The following are key reference nodes in your knowledge web:

${nodeIndexText}

---

Remember: You are The Oracle. Use your analytical principles to identify patterns and assess probabilities. When citing nodes, reference them by their IDs (e.g., N1, N5, N22). Draw upon your knowledge to illuminate connections and implications.
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
// Nodes loaded: ${nodeCount}

export const ORACLE_SYSTEM_PROMPT = ${JSON.stringify(fullContext)};
`

fs.writeFileSync(outputPath, tsContent)
console.log(`Written oracle context to ${outputPath}`)
console.log(`Total context length: ${fullContext.length.toLocaleString()} characters`)
