"""
统一大模型 API 客户端适配器 — llm_client.py
支持 DeepSeek (首选)、OpenAI 和 Google Gemini，通过读取根目录的 .env 文件进行配置。
采用纯标准库 urllib/requests，无三方 SDK 依赖，保障高可用与轻量级响应。
"""
import os
import json
import requests

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
ENV_PATH = os.path.join(BASE, ".env")

def load_env_file():
    """手动读取并解析 .env 文件，避开 python-dotenv 依赖"""
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

class LLMClient:
    def __init__(self):
        load_env_file()
        self.api_type = os.environ.get("LLM_API_TYPE", "deepseek").lower()
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.api_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")
        
        # 兼容性适配：如果是 deepseek 但没指定 base，设置为默认值
        if self.api_type == "deepseek" and not os.environ.get("LLM_API_BASE"):
            self.api_base = "https://api.deepseek.com/v1"
        # 兼容性适配：如果是 openai 且没指定 base，设置为 OpenAI 官方接口
        elif self.api_type == "openai" and not os.environ.get("LLM_API_BASE"):
            self.api_base = "https://api.openai.com/v1"

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置"""
        return len(self.api_key.strip()) > 0

    def call_llm(self, prompt: str, system_prompt: str = None, json_mode: bool = False) -> str:
        """
        调用大模型接口并返回生成的纯文本。
        """
        if not self.is_configured():
            raise ValueError("LLM API Key 尚未配置，请在根目录创建 .env 文件并填入 LLM_API_KEY")

        # ── 1. Google Gemini API 路径 ─────────────────────────────────────
        if self.api_type == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            
            contents = []
            if system_prompt:
                contents.append({"role": "user", "parts": [{"text": f"System Context:\n{system_prompt}"}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            
            payload = {"contents": contents}
            if json_mode:
                payload["generationConfig"] = {"responseMimeType": "application/json"}
                
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            res_json = resp.json()
            
            try:
                return res_json["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                raise ValueError(f"Gemini API 响应解析失败: {res_json}")

        # ── 2. OpenAI / DeepSeek API 路径 (OpenAI 兼容接口) ────────────────
        else:
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3
            }
            if json_mode:
                # 兼容 deepseek 和 openai 的 json_object
                payload["response_format"] = {"type": "json_object"}
                
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            res_json = resp.json()
            
            try:
                return res_json["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                raise ValueError(f"OpenAI/DeepSeek API 响应解析失败: {res_json}")
