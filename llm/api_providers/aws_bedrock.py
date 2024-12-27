import json
from typing import Dict, List, Optional, AsyncIterator, Any
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from utils.aws import get_aws_client
from botocore import exceptions as boto_exceptions
from .base import LLMAPIProvider, LLMConfig, Message, LLMResponse
from ..tools.bedrock_tools import tool_registry, BedrockToolRegistry


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

    def _process_response_content(
        self,
        content_blocks: List[Dict],
        content: List[str],
        tool_calls: List[Dict]
    ) -> None:
        """Process content blocks from a response, extracting text and tool use.
        
        Args:
            content_blocks: List of content blocks from the response
            content: List to append text content to
            tool_calls: List to append tool calls to
        """
        for content_block in content_blocks:
            if 'text' in content_block:
                content.append(content_block['text'])
            if 'toolUse' in content_block:
                tool_use = content_block['toolUse']
                tool_calls.append({
                    'name': tool_use['name'],
                    'args': tool_use['input'],
                    'toolUseId': tool_use['toolUseId']
                })
                # Tool will be processed in the next iteration

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

    def _format_messages(
        self,
        messages: List[Message]
    ) -> List[Dict]:
        """Convert messages to Bedrock-specific format"""
        logger.debug(f"Unformatted messages: {messages}")
        formatted_messages = []

        for message in messages:
            content = []
            if message.context:
                # Format all context key-value pairs in a natural way
                context_text = []
                for key, value in message.context.items():
                    # Convert snake_case to spaces and capitalize
                    readable_key = key.replace('_', ' ').capitalize()
                    context_text.append(f"{readable_key}: {value}")
                
                if context_text:
                    # Add formatted context as a bracketed prefix
                    content.append({"text": f"{' | '.join(context_text)}\n"})

            if isinstance(message.content, str):
                content.append({"text": message.content})
            elif isinstance(message.content, dict):
                # Handle Gradio chatbox format with text and files
                if "text" in message.content:
                    content.append({"text": message.content["text"].strip()})
                # Handle multimodal content
                if "files" in message.content and isinstance(message.content["files"], list):
                    for file_path in message.content["files"]:
                        file_type, format = self._get_file_type_and_format(file_path)
                        if file_type:
                            # Read file bytes
                            file_bytes = self._read_file_bytes(file_path)
                            content.append({
                                file_type: {
                                    "format": format,
                                    "source": {
                                        "bytes": file_bytes
                                    }
                                }
                            })
            
            formatted_messages.append({
                "role": message.role,
                "content": content
            })

            logger.debug(f"Formatted messages: {formatted_messages}")        
        
        return formatted_messages

    async def _bedrock_stream(
            self,
            messages,
            system_prompt,
            **kwargs
        ):
        """
        Sends a message to a model and streams the response.
        Args:
            messages (JSON) : The messages to send to the model.
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

            # Track response metadata and tool use state
            response_metadata = {
                'stop_reason': None,
                'usage': None,
                'metrics': None,
                'performance_config': None
            }
       
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
                    # Capture stop reason and additional fields
                    response_metadata['stop_reason'] = chunk['messageStop'].get('stopReason')
                    logger.debug(f"Stream stopped: {response_metadata['stop_reason']}")
                    
                elif 'metadata' in chunk:
                    # Capture complete metadata
                    metadata = chunk['metadata']
                    response_metadata.update({
                        'usage': metadata.get('usage'),
                        'metrics': metadata.get('metrics'),
                        'performance_config': metadata.get('performanceConfig')
                    })
                    # Make metadata available to ChatService
                    message['metadata']= response_metadata
            return message
        
        except ClientError as e:
            self._handle_bedrock_error(e)
            logger.error(f"Streaming error: {str(e)}")


    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Bedrock"""
        try:
            formatted_messages = self._format_messages(messages)
            inference_params = self._prepare_inference_params(**kwargs)
            
            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
                "messages": formatted_messages,
                "inferenceConfig": inference_params
            }

            # Only add toolConfig if we have tools
            if self.tools and len(self.tools) > 0:
                request_params["toolConfig"] = {"tools": self.tools}
            
            # Only include system if prompt is provided and not empty
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            
            # Add additional parameters if specified
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            # Log request before API call
            logger.debug(f"Request params for Bedrock: {request_params}")
            
            response = self.client.converse(
                **request_params,
                **({"additionalModelRequestFields": additional_params} if additional_params else {})
            )
            
            # Log raw response
            logger.debug(f"Raw Bedrock response: {response}")
            
            # Extract content and tool use from output message
            output_message = response.get('output', {}).get('message', {})
            content = []
            tool_calls = []
            tool_results = []
            
            # Process each content block
            for content_block in output_message.get('content', []):
                if 'text' in content_block:
                    content.append(content_block['text'])
                if 'toolUse' in content_block:
                    tool_use = content_block['toolUse']
                    tool_calls.append({
                        'name': tool_use['name'],
                        'args': tool_use['input'],
                        'toolUseId': tool_use['toolUseId']
                    })
                    try:
                        result = tool_registry.execute_tool(tool_use['name'], **tool_use['input'])
                        # Handle tool result
                        tool_result_message = self._handle_tool_result(
                            tool_use, result, is_error=False
                        )
                        # Add result to conversation context
                        formatted_messages.append(tool_result_message)
                        request_params['messages'] = formatted_messages
                        tool_results.append(tool_result_message)
                        
                        # Continue conversation with updated context
                        response = self.client.converse(
                            **request_params,
                            **({"additionalModelRequestFields": additional_params} if additional_params else {})
                        )
                        output_message = response.get('output', {}).get('message', {})
                        self._process_response_content(
                            output_message.get('content', []),
                            content,
                            tool_calls
                        )
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_use['name']}: {str(e)}")
                        # Handle error result
                        error_message = self._handle_tool_result(
                            tool_use, str(e), is_error=True
                        )
                        # Add error to conversation context
                        formatted_messages.append(error_message)
                        request_params['messages'] = formatted_messages
                        tool_results.append(error_message)

                        # Continue conversation with updated context
                        response = self.client.converse(
                            **request_params,
                            **({"additionalModelRequestFields": additional_params} if additional_params else {})
                        )
                        output_message = response.get('output', {}).get('message', {})
                        self._process_response_content(
                            output_message.get('content', []),
                            content,
                            tool_calls
                        )

            response_metadata = {
                'usage': response.get('usage'),
                'metrics': response.get('metrics'),
                'stop_reason': response.get('stopReason'),
                'performance_config': response.get('performanceConfig')
            }

            return LLMResponse(
                content=''.join(content),  # Join text blocks into single string
                tool_calls=tool_calls,
                tool_results=tool_results,
                metadata=response_metadata
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)
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
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Bedrock using converse_stream"""
        # Placeholder, to be implemented in the next task
        pass

    async def multi_turn_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Bedrock using converse_stream"""
        try:
            formatted_messages = self._format_messages(messages)

            # Get initial response
            resp_message = await self._bedrock_stream(
                messages=formatted_messages,
                system_prompt=system_prompt,
                **kwargs
            )

            if resp_message['metadata']['stop_reason'] == "tool_use":
                # Add initial response message to conversation
                resp_message.pop('metadata')
                formatted_messages.append(resp_message)
                # Process response content
                for content_block in resp_message.get('content', []):
                    if 'toolUse' in content_block:
                        tool_use = content_block['toolUse']
                        logger.debug(f"Tool use: {tool_use}")
                        try:
                            # Execute tool
                            tool_result = tool_registry.execute_tool(tool_use['name'], **tool_use['input'])
                            tool_result_message = self._handle_tool_result(
                                tool_use, tool_result, is_error=False
                            )
                                    
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_use['name']}: {str(e)}")
                            tool_result_message = self._handle_tool_result(
                                tool_use, str(e), is_error=True
                            )
                            continue

                # Add tool result to formatted messages
                formatted_messages.append(tool_result_message)
                
                # Get model's response to tool result
                logger.debug(f"Messages after tool result: {formatted_messages}")
                resp_message = await self._bedrock_stream(
                    messages=formatted_messages,
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
