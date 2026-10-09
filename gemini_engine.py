import os
import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

logger = logging.getLogger("gemini_engine")
logging.basicConfig(level=logging.INFO)

class RotatingGeminiClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_idx = 0
        self.clients = [genai.Client(api_key=key) for key in api_keys]
        self._wrapped_services = {}
        logger.info(f"🔑 Initialized RotatingGeminiClient with {len(api_keys)} API keys.")

    @property
    def current_client(self):
        return self.clients[self.current_key_idx]

    def rotate_key(self):
        old_idx = self.current_key_idx
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        logger.warning(f"🔄 API Key Rotated: Switched from key index {old_idx} to {self.current_key_idx}")
        time.sleep(1.5)

    def __getattr__(self, name):
        if name in self._wrapped_services:
            return self._wrapped_services[name]
        val = getattr(self.current_client, name)
        wrapped = ServiceWrapper(self, name, val)
        self._wrapped_services[name] = wrapped
        return wrapped


class ServiceWrapper:
    def __init__(self, parent_client, service_name, real_service):
        super().__setattr__("parent_client", parent_client)
        super().__setattr__("service_name", service_name)
        super().__setattr__("real_service", real_service)

    def __getattr__(self, method_name):
        if method_name in self.__dict__:
            return self.__dict__[method_name]

        def wrapper(*args, **kwargs):
            max_rotations = len(self.parent_client.api_keys)
            for rotation_attempt in range(max_rotations + 1):
                try:
                    curr_client = self.parent_client.current_client
                    curr_service = getattr(curr_client, self.service_name)
                    active_method = getattr(curr_service, method_name)
                    return active_method(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    is_rate_limit = any(x in error_msg for x in ("429", "quota", "503", "limit", "exhausted", "resource_exhausted", "timeout", "connection"))
                    if hasattr(e, 'code') and e.code in [429, 503]:
                        is_rate_limit = True

                    if is_rate_limit and rotation_attempt < max_rotations:
                        wait_time = min(3.0 * (rotation_attempt + 1), 15.0)
                        logger.warning(f"⚠️ API Rate limit on key {self.parent_client.current_key_idx}: {e}. Rotating in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        self.parent_client.rotate_key()
                        continue
                    else:
                        raise e
        return wrapper

    def __setattr__(self, name, value):
        if name in ("parent_client", "service_name", "real_service"):
            super().__setattr__(name, value)
        else:
            self.__dict__[name] = value


class GeminiRotationEngine:
    def __init__(self, api_key: Optional[str] = None):
        keys_pool = []
        if api_key:
            keys_pool.append(api_key)
        else:
            env_keys = os.getenv("GEMINI_API_KEYS")
            if env_keys:
                keys_pool = [k.strip() for k in env_keys.split(",") if k.strip()]
            if not keys_pool:
                idx = 1
                while True:
                    k = os.getenv(f"GEMINI_API_KEY_{idx}") or os.getenv(f"GEMINI_API_{idx}")
                    if not k:
                        break
                    keys_pool.append(k.strip())
                    idx += 1
            if not keys_pool:
                std_key = os.getenv("GEMINI_API")
                if std_key:
                    keys_pool.append(std_key.strip())

        if not keys_pool:
            raise ValueError("No Gemini API keys found. Configure GEMINI_API_KEYS in .env.")

        self.api_keys = keys_pool
        self.client = RotatingGeminiClient(self.api_keys)

        # General text generation models priority (flash-lite first for high quotas)
        self.model_priority = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash"
        ]

        # Search Grounding models priority (gemini-2.5-flash-lite has 1,500 daily quota on Free Tier)
        self.grounding_model_priority = [
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ]

        # Vision verification models priority (flash-lite first for high rate limits & zero 404s)
        self.vision_model_priority = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
            "gemini-2.5-flash"
        ]

        self.active_working_model = None

    @property
    def current_client(self):
        return self.client.current_client

    @property
    def current_key_idx(self):
        return self.client.current_key_idx

    def rotate_key(self):
        self.client.rotate_key()

    def generate_text(self, prompt: str, model: Optional[str] = None, system_instruction: Optional[str] = None, response_schema: Optional[Any] = None, temperature: float = 0.2) -> str:
        models_to_try = [model] if model else ([self.active_working_model] + [m for m in self.model_priority if m != self.active_working_model] if self.active_working_model else self.model_priority)
        
        last_error = None
        for m in models_to_try:
            if not m:
                continue
            for attempt in range(len(self.api_keys) + 1):
                try:
                    config_kwargs = {"temperature": temperature}
                    if system_instruction:
                        config_kwargs["system_instruction"] = system_instruction
                    if response_schema:
                        config_kwargs["response_mime_type"] = "application/json"
                        config_kwargs["response_schema"] = response_schema

                    cfg = types.GenerateContentConfig(**config_kwargs)
                    response = self.client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=cfg
                    )
                    if response and response.text:
                        self.active_working_model = m
                        return response.text
                except Exception as e:
                    last_error = e
                    logger.warning(f"Model {m} error on attempt {attempt}: {e}")
                    if any(x in str(e).lower() for x in ("429", "quota", "exhausted", "limit")):
                        self.rotate_key()
                        continue
                    break

        raise RuntimeError(f"generate_text failed across models. Last error: {last_error}")

    def generate_grounded_content(self, prompt: str) -> str:
        last_error = None
        for model in self.grounding_model_priority:
            for attempt in range(min(3, len(self.api_keys))):
                try:
                    raw_client = self.client.current_client
                    response = raw_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=0.1
                        )
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_error = e
                    logger.warning(f"Search grounding with {model} error: {e}")
                    if any(x in str(e).lower() for x in ("429", "quota", "exhausted")):
                        self.rotate_key()
                        continue
                    break

        logger.warning(f"Grounding fallback to standard text: {last_error}")
        return self.generate_text(prompt)

    def verify_image_relevance(self, image_bytes: bytes, question_text: str, visual_query: str) -> Tuple[bool, str]:
        prompt = (
            f"Question:\n{question_text}\n\n"
            f"Topic Query: {visual_query}\n\n"
            "Analyze the attached image. Is this image directly relevant, educational, and suitable for the question and topic?\n"
            "Respond in JSON format with fields:\n"
            "{\n"
            '  "is_relevant": true or false,\n'
            '  "reason": "short explanation"\n'
            "}"
        )

        for model in self.vision_model_priority:
            for attempt in range(min(3, len(self.api_keys))):
                try:
                    raw_client = self.client.current_client
                    part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                    res = raw_client.models.generate_content(
                        model=model,
                        contents=[part, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    if res and res.text:
                        data = json.loads(res.text)
                        return bool(data.get("is_relevant", False)), str(data.get("reason", ""))
                except Exception as e:
                    logger.warning(f"Vision verification with {model} failed on attempt {attempt+1}: {e}")
                    if any(x in str(e).lower() for x in ("429", "quota", "exhausted", "limit", "resource_exhausted")):
                        self.rotate_key()
                        continue
                    break

        return False, "Vision verification failed across all available models and keys."
