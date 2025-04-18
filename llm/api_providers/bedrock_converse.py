import io
import json
from typing import Dict, List, Optional, Iterator, AsyncIterator, Any
from botocore.exceptions import ClientError, ParamValidationError
from core.logger import logger
from core.config import env_config
from utils.aws import get_aws_client
from utils.file import FileProcessor
from llm.model_manager import model_manager
from llm.tools.tool_registry import br_registry
from llm import ResponseMetadata, LLMParameters, LLMMessage, LLMResponse
from . import LLMAPIProvider, LLMProviderError


# Define the content types to include in the output message
CONTENT_TYPES = ['text', 'image', 'document', 'video']
# Maximum file size for Bedrock API (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024
# Maximum allowed imaage dimension for Bedrock API (8000 pixels)
MAX_IMG_DIMENSION_= 8000

class BedrockConverse(LLMAPIProvider):
    """Amazon Bedrock LLM API provider implemented with Converse API, featuring comprehensive tool support."""
    
    def __init__(self, model_id: str, llm_params: LLMParameters, tools: Optional[List[str]] = None):
        """Initialize provider with configuration and tools
        
        Args:
            model_id: Model identifier
            llm_params: LLM inference parameters
            tools: Optional list of tool names to enable
        """
        super().__init__(model_id, llm_params, [])  # Initialize base with empty tools list

        # Initialize FileProcessor for file handling
        self.file_processor = FileProcessor(max_file_size=MAX_FILE_SIZE)

        # Check if model supports tool use before initializing tools
        model = model_manager.get_model_by_id(model_id)
        supports_tool_use = model and model.capabilities and model.capabilities.tool_use

        # Initialize tools if provided and model supports tool use
        if tools and supports_tool_use:
            # Get tool specifications from registry
            tool_specs = []
            for tool_name in tools:
                try:
                    tool_spec = br_registry.get_tool_spec(tool_name)
                    if tool_spec:
                        tool_specs.append(tool_spec)
                        logger.info(f"[BRConverseProvider] Loaded tool specification for {tool_name}")
                    else:
                        logger.warning(f"[BRConverseProvider] No specification found for tool: {tool_name}")
                except Exception as e:
                    logger.error(f"[BRConverseProvider] Error loading tool {tool_name}: {str(e)}")

            # Store initialized tool specs
            self.tools = tool_specs
            logger.debug(f"[BRConverseProvider] Initialized {len(tool_specs)} tools")
        elif tools and not supports_tool_use:
            logger.warning(f"[BRConverseProvider] Model {model_id} does not support tool use. Tools will not be initialized.")

    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration
        
        Raises:
            ParamValidationError: If configuration is invalid
        """
        logger.debug(f"[BRConverseProvider] Model Configurations: {self.model_id}, {self.llm_params}")
        if not self.model_id:
            raise ParamValidationError(
                report="Model ID must be specified for Bedrock"
            )

    def _initialize_client(self) -> None:
        try:
            # Get region from env_config
            region = env_config.bedrock_config['default_region']
            if not region:
                raise ParamValidationError(
                    report="AWS region must be configured for Bedrock"
                )
                
            self.client = get_aws_client('bedrock-runtime', region_name=region)
        except Exception as e:
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InitializationError',
                        'Message': f"Failed to initialize Bedrock client: {str(e)}"
                    }
                },
                operation_name='initialize_client'
            )

    def _handle_bedrock_error(self, error: ClientError):
        """Handle Bedrock-specific errors by raising exceptions with user-friendly messages
        
        Args:
            error: ClientError exception that occurred during Bedrock API calls
            
        Raises:
            Exception with user-friendly message and original error details
        """
        # Extract error details from ClientError
        error_code = error.response.get('Error', {}).get('Code', 'UnknownError')
        error_detail = error.response.get('Error', {}).get('Message', str(error))
        logger.error(f"[BRConverseProvider] ClientError: {error_code} - {error_detail}")

        # Map error codes to user-friendly messages
        error_messages = {
            'ThrottlingException': "Rate limit exceeded. Please try again later.",
            'ServiceQuotaExceededException': "Service quota has been exceeded. Please try again later.",
            'ValidationException': "There was an issue with the request format. Please try again with different input.",
            'ModelTimeoutException': "The model took too long to respond. Please try with a shorter message.",
            'ModelNotReadyException': "The model is currently initializing. Please try again in a moment.",
            'ModelStreamErrorException': "Error in model stream. Please try again with different parameters.",
            'ModelErrorException': "The model encountered an error processing your request. Please try again with different input."
        }

        # Get the appropriate message or use a default one
        message = error_messages.get(error_code, f"AWS Bedrock error ({error_code}). Please try again.")
        
        # Raise LLMProviderError with error code, user-friendly message, and technical details
        raise LLMProviderError(error_code, message, error_detail)

    def _prepare_inference_params(self, **kwargs) -> tuple[dict, Optional[dict]]:
        """Prepare model-specific inference config and additional model request fields
        
        Args:
            **kwargs: Keyword arguments containing model parameters
            
        Returns:
        - inference_config: Standard inference parameters
        - additional_fields: Model-specific parameters (if applicable)
        """

        # Initialize empty inference parameters
        inference_config = {}
        # Add standard parameters only if they're not None
        if max_tokens := kwargs.get('max_tokens', self.llm_params.max_tokens):
            inference_config["maxTokens"] = max_tokens
        if temperature := kwargs.get('temperature', self.llm_params.temperature):
            inference_config["temperature"] = temperature
        if top_p := kwargs.get('top_p', self.llm_params.top_p):
            inference_config["topP"] = top_p
        if stop_sequences := kwargs.get('stop_sequences', self.llm_params.stop_sequences):
            inference_config["stopSequences"] = stop_sequences

        # Check for thinking config early to avoid redundant operations
        thinking_config = kwargs.get('thinking', self.llm_params.thinking)
        is_claude_thinking = thinking_config and 'claude-3-7' in self.model_id
        
        # Prepare additional model request fields if needed
        additional_fields = {}

        # Handle thinking parameters for Claude reasoning models
        if is_claude_thinking:
            # Apply all Claude thinking parameters at once
            additional_fields['thinking'] = thinking_config
            logger.debug(f"[BRConverseProvider] Applied Claude thinking parameters")

            # Override inference parameters for thinking
            inference_config['temperature'] = 1.0
            if 'topP' in inference_config:
                del inference_config['topP']

            # Ensure maxTokens is sufficient for thinking
            budget_tokens = thinking_config.get('budget_tokens', 2048)
            if inference_config.get('maxTokens', 0) <= budget_tokens:
                inference_config['maxTokens'] = budget_tokens * 2

        # Handle top_k parameter - only if thinking is not enabled for Claude
        else:
            if top_k := kwargs.get('top_k', self.llm_params.top_k):
                # Optimize model-specific logic with direct assignment
                if 'deepseek' in self.model_id:
                    # For deepseek, return None as additional_fields
                    return inference_config, None
                elif 'nova' in self.model_id:
                    additional_fields = {"inferenceConfig": {"topK": top_k}}
                else:
                    additional_fields = {'top_k': top_k}

        return inference_config, additional_fields

    def _handle_tool_result(
        self,
        tool_use: Dict,
        exec_result: Dict[str, Any],
        is_error: bool = False
    ) -> Dict:
        """Format a tool result or error as a user message.
        
        Args:
            tool_use: The tool use information
            exec_result: The result or error message
            is_error: Whether this is an error result
            
        Returns:
            Dict: Formatted message for the tool result
        """
        tool_result = {
            'toolUseId': tool_use['toolUseId']
        }
        logger.debug(f"[BRConverseProvider] handle result for {tool_result}:")
        if is_error:
            tool_result['content'] = [{'text': str(exec_result)}]
            tool_result['status'] = 'error'
            logger.debug(f"--- error content: {tool_result['content']}")
        else:
            # For successful results, handle different result types
            tool_result.setdefault('content', [])  # Initialize content
            if isinstance(exec_result, dict):
                result = exec_result.copy()
                # Handle text content
                if text := result.pop('text', None):
                    tool_result['content'].append({'text': text})
                    logger.debug(f"--- text content: {tool_result['content']}")
                # Handle image content
                if image := result.pop('image', None):
                    # Handle image results by adding both image and metadata
                    buffer = io.BytesIO()
                    image.save(buffer, format='PNG')
                    # Convert IPL.Image to bytes using BytesIO
                    image_bytes = buffer.getvalue()
                    # Add image content and metadata
                    tool_result['content'].extend([
                        {'image': {'format': 'png', 'source': {'bytes': image_bytes}}},
                        {'json': result.pop('metadata', {})}
                    ])
                    logger.debug("--- image content w/metadata added successfully")
                # Handle video content (placeholder for future implementation)
                if video := result.pop('video', None):
                    pass
                # Handle remaining content as JSON
                if result:
                    tool_result['content'].append({'json': result})
            else:
                # Convert non-dict results to string and use text format
                tool_result['content'].append({'text': str(exec_result)})
                logger.debug(f"--- non-dict content: {tool_result['content']}")        
        return {
            'role': 'user',
            'content': [{'toolResult': tool_result}]
        }

    def _convert_message(self, message: LLMMessage) -> Dict:
        """Convert a single message for Bedrock API

        Args:
            message: Message to format
            
        Returns:
            Dict in Bedrock message format, containing:
            - role: str ('user' or 'assistant')
            - content: List ({'text':'string'})
        """
        content_parts = []

        # Handle context if present and not None
        if context := getattr(message, 'context', None):
            if isinstance(context, dict) and context:
                context_items = []
                for key, value in context.items():
                    if value is not None:
                        # Transform key from snake_case to readable format
                        readable_key = key.replace('_', ' ').capitalize()
                        context_items.append(f"{readable_key}: {value}")

                if context_items:
                    # Join all items at once for better string performance
                    content_parts.append({"text": f"Context Information:\n{' | '.join(context_items)}\n"})

        # Handle message content
        content = message.content
        if isinstance(content, str):
            if content := content.strip():  # Skip empty strings
                content_parts.append({"text": content})

        # Handle multimodal content from Gradio chatbox
        elif isinstance(content, dict):
            # Add text if present
            if text := content.get("text", "").strip():
                content_parts.append({"text": text})
                
            # Add files if present
            if files := content.get("files"):
                self._process_files(files, content_parts)
            
        return {"role": message.role, "content": content_parts}
        
    def _process_files(self, files: List[str], content_parts: List[Dict]) -> None:
        """Process files and add them to content parts - extracted for clarity and reuse
        
        Args:
            files: List of file paths
            content_parts: List to append content parts to
        """
        for file_path in files:
            file_type, format = self.file_processor.get_file_type_and_format(file_path)
            
            if file_type == 'image':
                # Handle image files according to Nova schema
                content_parts.append({
                    "image": {
                        "format": format,  # Nova requires explicit format
                        "source": {
                            "bytes": self.file_processor.read_file(file_path, optimize=True)
                        }
                    }
                })
                logger.debug(f"[BRConverseProvider] Added image with format: {format}")
                
            elif file_type == 'document':
                # Handle document files
                content_parts.append({
                    file_type: {
                        "format": format,
                        "source": {
                            "bytes": self.file_processor.read_file(file_path, optimize=True)
                        },
                        "name": self.file_processor.get_file_name(file_path)
                    }
                })

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """Convert messages to Bedrock-specified format efficiently
        
        Args:
            messages: List of messages to format
            
        Returns:
            List of Converted messages for Bedrock API
        """
        return [self._convert_message(msg) for msg in messages]

    def _converse_sync(
            self,
            messages: List[LLMMessage],
            system_prompt: Optional[str] = '',
            **kwargs
        ) -> Dict:
        """Send a request to Bedrock's converse API and handle the response

        Args:
            messages: List of Converted messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference

        Returns:
            Dict containing:
            - {'role': str} ('user' or 'assistant')
            - {'content': dict} for LLM-generated content
            - {'thinking': dict} for thinking process text (for reasoning models)
            - {'tool_use': dict} for tool use information
            - {"metadata": dict} for response metadata, such as usage, metrics and stop reason

        Raises:
            ClientError: For Bedrock-specific errors
            Exception: For unexpected errors
        """
        try:
            inference_config, additional_fields = self._prepare_inference_params(**kwargs)
            
            # Prepare request parameters
            request_params = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": inference_config
            }
            # Add additional parameters if specified
            if additional_fields:
                request_params["additionalModelRequestFields"] = additional_fields

            # Add system parm if system prompt is provided
            if system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]

            # Add toolConfig if specified
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}

            # Get response
            # logger.debug(f"[BRConverseProvider] Full request params: {request_params}")
            response = self.client.converse(**request_params)
            # logger.debug(f"Raw Bedrock response: {response}")

            # Get message and restructure response
            resp_msg = response.get('output', {}).get('message', {})
            content_blocks = resp_msg.get('content', [])

           # Initialize response components
            content = {}
            thinking_block = {}
            tool_use = {}

            # Process all blocks
            for block in content_blocks:
                # Iterate through all keys in the block
                for key, value in block.items():
                    # If key is in content_keys, add to content dict
                    if key in CONTENT_TYPES:
                        content[key] = value
                    # If key is reasoningContent, extract thinking information
                    elif key == 'reasoningContent':
                        if reasoning_text := value.get('reasoningText', {}):
                            thinking_block = {
                                'text': reasoning_text.get('text', ''),
                                'signature': reasoning_text.get('signature', '')
                            }
                    # If key is toolUse, add to tool_use
                    elif key == 'toolUse':
                        tool_use = value

            return {
                'role': resp_msg.get('role', 'assistant'),
                'content': content,
                'thinking': thinking_block,
                'tool_use': tool_use,
                'metadata': {
                    'usage':response.get('usage'),
                    'metrics':response.get('metrics'),
                    'stop_reason':response.get('stopReason')
                }
            }

        except ClientError as e:
            # Handle all exceptions with the common error handler
            self._handle_bedrock_error(e)

    def _converse_stream_sync(
            self,
            messages: List[LLMMessage],
            system_prompt: Optional[str] = '',
            **kwargs
        ) -> Iterator[Dict]:
        """
        Send a request to Bedrock's converse stream API and handle the streaming response
        Args:
            messages: List of Converted messages
            system_prompt: The system prompt send to the model.
            **kwargs: Additional parameters for inference

        Yields:
            Dict containing:
            - {'role': str} ('user' or 'assistant')
            - {'content': dict} for LLM-generated content chunks
            - {'thinking': dict} for thinking process chunks (for reasoning models)
            - {'tool_use': dict} for tool use information
            - {"metadata": dict} for response metadata, such as usage, metrics and stop reason
        """
        try:
            inference_config, additional_fields = self._prepare_inference_params(**kwargs)
            logger.debug(f"[BRConverseProvider] Stream using model: {self.model_id}")
            # Prepare request parameters
            request_params = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": inference_config
            }
            # Add additional parameters if specified
            if additional_fields:
                request_params["additionalModelRequestFields"] = additional_fields

            # Add system parm if system prompt is provided
            if system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]

            # Add toolConfig if specified
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}

            # Initialize response tracking
            metadata = ResponseMetadata()
            current_role = None
            tool_use = {}

            # logger.debug(f"[BRConverseProvider] Full request params: {request_params}")
            # Stream response chunks - handle synchronous EventStream
            for chunk in self.client.converse_stream(**request_params)['stream']:
                if 'messageStart' in chunk:
                    current_role = chunk['messageStart']['role']
                    # Yield initial message structure with role
                    yield {
                        'role': current_role,
                        'content': {},
                        'tool_use': {},
                        'metadata': {}
                    }
                    
                elif 'contentBlockStart' in chunk:
                    if 'toolUse' in chunk['contentBlockStart'].get('start', {}):
                        tool = chunk['contentBlockStart']['start']['toolUse']
                        tool_use = {
                            'toolUseId': tool['toolUseId'],
                            'name': tool['name'],
                            'input': ''
                        }
                        # Yield tool use information if the 'toolUse' exists
                        yield {
                            'role': current_role,
                            'content': {},
                            'tool_use': tool_use,
                            'metadata': {}
                        }

                elif 'contentBlockDelta' in chunk:
                    delta = chunk['contentBlockDelta']['delta']
                    if 'toolUse' in delta:
                        tool_use['input'] += delta['toolUse'].get('input', '')
                        yield {
                            'role': current_role,
                            'content': {},
                            'tool_use': tool_use,
                            'metadata': {}
                        }
                    elif 'text' in delta:
                        content = {'text': delta['text']} if 'text' in delta else {}
                        yield {
                            'role': current_role,
                            'content': content,
                            'tool_use': {},
                            'metadata': {}
                        }
                    elif 'reasoningContent' in delta:
                        thinking_block = {
                            # For Claude 3.7, Deepseek r1, the thinking text is in reasoningContent.text
                            'text': delta['reasoningContent'].get('text', ''),
                            'signature': delta['reasoningContent'].get('signature', '')
                        }
                        yield {
                            'role': current_role,
                            'thinking': thinking_block,
                            'tool_use': {},
                            'metadata': {}
                        }

                elif 'contentBlockStop' in chunk:
                    if tool_use:
                        try:
                            # Parse accumulated tool input as JSON
                            tool_use['input'] = json.loads(tool_use['input'])
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse tool input as JSON")
                        # Final yield of complete tool use in JSON format
                        yield {
                            'role': current_role,
                            'content': {},
                            'tool_use': tool_use,
                            'metadata': {}
                        }
                        tool_use = {}

                elif 'messageStop' in chunk:
                    # Update metadata from both messageStop and metadata chunks
                    metadata.update_from_chunk(chunk.get('metadata', {}))
                    metadata.stop_reason = chunk['messageStop'].get('stopReason')
                    
                    # Yield final message with complete metadata
                    yield {
                        'role': current_role,
                        'content': {},
                        'tool_use': {},
                        'metadata': {
                            'stop_reason': metadata.stop_reason,
                            'usage': metadata.usage,
                            'metrics': metadata.metrics
                        }
                    }

        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_content(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = '',
        **kwargs
    ) -> LLMResponse:
        """Generate response with tool use handling
        
        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Return:
            Dict containing either:
            - {"content": dict} for content such as text, images, and videos.
            - {"metadata": dict} for response metadata        
        
        """
        try:
            # Converted messages to be sent to LLM
            llm_messages = self._convert_messages(messages)
            logger.debug(f"Converted messages: {llm_messages}")
              
            # Get initial response
            response = self._converse_sync(
                messages=llm_messages,
                system_prompt=system_prompt,
                **kwargs
            )

            # Get response content and tool use from response
            tool_use = response.pop('tool_use')
            
            # Handle tool use if present
            if tool_use:
                logger.debug(f"Tool use: {tool_use}")
                # Add initial Assistant message to conversation with toolUse
                llm_messages.append({
                    'role': response.get('role'),
                    'content': [{'toolUse': tool_use}]
                })
  
                try:
                    # Execute tool
                    result = await br_registry.execute_tool(
                        tool_use['name'],
                        **tool_use['input']
                    )
                    message_with_result = self._handle_tool_result(tool_use, result)
                except Exception as e:
                    logger.error(f"Tool executing error: {str(e)}")
                    message_with_result = self._handle_tool_result(
                        tool_use, str(e), is_error=True
                    )
                # Add tool result and get final response
                llm_messages.append(message_with_result)
                logger.debug(f"Messages with tool result: {llm_messages}")
                response = self._converse_sync(
                    messages=llm_messages,
                    system_prompt=system_prompt,
                    **kwargs
                )
                
                # Update content from final response
                if response.get('content'):
                    resp_content = response['content']

            # Update content if present
            elif response.get('content'):
                resp_content = response['content']
            else:
                resp_content = {'text': ''}
                logger.warning("[BRConverseProvider] No content found in response, return empty text")

            return LLMResponse(
                content=resp_content,
                thinking=response.get('thinking', ''),
                metadata=response.get('metadata')
            )

        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = '',
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response with multi-turn tool use handling

        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference

        Yields:
            Dict containing either:            
            - {"content": dict} for content chunks (text, file_path)
            - {'thinking': str} for thinking process chunks (for reasoning models)
            - {"metadata": dict} for response metadata

        Note:
            Supports multi-turn tool use by:
            1. Streaming initial LLM response
            2. If tool use detected:
                - Execute tool and add result to conversation
                - Continue conversation with tool result
                - Repeat if another tool use is detected
            3. Stream final response with any generated content
        """
        try:
            # Format messages for Bedrock
            llm_messages = self._convert_messages(messages)
            # logger.debug(f"[BRConverseProvider] Initial messages for Bedrock: {llm_messages}")  #Todo: Remove 'content' field from request_params to prevent excessively long log

            # Check if thinking is enabled
            thinking_enabled = False
            if thinking_config := kwargs.get('thinking', self.llm_params.thinking):
                if thinking_config.get('type', '') == 'enabled':
                    thinking_enabled = True

            # Use StringIO for efficient string accumulation
            from io import StringIO
            
            while True:  # Continue until no more tool uses
                has_tool_use = False
                thinking_buffer = StringIO()  # track thinking content that comes before a tool use

                # Convert synchronous stream to async
                for chunk in self._converse_stream_sync(
                    messages=llm_messages,
                    system_prompt=system_prompt,
                    **kwargs
                ):
                    # Stream content and thinking immediately if present
                    content = chunk.get('content', {})
                    thinking_block = chunk.get('thinking', {})

                    # Only update signature if it's not empty
                    if signature := thinking_block.get('signature', ''):
                        reasoning_signature = signature

                    # Process thinking text if present
                    if thinking_text := thinking_block.get('text', ''):
                        thinking_buffer.write(thinking_text)  # Accumulate thinking content

                    # Yield content immediately to client
                    if content or thinking_text:
                        yield {
                            'content': content,
                            'thinking': thinking_text,
                            'metadata': chunk.get('metadata', {})
                        }

                    # Handle tool use if present
                    tool_use = chunk.get('tool_use', {})
                    if tool_use and isinstance(tool_use.get('input'), dict):
                        has_tool_use = True
                        logger.debug(f"[BRConverseProvider] Tool use detected: {tool_use}")

                        # Add LLM message with thinking (if enabled) and toolUse
                        content_blocks = []

                        # Add thinking block first if thinking is enabled and we have accumulated thinking
                        accumulated_thinking = thinking_buffer.getvalue()
                        if thinking_enabled and accumulated_thinking:
                            content_blocks.append({
                                'reasoningContent': {
                                    'reasoningText': {
                                        'text': accumulated_thinking,
                                        'signature': reasoning_signature
                                    }
                                }
                            })

                        # Add tool use block
                        content_blocks.append({'toolUse': tool_use})
                        
                        assistant_message = {
                            'role': chunk.get('role'),
                            'content': content_blocks
                        }

                        llm_messages.append(assistant_message)
                        # logger.debug(f"[BRConverseProvider] Added Assistant message: {assistant_message}")
                        
                        try:
                            # Execute tool with unpacked input
                            execute_result = await br_registry.execute_tool(
                                tool_use['name'],
                                **tool_use['input']
                            )
                            message_with_result = self._handle_tool_result(tool_use, execute_result)
                            
                            # Stream file_path immediately if present
                            if isinstance(execute_result, dict):
                                if file_path := execute_result.get('metadata', {}).get('file_path'):
                                    yield {'content': {'file_path': file_path}}

                        except Exception as e:
                            logger.error(f"[BRConverseProvider] Tool executing error: {str(e)}")
                            message_with_result = self._handle_tool_result(
                                tool_use, str(e), is_error=True
                            )

                        # Add tool execute result to conversation
                        llm_messages.append(message_with_result)
                        # logger.debug(f"[BRConverseProvider] Added User message w/tool result: {message_with_result}")
                        break  # Break inner loop to get next response with tool result

                # Clean up resources
                thinking_buffer.close()
                
                # Break outer loop if no tool use in this turn
                if not has_tool_use:
                    logger.debug("[BRConverseProvider] No more tool uses detected, ending loop")
                    break

        except ClientError as e:
            self._handle_bedrock_error(e)

    async def multi_turn_generate(
        self,
        message: LLMMessage,
        history: Optional[List[LLMMessage]] = None,
        system_prompt: Optional[str] = '',
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response for multi-turn chat with tool use handling

        Args:
            message: Current user message
            history: Optional chat history
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference

        Yields:
            Dict containing either:
            - {"content": dict} for content chunks
            - {'thinking': str} for thinking process chunks (for reasoning models)
            - {"metadata": dict} for response metadata
        """
        try:
            # Prepare conversation messages
            messages = []
            if history:
                messages.extend(history)   
            # Add current message
            messages.append(message)
            logger.info(f"[BRConverseProvider] Processing multi-turn chat with {len(messages)} messages")
            
            # Stream responses using async iterator
            async for chunk in self.generate_stream(
                messages=messages,
                system_prompt=system_prompt,
                **kwargs
            ):
                yield chunk

        except ClientError as e:
            self._handle_bedrock_error(e)
