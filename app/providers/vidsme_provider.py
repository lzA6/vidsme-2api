# /app/providers/vidsme_provider.py
import time
import logging
import asyncio
from typing import Dict, Any, Tuple

import cloudscraper
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.providers.base_provider import BaseProvider
from app.utils.security import VidsmeSigner

# 注意：这里使用 loguru 的 logger，它已在 main.py 中配置
from loguru import logger

class VidsmeProvider(BaseProvider):
    BASE_URL = "https://api.vidsme.com/api/texttoimg/v1"

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.signer = VidsmeSigner()

    def _prepare_headers(self) -> Dict[str, str]:
        """
        准备模拟真实浏览器请求所需的请求头。
        """
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://chatsweetie.ai",
            "Referer": "https://chatsweetie.ai/",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

    def _parse_size(self, size: str) -> Tuple[int, int]:
        size_map = {
            "1:1": (512, 512),
            "3:2": (768, 512),
            "2:3": (512, 768),
        }
        if size in size_map:
            return size_map[size]
        logger.warning(f"无效的 size/ratio 参数: '{size}', 使用默认值 512x768")
        return 512, 768

    async def _submit_task(self, payload: Dict[str, Any]) -> str:
        auth_params = self.signer.generate_signature()
        url = f"{self.BASE_URL}/task"
        headers = self._prepare_headers()
        
        # --- [修改] 增强日志：打印完整的请求信息 ---
        logger.info("--- [VidsmeProvider] 开始向上游提交任务 ---")
        logger.info(f"请求方法: POST")
        logger.info(f"请求 URL: {url}")
        logger.info(f"请求头 (Headers): {headers}")
        logger.info(f"查询参数 (Params): {auth_params}")
        logger.info(f"请求载荷 (Payload): {payload}")
        # --- 增强日志结束 ---
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.scraper.post(
                url,
                headers=headers,
                params=auth_params,
                json=payload,
                timeout=settings.API_REQUEST_TIMEOUT
            )
        )

        # --- [修改] 增强日志：打印完整的响应信息 ---
        response_text = "N/A"
        try:
            # 优先尝试以 JSON 格式记录，如果失败则记录原始文本
            response_text = response.json()
        except Exception:
            response_text = response.text

        logger.info(f"收到上游响应状态码: {response.status_code}")
        logger.info(f"收到上游响应内容: {response_text}")
        logger.info("--- [VidsmeProvider] 上游响应接收完毕 ---")
        # --- 增强日志结束 ---

        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200 or "data" not in data or "job_id" not in data["data"]:
            raise Exception(f"提交预测任务失败: {data.get('msg', '未知错误')}")
        
        job_id = data["data"]["job_id"]
        logger.info(f"任务提交成功，Job ID: {job_id}")
        return job_id

    async def _poll_result(self, job_id: str) -> str:
        start_time = time.time()
        
        while time.time() - start_time < settings.POLLING_TIMEOUT:
            await asyncio.sleep(settings.POLLING_INTERVAL)
            
            auth_params = self.signer.generate_signature()
            auth_params['user_id'] = settings.USER_ID
            auth_params['job_id'] = job_id
            url = f"{self.BASE_URL}/task"
            headers = self._prepare_headers()
            
            # --- [修改] 增强日志：打印轮询请求的详细信息 ---
            logger.info(f"--- [VidsmeProvider] 开始轮询任务状态 (Job ID: {job_id}) ---")
            logger.info(f"请求方法: GET")
            logger.info(f"请求 URL: {url}")
            logger.info(f"请求头 (Headers): {headers}")
            logger.info(f"查询参数 (Params): {auth_params}")
            # --- 增强日志结束 ---

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.scraper.get(
                    url,
                    headers=headers,
                    params=auth_params,
                    timeout=settings.API_REQUEST_TIMEOUT
                )
            )

            # --- [修改] 增强日志：打印轮询响应的详细信息 ---
            response_text = "N/A"
            try:
                response_text = response.json()
            except Exception:
                response_text = response.text
            
            logger.info(f"轮询响应状态码: {response.status_code}")
            logger.info(f"轮询响应内容: {response_text}")
            # --- 增强日志结束 ---

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                logger.warning(f"轮询状态异常: {data.get('msg')}")
                continue

            status_data = data.get("data", {})
            if "generate_url" in status_data and status_data["generate_url"]:
                logger.info(f"任务成功，获取到结果路径: {status_data['generate_url']}")
                return settings.IMAGE_BASE_URL + status_data['generate_url']
            
            # 将 debug 改为 info，确保在默认配置下可见
            logger.info(f"任务仍在处理中... Status: {status_data.get('status', 'unknown')}")

        raise Exception("轮询任务状态超时。")

    async def generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request_data.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="参数 'prompt' 不能为空。")

        model = request_data.get("model", settings.DEFAULT_MODEL)
        if model not in settings.KNOWN_MODELS:
            raise HTTPException(status_code=400, detail=f"不支持的模型: '{model}'. 可用模型: {settings.KNOWN_MODELS}")
        
        api_model_name = "hassaku(hentai)" if model == "hassaku" else model

        width, height = self._parse_size(request_data.get("size", "2:3"))
        
        payload = {
            "prompt": f"(masterpiece), best quality, expressiveeyes, perfect face,{prompt}",
            "model": api_model_name,
            "user_id": settings.USER_ID,
            "height": height,
            "width": width,
        }

        try:
            job_id = await self._submit_task(payload)
            result_url = await self._poll_result(job_id)
            
            return {
                "created": int(time.time()),
                "data": [{"url": result_url}]
            }

        except Exception as e:
            # 使用 loguru 记录异常信息，会包含更详细的堆栈
            logger.error(f"处理图像任务时出错: {e}", exc_info=True)
            # 向上层抛出 HTTP 异常
            raise HTTPException(status_code=502, detail=f"上游服务错误: {str(e)}")

    async def get_models(self) -> Dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
