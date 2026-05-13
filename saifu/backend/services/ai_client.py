"""
LLM API 调用封装 — 提供 call_deepseek() 和 call_deepseek_json() 两个函数。
支持用户自带 API Key / Base URL / Model，实现多平台兼容。
集成服务端 5 元预算追踪，超额后强制用户使用自有密钥。
"""
import json
import re
from openai import OpenAI
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from services.budget import check_budget, record_usage, is_bankrupt, get_bankrupt_message


class ServerAPIExhausted(Exception):
    """服务器 API 额度耗尽或用户密钥无效时抛出。前端捕获后提示「小雷已破产」。"""
    pass


def _is_using_server_key(api_key=None) -> bool:
    """判断当前调用是否使用服务端 Key（非用户自带）。"""
    if api_key is None:
        return True
    if isinstance(api_key, dict):
        key = api_key.get("api_key", "") or api_key.get("key", "")
        return not bool(key)
    return not bool(api_key)


# 全局默认客户端（使用服务器 Key）
_default_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=120.0)

# 用户客户端缓存：按 (key, base_url, model) 去重
_user_clients: dict = {}


def _parse_llm_config(api_key=None, api_base=None, api_model=None):
    """解析 LLM 配置，兼容三种传参方式：
    - api_key 为字符串 → 用服务器 base_url/model
    - api_key 为 dict → 从 dict 取 api_key/base_url/model
    - api_base/api_model 显式传参 → 优先使用
    """
    if isinstance(api_key, dict):
        key = api_key.get("api_key", "") or api_key.get("key", "")
        base = api_base or api_key.get("base_url", "") or LLM_BASE_URL
        model = api_model or api_key.get("model", "") or LLM_MODEL
    else:
        key = api_key or ""
        base = api_base or LLM_BASE_URL
        model = api_model or LLM_MODEL
    return key, base, model


def _get_client(api_key=None, api_base=None, api_model=None):
    """获取 OpenAI 客户端。优先用户配置，否则服务器默认。"""
    key, base, model = _parse_llm_config(api_key, api_base, api_model)

    if not key:
        return _default_client, model

    cache_key = f"{key}@{base}@{model}"
    if cache_key not in _user_clients:
        _user_clients[cache_key] = OpenAI(
            api_key=key,
            base_url=base,
            timeout=120.0,
        )
    return _user_clients[cache_key], model


def call_deepseek(messages, temperature=None, max_tokens=None, api_key=None, api_base=None, api_model=None):
    """调用 LLM API，返回原始文本回复。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数，默认用 config 中的值
        max_tokens: 最大 token 数，默认用 config 中的值
        api_key: 用户 API Key（字符串或 {"api_key","base_url","model"} dict）
        api_base: 用户指定的 Base URL（可选）
        api_model: 用户指定的模型名（可选）

    Returns:
        str: LLM 的原始文本回复

    Raises:
        ServerAPIExhausted: 服务器或用户 API 额度耗尽
    """
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    client, model = _get_client(api_key, api_base, api_model)

    # ── 预算检查（仅服务端 Key）──
    using_server_key = _is_using_server_key(api_key)
    if using_server_key and is_bankrupt():
        raise ServerAPIExhausted(get_bankrupt_message())

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
        )
        # ── 记录消费（仅服务端 Key）──
        if using_server_key and resp.usage:
            record_usage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
            )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # 预算检查已在上面完成，这里只处理真实 API 错误
        # 不重复检查预算（避免覆盖破产消息）
        error_str = str(e).lower()
        # 识别额度/余额/付费相关错误 + 鉴权失败
        bankrupt_keywords = [
            'insufficient', 'balance', 'quota', 'billing', 'exhausted',
            '402', '401', 'payment', '充值', '余额不足', '欠费', 'rate limit',
            'rate_limit', 'too many requests', 'authentication', 'invalid',
            'invalid_request_error', 'api key',
        ]
        if any(kw in error_str for kw in bankrupt_keywords):
            raise ServerAPIExhausted(
                f"[BANKRUPT] API 额度不足或余额耗尽，请使用自己的密钥。原始错误: {e}"
            ) from e
        raise


def call_deepseek_json(messages, temperature=None, max_tokens=None, api_key=None, api_base=None, api_model=None):
    """调用 LLM API 并解析 JSON 回复。

    自动清理 markdown 代码块、尝试多种 JSON 修复策略。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 温度参数
        max_tokens: 最大 token 数
        api_key: 用户 API Key（字符串或 dict）
        api_base: 用户指定的 Base URL（可选）
        api_model: 用户指定的模型名（可选）

    Returns:
        list[dict]: 解析后的 JSON 列表。解析失败返回空列表。
    """
    text = call_deepseek(messages, temperature=temperature, max_tokens=max_tokens,
                         api_key=api_key, api_base=api_base, api_model=api_model)

    # ── 清理 markdown 代码块 ──
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # ── 清洗不可见字符 ──
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t ")

    # ── 多重 JSON 修复策略 ──
    strategies = [text, text.rstrip().rstrip(",") + "\n]"]

    for pattern in [r'\}\s*,?\s*\n', r'\}']:
        matches = list(re.finditer(pattern, text))
        if matches:
            strategies.append(text[:matches[-1].end()].rstrip().rstrip(",") + "\n]")

    last_brace = text.rfind("}")
    if last_brace > 0:
        strategies.append(text[:last_brace + 1].rstrip().rstrip(",") + "\n]")

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
