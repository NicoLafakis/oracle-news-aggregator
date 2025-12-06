const fs = require('fs')
const path = require('path')

// Paths
const nodesDir = path.join(__dirname, '..', '..', 'oracle', 'oracle-nodes')
const systemPromptPath = path.join(__dirname, '..', '..', 'oracle', 'ORACLE_SYSTEM_PROMPT.md')
const outputPath = path.join(__dirname, '..', 'lib', 'oracle-context.ts')

// Read the system prompt
let systemPrompt = ''
if (fs.existsSync(systemPromptPath)) {
  systemPrompt = fs.readFileSync(systemPromptPath, 'utf-8')
  console.log('Loaded system prompt')
} else {
  console.warn('Warning: System prompt not found at', systemPromptPath)
}

// Read all node files
let nodesContent = ''
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
    nodesContent += `\n\n---\n\n${content}`
    nodeCount++
  }
  console.log(`Loaded ${nodeCount} oracle nodes`)
} else {
  console.warn('Warning: Nodes directory not found at', nodesDir)
}

// Combine into full context
const fullContext = `${systemPrompt}

---

# ORACLE KNOWLEDGE WEB

The following are the verified nodes in The Oracle's knowledge web. Use these to inform your assessments and trace causal threads.

${nodesContent}

---

Remember: You are The Oracle. Draw upon this knowledge web to illuminate patterns and assess probabilities. Always cite relevant nodes when making assessments.
`

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
