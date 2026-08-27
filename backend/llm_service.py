"""
llm_service.py
硅基流动 (SiliconFlow) 视觉大模型服务 —— 病虫害识别

功能:
  1. 接收用户上传的农田照片
  2. 将图片转为 base64 + 构建农业专家提示词
  3. 调用硅基流动视觉 API (Qwen2.5-VL) 进行分析
  4. 解析返回结果，包装为统一数据结构

API Key 配置:
  方式 1: 设置环境变量 SILICONFLOW_API_KEY
  方式 2: 在 backend/.env 文件中写入 SILICONFLOW_API_KEY=xxx
  方式 3: 无 API Key 时自动降级为模拟模式（延迟 2 秒后返回 mock 结果）

硅基流动:
  官网: https://siliconflow.cn
  文档: https://docs.siliconflow.cn
  支持的视觉模型: Qwen/Qwen2.5-VL-72B-Instruct, Qwen/Qwen2-VL-72B-Instruct 等
  API 格式: OpenAI 兼容
"""

import os
import json
import time
import base64
import asyncio
from typing import Optional

import httpx

from logger import get_logger

logger = get_logger(__name__)

# ============================================================
# 配置
# ============================================================

# 从环境变量或 .env 文件读取 API Key
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")

# 通用 .env 加载函数
def _load_env(path):
    config = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip().strip('"').strip("'")
    return config

# 尝试从 .env 文件加载
_env_path = os.path.join(os.path.dirname(__file__), ".env")
_env = _load_env(_env_path) if os.path.exists(_env_path) else {}
if not SILICONFLOW_API_KEY:
    SILICONFLOW_API_KEY = _env.get("SILICONFLOW_API_KEY", "")

# 硅基流动 API 配置
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_CHAT_URL = f"{SILICONFLOW_BASE_URL}/chat/completions"

# 视觉模型（支持图像输入）
SILICONFLOW_VISION_MODEL = os.getenv(
    "SILICONFLOW_MODEL",
    _env.get("SILICONFLOW_MODEL", "Qwen/Qwen3-VL-32B-Instruct")
)

# 是否启用模拟模式（无 API Key 时自动启用）
MOCK_MODE = not bool(SILICONFLOW_API_KEY)


# ============================================================
# 提示词构建
# ============================================================

PEST_IDENTIFY_PROMPT = """你是一位经验丰富的农业植保专家，专门负责华南地区（特别是广东）水稻、蔬菜等农作物的病虫害诊断。

请仔细分析这张农田照片，识别其中的作物类型和可能的病虫害。

请严格按照以下 JSON 格式返回结果（只返回 JSON，不要有任何其他文字）：

{
  "diseaseName": "病虫害名称（中文，如"稻瘟病"、"稻飞虱"、"纹枯病"。如果照片健康无异常，填"未发现异常"）",
  "severity": "严重程度（low / medium / critical，如果健康则填 low）",
  "confidence": 0.0到1.0之间的置信度数值,
  "cropType": "识别到的作物类型（如"水稻"、"玉米"、"蔬菜"）",
  "symptoms": "观察到的症状描述（1-2句话）",
  "treatments": [
    {"label": "药剂推荐", "value": "具体药剂和用量"},
    {"label": "防治窗口", "value": "建议施药时间"},
    {"label": "飞防参数", "value": "航高和喷幅参数"}
  ]
}

注意事项:
- 如果照片不清晰或无法判断，confidence 设为 0.3 以下，并在 symptoms 中说明原因
- 如果照片中作物健康，treatments 中填"暂不需要防治，建议继续观察"
- treatments 数组始终返回 3 项"""


def build_siliconflow_request(image_bytes: bytes, image_type: str = "image/jpeg") -> dict:
    """
    构建豆包视觉 API 请求体

    Args:
        image_bytes: 图片二进制数据
        image_type: 图片 MIME 类型

    Returns:
        硅基流动 API 请求体 dict
    """
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{image_type};base64,{image_b64}"

    return {
        "model": SILICONFLOW_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PEST_IDENTIFY_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.1,      # 低温度 = 更确定性的输出
        "max_tokens": 1000,
    }


# ============================================================
# 硅基流动 API 调用
# ============================================================

