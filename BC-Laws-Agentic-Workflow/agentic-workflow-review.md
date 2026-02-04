# Agentic Workflow Review

---

## 1. Executive Summary

The project contains a functional agentic workflow built on **FastMCP** (Model Context Protocol) with a **FastAPI HMVC backend**. The agent system supports tool-calling orchestration via Azure OpenAI, with specialized search agents backed by Neo4j. The core agent infrastructure works, but the orchestrator and community detection agent remain incomplete. The system is tightly coupled to Azure and AWS cloud services with no abstraction layer, meaning adoption into a new app requires rework at the model integration level.

---

## 2. Agent Architecture

### 2.1 Registry Pattern

The system uses a centralized **AgentRegistry** (`app/modules/agent/agents/__init__.py`) that:

- Auto-discovers agents from subdirectories at startup
- Maintains a capability-to-agent mapping
- Exposes a single combined FastMCP server with all agent tools

### 2.2 Agent Execution Flow

```
User Query
  -> POST /api/agent/
  -> AgentService.process_agent_chat()
  -> Azure OpenAI LLM (with tool definitions)
  -> LLM selects tool(s)
  -> FastMCP Client calls agent tool
  -> Tool returns result
  -> Result fed back to LLM
  -> Loop until finish_reason == "stop" (max 10 iterations)
  -> Final synthesized response returned
```

### 2.3 Agents

| Agent | Status | Description |
|-------|--------|-------------|
| **Semantic Search** | Working | Cosine similarity search against Neo4j vector index (`Acts_Updatedchunks`). Uses `all-MiniLM-L6-v2` embeddings. |
| **Explicit Search** | Working | Executes read-only Cypher queries. Includes mutation safety validation (rejects writes). |
| **Community Detection** | Stub | Returns hardcoded placeholder data. No real graph analysis implemented. |
| **Orchestrator** | Partial | Can plan multi-agent tasks (parallel, sequential, adaptive strategies). Full execution chain not validated. |

### 2.4 Tool Integration

Each agent is a FastMCP server. Tools are registered with `@agent_mcp.tool()` decorators and return structured dictionaries. The AgentService converts FastMCP tool schemas into Azure OpenAI function-calling format at runtime.

---

## 3. Backend Infrastructure & Model Dependencies

### 3.1 LLM Providers

**Azure OpenAI** (agent orchestration):
- Used as the "brain" of the tool-calling loop
- Direct HTTP calls via `requests.post` to an Azure endpoint
- Authenticated with API key (`AZURE_AI_KEY`)
- No SDK used — raw REST API
- Manages conversation history in-memory

**AWS Bedrock** (RAG/chat inference):
- Three models configured: Mixtral 8x7B, Llama 3 8B, Claude 3.5 Sonnet
- Uses `boto3` client, region `ca-central-1`
- Authenticated via AWS access key/secret
- Used for the non-agent chat pipeline

### 3.2 Local Model Compatibility

**Current state: Not compatible with local models without changes.**

The `AzureAI` class (`app/shared/models/azure.py`) makes direct HTTP calls to Azure's API with Azure-specific auth headers and response parsing. The Bedrock integration similarly depends on AWS SDK authentication and model IDs.

To run on OpenShift with local models, you would need to:

1. **Replace `AzureAI` with an OpenAI-compatible client** — Local model servers (vLLM, Ollama, llama.cpp) expose OpenAI-compatible APIs. The current `AzureAI` class is close to this format but has Azure-specific auth headers.
2. **Abstract the model layer** — Create a common interface (e.g., `LLMClient`) that both cloud and local backends can implement.
3. **Handle tool-calling support** — The agent loop depends on the LLM returning `tool_calls` in its response. Local models must support function/tool calling (vLLM and Ollama do with compatible models).

### 3.3 Other Services

| Service | Purpose | Coupling |
|---------|---------|----------|
| **Neo4j** | Graph DB + vector index | Tightly coupled — agents query it directly |
| **PostgreSQL** | TruLens feedback tracking | Optional, monitoring only |
| **Sentence Transformers** | Embedding generation (`all-MiniLM-L6-v2`) | Runs locally, no cloud dependency |
| **Cross-Encoder** | Re-ranking (`ms-marco-MiniLM-L-6-v2`) | Runs locally, no cloud dependency |

---

## 4. What to Reclaim for a New App

### 4.1 High Value — Reuse Directly

- **AgentRegistry pattern** — The auto-discovery and capability mapping design is clean and framework-agnostic. Can be lifted with minimal changes.
- **FastMCP agent structure** — The tool decorator pattern and agent-as-server model is solid. Agents are self-contained and can be ported individually.
- **Tool-calling loop logic** — The iteration pattern in `AgentService.process_agent_chat()` (lines 126-182) is the core orchestration logic. Reusable with any OpenAI-compatible API.
- **Semantic search agent** — The vector search implementation against Neo4j is working and well-structured.
- **Explicit search agent** — Includes useful safety validation (mutation rejection).

### 4.2 Medium Value — Reuse With Modifications

- **AzureAI class** — The conversation history management and tool response handling are useful, but the HTTP layer needs to be swapped to an OpenAI-compatible client or SDK.
- **Database schema injection** — The pattern of dynamically fetching Neo4j schema and injecting it as a system message is a good approach, portable to any LLM.
- **HMVC module structure** — The module registry pattern (`controllers/services/models/views` per module) is clean but may be more structure than a new app needs initially.

### 4.3 Low Value — Do Not Reuse

- **Community detection agent** — Stub only, no real implementation.
- **Orchestrator agent** — Incomplete, untested execution chain.
- **Bedrock integration** — AWS-specific, not useful for OpenShift/local deployment.
- **TruLens integration** — Monitoring add-on, not core functionality.

---

## 5. Key Files Reference

| File | Purpose |
|------|---------|
| `app/modules/agent/agents/__init__.py` | AgentRegistry — agent discovery and combined MCP server |
| `app/modules/agent/services/agent_service.py` | Core tool-calling orchestration loop |
| `app/shared/models/azure.py` | Azure OpenAI client (conversation + tool history) |
| `app/shared/models/bedrock.py` | AWS Bedrock model wrappers |
| `app/modules/agent/agents/search/semantic_search/` | Semantic search agent |
| `app/modules/agent/agents/search/explicit_search/` | Explicit Cypher search agent |
| `app/modules/agent/agents/orchestrator/` | Orchestrator agent (partial) |

---

## 6. Recommendations

1. **Extract the agent registry + FastMCP pattern first.** This is the most reusable piece and defines the architecture of the new app's agent layer.
2. **Replace `AzureAI` with an OpenAI-compatible SDK** (e.g., the `openai` Python package). This makes the tool-calling loop work with local models (vLLM, Ollama) on OpenShift without Azure dependency.
3. **Keep the semantic and explicit search agents** if the new app also uses Neo4j. They are self-contained and working.
4. **Skip the orchestrator and community detection agents.** They are incomplete and would need to be rebuilt anyway.
5. **Preserve the embedding and re-ranking models.** `all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2` run locally and have no cloud dependency.
