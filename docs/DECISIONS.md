# Technology decisions

Each entry follows the same shape: the question, what was evaluated, the recommendation, and when to revisit it.

## 1. Who judges a spreadsheet answer?

Evaluated: an LLM judge, versus a deterministic formula engine compared against an independently computed answer key.
Recommendation: deterministic engine. LLMs are unreliable at spreadsheet arithmetic, cost money per check, and can be talked into accepting wrong answers. The engine is free, instant and reproducible, and the answer key is computed by separate code so the two cross-check each other (see tests/test_validator.py).
Revisit when: missions need open-ended grading such as chart quality or dashboard layout. Use an LLM there with a rubric, and keep it advisory.

## 2. Expose the game through MCP?

Evaluated: plain function calls between modules, versus an MCP server that wraps the same service.
Recommendation: keep logic in GameService and expose it through a thin MCP layer. The service stays testable on its own, and any MCP client (Claude Code, Cursor, Desktop) can play and test missions with real tool calls. The MCP SDK moved to 2.x (MCPServer replaces FastMCP), so the dependency is pinned at mcp>=2.0.
Revisit when: tool count grows large. Then group tools or add resource endpoints.

## 3. How to stop the coach leaking answers?

Evaluated: prompt instructions only, versus architecture plus filters.
Recommendation: architecture first. The coach never receives the answer key, so there is nothing to extract. Layered on top: input screening for injection and extraction attempts, and an output check that blocks the answer value or reference formula. Pattern filters are a baseline and will miss novel attacks, so the regression set in tests/test_guardrails.py should grow with every bypass found.
Revisit when: the coach becomes an LLM with tool access. Add a classifier-based guard and red-team it.

## 4. Infrastructure as code

Evaluated: Crossplane, Terraform, Pulumi.
Recommendation for this project: Terraform or Pulumi. Crossplane needs a Kubernetes control plane, which is more than a single stateless API needs. Not built yet.
Revisit when: running on several clouds with a platform team that already operates Kubernetes.
