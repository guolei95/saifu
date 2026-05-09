"""
DeepSeek API 调用封装 — 提供 call_deepseek() 和 call_deepseek_json() 两个函数。
"""
import json
import re
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=120.0)


def call_deepseek(messages, temperature=None, max_tokens=None):
    """调用 DeepSeek API，返回原始文本回复。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数，默认用 config 中的值
        max_tokens: 最大 token 数，默认用 config 中的值

    Returns:
        str: LLM 的原始文本回复
    """
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS

    resp = _client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temp,
        max_tokens=tokens,
    )
    return resp.choices[0].message.content.strip()


def call_deepseek_json(messages, temperature=None, max_tokens=None):
    """调用 DeepSeek API 并解析 JSON 回复。

    自动清理 markdown 代码块、尝试多种 JSON 修复策略。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        list[dict]: 解析后的 JSON 列表。解析失败返回空列表。
    """
    text = call_deepseek(messages, temperature=temperature, max_tokens=max_tokens)

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
