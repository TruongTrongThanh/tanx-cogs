from redbot.core import commands
import discord
import logging
import aiohttp
import os
import json
import base64
import io
import re
from typing import Optional, List, Dict, Any, Tuple

log = logging.getLogger("red.tanx.llm")


class LLM(commands.Cog):
    """
    LLM Cog that uses OpenRouter API to respond to:
    1. Bot mentions
    2. User complaints
    3. Questions requiring calculation or search
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.4-mini")
        
        # Initialize tool registry
        from .tools import ToolRegistry
        self.tool_registry = ToolRegistry()
        log.info(f"Loaded {len(self.tool_registry.list_tools())} tools: {', '.join(self.tool_registry.list_tools())}")
        
        if not self.api_key:
            log.warning("OPENROUTER_API_KEY environment variable not set.")
    
    def is_configured(self) -> bool:
        """Check if OpenRouter API is properly configured"""
        return bool(self.api_key)
    
    async def _classify_message(self, message: str, classification_type: str) -> bool:
        """
        Use LLM to classify a message.
        
        Args:
            message (str): The message content
            classification_type (str): Type of classification ('complaint' or 'question')
            
        Returns:
            bool: True if message matches the classification
        """
        if not self.is_configured():
            return False
        
        if classification_type == "complaint":
            system_prompt = (
                "You are a message classifier. Analyze if the following message expresses a complaint, "
                "frustration, dissatisfaction, or negative sentiment about something. "
                "Consider expressions of annoyance, problems, issues, things not working, or general negativity. "
                "Respond with ONLY 'YES' if it's a complaint, or 'NO' if it's not. "
                "Do not provide any explanation."
            )
        elif classification_type == "question":
            system_prompt = (
                "You are a message classifier. Analyze if the following message is a question that requires "
                "calculation, factual information, or research to answer. "
                "Questions about facts, math, definitions, how things work, or requests for information count as YES. "
                "Casual chat, greetings, or rhetorical questions count as NO. "
                "Respond with ONLY 'YES' if it needs help, or 'NO' if it doesn't. "
                "Do not provide any explanation."
            )
        else:
            return False
        
        try:
            response = await self.call_openrouter(
                user_message=message,
                system_prompt=system_prompt,
                max_tokens=16,
                use_tools=False  # No tools for classification
            )
            
            if response:
                response_clean = response.strip().upper()
                return response_clean.startswith("YES")
            return False
            
        except Exception as e:
            log.error(f"Error in message classification: {e}")
            return False
    
    def _should_ignore_message(self, message: discord.Message) -> bool:
        """Check if message should be ignored."""
        return (
            message.author == self.bot.user or
            message.author.bot or
            not message.content or
            not message.content.strip() or
            not self.is_configured()
        )
    
    async def _determine_response_type(self, message: discord.Message) -> Optional[str]:
        """
        Determine if and how the bot should respond to a message.
        
        Returns:
            str: Response type ('mention', 'complaint', or 'question'), or None if no response needed
        """
        # Case 1: Bot is mentioned
        if self.bot.user in message.mentions:
            log.info(f"Bot mentioned by {message.author} in {message.channel}")
            return "mention"
        
        # Case 2: Message is a complaint
        if await self.is_complaint(message.content):
            log.info(f"Complaint detected from {message.author} in {message.channel}")
            return "complaint"
        
        # Case 3: Message is a question needing help
        if await self.is_question_needing_help(message.content):
            log.info(f"Question detected from {message.author} in {message.channel}")
            return "question"
        
        return None
    
    def _get_system_prompt(self, response_type: str) -> str:
        """Get appropriate system prompt based on response type."""
        prompts = {
            "mention": (
                "You are a helpful Discord bot assistant. Respond naturally and helpfully to user messages. "
                "Be friendly, concise, and engaging. Keep responses under 300 words."
            ),
            "complaint": (
                "You are a supportive Discord bot. The user seems to be expressing a complaint or frustration. "
                "Acknowledge their feelings empathetically and offer helpful suggestions if appropriate. "
                "Be understanding and constructive. Keep responses under 300 words."
            ),
            "question": (
                "You are a knowledgeable Discord bot assistant. The user has asked a question. "
                "IMPORTANT: Only answer if you have enough information to provide a helpful response. "
                "If you don't have sufficient information, politely say so and explain what information you would need. "
                "Be accurate and concise. Keep responses under 300 words."
            )
        }
        return prompts.get(response_type, "You are a helpful assistant. Respond concisely.")
    
    def _extract_image_urls(self, message: discord.Message) -> List[str]:
        """Extract image URLs from Discord message attachments."""
        image_urls = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_urls.append(attachment.url)
        return image_urls
    
    def _parse_processed_images(self, response: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Parse processed images from tool response.
        
        Returns:
            Tuple of (cleaned_response, list of image_data dicts)
        """
        images = []
        # Pattern to match IMAGE_PROCESSED blocks, possibly within markdown code blocks
        # First try without markdown, then try with markdown wrapping
        pattern = r'\[IMAGE_PROCESSED\]\s*Format:\s*(\w+)\s*Data:\s*([A-Za-z0-9+/=\s]+?)\s*\[/IMAGE_PROCESSED\]'
        
        # Also try to match if wrapped in markdown code blocks
        pattern_with_markdown = r'```[a-z]*\s*\[IMAGE_PROCESSED\]\s*Format:\s*(\w+)\s*Data:\s*([A-Za-z0-9+/=\s]+?)\s*\[/IMAGE_PROCESSED\]\s*```'
        
        matches = re.findall(pattern, response, re.DOTALL)
        
        # If no matches, try the markdown pattern
        if not matches:
            matches = re.findall(pattern_with_markdown, response, re.DOTALL)
            if matches:
                log.info("Found images wrapped in markdown code blocks")
                # Also clean the markdown blocks from response
                response = re.sub(pattern_with_markdown, '[Processed image attached]', response, flags=re.DOTALL)
        
        if matches:
            log.info(f"Found {len(matches)} processed image(s) in response")
        else:
            # Check if marker exists but didn't match
            if "[IMAGE_PROCESSED]" in response:
                log.warning("Response contains [IMAGE_PROCESSED] marker but regex did not match!")
                log.warning(f"Response snippet: {response[:500]}")
        
        for format_type, base64_data in matches:
            # Clean any whitespace from base64 data
            base64_data = base64_data.strip().replace("\n", "").replace("\r", "").replace(" ", "")
            log.debug(f"Parsed image: format={format_type}, data_length={len(base64_data)}")
            images.append({
                'format': format_type,
                'data': base64_data
            })
        
        # Remove the image markers from response
        cleaned_response = re.sub(pattern, '[Processed image attached]', response, flags=re.DOTALL)
        
        return cleaned_response, images
    
    async def _send_response(self, channel: discord.TextChannel, response: str):
        """Send response to channel, handling images and text splitting."""
        # Log the raw response for debugging
        log.info(f"Raw response length: {len(response)}")
        if "[IMAGE_PROCESSED]" in response:
            log.info("Response contains [IMAGE_PROCESSED] marker")
            # Log a snippet around the marker
            marker_pos = response.find("[IMAGE_PROCESSED]")
            snippet = response[max(0, marker_pos):min(len(response), marker_pos + 200)]
            log.info(f"Snippet around marker: {snippet[:200]}...")
        
        # Check for processed images
        cleaned_response, images = self._parse_processed_images(response)
        
        log.info(f"Parsed {len(images)} image(s) from response")
        
        # Send images as attachments
        files = []
        for i, img_data in enumerate(images):
            try:
                log.debug(f"Attempting to decode image {i+1}: format={img_data['format']}, data_len={len(img_data['data'])}")
                image_bytes = base64.b64decode(img_data['data'])
                log.info(f"Successfully decoded image {i+1}: {len(image_bytes)} bytes")
                image_file = discord.File(
                    io.BytesIO(image_bytes),
                    filename=f"processed_image_{i+1}.{img_data['format']}"
                )
                files.append(image_file)
            except Exception as e:
                log.error(f"Error preparing image attachment {i+1}: {e}", exc_info=True)
                cleaned_response += f"\n[Error displaying processed image {i+1}: {str(e)}]"
        
        # Send response with images if any
        if files:
            # Send first message with files
            if len(cleaned_response) > 2000:
                chunks = [cleaned_response[i:i+2000] for i in range(0, len(cleaned_response), 2000)]
                await channel.send(chunks[0], files=files)
                # Send remaining chunks without files
                for chunk in chunks[1:]:
                    await channel.send(chunk)
            else:
                await channel.send(cleaned_response, files=files)
        else:
            # No images, send text only
            if len(cleaned_response) > 2000:
                chunks = [cleaned_response[i:i+2000] for i in range(0, len(cleaned_response), 2000)]
                for chunk in chunks:
                    await channel.send(chunk)
            else:
                await channel.send(cleaned_response)
    
    async def is_complaint(self, message: str) -> bool:
        """
        Detect if a message is a complaint using LLM.
        
        Args:
            message (str): The message content
            
        Returns:
            bool: True if message appears to be a complaint
        """
        return await self._classify_message(message, "complaint")
    
    async def is_question_needing_help(self, message: str) -> bool:
        """
        Detect if a message is a question that needs calculation or searching using LLM.
        
        Args:
            message (str): The message content
            
        Returns:
            bool: True if message appears to be a question needing help
        """
        return await self._classify_message(message, "question")
    
    async def call_openrouter(
        self, 
        user_message: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        use_tools: bool = True,
        image_urls: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Call OpenRouter API to get LLM response with tool calling support.
        
        Args:
            user_message (str): The user's message
            system_prompt (str, optional): System prompt to guide the LLM
            max_tokens (int): Maximum tokens in response
            use_tools (bool): Whether to enable tool calling
            image_urls (List[str], optional): Image URLs to send for vision context
            
        Returns:
            str: LLM response, or None if error occurred
        """
        if not self.is_configured():
            log.error("OpenRouter API not configured.")
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Format user message with images if provided (for vision models)
        if image_urls:
            content = [{"type": "text", "text": user_message}]
            for img_url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url}
                })
            messages.append({"role": "user", "content": content})
            log.info(f"Sending message with {len(image_urls)} image(s) to LLM")
        else:
            messages.append({"role": "user", "content": user_message})
        
        # Try to get response with tool calling (may require multiple iterations)
        max_iterations = 5
        image_tool_results = []  # Track tool results containing IMAGE_PROCESSED
        
        for _ in range(max_iterations):
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/tanx-cogs",
                "X-Title": "Tanx Discord Bot"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            # Add tools if enabled
            if use_tools and self.tool_registry:
                payload["tools"] = self.tool_registry.get_tool_schemas()
                payload["tool_choice"] = "auto"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            log.error(f"OpenRouter API returned status {response.status}: {error_text}")
                            return None
                        
                        data = await response.json()
                        
                        if "choices" not in data or len(data["choices"]) == 0:
                            log.error(f"Unexpected API response format: {data}")
                            return None
                        
                        choice = data["choices"][0]
                        message = choice["message"]
                        
                        # Check if LLM wants to call tools
                        if message.get("tool_calls"):
                            log.info(f"LLM requested {len(message['tool_calls'])} tool call(s)")
                            
                            # Add assistant message with tool calls
                            messages.append(message)
                            
                            # Execute each tool call
                            for tool_call in message["tool_calls"]:
                                function_name = tool_call["function"]["name"]
                                function_args = json.loads(tool_call["function"]["arguments"])
                                
                                log.info(f"Executing tool: {function_name} with args: {function_args}")
                                
                                # Execute the tool
                                result = self.tool_registry.execute_tool(function_name, function_args)
                                
                                # Log tool result for debugging
                                if "[IMAGE_PROCESSED]" in result:
                                    log.info(f"Tool {function_name} returned IMAGE_PROCESSED marker")
                                    # Log first 300 chars of result
                                    log.debug(f"Tool result preview: {result[:300]}...")
                                    # Store this result so we can append it to final response
                                    image_tool_results.append(result)
                                    
                                    # Send simplified message to LLM (don't waste tokens on base64)
                                    llm_message = "Image processed successfully. The processed image will be sent to the user."
                                else:
                                    log.info(f"Tool {function_name} returned: {result[:200]}...")
                                    llm_message = result
                                
                                # Add tool response to messages
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "name": function_name,
                                    "content": llm_message
                                })
                            
                            # Log the messages being sent back to LLM
                            log.info(f"Sending {len(messages)} messages back to LLM for next iteration")
                            
                            # Continue to next iteration to get final response
                            continue
                        
                        #  No tool calls, return the content
                        if message.get("content"):
                            content = message["content"]
                            
                            # Append any IMAGE_PROCESSED blocks from tool results
                            if image_tool_results:
                                log.info(f"Appending {len(image_tool_results)} image tool result(s) to response")
                                for img_result in image_tool_results:
                                    content += "\n\n" + img_result
                            
                            # Log if response contains image markers
                            if "[IMAGE_PROCESSED]" in content:
                                log.info("Final response contains [IMAGE_PROCESSED] marker")
                                log.debug(f"Final response preview: {content[:300]}...")
                            
                            return content
                        else:
                            log.error(f"No content in response: {message}")
                            return None
                            
            except aiohttp.ClientError as e:
                log.error(f"Network error calling OpenRouter API: {e}")
                return None
            except json.JSONDecodeError as e:
                log.error(f"Error parsing tool arguments: {e}")
                return None
            except Exception as e:
                log.error(f"Unexpected error calling OpenRouter API: {e}")
                return None
        
        log.warning(f"Reached max iterations ({max_iterations}) in tool calling loop")
        response = "I encountered an issue processing your request with the available tools."
        
        # Still append any image results even if we hit max iterations
        if image_tool_results:
            log.info(f"Appending {len(image_tool_results)} image tool result(s) to fallback response")
            for img_result in image_tool_results:
                response += "\n\n" + img_result
        
        return response
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen to all messages and respond when appropriate:
        1. When bot is mentioned
        2. When user complains
        3. When user asks something needing calculation/search
        """
        if self._should_ignore_message(message):
            return
        
        # Ignore messages that start with bot prefix (commands)
        prefixes = await self.bot.get_valid_prefixes(message.guild)
        if any(message.content.startswith(prefix) for prefix in prefixes):
            return
        
        response_type = await self._determine_response_type(message)
        if not response_type:
            return
        
        async with message.channel.typing():
            # Extract image URLs from message if any
            image_urls = self._extract_image_urls(message)
            
            # Prepare user message
            user_message = message.content
            
            system_prompt = self._get_system_prompt(response_type)
            if image_urls:
                system_prompt += (
                    "\n\nNote: The user has attached images which you can see. "
                    "If they want to process/edit an image, use the process_image tool with the provided image URL(s)."
                )
            
            llm_response = await self.call_openrouter(
                user_message=user_message,
                system_prompt=system_prompt,
                image_urls=image_urls
            )
            
            if llm_response:
                await self._send_response(message.channel, llm_response)
            else:
                log.error(f"Failed to get LLM response for message from {message.author}")
                await message.channel.send(
                    "❌ Sorry, I'm having trouble processing that right now. Please try again later."
                )
    
    @commands.command()
    @commands.is_owner()
    async def llmtest(self, ctx, *, prompt: str):
        """
        Test the LLM functionality (owner only).
        
        Usage: .llmtest <your prompt>
        """
        if not self.is_configured():
            await ctx.send("❌ OpenRouter API not configured. Please set OPENROUTER_API_KEY environment variable.")
            return
        
        async with ctx.typing():
            response = await self.call_openrouter(
                user_message=prompt,
                system_prompt="You are a helpful assistant. Respond concisely."
            )
            
            if response:
                await self._send_response(ctx.channel, response)
            else:
                await ctx.send("❌ Failed to get response from LLM.")
    
    @commands.command()
    @commands.is_owner()
    async def llmstatus(self, ctx):
        """
        Check LLM cog configuration status (owner only).
        """
        status_msg = "**LLM Cog Status:**\n"
        status_msg += f"✅ API Key: {'Configured' if self.api_key else '❌ Not set'}\n"
        status_msg += f"✅ Model: {self.model}\n"
        status_msg += f"✅ API URL: {self.api_url}\n"
        
        # List available tools
        tools = self.tool_registry.list_tools()
        status_msg += f"\n**Available Tools ({len(tools)}):**\n"
        for tool in tools:
            status_msg += f"  • {tool}\n"
        
        await ctx.send(status_msg)
    
    @commands.command()
    @commands.is_owner()
    async def llmtools(self, ctx):
        """
        List all available tools and their descriptions (owner only).
        """
        tools = self.tool_registry.tools
        
        if not tools:
            await ctx.send("No tools loaded.")
            return
        
        for tool_name, tool in tools.items():
            tool_info = f"**{tool_name}**\n"
            tool_info += f"Description: {tool.description}\n"
            tool_info += f"Parameters: ```json\n{json.dumps(tool.parameters, indent=2)}\n```"
            await ctx.send(tool_info)
