from core.logger import logger
from .chat_service import ChatService
from .gen_service import GenService
from .draw_service import DrawService


class ServiceFactory:
    """Factory for creating service instances"""

    @classmethod
    def create_gen_service(cls, module_name: str) -> GenService:
        """Create general content generation service
        
        Args:
            module_name: Name of the module requesting service
            
        Returns:
            GenService: Configured service instance
        """
        try:
            logger.debug(f"[ServiceFactory] Creating GenService for {module_name}")
            return GenService(module_name=module_name)
        except Exception as e:
            logger.error(f"[ServiceFactory] Failed to create GenService: {str(e)}")
            raise

    @classmethod
    def create_chat_service(cls, module_name: str) -> ChatService:
        """Create chat service with streaming capabilities
        
        Args:
            module_name: Name of the module requesting service
            
        Returns:
            ChatService: Configured service instance
        """
        try:
            logger.debug(f"[ServiceFactory] Creating ChatService for {module_name}")
            return ChatService(module_name=module_name)
        except Exception as e:
            logger.error(f"[ServiceFactory] Failed to create ChatService: {str(e)}")
            raise

    @classmethod
    def create_draw_service(cls, module_name: str = 'draw') -> DrawService:
        """Create image generation service
        
        Args:
            module_name: Name of the module requesting service (defaults to 'draw')
            
        Returns:
            DrawService: Configured service instance
        """
        try:
            logger.debug(f"[ServiceFactory] Creating DrawService for {module_name}")
            return DrawService(module_name=module_name)
        except Exception as e:
            logger.error(f"[ServiceFactory] Failed to create DrawService: {str(e)}")
            raise
