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


class BedrockInvoke(LLMAPIProvider):
    """Amazon Bedrock LLM provider powered by the invoke model API for single-turn generation."""

    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration"""
        if not self.config.model_id:
            raise boto_exceptions.ParamValidationError(
                report="Model ID must be specified for Bedrock"
            )
        if self.config.api_provider.upper() != 'BEDROCKINVOKE':
            raise boto_exceptions.ParamValidationError(
                report=f"Invalid API provider: {self.config.api_provider}"
            )

    def _initialize_client(self) -> None:
        """Initialize Bedrock client"""
        try:
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
        
        logger.error(f"[BedrockInvoke] {error_message}")
        if error_code in ['ThrottlingException', 'TooManyRequestsException']:
            raise error

    def _invoke_model_sync(
        self,
        request_body: Dict,
        accept: str = "application/json",
        content_type: str = "application/json",
        **kwargs
    ) -> Dict:
        """Send a request to Bedrock's invoke model API
        
        Args:
            request_body: Model-specific request parameters
            accept: Response content type
            content_type: Request content type
            **kwargs: Additional parameters
            
        Returns:
            Dict containing model response
        """
        try:
            # Prepare request body
            body = json.dumps(request_body)
            logger.debug(f"[BedrockInvoke] Request body: {body}")
            
            # Invoke model
            logger.debug(f"[BedrockInvoke] Invoking model {self.config.model_id}")
            resp = self.client.invoke_model(
                modelId=self.config.model_id,
                body=body,
                accept=accept,
                contentType=content_type
            )
            
            # Parse response
            raw_resp = resp.get('body').read()
            # logger.debug(f"[BedrockInvoke] Raw response: {raw_response}")
            parsed_resp = json.loads(raw_resp)
            logger.debug(f"[BedrockInvoke] Parsed response: ('seeds': {parsed_resp['seeds']}, 'finish_reasons': {parsed_resp['finish_reasons']}, 'images': ['Place_holder'])")
            
            return parsed_resp
            
        except ClientError as e:
            logger.error(f"[BedrockInvoke] Client error response: {e.response}")
            self._handle_bedrock_error(e)
    
    def _invoke_model_stream_sync(
        self,
        request_body: Dict,
        accept: str = "application/json",
        content_type: str = "application/json",
        **kwargs
    ) -> Iterator[Dict]:
        """Send a request to Bedrock's invoke model API with streaming
        
        Args:
            request_body: Model-specific request parameters
            accept: Response content type
            content_type: Request content type
            **kwargs: Additional parameters
            
        Yields:
            Dict containing response chunks
        """
        try:
            # Prepare request body
            body = json.dumps(request_body)
            
            # Get streaming response
            response = self.client.invoke_model_with_response_stream(
                modelId=self.config.model_id,
                body=body,
                accept=accept,
                contentType=content_type
            )
            
            # Stream response chunks
            for chunk in response.get('body'):
                # Parse and yield chunk
                yield json.loads(chunk.get('chunk').get('bytes'))
                
        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_content(
        self,
        request_body: Dict,
        accept: str = "application/json",
        content_type: str = "application/json",
        **kwargs
    ) -> LLMResponse:
        """Generate single-turn response
        
        Args:
            request_body: Model-specific request parameters
            accept: Response content type
            content_type: Request content type
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse containing generated content
        """
        try:
            response = self._invoke_model_sync(
                request_body=request_body,
                accept=accept,
                content_type=content_type,
                **kwargs
            )
            
            return LLMResponse(
                content=response,
                metadata={}
            )
            
        except ClientError as e:
            self._handle_bedrock_error(e)

    async def generate_stream(
        self,
        request_body: Dict,
        accept: str = "application/json",
        content_type: str = "application/json",
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response
        
        Args:
            request_body: Model-specific request parameters
            accept: Response content type
            content_type: Request content type
            **kwargs: Additional parameters
            
        Yields:
            Dict containing response chunks
        """
        try:
            # Convert sync stream to async
            for chunk in self._invoke_model_stream_sync(
                request_body=request_body,
                accept=accept,
                content_type=content_type,
                **kwargs
            ):
                yield chunk
                
        except ClientError as e:
            self._handle_bedrock_error(e)

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Multi-turn generation is not supported by invoke API"""
        raise NotImplementedError(
            "Multi-turn generation is not supported by the invoke API. "
            "Use BedrockConverse provider for chat functionality."
        )
