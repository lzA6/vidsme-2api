# /app/providers/base_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi.responses import JSONResponse

class BaseProvider(ABC):
    @abstractmethod
    async def generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_models(self) -> Dict[str, Any]:
        pass
