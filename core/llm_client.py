"""
LLM Client for Alpha Clinical Agents
Async OpenAI/Anthropic integration with retry logic
"""

import os
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from core.logging_config import AgentLogger


@dataclass
class LLMResponse:
    """Structured LLM response"""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    timestamp: datetime


class LLMClient:
    """
    Async LLM client with:
    - Retry logic with exponential backoff
    - Multiple provider support (OpenAI, Anthropic)
    - Request/response logging
    - Token tracking
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_retries: int = 3
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.logger = AgentLogger("LLMClient")
        
        # Initialize client
        if provider == "openai":
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                self.logger.error("openai package not installed")
                self.client = None
        elif provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                self.logger.error("anthropic package not installed")
                self.client = None
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """
        Generate text with retry logic
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            context: Retrieved context documents
            max_tokens: Max output tokens
            
        Returns:
            LLMResponse with metadata
        """
        start_time = datetime.utcnow()
        
        # Build messages
        messages = []
        
        if system_prompt:
            if self.provider == "openai":
                messages.append({"role": "system", "content": system_prompt})
        
        # Add context if provided
        if context:
            context_str = "\n\n".join([f"[Source {i+1}]: {c}" for i, c in enumerate(context)])
            prompt = f"Context:\n{context_str}\n\nTask:\n{prompt}"
        
        messages.append({"role": "user", "content": prompt})
        
        # Retry loop
        for attempt in range(self.max_retries):
            try:
                if self.provider == "openai":
                    response = await self._call_openai(messages, max_tokens)
                elif self.provider == "anthropic":
                    response = await self._call_anthropic(messages, system_prompt, max_tokens)
                
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                self.logger.info(
                    "llm_generation_complete",
                    model=self.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    latency_ms=latency
                )
                
                return response
                
            except Exception as e:
                self.logger.warning(
                    "llm_retry",
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise RuntimeError("Max retries exceeded")
    
    async def _call_openai(
        self,
        messages: List[Dict],
        max_tokens: int
    ) -> LLMResponse:
        """Call OpenAI API"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=0,
            timestamp=datetime.utcnow()
        )
    
    async def _call_anthropic(
        self,
        messages: List[Dict],
        system_prompt: Optional[str],
        max_tokens: int
    ) -> LLMResponse:
        """Call Anthropic API"""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Convert messages to Anthropic format
        user_message = messages[-1]["content"] if messages else ""
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": user_message}]
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            latency_ms=0,
            timestamp=datetime.utcnow()
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars)"""
        return len(text) // 4
