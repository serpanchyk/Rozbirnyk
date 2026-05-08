"""Create Bedrock chat models for agent graph execution."""

from langchain_aws import ChatBedrockConverse

from agent_service.schema import AgentServiceConfig


def create_bedrock_model(config: AgentServiceConfig) -> ChatBedrockConverse:
    """Create the configured AWS Bedrock chat model.

    Args:
        config: Agent service configuration.

    Returns:
        A LangChain chat model backed by Bedrock Converse.
    """
    return ChatBedrockConverse(
        model_id=config.model.model_id,
        region_name=config.model.region_name,
        temperature=config.model.temperature,
        max_tokens=config.model.max_tokens,
    )
