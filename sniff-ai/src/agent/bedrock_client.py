"""AWS Bedrock client wrapper for sniff Agent Service.

Provides a clean interface to AWS Bedrock with:
- Model invocation with structured prompts
- JSON response parsing
- Error handling and timeout management
- Configurable model selection
"""

import json
import os
from typing import Any, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class BedrockClient:
    """AWS Bedrock client for LLM-based decision making.

    Wraps boto3 Bedrock runtime with simplified interface for
    agent decision generation.

    Architecture boundary: This client only makes API calls.
    Decision validation and schema enforcement happens in DecisionService.
    """

    def __init__(
        self,
        region: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 2
    ):
        """Initialize Bedrock client.

        Args:
            region: AWS region (defaults to AWS_REGION env var or us-west-2)
            model_id: Bedrock model ID (defaults to BEDROCK_MODEL_ID env var or Claude 3.5 Sonnet)
            timeout_seconds: API call timeout in seconds
            max_retries: Number of retries for transient failures
        """
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.timeout_seconds = timeout_seconds

        # Inference profile ARN (used for models that require it)
        self._inference_profile_arn = None

        # Configure boto3 client with timeouts and retries
        config = Config(
            region_name=self.region,
            connect_timeout=timeout_seconds,
            read_timeout=timeout_seconds,
            retries={
                'max_attempts': max_retries,
                'mode': 'standard'
            }
        )

        try:
            self.client = boto3.client(
                service_name='bedrock-runtime',
                config=config
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Bedrock client: {e}\n"
                "Ensure AWS credentials are configured and Bedrock is accessible."
            ) from e

    def _get_inference_profile_arn(self) -> str:
        """Get or create inference profile ARN for models that require it.

        For Claude Sonnet 4.5 and similar models, we need to use cross-region
        inference profiles instead of direct model IDs.

        Returns:
            Inference profile ID or ARN
        """
        if self._inference_profile_arn:
            return self._inference_profile_arn

        # Map model IDs to their cross-region inference profile IDs
        # For Claude Sonnet 4.5, use the cross-region inference profile ID
        if "claude-sonnet-4-5-20250929" in self.model_id:
            # Use cross-region inference profile ID for Claude Sonnet 4.5
            # Format: us.anthropic.claude-sonnet-4-5-20250929-v1:0
            self._inference_profile_arn = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        elif "anthropic.claude-sonnet-4" in self.model_id:
            # Generic cross-region profile for other Claude Sonnet 4.x models
            # Extract version from model ID and create profile ID
            model_name = self.model_id.replace("anthropic.", "")
            self._inference_profile_arn = f"us.anthropic.{model_name}"
        else:
            # For other models, use the model ID directly
            self._inference_profile_arn = self.model_id

        return self._inference_profile_arn

    def invoke(
        self,
        system_prompt: str,
        user_message: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: Optional[float] = None
    ) -> str:
        """Invoke Bedrock model with a prompt.

        Args:
            system_prompt: System instructions for the model
            user_message: User message/prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling threshold (optional, not used with temperature)

        Returns:
            Model response text

        Raises:
            BedrockInvocationError: If invocation fails
            BedrockTimeoutError: If request times out
        """
        try:
            # Detect model type and construct appropriate request body
            is_claude = "anthropic.claude" in self.model_id.lower()
            is_deepseek = "deepseek" in self.model_id.lower()
            is_nvidia = "nvidia" in self.model_id.lower()
            is_llama = "llama" in self.model_id.lower()

            # Normalize user_message to list format if it's a string
            if isinstance(user_message, str):
                user_content = user_message
            else:
                # user_message is already a list of content blocks (text + images)
                user_content = user_message

            if is_deepseek or is_nvidia:
                # DeepSeek and NVIDIA use OpenAI-compatible format
                # NVIDIA Nemotron supports vision, DeepSeek v3.2 is text-only
                request_body = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            elif is_llama:
                # Llama uses prompt format (text only, no vision support)
                # Convert user_content to string if it's a list
                if isinstance(user_content, list):
                    # Extract text from content blocks
                    text_parts = [block.get('text', '') for block in user_content if block.get('type') == 'text']
                    user_text = '\n'.join(text_parts)
                else:
                    user_text = user_content

                prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>{user_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
                request_body = {
                    "prompt": prompt,
                    "max_gen_len": max_tokens,
                    "temperature": temperature,
                }
            else:
                # Claude format (default) - supports vision
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ]
                }
                # Only add top_p if explicitly provided (don't use both temperature and top_p)
                if top_p is not None:
                    request_body["top_p"] = top_p

            # Try with direct model ID first
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json"
                )
            except ClientError as e:
                # Check if this is the inference profile requirement error
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', '')

                if error_code == 'ValidationException' and 'inference profile' in error_message.lower():
                    # Retry with inference profile ARN
                    profile_arn = self._get_inference_profile_arn()
                    response = self.client.invoke_model(
                        modelId=profile_arn,
                        body=json.dumps(request_body),
                        contentType="application/json",
                        accept="application/json"
                    )
                else:
                    # Re-raise other errors
                    raise

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract text based on model type
            is_deepseek = "deepseek" in self.model_id.lower()
            is_nvidia = "nvidia" in self.model_id.lower()
            is_llama = "llama" in self.model_id.lower()

            if is_deepseek or is_nvidia:
                # DeepSeek and NVIDIA use OpenAI format
                if 'choices' in response_body and len(response_body['choices']) > 0:
                    return response_body['choices'][0]['message']['content']
                else:
                    raise BedrockInvocationError(
                        "Unexpected response format",
                        response_body
                    )
            elif is_llama:
                # Llama format
                if 'generation' in response_body:
                    return response_body['generation']
                else:
                    raise BedrockInvocationError(
                        "Unexpected Llama response format",
                        response_body
                    )
            else:
                # Claude response format (default)
                if 'content' in response_body and len(response_body['content']) > 0:
                    return response_body['content'][0]['text']
                else:
                    raise BedrockInvocationError(
                        "Unexpected response format from Bedrock",
                        response_body
                    )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'TimeoutError':
                raise BedrockTimeoutError(
                    f"Bedrock request timed out after {self.timeout_seconds}s"
                ) from e
            else:
                raise BedrockInvocationError(
                    f"Bedrock invocation failed: {error_code} - {error_message}",
                    e.response
                ) from e

        except json.JSONDecodeError as e:
            raise BedrockInvocationError(
                "Failed to parse Bedrock response as JSON",
                response.get('body', 'No body')
            ) from e

        except Exception as e:
            raise BedrockInvocationError(
                f"Unexpected error during Bedrock invocation: {e}"
            ) from e

    def invoke_with_json_response(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> dict[str, Any]:
        """Invoke model and parse response as JSON.

        Expects model to return valid JSON in response.
        Useful for structured decision outputs.

        Args:
            system_prompt: System instructions (should request JSON output)
            user_message: User message/prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Parsed JSON response as dictionary

        Raises:
            BedrockInvocationError: If invocation or JSON parsing fails
        """
        response_text = self.invoke(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=temperature
        )

        try:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                # Extract content between ```json and ```
                start_idx = response_text.find("```json") + 7
                end_idx = response_text.find("```", start_idx)
                json_text = response_text[start_idx:end_idx].strip()
            elif "```" in response_text:
                # Extract content between ``` and ```
                start_idx = response_text.find("```") + 3
                end_idx = response_text.find("```", start_idx)
                json_text = response_text[start_idx:end_idx].strip()
            else:
                json_text = response_text.strip()

            return json.loads(json_text)

        except json.JSONDecodeError as e:
            raise BedrockInvocationError(
                f"Model response is not valid JSON: {e}\nResponse: {response_text}"
            ) from e


class BedrockInvocationError(Exception):
    """Raised when Bedrock invocation fails."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.details = details


class BedrockTimeoutError(BedrockInvocationError):
    """Raised when Bedrock invocation times out."""
    pass
