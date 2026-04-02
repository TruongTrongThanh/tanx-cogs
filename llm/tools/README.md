# LLM Tools System

## Overview
The LLM cog now supports **function calling (tool use)** - allowing the AI agent to use tools to perform calculations, get current time, and more.

## How It Works

When a user asks a question, the LLM can:
1. Decide if it needs to use a tool
2. Call one or more tools with appropriate arguments
3. Receive the tool results
4. Formulate a natural language response based on the results

This happens automatically - users don't need to explicitly request tool usage.

## Available Tools

### 🧮 Calculator (`calculator`)
Performs mathematical calculations.

**Example Usage:**
- User: "What's 15% of 250?"
- Bot uses: `calculator("250 * 0.15")`
- Bot responds: "The result of 250 * 0.15 is 37.5"

**Supported Operations:**
- Basic arithmetic: `+`, `-`, `*`, `/`, `**` (power)
- Functions: `sqrt()`, `sin()`, `cos()`, `tan()`, `log()`, `exp()`
- Constants: `pi`, `e`

### 🕐 Current Time (`get_current_time`)
Gets the current date and time.

**Example Usage:**
- User: "What time is it?"
- Bot uses: `get_current_time(format="time")`
- Bot responds: "It's currently 14:30:45"

**Format Options:**
- `full` - Complete date and time
- `date` - Just the date (YYYY-MM-DD)
- `time` - Just the time (HH:MM:SS)
- `day` - Day of week and date

### 🔍 Web Search (`web_search`)
Searches the web using Brave Search API.

**Example Usage:**
- User: "What's the latest news about AI?"
- Bot uses: `web_search("latest AI news")`
- Bot responds with current information from the web

**Setup Required:**
1. Get a free API key from [Brave Search API](https://brave.com/search/api/)
2. Set environment variable: `BRAVE_SEARCH_API_KEY=your_api_key`
3. Restart the bot

**Parameters:**
- `query` - The search query (required)
- `count` - Number of results (1-10, default: 3)

### 🖼️ Image Processor (`process_image`)
Processes images using ImageMagick commands via Windmill API.

**Example Usage:**
- User: *attaches image* "Make this 50% smaller"
- Bot uses: `process_image(image_url, "-resize 50%")`
- Bot responds with processed image

**Setup Required:**
1. Set up Windmill instance with image processing workflow
2. Create endpoint that accepts `image_url` and `magick_command`
3. Set environment variables: `WINDMILL_TOKEN` and `WINDMILL_URL`
4. Restart the bot

**Parameters:**
- `image_url` - URL of the image to process (required)
- `magick_command` - ImageMagick command without 'magick' prefix (required)

**Example Commands:**
- `"-resize 50%"` - Resize to 50%
- `"-rotate 90"` - Rotate 90 degrees
- `"-sepia-tone 80%"` - Apply sepia effect
- `"-blur 0x8"` - Blur image
- `"-quality 85 -format jpg"` - Convert and compress

**Status:** ✅ Fully implemented with Windmill API integration

**Status:** ✅ Fully implemented with Brave Search API

## Creating Custom Tools

### 1. Create a new file in `llm/tools/`

Example: `llm/tools/weather.py`

```python
from typing import Dict, Any
from .base import BaseTool


class WeatherTool(BaseTool):
    """Tool for getting weather information."""
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get current weather for a given location."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location"
                }
            },
            "required": ["location"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        location = arguments.get("location", "")
        # TODO: Call weather API
        return f"Weather data for {location} not available (API not configured)"
```

### 2. Tools are auto-loaded

The ToolRegistry automatically discovers and loads all tools from the `tools/` directory.

### 3. Test your tool

Use `.llmtest` to test if the LLM correctly uses your tool:
```
.llmtest What's the weather in Tokyo?
```

## Tool Development Guidelines

### Parameter Schema

Use JSON Schema format for parameters:

```python
{
    "type": "object",
    "properties": {
        "param_name": {
            "type": "string|number|boolean|array|object",
            "description": "Clear description for the LLM",
            "enum": ["option1", "option2"],  # Optional
            "default": "value"  # Optional
        }
    },
    "required": ["param1", "param2"]
}
```

### Error Handling

Always handle errors gracefully in `execute()`:

```python
def execute(self, arguments: Dict[str, Any]) -> str:
    try:
        # Your logic here
        return "Success result"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Return Format

Always return a string that the LLM can understand:
- ✅ "The temperature in Tokyo is 18°C"
- ✅ "Error: Location not found"
- ❌ Don't return JSON or complex objects

## Model Compatibility

Not all models support function calling. Known compatible models:

✅ **Supported:**
- `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo` (OpenAI)
- `claude-3-opus`, `claude-3-sonnet` (Anthropic)
- `gemini-pro-1.5` (Google)
- `mistral-large` (Mistral)
-  `meta-llama/llama-3.1-70b-instruct` (Meta, via OpenRouter)

❌ **Not Supported:**
- Most free models (they may ignore tools)
- Older models

**Recommendation:** Use `gpt-3.5-turbo` or `claude-3-sonnet` for reliable tool calling.

## Configuration

### Enable/Disable Tools

Tools are enabled by default. To disable for specific calls:

```python
response = await self.call_openrouter(
    user_message=message,
    system_prompt=prompt,
    use_tools=False  # Disable tools
)
```

### Model Selection

Set via environment variable:
```bash
$env:OPENROUTER_MODEL="gpt-4-turbo"
```

## Commands

### `.llmtest <prompt>`
Test LLM with tool calling

### `.llmstatus`
View configuration and loaded tools

### `.llmtools`
List all tools with full details

## Debugging

Enable debug logging to see tool calls:

```python
import logging
logging.getLogger("red.tanx.llm").setLevel(logging.DEBUG)
```

You'll see logs like:
```
INFO: LLM requested 1 tool call(s)
INFO: Executing tool: calculator with args: {'expression': '250 * 0.15'}
```

## Limitations

- Maximum 5 iterations per request (prevents infinite loops)
- Tools must complete within 30 seconds
- Tool responses limited to reasonable text length
- Some models may not support tool calling

## Security Considerations

- Calculator uses limited `eval()` scope (no access to dangerous functions)
- Never pass user input directly to system commands
- Validate all tool inputs
- Consider rate limiting for expensive tools (API calls)

## Future Tools Ideas

- Database queries
- Image generation
- File search
- Discord server info (member count, roles, etc.)
- Custom game stats lookup
- Translation services
- Code execution (sandboxed)

## Troubleshooting

**Tools not being called?**
1. Check if model supports function calling
2. Ensure question requires tool use
3. Check logs for errors
4. Try GPT-3.5-turbo or newer

**Tool execution fails?**
1. Check tool implementation
2. Verify parameter schema matches
3. Check for exceptions in execute()
4. Test tool individually

**Too many iterations?**
1. Model might be stuck in a loop
2. Check tool responses are clear
3. Simplify tool descriptions
