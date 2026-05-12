"""
LLM API 调用封装 — 提供 call_deepseek() 和 call_deepseek_json() 两个函数。
支持用户自带 API Key，实现开发者/用户双轨调用。
"""
import json
import re
from openai import OpenAI
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# 全局默认客户端（使用服务器 Key）
_default_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=120.0)

# 用户客户端缓存：避免同一用户短时间内重复创建连接
_user_clients: dict = {}


def _get_client(api_key: str | None = None) -> OpenAI:
    """获取 OpenAI 客户端。传 api_key 用用户的，否则用服务器的。"""
    if api_key:
        # 缓存用户客户端（按 key 去重，避免频繁创建）
        if api_key not in _user_clients:
            _user_clients[api_key] = OpenAI(
                api_key=api_key,
                base_url=LLM_BASE_URL,
                timeout=120.0,
            )
        return _user_clients[api_key]
    return _default_client


def call_deepseek(messages, temperature=None, max_tokens=None, api_key=None):
    """调用 LLM API，返回原始文本回复。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数，默认用 config 中的值
        max_tokens: 最大 token 数，默认用 config 中的值
        api_key: 可选，用户自己的 API Key。传了就用用户的，不传用服务器的。

    Returns:
        str: LLM 的原始文本回复
    """
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    client = _get_client(api_key)

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temp,
        max_tokens=tokens,
    )
    return resp.choices[0].message.content.strip()


def call_deepseek_json(messages, temperature=None, max_tokens=None, api_key=None):
    """调用 LLM API 并解析 JSON 回复。

    自动清理 markdown 代码块、尝试多种 JSON 修复策略。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数
        max_tokens: 最大 token 数
        api_key: 可选，用户自己的 API Key

    Returns:
        list[dict]: 解析后的 JSON 列表。解析失败返回空列表。
    """
    text = call_deepseek(messages, temperature=temperature, max_tokens=max_tokens, api_key=api_key)

    # ── 清理 markdown 代码块 ──
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # ── 清洗不可见字符 ──
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t ")

    # ── 多重 JSON 修复策略 ──
    strategies = [text, text.rstrip().rstrip(",") + "\n]"]

    # 策略 2: 在最后一个完整对象后截断
    for pattern in [r'\}\s*,?\s*\n', r'\}']:
        matches = list(re.finditer(pattern, text))
        if matches:
            strategies.append(text[:matches[-1].end()].rstrip().rstrip(",") + "\n]")

    # 策略 3: 从最后一个 } 截断
    last_brace = text.rfind("}")
    if last_brace > 0:
        strategies.append(text[:last_brace + 1].rstrip().rstrip(",") + "\n]")

    # 策略 4: 如果看起来是单对象，包裹成数组
    trimmed = text.strip()
    if trimmed.startswith("{") and not trimmed.startswith("[{"):
        strategies.insert(0, "[" + trimmed + "]")

    for s in strategies:
        try:
            result = json.loads(s)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return [result]
        except Exception:
            pass

    return []
