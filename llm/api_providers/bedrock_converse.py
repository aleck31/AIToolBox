import json
from typing import Dict, List, Optional, Iterator, AsyncIterator, Any
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from botocore import exceptions as boto_exceptions
from utils.aws import get_aws_client
from llm import ResponseMetadata
from .base import LLMAPIProvider, LLMConfig, Message, LLMResponse
from ..tools.bedrock_tools import tool_registry


class BedrockConverse(LLMAPIProvider):
    """Amazon Bedrock LLM provider implemented with Converse API, featuring comprehensive tool support."""
    
    def __init__(self, config: LLMConfig, tools: Optional[List[str]] = None):
        """Initialize provider with config and tools
        
        Args:
            config: LLM configuration
            tools: Optional list of tool names to enable
        """
        super().__init__(config, [])  # Initialize base with empty tools list
        self._initialize_client()
        
        # Initialize tools if provided
        if tools:
            # Get tool specifications from registry
            tool_specs = []
            for tool_name in tools:
                try:
                    tool_spec = tool_registry.get_tool_spec(tool_name)
                    if tool_spec:
                        tool_specs.append(tool_spec)
                        logger.info(f"Loaded tool specification for {tool_name}")
                    else:
                        logger.warning(f"No specification found for tool: {tool_name}")
                except Exception as e:
                    logger.error(f"Error loading tool {tool_name}: {str(e)}")
            
            # Store initialized tool specs
            self.tools = tool_specs
            logger.debug(f"Initialized {len(tool_specs)} tools for Bedrock provider")

    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration"""
        if not self.config.model_id:
            raise boto_exceptions.ParamValidationError(
                report="Model ID must be specified for Bedrock"
            )
        if self.config.api_provider.upper() != 'BEDROCK':
            raise boto_exceptions.ParamValidationError(
                report=f"Invalid API provider: {self.config.api_provider}"
            )

    def _initialize_client(self) -> None:
        try:
            # Get region from env_config
            region = env_config.bedrock_config['default_region']
            if not region:
                raise boto_exceptions.ParamValidationError(
                    report="AWS region must be configured for Bedrock"
                )
                
            self.client = get_aws_client('bedrock-runtime', region_name=region)
        except Exception as e:
            raise boto_exceptions.ClientError(
                error_response={
                    'Error': {
                        'Code': 'InitializationError',
                        'Message': f"Failed to initialize Bedrock client: {str(e)}"
                    }
                },
                operation_name='initialize_client'
            )

    def _handle_bedrock_error(self, error: ClientError) -> None:
        """Handle Bedrock-specific errors"""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        logger.error(f"[BedrockConverse] {error_message}")
        if error_code in ['ThrottlingException', 'TooManyRequestsException']:
            raise error  # Already a boto ClientError with proper error code

    def _prepare_inference_params(self, **kwargs) -> Dict:
        """Prepare model-specific inference parameters"""
        params = {
            "maxTokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "topP": kwargs.get('top_p', self.config.top_p),
            "stopSequences": kwargs.get('stop_sequences', self.config.stop_sequences)
        }
        return {k: v for k, v in params.items() if v is not None}

    def _get_file_type_and_format(self, file_path: str) -> tuple:
        """Determine file type and format from file path"""
        ext = file_path.lower().split('.')[-1]
        
        # Image formats - normalize to Bedrock supported formats
        if ext in ['jpg', 'jpeg']:
            return 'image', 'jpeg'
        elif ext in ['png', 'gif', 'webp']:
            return 'image', ext
        
        # Document formats    
        if ext in ['pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'md']:
            return 'document', ext
            
        # Video formats
        if ext in ['mkv', 'mov', 'mp4', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
            return 'video', ext
            
        return None, None

    def _handle_tool_result(
        self,
        tool_use: Dict,
        result: Dict[str, Any],
        is_error: bool = False
    ) -> Dict:
        """Format a tool result or error as a user message.
        
        Args:
            tool_use: The tool use information
            result: The result or error message
            is_error: Whether this is an error result
            
        Returns:
            Dict: Formatted message for the tool result
        """
        tool_result = {
            'toolUseId': tool_use['toolUseId']
        }
        
        if is_error:
            tool_result['content'] = [{'text': str(result)}]
            tool_result['status'] = 'error'
        else:
            # For successful results, handle different result types
            if isinstance(result, dict) and 'base64_image' in result:
                # Handle image results by adding both image and metadata
                tool_result['content'] = [
                    {
                        'image': {
                            'format': 'png',
                            'source': {
                                'bytes': result['base64_image'].encode()
                            }
                        }
                    },
                    {'json': result.get('metadata', {})}
                ]
            elif isinstance(result, dict):
                tool_result['content'] = [{'json': result}]
            else:
                # Convert non-dict results to string and use text format
                tool_result['content'] = [{'text': str(result)}]
        
        tool_result_message = {
            'role': 'user',
            'content': [{'toolResult': tool_result}]
        }
        logger.debug(f"Formatted tool result: {tool_result_message}")

        return tool_result_message

    def _read_file_bytes(self, file_path: str) -> bytes:
        """Read file bytes from file path"""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise boto_exceptions.ClientError(
                error_response={
                    'Error': {
                        'Code': 'FileReadError',
                        'Message': f"Failed to read file {file_path}: {str(e)}"
                    }
                },
                operation_name='read_file'
            )

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """Convert messages to Bedrock-specified format efficiently
        
        Args:
            messages: List of messages to format
            
        Returns:
            List of Converted messages for Bedrock API
        """
        return [self._convert_message(msg) for msg in messages]

    def _convert_message(self, message: Message) -> Dict:
        """Convert a single message for Bedrock API
        
        Args:
            message: Message to format
            
        Returns:
            Dict in Bedrock message format, containing:
            - role: str ('user' or 'assistant')
            - content: List ({'text':'string'})

        """
        content = []
        
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
                content.append({
                    "text": f"Context Information:\n{' | '.join(context_items)}\n"
                })

        # Handle message content
        if isinstance(message.content, str):
            if message.content.strip():  # Skip empty strings
                content.append({"text": message.content})
        # Handle multimodal content from Gradio chatbox
        elif isinstance(message.content, dict):
            # Add text if present
            if text := message.content.get("text", "").strip():
                content.append({"text": text})
                
            # Add files if present
            if files := message.content.get("files", []):
                for file_path in files:
                    file_type, format = self._get_file_type_and_format(file_path)
                    if file_type:
                        content.append({
                            file_type: {
                                "format": format,
                                "source": {
                                    "bytes": self._read_file_bytes(file_path)
                                }
                            }
                        })
            
        return {"role": message.role, "content": content}

    def _converse_sync(
            self,
            messages: List[Message],
            system_prompt: Optional[str] = None,
            **kwargs
        ) -> Dict:
        """Send a request to Bedrock's converse API and handle the response
        
        Args:
            messages: List of Converted messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Returns:
            Dict containing:
            - role: str ('user' or 'assistant')
            - content: Dict containing LLM-generated content
            - tool_use: Dict containing tool use information
            - metadata: Dict containing usage, metrics and stop reason
            
        Raises:
            ClientError: For Bedrock-specific errors
            Exception: For unexpected errors
        """
        try:
            inference_params = self._prepare_inference_params(**kwargs)
            
            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
                "messages": messages,
                "inferenceConfig": inference_params
            }

            # Add include system if prompt is provided and not empty
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            # Add additional parameters if specified
            if 'top_k' in kwargs:
                request_params["additionalModelRequestFields"] = {'topK': kwargs['top_k']}
            # Add toolConfig if specified
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}

            # Get response stream
            logger.debug(f"Request params for Bedrock: {request_params}")
            response = self.client.converse(**request_params)
            # logger.debug(f"Raw Bedrock response: {response}")

            # Get message and restructure response
            resp_msg = response.get('output', {}).get('message', {})
            if first_block := resp_msg.get('content', [{}])[0]:
                # Currently only considering text generation
                content={'text': first_block.get('text', '')} if 'text' in first_block else {}
                tool_use = first_block.get('toolUse', {})

            return {
                'role': resp_msg.get('role', 'assistant'),
                'content': content,
                'tool_use': tool_use,
                'metadata': {
                    'usage':response.get('usage'),
                    'metrics':response.get('metrics'),
                    'stop_reason':response.get('stopReason')
                }
            }
            
        except ClientError as e:
            self._handle_bedrock_error(e)

    def _converse_stream_sync(
            self,
            messages: List[Message],
            system_prompt: Optional[str] = None,
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
            - role: str ('user' or 'assistant')
            - content: Dict containing LLM-generated content
            - tool_use: Dict containing tool use information
            - metadata: Dict containing usage, metrics and stop reason
        """
        try:
            inference_params = self._prepare_inference_params(**kwargs)
            logger.debug("Streaming messages with model: %s", self.config.model_id)

            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
                "messages": messages,
                "inferenceConfig": inference_params
            }            
            # Add include system if prompt is provided and not empty
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            # Add additional parameters if specified
            if 'top_k' in kwargs:
                request_params["additionalModelRequestFields"] = {'topK': kwargs['top_k']}
            # Add toolConfig if specified
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}

            # Get response stream
            logger.debug(f"Request params for Bedrock: {request_params}")
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
                    elif 'text' in delta:
                        # Yield delta text only, which aligns with the principle of stream processing
                        yield {
                            'role': current_role,
                            'content': {'text': delta['text']},
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
        system_prompt: Optional[str] = None,
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
                    result = await tool_registry.execute_tool(
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
                metadata=response.get('metadata')
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response with tool use handling
        
        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing either:            
            - {"content": dict} for content chunks
            - {"metadata": dict} for response metadata

        Note:
            Handles tool use by maintaining proper conversation flow:
            Send Chat message to [Converse api] get streaming LLM response
                If the tool_use field in response is empty: stream back the response directly
                If the tool_use field in response is not empty:
                    Execute the tool function
                    Update Chat message with LLM response message and tool result 
                    Send message to [Converse api] and stream back the response
        """
        try:
            # Format messages for Bedrock
            llm_messages = self._convert_messages(messages)
            logger.debug(f"Converted messages: {llm_messages}")
            
            # Convert synchronous stream to async
            for chunk in self._converse_stream_sync(
                messages=llm_messages,
                system_prompt=system_prompt,
                **kwargs
            ):
                # Handle tool use if present
                tool_use = chunk.get('tool_use', {})
                if tool_use and isinstance(tool_use.get('input'), dict):
                    logger.debug(f"Tool use: {tool_use}")
                    # Add initial Assistant message to conversation with toolUse
                    llm_messages.append({
                        'role': chunk.get('role'),
                        'content': [{'toolUse': tool_use}]
                    })
                    try:
                        # Execute tool with unpacked input
                        tool_result = await tool_registry.execute_tool(
                            tool_use['name'],
                            **tool_use['input']
                        )
                        message_with_result = self._handle_tool_result(tool_use, tool_result)
                    except Exception as e:
                        logger.error(f"Tool executing error: {str(e)}")
                        message_with_result = self._handle_tool_result(
                            tool_use, str(e), is_error=True
                        )
                        continue
                    # Add tool result to conversation
                    llm_messages.append(message_with_result)
                        
                    # Get follow-on response
                    for response in self._converse_stream_sync(
                        messages=llm_messages,
                        system_prompt=system_prompt,
                        **kwargs
                    ):
                        content = {}
                        # Add text if present
                        if text := response.get('content', {}).get('text'):
                            content['text'] = text
                        # Check for file_path in tool result
                        if 'file_path' in tool_result:
                            content['file_path'] = tool_result['file_path']

                        if content:
                            yield {
                                'content': content,
                                'metadata': response.get('metadata', {})
                            }

                # Stream text content if present
                elif text := chunk.get('content', {}).get('text'):
                    yield {
                        'content': {'text': text},
                        'metadata': chunk.get('metadata', {})
                    }

        except ClientError as e:
            self._handle_bedrock_error(e)

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
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
            - {"metadata": dict} for response metadata
        """
        try:
            # Prepare conversation messages
            messages = []
            if history:
                logger.debug(f"Unconverted history messages: {history}")
                messages.extend(history)   
            # Add current message
            messages.append(message)
            logger.info(f"Processing multi-turn chat with {len(messages)} messages")
            
            # Stream responses using async iterator
            async for chunk in self.generate_stream(
                messages=messages,
                system_prompt=system_prompt,
                **kwargs
            ):
                yield chunk

        except ClientError as e:
            self._handle_bedrock_error(e)
