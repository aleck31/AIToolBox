import json
from typing import Dict, List, Optional, AsyncIterator
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from utils.aws import get_aws_client
from . import (
    BaseLLMProvider,
    LLMConfig,
    Message,
    LLMResponse,
    ModelProvider,
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    ModelError
)


class BedrockProvider(BaseLLMProvider):
    """Amazon Bedrock LLM provider implementation"""
    
    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration"""
        if not self.config.model_id:
            raise ConfigurationError("Model ID must be specified for Bedrock")

    def _initialize_client(self) -> None:
        """Initialize Bedrock client"""
        try:
            # Get region from env_config
            region = env_config.bedrock_config['default_region']
            if not region:
                raise ConfigurationError("AWS region must be configured for Bedrock")
                
            self.client = get_aws_client('bedrock-runtime', region_name=region)
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Bedrock client: {str(e)}")

    def _handle_bedrock_error(self, error: ClientError) -> None:
        """Handle Bedrock-specific errors"""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        if error_code in ['ThrottlingException', 'TooManyRequestsException']:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif error_code in ['UnauthorizedException', 'AccessDeniedException']:
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif error_code == 'ValidationException':
            raise ConfigurationError(f"Invalid configuration: {error_message}")
        else:
            raise ModelError(f"Bedrock error: {error_code} - {error_message}")

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
            raise ModelError(f"Failed to read file {file_path}: {str(e)}")

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
            
            system = [{"text": system_prompt}] if system_prompt else None
            
            # Handle additional parameters
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            response = self.client.invoke_model(
                modelId=self.config.model_id,
                body=json.dumps({
                    "messages": formatted_messages,
                    "system": system,
                    "inferenceConfig": inference_params,
                    **({"additionalModelRequestFields": additional_params} if additional_params else {})
                })
            )
            
            response_body = json.loads(response.get('body').read())
            
            return LLMResponse(
                content=response_body.get('content', ''),
                usage=response_body.get('usage', {}),
                metadata={
                    'model_id': self.config.model_id,
                    'finish_reason': response_body.get('finish_reason')
                }
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)
        except Exception as e:
            raise ModelError(f"Unexpected error during generation: {str(e)}")

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
            
            # Prepare system messages if provided
            system = [{"text": system_prompt}] if system_prompt else None
            
            # Handle additional parameters
            additional_params = {}
            if 'top_k' in kwargs:
                additional_params['topK'] = kwargs['top_k']
            
            # Use converse_stream for streaming response
            response = self.client.converse_stream(
                modelId=self.config.model_id,
                messages=formatted_messages,
                system=system,
                inferenceConfig=inference_params,
                **({"additionalModelRequestFields": additional_params} if additional_params else {})
            )
            
            # Process the streaming response
            for event in response['stream']:
                try:
                    if 'contentBlockDelta' in event:
                        # Extract text from content block delta
                        delta = event['contentBlockDelta'].get('delta', {})
                        if 'text' in delta:
                            yield delta['text']
                    elif 'messageStop' in event:
                        # Log any stop reason for debugging
                        stop_reason = event['messageStop'].get('stopReason')
                        if stop_reason:
                            logger.debug(f"Stream stopped: {stop_reason}")
                    elif 'internalServerException' in event:
                        raise ModelError(f"Internal server error: {event['internalServerException']['message']}")
                    elif 'modelStreamErrorException' in event:
                        raise ModelError(f"Model stream error: {event['modelStreamErrorException']['message']}")
                    elif 'validationException' in event:
                        raise ConfigurationError(f"Validation error: {event['validationException']['message']}")
                    elif 'throttlingException' in event:
                        raise RateLimitError(f"Throttling error: {event['throttlingException']['message']}")
                    elif 'serviceUnavailableException' in event:
                        raise ModelError(f"Service unavailable: {event['serviceUnavailableException']['message']}")
                        
                except Exception as e:
                    logger.error(f"Error processing stream event: {str(e)}")
                    continue
                    
        except ClientError as e:
            self._handle_bedrock_error(e)
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            raise ModelError(f"Unexpected error during streaming: {str(e)}")
