# tanx-cogs

Custom cogs for Red-DiscordBot with AI/LLM capabilities.

## Available Cogs

### 🤖 LLM - AI-Powered Conversational Bot
Uses any-llm SDK to provide intelligent responses from multiple LLM providers.

**Features:**
- Responds to @mentions automatically
- Detects and empathetically responds to complaints
- Answers questions requiring calculation or research
- Smart detection - only responds when appropriate
- Supports multiple LLM providers (OpenAI, Anthropic, Mistral, Ollama, etc.)

**Setup:**
```bash
# Set environment variables
# Format: PROVIDER:MODEL (e.g., "openai:gpt-4o-mini", "anthropic:claude-3-5-sonnet-20241022")
LLM_MODEL=openai:gpt-4o-mini

# Set provider-specific API key
OPENAI_API_KEY=your_api_key_here
# OR
ANTHROPIC_API_KEY=your_api_key_here
# OR any other supported provider

# Load the cog
[p]load llm
```

See [llm/README.md](llm/README.md) for detailed documentation.

### 📊 Rec - Recommendation Engine
Automated recommendation system using Windmill API.

**Features:**
- Scheduled recommendations every Saturday at 10:00 AM
- Manual recommendation command
- Windmill API integration

**Setup:**
```bash
# Set environment variables
WINDMILL_TOKEN=your_token_here
WINDMILL_URL=your_windmill_url_here
REC_CHANNEL_ID=channel_id_for_recommendations

# Load the cog
[p]load rec
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tanx-cogs.git
cd tanx-cogs

# Install dependencies
pip install -r requirements.txt

# Load cogs in Discord
[p]load llm
[p]load rec
```

## Requirements
- Red-DiscordBot 3.5.24+
- Python 3.11+
- any-llm-sdk
- Environment variables for API keys
