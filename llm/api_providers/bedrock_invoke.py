import json
from typing import Dict, List, Optional, Iterator, AsyncIterator
from botocore.exceptions import ClientError
from core.logger import logger
from core.config import env_config
from botocore import exceptions as boto_exceptions
from utils.aws import get_aws_client
from . import LLMAPIProvider, LLMParameters, LLMMessage, LLMResponse, LLMProviderError


class BedrockInvoke(LLMAPIProvider):
    """Amazon Bedrock LLM provider powered by the invoke model API for single-turn generation."""
    
    def __init__(self, model_id: str, llm_params: LLMParameters, tools=None):
        """Initialize provider with model ID, parameters and tools
        
        Args:
            model_id: Model identifier
            llm_params: LLM inference parameters
            tools: Optional list of tool specifications
        """
        super().__init__(model_id, llm_params, tools)

    def _validate_config(self) -> None:
        """Validate Bedrock-specific configuration"""
        if not self.model_id:
            raise boto_exceptions.ParamValidationError(
                report="Model ID must be specified for Bedrock"
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

    def _handle_bedrock_error(self, error: ClientError):
        """Handle Bedrock-specific errors by raising LLMProviderError
        
        Args:
            error: ClientError exception that occurred during Bedrock API calls
            
        Raises:
            LLMProviderError with error code, user-friendly message, and technical details
        """
        # Extract error details from ClientError
        error_code = error.response.get('Error', {}).get('Code', 'UnknownError')
        error_detail = error.response.get('Error', {}).get('Message', str(error))
        logger.error(f"[BRInvokeProvider] ClientError: {error_code} - {error_detail}")

        # Map error codes to user-friendly messages
        error_messages = {
            'ThrottlingException': "Rate limit exceeded. Please try again later.",
            'TooManyRequestsException': "Too many requests. Please try again later.",
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

            # Invoke model
            logger.debug(f"[BRInvokeProvider] Invoking model {self.model_id}")
            logger.debug(f"--- Request body: {body}")
            resp = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                accept=accept,
                contentType=content_type
            )
            
            # Parse response
            raw_resp = resp.get('body').read()
            # logger.debug(f"[BRInvokeProvider] Raw response: {raw_resp}")
            return json.loads(raw_resp)
            
        except ClientError as e:
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
                modelId=self.model_id,
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
        message: LLMMessage,
        history: Optional[List[LLMMessage]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Multi-turn generation is not supported by invoke API"""
        raise NotImplementedError(
            "Multi-turn generation is not supported by the invoke API. "
            "Use BedrockConverse provider for chat functionality."
        )
