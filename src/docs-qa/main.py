"""Documentation Q&A agent -- a Microsoft Foundry *hosted* agent.

Demonstrates the grounded-answer pattern: the agent may only answer from what
retrieval returns, must cite the chunk it used, and must decline when the corpus
has no answer. That last behaviour is the one worth demoing -- it is what makes
a grounded agent trustworthy, and it is directly measurable in an eval.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

import retrieval

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("docs-qa")

INSTRUCTIONS = """
You answer questions about the Contoso Payments platform using ONLY the bundled
documentation corpus.

Process:
1. Call `search_documentation` with the user's question.
2. If the top results do not actually contain the answer, call
   `search_documentation` again with different wording before giving up.
3. Call `fetch_document` only when you need more surrounding context than the
   returned chunk provides.

Answering rules -- these are the point of this agent, do not relax them:
- Every factual sentence must come from a retrieved chunk.
- End your answer with a `Sources:` line listing the `citation` values you used,
  exactly as returned by the tool.
- If `search_documentation` returns no results, or the results do not answer the
  question, reply exactly:
  "I don't have that in the Contoso Payments documentation." You may then list
  the available document ids so the user knows the scope. Do not add anything
  else, and do not answer the question from your own knowledge.
- Never use general world knowledge to fill a gap, even when you are confident.
- Never invent a citation. If you did not retrieve it, you cannot cite it.
- Be concise: answer in at most 150 words before the Sources line.
"""


@tool(approval_mode="never_require")
def search_documentation(
    query: Annotated[str, Field(description="Natural-language search query.")],
    top_k: Annotated[int, Field(description="How many chunks to return, 1-10.")] = 3,
) -> str:
    """Search the Contoso Payments documentation corpus for relevant passages."""
    results = retrieval.search(query, top_k=top_k)
    logger.info("search_documentation(%r) -> %d hit(s)", query, len(results))
    return json.dumps(
        {
            "query": query,
            "result_count": len(results),
            "results": results,
            "available_documents": retrieval.list_documents() if not results else None,
        }
    )


@tool(approval_mode="never_require")
def fetch_document(
    doc_id: Annotated[str, Field(description="Document id, e.g. 'refunds-policy'.")],
) -> str:
    """Fetch a full documentation page by id."""
    result = retrieval.get_document(doc_id)
    logger.info("fetch_document(%s) -> found=%s", doc_id, result["found"])
    return json.dumps(result)


def build_agent() -> Agent:
    """Construct the agent. Split out so tests can build it without serving."""
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    return Agent(
        client=client,
        name="docs-qa",
        instructions=INSTRUCTIONS,
        tools=[search_documentation, fetch_document],
        default_options={"store": False},
    )


def main() -> None:
    logger.info("starting docs-qa hosted agent over %d document(s)", len(retrieval.list_documents()))
    ResponsesHostServer(build_agent()).run()


if __name__ == "__main__":
    main()
