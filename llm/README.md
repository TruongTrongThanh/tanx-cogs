# LLM Cog for Tanx Discord Bot

## Overview
This cog uses the any-llm SDK to provide intelligent LLM-powered responses in Discord with support for multiple providers. It automatically responds to:

1. **Bot Mentions** - When any user @mentions the bot in any channel
2. **Complaints** - When users express frustration or complaints
3. **Questions** - When users ask questions requiring calculation or search (only responds if enough information is available)
4. **🔧 Tool Calling** - Agent can use tools like calculator, current time, web search, etc. (see [tools/README.md](tools/README.md))

## Setup

### 1. Environment Variables
Set the following environment variables:

```bash
# Required - specify provider and model
# Format: PROVIDER:MODEL
LLM_MODEL=openai:gpt-4o-mini
# OR
LLM_MODEL=anthropic:claude-3-5-sonnet-20241022
# OR
LLM_MODEL=mistral:mistral-small-latest
# etc.

# Required - provider-specific API key
# For OpenAI:
OPENAI_API_KEY=your_openai_api_key_here

# For Anthropic:
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# For Mistral:
# MISTRAL_API_KEY=your_mistral_api_key_here

# For other providers, see: https://mozilla-ai.github.io/any-llm/providers/

# Optional - for web search tool
BRAVE_SEARCH_API_KEY=your_brave_search_api_key_here

# Optional - for image processing tool
WINDMILL_TOKEN=your_windmill_token_here
WINDMILL_URL=your_windmill_url_here
```

