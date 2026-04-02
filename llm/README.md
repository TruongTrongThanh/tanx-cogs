# LLM Cog for Tanx Discord Bot

## Overview
This cog uses OpenRouter API to provide intelligent LLM-powered responses in Discord. It automatically responds to:

1. **Bot Mentions** - When any user @mentions the bot in any channel
2. **Complaints** - When users express frustration or complaints
3. **Questions** - When users ask questions requiring calculation or search (only responds if enough information is available)
4. **🔧 Tool Calling** - Agent can use tools like calculator, current time, web search, etc. (see [tools/README.md](tools/README.md))

## Setup

### 1. Environment Variables
Set the following environment variables:

```bash
# Required
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional (defaults to free model)
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free

# Optional - for web search tool
BRAVE_SEARCH_API_KEY=your_brave_search_api_key_here

# Optional - for image processing tool
WINDMILL_TOKEN=your_windmill_token_here
WINDMILL_URL=your_windmill_url_here
```

### 2. Get OpenRouter API Key
1. Visit [OpenRouter](https://openrouter.ai/)
2. Sign up for an account
3. Generate an API key from your dashboard
4. Set the `OPENROUTER_API_KEY` environment variable

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Load the Cog
In 

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
5. Restart the botDiscord, use the Red-DiscordBot commands:
```
[p]load llm
```

## Available Models
You can use any model available on OpenRouter. Some popular free options:
- `meta-llama/llama-3.1-8b-instruct:free` (default)
- `google/gemini-flash-1.5:free`
- `mistralai/mistral-7b-instruct:free`

For better responses, consider paid models:
- `anthropic/claude-3-sonnet`
- `openai/gpt-4-turbo`
- `google/gemini-pro-1.5`

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
2. **Message Classification** - Uses OpenRouter API with specialized prompts to classify messages
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
- Messages are sent to OpenRouter API for both detection and response generation
- **Note:** Detection uses minimal tokens (10 tokens max) to classify messages efficiently
- Consider channel permissions to limit where the bot responds
- Monitor API usage and costs (free models have rate limits)
- Review OpenRouter's privacy policy and terms of service

## Performance Considerations
- **Detection Latency:** Each message requires 1-2 LLM calls for classification (complaint/question detection)
- **Cost Optimization:** Detection uses max_tokens=10 to minimize API costs
- **Free Tier:** Free models like Llama 3.1 have rate limits; consider paid models for high-traffic servers
- **Parallel Processing:** Bot processes one message at a time to avoid overwhelming the API

## Troubleshooting

**Bot not responding?**
1. Check if `OPENROUTER_API_KEY` is set correctly
2. Use `.llmstatus` to verify configuration
3. Check bot permissions (needs Read Messages, Send Messages)
4. Check logs for errors

**API errors?**
1. Verify API key is valid
2. Check if you've exceeded rate limits (free tier)
3. Try a different model
4. Check OpenRouter service status

## Support
For issues or questions, check the logs or contact the bot administrator.
