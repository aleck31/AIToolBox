import json
from typing import Dict, List, Optional, AsyncIterator, Any
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from botocore import exceptions as boto_exceptions
from utils.aws import get_aws_client
from llm import ResponseMetadata
from .base import LLMAPIProvider, LLMConfig, Message, LLMResponse
from ..tools.bedrock_tools import tool_registry


class BedrockProvider(LLMAPIProvider):
    """Amazon Bedrock LLM provider implementation with tool support"""
    
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
            # For successful results, ensure we have a proper JSON structure
            if isinstance(result, dict):
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
            List of formatted messages for Bedrock API
        """
        logger.debug(f"Unformatted messages: {messages}")
        return [self._convert_message(msg) for msg in messages]

    def _convert_message(self, message: Message) -> Dict:
        """Convert a single message for Bedrock API
        
        Args:
            message: Message to format
            
        Returns:
            Dict in Bedrock message format
        """
        content = []

        # Handle context if present and not None
        context = getattr(message, 'context', None)
        if context and isinstance(context, dict):
            context_text = []
            for key, value in context.items():
                if value is not None:
                    # Convert snake_case to spaces and capitalize
                    readable_key = key.replace('_', ' ').capitalize()
                    context_text.append(f"{readable_key}: {value}")
            if context_text:
                # Add formatted context to contex as a bracketed prefix
                content.append({"text": f"{' | '.join(context_text)}\n"})

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

    async def _bedrock_stream(
            self,
            messages: List[Message],
            system_prompt: Optional[str] = None,
            **kwargs
        ):
        """
        Sends a message to a model and streams the response.
        Args:
            messages: List of formatted messages
            system_prompt: The system prompt send to the model.
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
                additional_params = {'topK': kwargs['top_k']}
                request_params["additionalModelRequestFields"] = additional_params
            # Add toolConfig if if specified
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}

            response = self.client.converse_stream(
                **request_params
            )

            # Initialize response metadata
            metadata = ResponseMetadata()
       
            message = {}
            content = []
            message['content'] = content
            text = ''
            tool_use = {}

            #stream the response into a message.
            for chunk in response['stream']:
                if 'messageStart' in chunk:
                    # Capture role from message start                  
                    message['role'] = chunk['messageStart']['role']
                    
                elif 'contentBlockStart' in chunk:
                    tool = chunk['contentBlockStart']['start']['toolUse']
                    tool_use['toolUseId'] = tool['toolUseId']
                    tool_use['name'] = tool['name']

                elif 'contentBlockDelta' in chunk:
                    delta = chunk['contentBlockDelta']['delta']
                    if 'toolUse' in delta:
                        if 'input' not in tool_use:
                            tool_use['input'] = ''
                        tool_use['input'] += delta['toolUse']['input']
                    elif 'text' in delta:
                        text += delta['text']

                elif 'contentBlockStop' in chunk:
                    if 'input' in tool_use:
                        tool_use['input'] = json.loads(tool_use['input'])
                        content.append({'toolUse': tool_use})
                        tool_use = {}
                    else:
                        content.append({'text': text})
                        text = ''

                elif 'messageStop' in chunk:
                    # Update metadata from stop reason
                    metadata.stop_reason = chunk['messageStop'].get('stopReason')
                    logger.debug(f"Stream stopped: {metadata.stop_reason}")
                    
                elif 'metadata' in chunk:
                    # Update metadata from chunk
                    chunk_metadata = chunk['metadata']
                    metadata.update_from_chunk(chunk_metadata)
                    # Make metadata available to ChatService
                    message['metadata'] = metadata.to_dict()
            return message
        
        except ClientError as e:
            self._handle_bedrock_error(e)
            logger.error(f"Streaming error: {str(e)}")


    async def _bedrock_generate(
            self,
            messages: List[Message],
            system_prompt: Optional[str] = None,
            **kwargs
        ) -> Dict:
        """Send a request to Bedrock's converse API and handle the response
        
        Args:
            messages: List of formatted messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Returns:
            Dict containing the complete response message with metadata
            
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

            # Add toolConfig if tools are available
            if self.tools:
                request_params["toolConfig"] = {"tools": self.tools}
            
            # Add system prompt if provided
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            
            # Add additional parameters if specified
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            logger.debug(f"Request params for Bedrock: {request_params}")
            
            response = self.client.converse(
                **request_params,
                **({"additionalModelRequestFields": additional_params} if additional_params else {})
            )
            
            logger.debug(f"Raw Bedrock response: {response}")

            # Extract message and create metadata
            resp_message = response.get('output', {}).get('message', {})
            metadata = ResponseMetadata(
                usage=response.get('usage'),
                metrics=response.get('metrics'),
                stop_reason=response.get('stopReason'),
                performance_config=response.get('performanceConfig')
            )
            resp_message['metadata'] = metadata.to_dict()
            
            return resp_message
            
        except ClientError as e:
            self._handle_bedrock_error(e)
            raise

    async def generate_content(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Bedrock"""
        try:
            # Formatted messages to be sent to LLM
            llm_messages = self._convert_messages(messages)
            logger.debug(f"Formatted messages: {llm_messages}")
              
            # Get initial response
            resp_message = await self._bedrock_generate(
                messages=llm_messages,
                system_prompt=system_prompt,
                **kwargs
            )

            # Initialize response content and tool use
            content = None
            tool_use = None
            
            # Check if response has content
            if resp_message.get('content'):
                first_block = resp_message['content'][0]
                if 'text' in first_block:
                    content = first_block['text']
                if 'toolUse' in first_block:
                    tool_use = first_block['toolUse']
                    
                    # Handle tool use if present
                    if tool_use and resp_message['metadata'].get('stop_reason') == "tool_use":
                        # Add initial Assistant message to conversation
                        resp_message.pop('metadata')
                        llm_messages.append(resp_message)
                        
                        try:
                            # Execute tool
                            result = tool_registry.execute_tool(
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
                        resp_message = await self._bedrock_generate(
                            messages=llm_messages,
                            system_prompt=system_prompt,
                            **kwargs
                        )
                        
                        # Update content from final response
                        if resp_message.get('content'):
                            content = resp_message['content'][0].get('text', content)

            if content is None:
                raise ValueError("No text content found in response")

            return LLMResponse(
                content=content,
                tool_use=tool_use,
                metadata=resp_message.get('metadata')
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)
            raise
        except Exception as e:
            raise boto_exceptions.ClientError(
                error_response={
                    'Error': {
                        'Code': 'UnexpectedError',
                        'Message': f"Unexpected error during generation: {str(e)}"
                    }
                },
                operation_name='generate'
            )

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response from Bedrock using converse_stream
        
        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing either:
            - {"text": str} for content chunks
            - {"metadata": dict} for response metadata
        """
        # Placeholder, to be implemented in the next task
        pass

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response for multi-turn chat
        
        Args:
            message: Current user message
            history: Optional chat history
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing either:
            - {"text": str} for content chunks
            - {"metadata": dict} for response metadata
            
        Note:
            Handles tool use by maintaining proper conversation flow:
            1. User message -> [Bedrock] -> LLM response (possibly with tool use)
            2. If stop_reason != tool_use: -> Assistant message (reply to user)
            3. If stop_reason == tool_use: -> execute tool -> package result as User message
            4. User message -> [Bedrock] -> LLM response -> Assistant message (reply to user)
        """
        try:
            # Formatted messages to be sent to LLM
            llm_messages = []
            if history:
                llm_messages.extend(self._convert_messages(history))
            llm_messages.append(self._convert_message(message))

            
            logger.debug(f"Formatted messages to _Bedrock: {llm_messages}")

            # Get initial response
            resp_message = await self._bedrock_stream(
                messages=llm_messages,
                system_prompt=system_prompt,
                **kwargs
            )

            if resp_message['metadata']['stop_reason'] == "tool_use":
                # Add initial Assistant message to conversation
                resp_message.pop('metadata')
                llm_messages.append(resp_message)
                # Process response content
                for content_block in resp_message.get('content', []):
                    if 'toolUse' in content_block:
                        tool_use = content_block['toolUse']
                        logger.debug(f"Tool use: {tool_use}")
                        try:
                            # Execute tool
                            result = tool_registry.execute_tool(
                                tool_use['name'],
                                **tool_use['input']
                            )
                            message_with_result = self._handle_tool_result(tool_use, result)
   
                        except Exception as e:
                            logger.error(f"Tool executing error: {str(e)}")
                            # Add error result
                            message_with_result = self._handle_tool_result(tool_use, str(e), is_error=True
                            )
                            continue
                                
                # Add tool result to llm messages
                llm_messages.append(message_with_result)
                logger.debug(f"Formatted messages with result: {llm_messages}")
                
                # Get model's response to tool result
                resp_message = await self._bedrock_stream(
                    messages=llm_messages,
                    system_prompt=system_prompt,
                    **kwargs
                )

            # Stream response content
            metadata = resp_message.pop('metadata', {})
            yield {'metadata': metadata}
            
            for content in resp_message.get('content', []):
                if 'text' in content:
                    yield {'text': content['text']}

        except ClientError as e:
            logger.error(f"Unexpected error during streaming: {str(e)}")