### 2. Get API Keys
You can use any supported provider from [any-llm](https://mozilla-ai.github.io/any-llm/providers/):

**OpenAI:**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account and generate an API key
3. Set `OPENAI_API_KEY` environment variable

**Anthropic:**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account and generate an API key
3. Set `ANTHROPIC_API_KEY` environment variable

**Mistral:**
1. Visit [Mistral AI](https://console.mistral.ai/)
2. Create an account and generate an API key
3. Set `MISTRAL_API_KEY` environment variable

**Other Providers:**
See the [any-llm providers documentation](https://mozilla-ai.github.io/any-llm/providers/) for a full list.

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Load the Cog
In Discord, use the Red-DiscordBot commands:
```
[p]load llm
```

### 5. (Optional) Enable Web Search
To enable the web search tool:
1. Visit [Brave Search API](https://brave.com/search/api/) and sign up for a free account
2. Get your API key from the dashboard
3. Set the environment variable: `BRAVE_SEARCH_API_KEY=your_api_key`
4. Restart the bot

The free tier includes 2,000 queries per month.

### 6. (Optional) Enable Image Processing
To enable the image processing tool:
1. Set up a Windmill instance with an image processing workflow
2. Create an endpoint at `process_image` that accepts:
   - `image_url` (string): URL of the image to process
   - `magick_command` (string): ImageMagick command to execute
3. The endpoint should return:
   - `image_base64` (string): Base64-encoded processed image
   - `format` (string): Image format (png, jpg, etc.)
4. Set environment variables:
   - `WINDMILL_TOKEN=your_token`
   - `WINDMILL_URL=your_windmill_url`
5. Restart the bot

## Available Models
You can use any model from any supported provider. Some popular options:

**OpenAI:**
- `openai:gpt-4o` - Latest flagship model
- `openai:gpt-4o-mini` - Fast and affordable
- `openai:o1-preview` - Advanced reasoning model

**Anthropic:**
- `anthropic:claude-3-5-sonnet-20241022` - Most capable Claude model
- `anthropic:claude-3-haiku-20240307` - Fast and affordable

**Mistral:**
- `mistral:mistral-large-latest` - Most capable Mistral model
- `mistral:mistral-small-latest` - Fast and affordable

**Ollama (Local):**
- `ollama:llama3.2` - Run models locally
- `ollama:mistral` - Local Mistral models

See the full list at: https://mozilla-ai.github.io/any-llm/providers/

## Owner Commands

### `.llmtest <prompt>`
Test the LLM functionality with a custom prompt.
```
.llmtest What is the meaning of life?
```

### `.llmstatus`
Check if the LLM cog is properly configured and view loaded tools.
```
.llmstatus
```

### `.llmtools`
List all available tools with detailed parameters and descriptions.
```
.llmtools
```

## Tool Calling (Function Calling)

The LLM agent can automatically use tools to answer questions more accurately:

**Available Tools:**
- 🧮 **Calculator** - Perform mathematical calculations
- 🕐 **Current Time** - Get current date/time information  
- 🔍 **Web Search** - Search the web using Brave Search API (requires API key)
- 🖼️ **Image Processor** - Process images using ImageMagick via Windmill API

**Example Interactions:**
```
User: What's 15% of 250?
Bot: [uses calculator tool]
Bot: The result of 250 × 0.15 is 37.5

User: What time is it?
Bot: [uses get_current_time tool]
Bot: It's currently Wednesday, April 2, 2026 at 2:45 PM

User: *attaches image* Can you resize this to 50%?
Bot: [uses process_image tool]
Bot: Here's your resized image! [image attached]
```

**Creating Custom Tools:**
See [tools/README.md](tools/README.md) for comprehensive documentation on:
- How to create custom tools
- Tool development guidelines
- Model compatibility for function calling
- Debugging and troubleshooting
```
.llmstatus
```

## How It Works

### LLM-Based Detection

The bot uses **intelligent LLM-based detection** instead of simple keyword matching to accurately identify:

**Complaints:**
- The LLM analyzes the message for expressions of frustration, dissatisfaction, or negative sentiment
- Detects nuanced complaints that keyword matching might miss
- Understands context better than regex patterns

**Questions:**
- The LLM determines if a message is asking for factual information, calculations, or research
- Distinguishes between genuine questions and casual chat or rhetorical questions
- Only responds when the question requires computational or informational help

### Detection Process
1. **Initial Filtering** - Skips bot messages, empty messages, and unconfigured API
2. **Message Classification** - Uses LLM with specialized prompts to classify messages
3. **Response Generation** - If classification matches criteria, generates contextual response
4. **Smart Response** - Bot uses different system prompts based on the detected message type

### Response Behavior
- The bot shows a typing indicator while processing
- Responses are limited to ~300 words for brevity
- Long responses are automatically split into multiple messages (2000 char Discord limit)
- The bot will only answer questions if it has sufficient information
- The bot ignores its own messages and other bots

## Examples

**Example 1: Bot Mention**
```
User: @Bot what's the weather like?
Bot: I don't have access to real-time weather data, but I can help you find...
```

**Example 2: Complaint**
```
User: Ugh, this is so annoying! Nothing works properly.
Bot: I understand your frustration. Let me try to help...
```

**Example 3: Question**
```
User: How do I calculate 15% of 250?
Bot: To calculate 15% of 250: 250 × 0.15 = 37.5
```

## Privacy & Best Practices
- Messages are sent to your chosen LLM provider for both detection and response generation
- **Note:** Detection uses minimal tokens (16 tokens max) to classify messages efficiently
- Consider channel permissions to limit where the bot responds
- Monitor API usage and costs
- Review your provider's privacy policy and terms of service

## Performance Considerations
- **Detection Latency:** Each message requires 1-2 LLM calls for classification (complaint/question detection)
- **Cost Optimization:** Detection uses max_tokens=16 to minimize API costs
- **Rate Limits:** Different providers have different rate limits; monitor your usage
- **Parallel Processing:** Bot processes one message at a time to avoid overwhelming the API

## Troubleshooting

**Bot not responding?**
1. Check if `LLM_MODEL` environment variable is set correctly (format: `provider:model`)
2. Check if provider-specific API key is set (e.g., `OPENAI_API_KEY`)
3. Use `.llmstatus` to verify configuration
4. Check bot permissions (needs Read Messages, Send Messages)
5. Check logs for errors

**API errors?**
1. Verify API key is valid for your provider
2. Check if you've exceeded rate limits
3. Try a different model from the same provider
4. Check your provider's service status
5. Ensure the model name is correct for your provider

## Support
For issues or questions, check the logs or contact the bot administrator.
