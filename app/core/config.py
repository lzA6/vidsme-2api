# /app/core/config.py
import uuid
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "vidsme-2api"
    APP_VERSION: str = "2.0.0"
    DESCRIPTION: str = "一个将 chatsweetie.ai (vidsme) 图像生成功能转换为兼容 OpenAI 格式 API 的高性能代理。"

    # --- 核心安全与部署配置 ---
    API_MASTER_KEY: Optional[str] = "1"
    NGINX_PORT: int = 8088
    
    # --- 用户标识 ---
    # 从 .env 文件读取。如果为空，则在下面自动生成。
    USER_ID: Optional[str] = None

    # --- 上游 API 配置 (可被 .env 文件覆盖) ---
    # 这些是当前的默认值，如果 .env 文件中定义了同名变量，将优先使用 .env 中的值。
    UPSTREAM_APP_ID: str = "chatsweetie"
    UPSTREAM_STATIC_SALT: str = "NHGNy5YFz7HeFb"
    UPSTREAM_PUBLIC_KEY: str = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDa2oPxMZe71V4dw2r8rHWt59gH
W5INRmlhepe6GUanrHykqKdlIB4kcJiu8dHC/FJeppOXVoKz82pvwZCmSUrF/1yr
rnmUDjqUefDu8myjhcbio6CnG5TtQfwN2pz3g6yHkLgp8cFfyPSWwyOCMMMsTU9s
snOjvdDb4wiZI8x3UwIDAQAB
-----END PUBLIC KEY-----"""
    IMAGE_BASE_URL: str = "https://art-global.yimeta.ai/"

    # --- 任务轮询配置 ---
    API_REQUEST_TIMEOUT: int = 180
    POLLING_INTERVAL: int = 3 # 秒
    POLLING_TIMEOUT: int = 240 # 秒

    # --- 模型配置 ---
    DEFAULT_MODEL: str = "anime"
    KNOWN_MODELS: List[str] = ["anime", "realistic", "hentai", "hassaku"]

    @model_validator(mode='after')
    def validate_settings(self) -> 'Settings':
        """
        在加载 .env 文件后进行验证和处理。
        """
        # 1. 处理 USER_ID: 如果 .env 中未提供或为空，则自动生成一个。
        if not self.USER_ID:
            self.USER_ID = str(uuid.uuid4().hex) + str(uuid.uuid4().hex)
        
        # 2. 处理多行公钥: 替换换行符，确保格式正确
        self.UPSTREAM_PUBLIC_KEY = self.UPSTREAM_PUBLIC_KEY.replace("\\n", "\n")
        
        return self

settings = Settings()
