"""Service for AI image generation"""
import io
import json
import base64
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from fastapi import HTTPException
from botocore.exceptions import ClientError
from core.logger import logger
from core.session import Session, SessionStore
from core.module_config import module_config
from llm.model_manager import model_manager
from llm.api_providers.base import LLMConfig, Message, LLMAPIProvider


class DrawService:
    """Service for AI image generation using Text-to-Image models"""

    def __init__(
        self,
        llm_config: LLMConfig
    ):
        """Initialize draw service with model configuration
        
        Args:
            llm_config: LLM configuration containing model ID and parameters
        """
        self.session_store = SessionStore.get_instance()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        
        # Validate model exists
        model = model_manager.get_model_by_id(llm_config.model_id)
        if not model:
            raise ValueError(f"Model not found: {llm_config.model_id}")
        
        self.default_llm_config = llm_config

    def _get_llm_provider(self, model_id: str) -> LLMAPIProvider:
        """Get or create LLM API provider for given model"""
        if model_id in self._llm_providers:
            return self._llm_providers[model_id]
            
        model = model_manager.get_model_by_id(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")
            
        # Create provider with model configuration
        config = LLMConfig(
            api_provider=model.api_provider,
            model_id=model_id,
            max_tokens=self.default_llm_config.max_tokens,
            temperature=self.default_llm_config.temperature,
            top_p=self.default_llm_config.top_p,
            stop_sequences=self.default_llm_config.stop_sequences
        )
        
        # No tools needed for image generation
        provider = LLMAPIProvider.create(config, [])
        self._llm_providers[model_id] = provider
        return provider

    async def get_or_create_session(
        self,
        user_name: str,
        module_name: str = "draw",
        session_name: Optional[str] = None
    ) -> Session:
        """Get existing active session or Create new session for stateful generation"""
        try:
            active_sessions = await self.session_store.list_sessions(
                user_name=user_name,
                module_name=module_name
            )

            if active_sessions:
                session = active_sessions[0]
                logger.debug(
                    f"Found existing {module_name} session {session.session_id} "
                    f"for user {user_name} (created: {session.created_time})"
                )
                return session

            session_name = session_name or f"{module_name.title()} Session"
            session = await self.session_store.create_session(
                user_name=user_name,
                module_name=module_name,
                session_name=session_name
            )

            logger.debug(
                f"Created new {module_name} session {session.session_id} "
                f"for user {user_name} (created: {session.created_time})"
            )
            
            return session
        except HTTPException as e:
            logger.error(f"Error in [get_or_create_session]: {str(e)}")
            raise e

    async def gen_image(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        style: str = "",
        steps: int = 50,
        option_params: Optional[Dict[str, Any]] = None
    ) -> Image.Image:
        """Generate image using the configured model with synchronous API
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to generate
            style: Style preset for generation
            steps: Number of diffusion steps
            seed: Random seed for reproducibility
            option_params: Optional parameters for generation
            
        Returns:
            Image.Image: Generated image
        """
        try:
            # Always use current default model from module settings
            model_id = self.default_llm_config.model_id
            llm = self._get_llm_provider(model_id)

            # Get model parameters from module config
            params = module_config.get_inference_params('draw') or {}

            # Prepare request body based on model type
            if "stable-diffusion-xl" in model_id:
                # Handle negative prompts as a single entry if present
                text_prompts = [{"text": prompt, "weight": 1}]
                if negative_prompt:
                    text_prompts.append({"text": negative_prompt, "weight": -1})
                
                # Ensure correct parameter types for SDXL
                request_body = {
                    "text_prompts": text_prompts,
                    "seed": seed if seed is not None else 0,
                    "steps": steps,
                    # SDXL specific parameters
                    'style_preset': style or 'enhance',
                    "height": int(params.get("height", 1152)),
                    "width": int(params.get("width", 896)),
                    "cfg_scale": params.get("cfg_scale", 7.0)
                }
            else:
                request_body = {
                    "prompt": f"{prompt}, style preset: {style or 'enhance'}",
                    "negative_prompt": negative_prompt,
                    "seed": seed if seed is not None else 0,
                    # SD3 specific parameters
                    "mode": params.get("mode", "text-to-image"),
                    "aspect_ratio": params.get("aspect_ratio", "2:3")
                }

            # Update with any additional parameters
            if option_params:
                request_body.update(option_params)

            # Generate image
            try:
                logger.info(f"Invoking model [{model_id}] for image generation")
                
                # Use synchronous generation
                logger.debug(f"[DrawService] Sending request body: {json.dumps(request_body, indent=2)}")
                response = await llm.generate_content(
                    request_body,
                    accept="application/json",
                    content_type="application/json"
                )
                
                if not response.content:
                    raise ValueError("No response received from model")
                    
                response_body = response.content
                logger.debug(f"[DrawService] Received response: {json.dumps(response_body, indent=2)}")
                
                # Log generation metrics
                if 'seeds' in response_body:
                    logger.info(f"Seeds: {response_body['seeds']}")
                if 'finish_reasons' in response_body:
                    logger.info(f"Finish reason: {response_body['finish_reasons']}")

                # Extract image from response based on model type
                if "stable-diffusion-xl" in model_id:
                    base64_img = response_body["artifacts"][0]["base64"]
                else:
                    base64_img = response_body["images"][0]
                    
                image = Image.open(io.BytesIO(base64.b64decode(base64_img)))
                return image

            except ClientError as e:
                logger.error(
                    f"Model invocation failed: {e.response['Error']['Code']} - "
                    f"{e.response['Error']['Message']}"
                )
                raise

        except Exception as e:
            logger.error(f"Error in [gen_image]: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {str(e)}"
            )
