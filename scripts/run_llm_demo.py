"""Run the vulnerability-analysis demo with a real LangChain chat model."""

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langchain.analyzer import (
    LangChainVulnerabilityAnalyzer,
)
from agentic_lab.adapters.langchain.model import create_chat_model
from agentic_lab.adapters.langgraph.llm_graph import (
    run_llm_analysis_graph,
)


def main() -> None:
    """Run the real-model LangGraph demo and print the validated result."""
    model = create_chat_model()
    analyzer = LangChainVulnerabilityAnalyzer(model)

    output = run_llm_analysis_graph(
        analyzer=analyzer,
        cve_id=DEMO_CVE_ID,
    )

    print(f"analysis_source: {output['analysis_source']}")
    print(f"validation_passed: {output['validation_passed']}")
    print(f"validation_reason: {output['validation_reason']}")
    print()
    print(output["result"].model_dump_json(indent=2))


if __name__ == "__main__":
    main()
