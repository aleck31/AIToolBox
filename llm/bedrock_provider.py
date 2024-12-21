import json
from typing import Dict, List, Optional, AsyncIterator
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from utils.aws import get_aws_client
from botocore import exceptions as boto_exceptions
from . import LLMAPIProvider, LLMConfig, Message, LLMResponse


class BedrockProvider(LLMAPIProvider):
    """Amazon Bedrock LLM provider implementation"""
    
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
        """Initialize Bedrock client"""
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

    def prepare_messages(
        self,
        messages: List[Message]
    ) -> List[Dict]:
        """Convert messages to Bedrock-specific format"""
        formatted_messages = []
        
        for message in messages:
            if isinstance(message.content, str):
                formatted_messages.append({
                    "role": message.role,
                    "content": [{"text": message.content}]
                })
            else:
                # Handle Gradio chatbox format with text and files
                content = []
                
                # Handle text content
                if "text" in message.content:
                    # If text is a dict with 'text' key (Gradio format), extract just the text
                    text = message.content["text"]["text"] if isinstance(message.content["text"], dict) else message.content["text"]
                    content.append({"text": text})
                
                # Handle files if present
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
                                        # "bytes": base64.b64encode(file_bytes).decode('utf-8')
                                        "bytes": file_bytes
                                    }
                                }
                            })
                
                formatted_messages.append({
                    "role": message.role,
                    "content": content
                })
        
        return formatted_messages

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Bedrock"""
        try:
            formatted_messages = self.prepare_messages(messages)
            inference_params = self._prepare_inference_params(**kwargs)
            
            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
                "messages": formatted_messages,
                "inferenceConfig": inference_params
            }
            
            # Only include system if prompt is provided and not empty
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            
            # Add additional parameters if specified
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            response = self.client.converse(
                **request_params,
                **({"additionalModelRequestFields": additional_params} if additional_params else {})
            )

            response_body = json.loads(response.get('body').read())

            response_metadata={
                'usage': response.get('usage'),
                'metrics': response.get('metrics'),
                'stop_reason': response.get('stopReason'),
                'performance_config': response.get('performanceConfig')
            }

            return LLMResponse(
                content=response_body.get('content', ''),
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
        try:
            formatted_messages = self.prepare_messages(messages)
            inference_params = self._prepare_inference_params(**kwargs)
            
            # Prepare request parameters
            request_params = {
                "modelId": self.config.model_id,
                "messages": formatted_messages,
                "inferenceConfig": inference_params
            }
            
            # Only include system if prompt is provided and not empty
            if system_prompt and system_prompt.strip():
                request_params["system"] = [{"text": system_prompt}]
            
            # Add additional parameters if specified
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            # Use converse_stream for streaming response
            response = self.client.converse_stream(
                **request_params,
                **({"additionalModelRequestFields": additional_params} if additional_params else {})
            )
            
            # Track response metadata
            response_metadata = {
                'stop_reason': None,
                'usage': None,
                'metrics': None,
                'performance_config': None
            }
            
            # Process the streaming response
            for event in response['stream']:
                try:
                    if 'messageStart' in event:
                        # Capture role from message start
                        response_metadata['role'] = event['messageStart'].get('role')
                        
                    elif 'contentBlockDelta' in event:
                        # Extract text from content block delta
                        delta = event['contentBlockDelta'].get('delta', {})
                        if 'text' in delta:
                            yield {'text': delta['text']}
                            
                    elif 'messageStop' in event:
                        # Capture stop reason and additional fields
                        response_metadata['stop_reason'] = event['messageStop'].get('stopReason')
                        logger.debug(f"Stream stopped: {response_metadata['stop_reason']}")
                        
                    elif 'metadata' in event:
                        # Capture complete metadata
                        metadata = event['metadata']
                        response_metadata.update({
                            'usage': metadata.get('usage'),
                            'metrics': metadata.get('metrics'),
                            'performance_config': metadata.get('performanceConfig')
                        })
                        # Make metadata available to ChatService
                        yield {'metadata': response_metadata}
                        
                except Exception as e:
                    logger.error(f"Error processing stream event: {str(e)}")
                    continue
                    
        except ClientError as e:
            self._handle_bedrock_error(e)
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            raise boto_exceptions.ClientError(
                error_response={
                    'Error': {
                        'Code': 'UnexpectedError',
                        'Message': f"Unexpected error during streaming: {str(e)}"
                    }
                },
                operation_name='generate_stream'
            )
