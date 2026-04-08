from redbot.core import commands
import discord
import logging
import os
import json
import base64
import io
import re
from typing import Optional, List, Dict, Any, Tuple
from any_llm import acompletion

log = logging.getLogger("red.tanx.llm")


class LLM(commands.Cog):
    """
    LLM Cog that uses any-llm SDK to respond to:
    1. Bot mentions
    2. User complaints
    3. Questions requiring calculation or search
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Get provider and model from environment variables
        # Format: PROVIDER:MODEL (e.g., "openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022")
        model_string = os.getenv("LLM_MODEL", "openai:gpt-4o-mini")
        if ":" in model_string:
            self.provider, self.model = model_string.split(":", 1)
        else:
            # Default to OpenAI if no provider specified
            self.provider = "openai"
            self.model = model_string
        
        # Check for local LLM configuration
        self.api_base = None
        if os.getenv("LLM_LOCAL") == "1":
            self.provider = "llamacpp"
            self.model = "local"
            self.api_base = os.getenv("LLM_API_BASE")
            if not self.api_base:
                log.warning("LLM_LOCAL is enabled but LLM_API_BASE is not set or empty")
            log.info(f"Local LLM mode enabled with api_base: {self.api_base}")
        
        # Load system prompt from file if specified
        self.system_prompt = None
        prompt_file = os.getenv("LLM_SYSTEM_PROMPT_FILE")
        if prompt_file:
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    self.system_prompt = f.read().strip()
                log.info(f"Loaded system prompt from: {prompt_file}")
            except FileNotFoundError:
                log.error(f"System prompt file not found: {prompt_file}")
            except Exception as e:
                log.error(f"Error loading system prompt file: {e}")
        
        # Initialize tool registry
        from .tools import ToolRegistry
        self.tool_registry = ToolRegistry()
        log.info(f"Loaded {len(self.tool_registry.list_tools())} tools: {', '.join(self.tool_registry.list_tools())}")
        log.info(f"Using LLM provider: {self.provider}, model: {self.model}")
    
    def is_configured(self) -> bool:
        """Check if LLM is properly configured"""
        # any-llm checks for provider-specific API keys automatically
        # We assume it's configured if provider and model are set
        return bool(self.provider and self.model)
    
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
            response = await self.call_llm(
                user_message=message,
                system_prompt=system_prompt,
                # max_tokens=16,
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
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the bot."""
        if self.system_prompt:
            return self.system_prompt
        
        # Default prompt if no file is specified
        return (
            "You are a helpful Discord bot assistant. Respond naturally and helpfully to user messages. "
            "Be friendly, concise, and engaging. Keep responses under 300 words."
        )
    
    def _extract_image_urls(self, message: discord.Message) -> List[str]:
        """Extract image URLs from Discord message attachments."""
        image_urls = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_urls.append(attachment.url)
        return image_urls
    
    def _format_message_for_llm(self, message: discord.Message) -> str:
        """Format Discord message for LLM by replacing user IDs with readable usernames.
        
        Args:
            message: Discord message object
            
        Returns:
            Formatted message content with readable mentions
        """
        content = message.content
        
        # Replace user mentions <@USER_ID> with @username
        for mention in message.mentions:
            user_id_mention = f"<@{mention.id}>"
            user_id_mention_nick = f"<@!{mention.id}>"  # Discord also uses <@!ID> for nicknames
            readable_mention = f"@{mention.name}"
            
            content = content.replace(user_id_mention, readable_mention)
            content = content.replace(user_id_mention_nick, readable_mention)
        
        # Replace role mentions <@&ROLE_ID> with @role_name
        for role in message.role_mentions:
            role_id_mention = f"<@&{role.id}>"
            readable_mention = f"@{role.name}"
            content = content.replace(role_id_mention, readable_mention)
        
        # Replace channel mentions <#CHANNEL_ID> with #channel-name
        if message.guild:
            # Use regex to find all channel mentions
            channel_pattern = re.compile(r'<#(\d+)>')
            for match in channel_pattern.finditer(content):
                channel_id = int(match.group(1))
                channel = message.guild.get_channel(channel_id)
                if channel:
                    content = content.replace(f"<#{channel_id}>", f"#{channel.name}")
        
        return content
    
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
    
    async def call_llm(
        self, 
        user_message: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 32000,
        use_tools: bool = True,
        image_urls: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Call LLM API using any-llm SDK to get response with tool calling support.
        
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
            log.error("LLM not configured.")
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Format user message with images if provided (for vision models)
        if image_urls:
            # # Check if we're using a vision-capable model
            # vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-vision", "claude-3", "gemini"]
            # is_vision_model = any(vm in self.model.lower() for vm in vision_models)
            
            # if not is_vision_model:
            #     log.warning(f"Images provided but model {self.model} may not support vision. Consider using a vision-capable model.")
            
            content = [{"type": "text", "text": user_message}]
            for img_url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url}
                })
            messages.append({"role": "user", "content": content})
            log.info(f"Sending message with {len(image_urls)} image(s) to LLM")
            log.debug(f"Image URLs: {image_urls}")
        else:
            messages.append({"role": "user", "content": user_message})
        
        # Try to get response with tool calling (may require multiple iterations)
        max_iterations = 5
        image_tool_results = []  # Track tool results containing IMAGE_PROCESSED
        
        for iteration in range(max_iterations):
            try:
                # Prepare completion arguments
                completion_args = {
                    "model": self.model,
                    "provider": self.provider,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
                
                # Add api_base if configured (for local LLM)
                if self.api_base:
                    completion_args["api_base"] = self.api_base
                
                # Add tools if enabled
                if use_tools and self.tool_registry:
                    completion_args["tools"] = self.tool_registry.get_tool_schemas()
                    completion_args["tool_choice"] = "auto"
                
                # Log what we're sending (without full base64 images)
                log.debug(f"Iteration {iteration + 1}: Sending {len(messages)} message(s) to {self.provider}:{self.model}")
                if use_tools:
                    log.debug(f"Tool calling enabled with {len(completion_args.get('tools', []))} tool(s)")
                
                # Call async completion directly (no executor needed)
                response = await acompletion(**completion_args)
                
                if not response or not hasattr(response, 'choices') or len(response.choices) == 0:
                    log.error(f"Unexpected API response format")
                    return None
                
                choice = response.choices[0]
                message = choice.message
                
                # Check if LLM wants to call tools
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    log.info(f"LLM requested {len(message.tool_calls)} tool call(s)")
                    
                    # Add assistant message with tool calls to history
                    # Convert message to dict format for next iteration
                    assistant_msg = {"role": "assistant", "content": message.content or ""}
                    if message.tool_calls:
                        assistant_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    messages.append(assistant_msg)
                    
                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        log.info(f"Executing tool: {function_name} with args: {function_args}")
                        
                        # Execute the tool
                        result = self.tool_registry.execute_tool(function_name, function_args)
                        
                        # Log tool result for debugging
                        if "[IMAGE_PROCESSED]" in result:
                            log.info(f"Tool {function_name} returned IMAGE_PROCESSED marker")
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
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": llm_message
                        })
                    
                    # Log the messages being sent back to LLM
                    log.info(f"Sending {len(messages)} messages back to LLM for next iteration")
                    
                    # Continue to next iteration to get final response
                    continue
                
                # No tool calls, return the content
                if hasattr(message, 'content'):
                    content = message.content or ""
                    
                    # If content is empty and we have no tool results, this might be an error
                    if not content and not image_tool_results:
                        log.warning(f"LLM returned empty content with no tool calls on iteration {iteration + 1}")
                        log.warning(f"Full message: {message}")
                        # Return a helpful error message instead of None
                        return "I received your request but wasn't sure how to respond. Could you please rephrase or provide more details?"
                    
                    # Append any IMAGE_PROCESSED blocks from tool results
                    if image_tool_results:
                        log.info(f"Appending {len(image_tool_results)} image tool result(s) to response")
                        for img_result in image_tool_results:
                            content += "\n\n" + img_result
                    
                    # Log if response contains image markers
                    if "[IMAGE_PROCESSED]" in content:
                        log.info("Final response contains [IMAGE_PROCESSED] marker")
                        log.debug(f"Final response preview: {content[:300]}...")
                    
                    return content if content else "I processed your request but don't have a text response."
                else:
                    log.error(f"Message has no content attribute: {message}")
                    return None
                    
            except json.JSONDecodeError as e:
                log.error(f"Error parsing tool arguments: {e}")
                return None
            except Exception as e:
                log.error(f"Unexpected error calling LLM API: {e}", exc_info=True)
                return None
        
        log.warning(f"Reached max iterations ({max_iterations}) in tool calling loop")
        response_text = "I encountered an issue processing your request with the available tools."
        
        # Still append any image results even if we hit max iterations
        if image_tool_results:
            log.info(f"Appending {len(image_tool_results)} image tool result(s) to fallback response")
            for img_result in image_tool_results:
                response_text += "\n\n" + img_result
        
        return response_text
    
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
            # Set Discord context for tools that need it
            self.tool_registry.set_discord_context(message.channel, message)
            
            # Extract image URLs from message if any
            image_urls = self._extract_image_urls(message)
            
            # Prepare user message with readable mentions and sender prefix
            formatted_content = self._format_message_for_llm(message)
            user_message = f"@{message.author.name} said: {formatted_content}"
            
            system_prompt = self._get_system_prompt()
            if image_urls:
                # Format image URLs for the prompt
                urls_list = "\n".join(f"- Image {i+1}: {url}" for i, url in enumerate(image_urls))
                system_prompt += (
                    f"\n\nIMPORTANT: The user has attached {len(image_urls)} image(s). You can see the image(s) in the message. "
                    "If the user wants to edit, process, or transform the image (resize, blur, adjust, etc.), "
                    "you MUST use the 'process_image' tool with the exact image URL and an appropriate ImageMagick command. "
                    f"Do NOT just describe the image - actually process it using the tool if requested.\n\n"
                    f"Available image URLs:\n{urls_list}"
                )
            
            llm_response = await self.call_llm(
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
            await ctx.send("❌ LLM not configured. Please set LLM_MODEL environment variable (format: provider:model).")
            return
        
        async with ctx.typing():
            response = await self.call_llm(
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
        status_msg += f"✅ Provider: {self.provider}\n"
        status_msg += f"✅ Model: {self.model}\n"
        status_msg += f"✅ SDK: any-llm\n"
        
        if self.api_base:
            status_msg += f"✅ API Base: {self.api_base}\n"
        
        prompt_file = os.getenv("LLM_SYSTEM_PROMPT_FILE")
        if prompt_file:
            status_msg += f"✅ System Prompt File: {prompt_file}\n"
        
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
