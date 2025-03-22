import io
import json
from typing import Dict, List, Optional, Iterator, AsyncIterator, Any
from botocore.exceptions import ClientError, ParamValidationError
from core.logger import logger
from core.config import env_config
from utils.aws import get_aws_client
from utils.file import FileProcessor
from llm import ResponseMetadata
from llm.tools.tool_registry import br_registry
from . import LLMAPIProvider, LLMConfig, Message, LLMResponse, LLMProviderError


# Maximum file size for Bedrock API (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024
# Maximum allowed imaage dimension for Bedrock API (8000 pixels)
MAX_IMG_DIMENSION_= 8000

class BedrockConverse(LLMAPIProvider):
    """Amazon Bedrock LLM API provider implemented with Converse API, featuring comprehensive tool support."""
    
    def __init__(self, config: LLMConfig, tools: Optional[List[str]] = None):
        """Initialize provider with config and tools
        
        Args:
            config: LLM configuration
            tools: Optional list of tool names to enable
        """
        super().__init__(config, [])  # Initialize base with empty tools list
        self._initialize_client()
        
        # Initialize FileProcessor for file handling
        self.file_processor = FileProcessor(max_file_size=MAX_FILE_SIZE)
        
        # Initialize tools if provided
        if tools:
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

    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration
        
        Raises:
            ParamValidationError: If configuration is invalid
        """
        logger.debug(f"[BRConverseProvider] Model Configurations: {self.config}")
        if not self.config.model_id:
            raise ParamValidationError(
                report="Model ID must be specified for Bedrock"
            )
        if self.config.api_provider.upper() != 'BEDROCK':
            raise ParamValidationError(
                report=f"Invalid API provider: {self.config.api_provider}"
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
        # Prepare standard inference parameters
        inference_config = {
            "maxTokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "topP": kwargs.get('top_p', self.config.top_p),
            "stopSequences": kwargs.get('stop_sequences', self.config.stop_sequences)
        }
        inference_config = {k: v for k, v in inference_config.items() if v is not None}

        # Prepare additional model request fields if needed
        additional_fields = None
        if top_k := kwargs.get('top_k', self.config.top_k):
            if isinstance(top_k, (int, float)):  # Validate top_k
                if 'deepseek' in self.config.model_id:
                    additional_fields = None
                elif 'nova' in self.config.model_id:
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

    def _convert_message(self, message: Message) -> Dict:
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
        context = getattr(message, 'context', None)
        if context and isinstance(context, dict):
            context_items = []
            for key, value in context.items():
                if value is not None:
                    # Convert snake_case to spaces and capitalize
                    readable_key = key.replace('_', ' ').capitalize()
                    context_items.append(f"{readable_key}: {value}")
            if context_items:
                # Add formatted context with clear labeling
                content_parts.append({
                    "text": f"Context Information:\n{' | '.join(context_items)}\n"
                })

        # Handle message content
        if isinstance(message.content, str):
            if message.content.strip():  # Skip empty strings
                content_parts.append({"text": message.content})
        # Handle multimodal content from Gradio chatbox
        elif isinstance(message.content, dict):
            # Add text if present
            if text := message.content.get("text", "").strip():
                content_parts.append({"text": text})
            # Add files if present
            if files := message.content.get("files", []):
                for file_path in files:
                    file_type, format = self.file_processor.get_file_type_and_format(file_path)
                    if file_type:
                        content_block = {
                            "format": format,
                            "source": {
                                "bytes": self.file_processor.read_file(file_path, optimize=True)
                            }
                        }
                        # Add name parameter only for document type
                        if file_type == 'document':
                            content_block["name"] = self.file_processor.get_file_name(file_path)
                        content_parts.append({
                            file_type: content_block
                        })
            
        return {"role": message.role, "content": content_parts}

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert messages to Bedrock-specified format efficiently
        
        Args:
            messages: List of messages to format
            
        Returns:
            List of Converted messages for Bedrock API
        """
        return [self._convert_message(msg) for msg in messages]

    def _converse_sync(
            self,
            messages: List[Message],
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
            - {'thinking': str} for thinking process text (for reasoning models)
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
                "modelId": self.config.model_id,
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
            # logger.debug(f"[BRConverseProvider] Request params: {request_params}")
            response = self.client.converse(**request_params)
            # logger.debug(f"Raw Bedrock response: {response}")

            # Get message and restructure response
            resp_msg = response.get('output', {}).get('message', {})
            content_blocks = resp_msg.get('content', [])

            # Process each content block
            for block in content_blocks:
                content = {'text': block['text']} if 'text' in block else {}
                thinking = block.get('reasoningContent', {}).get('reasoningText', '')
                tool_use = block.get('toolUse', {})

            return {
                'role': resp_msg.get('role', 'assistant'),
                'content': content,
                'thinking': thinking,
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
            messages: List[Message],
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
            - {'thinking': str} for thinking process chunks (for reasoning models)
            - {'tool_use': dict} for tool use information
            - {"metadata": dict} for response metadata, such as usage, metrics and stop reason
        """
        try:
            inference_config, additional_fields = self._prepare_inference_params(**kwargs)
            logger.debug(f"[BRConverseProvider] Stream using model: {self.config.model_id}")
            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
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

            # Get response stream
            # logger.debug(f"[BRConverseProvider] Request params: {request_params}")  #Todo: Remove 'messages' field from request_params to prevent excessively long log
            response = self.client.converse_stream(**request_params)
            
            # Initialize response tracking
            metadata = ResponseMetadata()
            current_role = None
            tool_use = {}

            # Stream response chunks - handle synchronous EventStream
            for chunk in response['stream']:
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
                    elif 'text' in delta or 'reasoningContent' in delta:
                        content = {'text': delta['text']} if 'text' in delta else {}
                        thinking = delta.get('reasoningContent', {}).get('text', '')
                        yield {
                            'role': current_role,
                            'content': content,
                            'thinking': thinking,
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
        messages: List[Message],
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
            elif 'text' in response.get('content', {}):
                resp_content = response['content']

            else:
                raise ValueError("No text content found in response")

            return LLMResponse(
                content=resp_content,
                thinking=response.get('thinking', ''),
                metadata=response.get('metadata')
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_stream(
        self,
        messages: List[Message],
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

            while True:  # Continue until no more tool uses
                has_tool_use = False
                # accumulated_text = ""   # track and preserve the text content that comes before a tool use

                # Convert synchronous stream to async
                for chunk in self._converse_stream_sync(
                    messages=llm_messages,
                    system_prompt=system_prompt,
                    **kwargs
                ):
                    # Stream content(only text) and thinking immediately if present
                    content = chunk.get('content', {})
                    thinking = chunk.get('thinking', '')
                    if content or thinking:
                        yield {
                            'content': content,
                            'thinking': thinking,
                            'metadata': chunk.get('metadata', {})
                        }

                    # Handle tool use if present
                    tool_use = chunk.get('tool_use', {})
                    if tool_use and isinstance(tool_use.get('input'), dict):
                        has_tool_use = True
                        logger.debug(f"[BRConverseProvider] Tool use detected: {tool_use}")
                        
                        # Add LLM message with toolUse
                        assistant_message = {
                            'role': chunk.get('role'),
                            'content': [{'toolUse': tool_use}]  # not including preceding text content
                        }
                        llm_messages.append(assistant_message)
                        logger.debug(f"[BRConverseProvider] Added LLM message: {assistant_message}")
                        
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
                        logger.debug(f"[BRConverseProvider] Added User message w/tool result: <content omitted>")
                        break  # Break inner loop to get next response with tool result

                # Break outer loop if no tool use in this turn
                if not has_tool_use:
                    logger.debug("[BRConverseProvider] No more tool uses detected, ending loop")
                    break

        except ClientError as e:
            self._handle_bedrock_error(e)

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = None,
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
