#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

from src.collector.models import AgentInteraction, ToolCall
from src.cleaner import CleaningPipeline


def create_sample_data() -> list[AgentInteraction]:
    interactions = []
    sample_interactions = [
        {
            "user_input": "Hello, my email is test@example.com, please help me",
            "agent_response": "Sure! I'll help you. Contact me at 123-456-7890",
        },
        {
            "user_input": "  Hello, my email is test@example.com, please help me  ",
            "agent_response": "Sure! I'll help you. Contact me at 123-456-7890",
        },
        {
            "user_input": "What's your IP?",
            "agent_response": "192.168.1.1 is the server IP",
        },
        {
            "user_input": "Short",
            "agent_response": "Response",
        },
    ]
    for i, data in enumerate(sample_interactions):
        interaction = AgentInteraction(
            id=f"sample-{i}",
            user_input=data["user_input"],
            agent_response=data["agent_response"],
            tool_calls=[
                ToolCall(
                    name="search",
                    arguments={"query": "test query", "email": "user@test.com"},
                )
            ],
            metadata={"source": "test", "user_id": f"user-{i}"},
        )
        interactions.append(interaction)
    return interactions


def main():
    print("=== Data Cleaning Example ===")
    print()
    pipeline = CleaningPipeline(
        deduplication_method="content",
        min_text_length=3,
    )
    sample_data = create_sample_data()
    print(f"Generated {len(sample_data)} sample interactions")
    print()
    print("=== Before Cleaning ===")
    metrics = pipeline.evaluate(sample_data)
    print(f"Total: {metrics.total_count}")
    print(f"Valid: {metrics.valid_count}")
    print(f"Overall Score: {metrics.overall_score:.2f}")
    print()
    cleaned_data = pipeline.process(sample_data)
    print("=== After Cleaning ===")
    print(f"Cleaned count: {len(cleaned_data)}")
    metrics = pipeline.evaluate(cleaned_data)
    print(f"Overall Score: {metrics.overall_score:.2f}")
    print()
    print("=== Sanitized Sample ===")
    for interaction in cleaned_data:
        print(f"User: {interaction.user_input}")
        print(f"Agent: {interaction.agent_response}")
        print(f"Tool Calls: {[tc.name for tc in interaction.tool_calls]}")
        print()
    data_dir = Path(__file__).parent.parent / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    if list(raw_dir.glob("*.jsonl")):
        print("=== Running from Directory ===")
        output_path = pipeline.run_from_directory(
            str(raw_dir),
            str(processed_dir),
        )
        print(f"Cleaned data saved to: {output_path}")


if __name__ == "__main__":
    main()