async def call_vision_llm(image_bytes: bytes, image_type: str = "image/jpeg") -> dict:
    """
    调用硅基流动视觉 API 分析图片

    Args:
        image_bytes: 图片二进制数据
        image_type: 图片 MIME 类型

    Returns:
        解析后的病虫害识别结果 dict

    Raises:
        Exception: API 调用失败时抛出
    """
    if MOCK_MODE:
        logger.warning("运行在模拟模式，返回 mock 数据（未配置 SILICONFLOW_API_KEY）")
        return await _mock_identify()

    image_size_kb = len(image_bytes) / 1024
    logger.info(
        f"调用硅基流动 API: model={SILICONFLOW_VISION_MODEL}, "
        f"image_size={image_size_kb:.1f}KB"
    )

    request_body = build_siliconflow_request(image_bytes, image_type)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
    }

    start_time = time.time()

    # 硅基流动偶尔会返回临时性 5xx（如 code=50507 Unknown error），
    # 对这类错误自动重试（最多 3 次），间隔递增 1s/2s/4s
    MAX_RETRIES = 3
    resp = None
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(SILICONFLOW_CHAT_URL, json=request_body, headers=headers)
            except httpx.RequestError as e:
                # 网络层异常（超时/连接失败）也纳入重试
                if attempt == MAX_RETRIES:
                    raise Exception(f"硅基流动 API 网络错误（已重试 {MAX_RETRIES} 次）: {e}")
                logger.warning(f"硅基流动 API 网络异常（第 {attempt} 次）: {e}，{2 ** (attempt - 1)}s 后重试")
                await asyncio.sleep(2 ** (attempt - 1))
                continue

            if resp.status_code < 500:
                break  # 4xx 等客户端错误不重试，直接走后面的错误处理
            if attempt == MAX_RETRIES:
                break  # 重试耗尽，跳出后统一报错
            logger.warning(
                f"硅基流动 API 临时错误 status={resp.status_code}（第 {attempt} 次），"
                f"{2 ** (attempt - 1)}s 后重试"
            )
            await asyncio.sleep(2 ** (attempt - 1))

        elapsed_ms = (time.time() - start_time) * 1000

        if resp is None or resp.status_code != 200:
            error_detail = resp.text[:500] if resp is not None else "无响应"
            logger.error(
                f"硅基流动 API 错误: status={resp.status_code if resp is not None else 'N/A'}, "
                f"elapsed={elapsed_ms:.0f}ms, detail={error_detail}"
            )
            raise Exception(f"硅基流动 API 返回错误 {resp.status_code if resp is not None else 'N/A'}: {error_detail}")

        data = resp.json()

        # 解析 OpenAI 兼容格式响应
        content = data["choices"][0]["message"]["content"]

        # 大模型可能返回纯文本或带 markdown 代码块的 JSON
        content = content.strip()
        if content.startswith("```"):
            # 去掉 markdown 代码块标记
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])

        result = json.loads(content)

        # 记录 API 返回的 token 用量
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        logger.info(
            f"硅基流动 API 成功: elapsed={elapsed_ms:.0f}ms, "
            f"tokens={prompt_tokens}+{completion_tokens}, "
            f"result={result.get('diseaseName', '未知')}"
        )

        # 标准化字段
        return _normalize_result(result)


# ============================================================
# 结果标准化
# ============================================================

def _normalize_result(raw: dict) -> dict:
    """将大模型返回的结果标准化为前端期望的数据结构"""
    return {
        "detection_id": f"D{int(time.time())}",
        "diseaseName": raw.get("diseaseName", "未知"),
        "severity": raw.get("severity", "low"),
        "confidence": float(raw.get("confidence", 0.5)),
        "cropType": raw.get("cropType", ""),
        "symptoms": raw.get("symptoms", ""),
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "treatments": raw.get("treatments", []),
    }


# ============================================================
# 模拟模式（无 API Key 时使用）
# ============================================================

async def _mock_identify() -> dict:
    """模拟大模型识别：延迟 2 秒后返回 mock 结果"""
    await asyncio.sleep(2.0)

    from data import DETECTION_RESULT

    return {
        "detection_id": f"D{int(time.time())}",
        **DETECTION_RESULT,
        "cropType": "水稻",
        "symptoms": "叶片出现梭形病斑，中央灰白色，边缘褐色，外围有黄色晕圈。（模拟数据 — 配置 SILICONFLOW_API_KEY 后将返回真实 AI 识别结果）",
    }


# ============================================================
# 启动时打印模式信息
# ============================================================

def get_mode_info() -> str:
    """返回当前模式描述"""
    if MOCK_MODE:
        return (
            "[模拟模式] 未配置 SILICONFLOW_API_KEY，将返回模拟数据。\n"
            "  硅基流动注册: https://siliconflow.cn\n"
            "  配置方法: 在 backend/.env 文件中写入:\n"
            "    SILICONFLOW_API_KEY=你的API Key"
        )
    return f"[大模型模式] 已配置硅基流动 API，模型: {SILICONFLOW_VISION_MODEL}"
