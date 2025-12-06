# The Oracle - Web Interface

A Next.js web application that provides a chat interface to consult The Oracle, an AI that synthesizes global events into actionable foresight.

## Setup

### 1. Install Dependencies

```bash
cd web
npm install
```

### 2. Configure Environment

Create a `.env.local` file:

```bash
cp .env.example .env.local
```

Add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Compile Oracle Nodes

This bundles all oracle nodes into the system context:

```bash
npm run compile-nodes
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Deploy to Vercel

### Option 1: Vercel CLI

```bash
npm i -g vercel
vercel
```

### Option 2: GitHub Integration

1. Push to GitHub
2. Import project in Vercel Dashboard
3. Set `ANTHROPIC_API_KEY` in Environment Variables
4. Set Root Directory to `web`
5. Deploy

## Architecture

```
web/
├── app/
│   ├── api/chat/route.ts   # Anthropic API endpoint
│   ├── layout.tsx          # App layout
│   ├── page.tsx            # Chat interface
│   └── globals.css         # Styling
├── lib/
│   └── oracle-context.ts   # Compiled system prompt + nodes
├── scripts/
│   └── compile-nodes.js    # Node compiler script
└── package.json
```

## How It Works

1. **compile-nodes.js** reads all oracle node markdown files and the system prompt
2. Bundles them into a single TypeScript module (`lib/oracle-context.ts`)
3. The API route sends this as the system prompt to Claude Sonnet
4. Users chat with The Oracle through the web interface

## Updating Oracle Nodes

When new nodes are added to `oracle/oracle-nodes/`:

```bash
npm run compile-nodes
npm run build
```

The nodes will be included in the next deployment.
