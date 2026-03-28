# Running Custom Coding Agents

Findings and guide for setting up AI coding agents using OpenCode and Pi with Azure OpenAI and OpenShift-hosted models.

> **Status:** OpenCode works with OpenShift-hosted (local) models and supports multi-agent routing. Azure OpenAI streaming works, but **tool calling is broken** due to an upstream AI SDK bug ([vercel/ai #7924](https://github.com/vercel/ai/issues/7924)), and **large request bodies are blocked** by APIM PII redaction policy. **Pi (pi.dev)** is being evaluated as an alternative harness that bypasses the AI SDK entirely — it may resolve the tool calling blocker. See [Connecting to Azure OpenAI](#connecting-to-azure-openai) and [Pi as Alternative Harness](#pi-as-alternative-harness) for details.

## Table of Contents

- [Overview](#overview)
- [Harness Comparison](#harness-comparison)
- [Prerequisites](#prerequisites)
- [Setting Up OpenCode](#setting-up-opencode)
- [Connecting to Azure OpenAI](#connecting-to-azure-openai)
- [Pi as Alternative Harness](#pi-as-alternative-harness)
- [Connecting to OpenShift-Hosted Models](#connecting-to-openshift-hosted-models)
- [Creating Custom Agents](#creating-custom-agents)
- [Model Routing Strategy](#model-routing-strategy)
- [Recommended Configuration](#recommended-configuration)
- [Troubleshooting](#troubleshooting)

---

## Findings Summary


| Capability                 | Status       | Notes                                                                |
| -------------------------- | ------------ | -------------------------------------------------------------------- |
| OpenCode as harness        | ✅ Working    | Preferred over Claude Code for our use case                          |
| OpenShift-hosted models    | ✅ Working    | Via `@ai-sdk/openai-compatible` provider                             |
| Azure OpenAI streaming     | ✅ Working    | Both `@ai-sdk/azure` and `@ai-sdk/openai-compatible` work           |
| Azure OpenAI tool calling  | ❌ Blocked    | AI SDK bug strips tool schemas — [vercel/ai #7924](https://github.com/vercel/ai/issues/7924) |
| APIM PII redaction         | ❌ Blocked    | Blocks request bodies >10KB; OpenCode sends ~62KB with tools         |
| APIM rate limit            | ⚠️ Very low  | 1000 tokens/min — triggers at ~10KB request bodies                   |
| Pi (pi.dev) as harness     | 🔍 Evaluating | Does not use AI SDK — may bypass tool schema bug. Needs testing      |
| Multi-agent model routing  | ✅ Working    | Config-time routing via agent-to-model mapping                       |
| Per-agent model assignment | ✅ Working    | Each agent can target a different provider/model                     |


---

## Harness Comparison


| Feature                     | OpenCode                                                                                                                 | Pi (pi.dev)                                                                  | Claude Code                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Provider support            | 75+ providers (OpenAI, Azure, Anthropic, local, etc.)                                                                    | Anthropic, OpenAI, Google, Azure, Bedrock, Groq, xAI, OpenRouter, any OpenAI-compatible | Anthropic API only                                                           |
| Azure OpenAI                | Streaming works, **tool calling blocked by AI SDK bug** and **APIM PII redaction** (see [findings](#connecting-to-azure-openai)) | Native `azure-openai-responses` API — does not use Vercel AI SDK             | Requires proxy to translate API formats                                      |
| OpenAI-compatible endpoints | Native support via `@ai-sdk/openai-compatible`                                                                           | Native via `openai-completions` API                                          | Not supported natively                                                       |
| Tool calling                | Broken — AI SDK strips tool schemas ([vercel/ai #7924](https://github.com/vercel/ai/issues/7924))                        | Own implementation with TypeBox schemas — not affected by AI SDK bug          | Works (Anthropic API only)                                                   |
| Per-agent model assignment  | Yes — each agent can target a different provider/model                                                                   | Yes — switch models mid-session, custom models via `models.json`             | Internal only (Haiku for search, Sonnet for review, Opus for implementation) |
| Custom agents               | Full control via JSON config or Markdown files                                                                           | Extensions, skills, prompt templates, AGENTS.md                              | Limited to model selection                                                   |
| Agent types                 | Primary agents + subagents with `@mention` invocation                                                                    | No built-in sub-agents — build via extensions or tmux                        | Single agent workflow                                                        |
| System prompt size          | Large (~62KB with tools)                                                                                                 | Minimal by design — may fit under APIM PII scan limit                        | Large                                                                        |
| Open source                 | Yes                                                                                                                      | Yes                                                                          | No                                                                           |


**Why OpenCode was initially preferred:** OpenCode's multi-agent architecture and native OpenAI-compatible support made it the best harness for connecting to OpenShift-hosted models with per-task model routing. However, the Vercel AI SDK dependency has introduced two blockers for Azure OpenAI tool calling that are outside our control.

**Why Pi is being evaluated:** Pi uses its own LLM layer (`@mariozechner/pi-ai`) instead of the Vercel AI SDK. This means it is not affected by the tool schema serialization bug that blocks OpenCode. Pi also has a much smaller system prompt and only 4 core tools (vs OpenCode's 12), which may keep request bodies under the APIM PII redaction scan limit (~10-20KB). If confirmed, Pi would bypass both blockers simultaneously.

---

## Prerequisites

- **OpenCode CLI** or **Pi CLI** (`npm i -g @mariozechner/pi-coding-agent`) installed
- Access to **OpenShift** running OpenAI-compatible model endpoints
- OpenShift model **endpoint URL**
- Access to BC Gov **Azure OpenAI** subscription with API key

---

## Setting Up OpenCode

OpenCode is configured via `opencode.json` (or `opencode.jsonc` for comments). Configuration is loaded in this order, with later sources overriding earlier ones:

1. **Remote config** (`.well-known/opencode`) — organizational defaults
2. **Global config** (`~/.config/opencode/opencode.json`) — user preferences
3. **Custom config** (`OPENCODE_CONFIG` env var) — custom overrides
4. **Project config** (`opencode.json` in project root) — project-specific settings

For team-wide defaults, use the global config. For project-specific model assignments, use the project config.

### Authentication

Run the `/connect` command inside OpenCode's TUI and select your provider, or configure API keys directly in the config file using environment variable references:

```json
{
  "provider": {
    "openshift": {
      "options": {
        "apiKey": "{env:OPENSHIFT_MODEL_API_KEY}"
      }
    }
  }
}
```

The `{env:VARIABLE_NAME}` syntax keeps credentials out of config files.

---

## Connecting to Azure OpenAI

> **⚠️ PARTIALLY UNBLOCKED:** Azure OpenAI streaming works through both `@ai-sdk/azure` and `@ai-sdk/openai-compatible`. However, **tool calling is broken** due to an upstream AI SDK bug that strips tool schemas, and **large request bodies are blocked** by APIM PII redaction policy. Both issues must be resolved before coding agents (which depend entirely on tool calling) can function. **Pi (pi.dev) may bypass both blockers** — see [Pi as Alternative Harness](#pi-as-alternative-harness).

### What Works

The APIM team added an OpenAI-compatible `/v1` endpoint, resolving the original URL construction issue. Both providers now connect successfully:

```
https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/v1
```

Authentication uses `Authorization: Bearer <key>` header. Streaming chat completions work from both providers:

```bash
curl "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BCGOV_AZURE_API_KEY" \
  -d '{"model":"gpt-4.1","messages":[{"role":"user","content":"hello"}]}'
```

### Available Azure Deployments

The following models are deployed on our test tenant (`sdpr-invoice-automation`):


| Deployment Name | Model               | Scale Type     | Capacity |
| --------------- | ------------------- | -------------- | -------- |
| `gpt-4.1`       | GPT-4.1             | GlobalStandard | 300      |
| `gpt-4.1-mini`  | GPT-4.1 Mini        | GlobalStandard | 1500     |
| `gpt-4.1-nano`  | GPT-4.1 Nano        | GlobalStandard | 1500     |
| `gpt-4o`        | GPT-4o              | GlobalStandard | 300      |
| `gpt-4o-mini`   | GPT-4o Mini         | GlobalStandard | 1500     |
| `o4-mini`       | o4-mini (reasoning) | GlobalStandard | 100      |
| `gpt-5-mini`    | GPT-5 Mini          | GlobalStandard | 100      |
| `gpt-5-nano`    | GPT-5 Nano          | GlobalStandard | 1500     |


### Working Provider Configuration (OpenCode)

Both providers connect and stream correctly. `@ai-sdk/azure` is preferred since it uses the standard Azure SDK path:

**Using `@ai-sdk/azure`:**

```jsonc
{
  "provider": {
    "bcgov-azure": {
      "npm": "@ai-sdk/azure",
      "name": "BC Gov Azure",
      "options": {
        "baseURL": "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai",
        "apiKey": "{env:BCGOV_AZURE_API_KEY}"
      },
      "models": {
        "gpt-4.1": { "name": "GPT-4.1" },
        "gpt-4.1-mini": { "name": "GPT-4.1 Mini" },
        "o4-mini": { "name": "o4-mini (reasoning)" }
      }
    }
  }
}
```

Note: `@ai-sdk/azure` supports `baseURL` which overrides `resourceName`. When a `baseURL` is provided, the SDK constructs `{baseURL}/v1/chat/completions`, which matches our APIM endpoint.

**Using `@ai-sdk/openai-compatible`:**

```jsonc
{
  "provider": {
    "bcgov-azure": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "BC Gov Azure",
      "options": {
        "baseURL": "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/v1",
        "apiKey": "{env:BCGOV_AZURE_API_KEY}"
      },
      "models": {
        "gpt-4.1": { "name": "GPT-4.1" }
      }
    }
  }
}
```

### Blocker 1: AI SDK Tool Schema Serialization Bug

**Impact:** All tool calling fails — coding agents cannot function.

The Vercel AI SDK has a known bug in its shared `@ai-sdk/provider-utils` package where the `asSchema()` function strips tool schema definitions during serialization. When you define a tool with `jsonSchema()` or zod, the SDK sends empty schemas to the API:

**What we define:**
```json
{
  "type": "object",
  "properties": {
    "command": { "type": "string", "description": "The command to execute" }
  },
  "required": ["command"],
  "additionalProperties": false
}
```

**What the SDK actually sends:**
```json
{
  "properties": {},
  "additionalProperties": false
}
```

The `type: "object"` field is missing, all property definitions are stripped, and `required` is gone. Azure's Python backend deserializes the missing `type` as Python `None`, returning:

```
Invalid schema for function 'bash': schema must be a JSON Schema of 'type: "object"', got 'type: "None"'.
```

This bug affects **both** `@ai-sdk/azure` and `@ai-sdk/openai-compatible` because they share the same `@ai-sdk/provider-utils` serialization layer. Testing confirmed identical empty schemas from both providers.

**Upstream issues (both still open):**
- [vercel/ai #7924](https://github.com/vercel/ai/issues/7924) — "OpenAI-compatible providers fail with tools - missing 'type: object' in JSON Schema"
- [vercel/ai #9761](https://github.com/vercel/ai/issues/9761) — "Vertex AI strips tool parameters schema to empty properties" (same root cause)

**Workaround (for custom application code only, not OpenCode):** A custom `fetch` interceptor can patch tool schemas before they reach the API. This was validated in testing — all tool calls succeed with the patch. However, OpenCode does not support injecting custom fetch functions through its config layer.

```typescript
// Workaround: patch tool schemas in a custom fetch interceptor
const fixedFetch: typeof fetch = async (input, init) => {
  if (init?.body) {
    const body = JSON.parse(init.body as string);
    if (body.tools) {
      for (const t of body.tools) {
        if (t.function?.parameters) {
          if (!t.function.parameters.type || t.function.parameters.type === "None") {
            t.function.parameters.type = "object";
          }
        }
      }
      init = { ...init, body: JSON.stringify(body) };
    }
  }
  return fetch(input, init);
};
```

Note: This only patches the missing `type` field. The stripped `properties` still means the model won't know what parameters to generate — it just won't error. A full fix requires the upstream AI SDK bug to be resolved.

### Blocker 2: APIM PII Redaction Blocks Large Requests

**Impact:** OpenCode's ~62KB request bodies are rejected before reaching the model.

The APIM gateway has PII redaction enabled with `fail_closed: true` in the Terraform configuration. This scans all request bodies for personally identifiable information before forwarding to Azure OpenAI. The scanner has a size limit — testing shows it fails on bodies above approximately 10-20KB.

OpenCode sends approximately 62KB per request because it includes a large system prompt and 12 tool definitions (bash, file read/write, grep, glob, webfetch, etc.) in every API call. When the PII scanner cannot process the full body, `fail_closed` blocks the entire request:

```
PII redaction incomplete. Not all messages were scanned. Request blocked for data protection.
```

**Test results (body size vs. success):**

| Body Size | Result |
|-----------|--------|
| 5KB       | ✅ Success |
| 10KB      | ❌ Rate limited (1000 tokens/min) |
| 20KB+     | ❌ PII redaction blocked |

The rate limit (`tokens_per_minute: 1000`) is also extremely low and triggers before the PII redaction limit on bodies around 10KB.

**Required APIM changes (any of these would work):**
- Disable PII redaction for the `/sdpr-invoice-automation/openai/v1` endpoint
- Increase the PII scan size limit well above 62KB
- Set `fail_closed = false` so requests pass through when scanning is incomplete
- Significantly increase the `tokens_per_minute` rate limit

### What Was Attempted (Historical)

The original blocker was URL construction — the APIM gateway only accepted deployment-based URLs, while the AI SDK constructed `/v1` URLs. This has been resolved:

1. **Built-in Azure OpenAI provider** — Used `AZURE_RESOURCE_NAME` to construct `https://{name}.openai.azure.com/...`. Did not match APIM gateway. **Resolved:** APIM team added `/v1` endpoint.
2. **Custom provider with `@ai-sdk/azure`** — `baseURL` override now works correctly with the new endpoint. **Resolved.**
3. **Custom provider with `@ai-sdk/openai-compatible`** — Works with the new `/v1` endpoint. **Resolved.**

### Path Forward

Both remaining blockers are external to OpenCode:

1. **AI SDK bug (tool schemas):** Wait for upstream fix in `@ai-sdk/provider-utils`, or contribute a PR. The fix is straightforward — adding `type: 'object'` to the `asSchema()` function and preserving property definitions. Monitor [vercel/ai #7924](https://github.com/vercel/ai/issues/7924).
2. **APIM PII redaction:** Request the APIM team to disable PII redaction or increase scan limits for the coding agent endpoint. This is a policy change, not a code change.
3. **APIM rate limit:** Request an increase from 1000 tokens/min to something usable for interactive coding (recommend 100K+ tokens/min).
4. **Evaluate Pi (pi.dev):** Pi does not use the Vercel AI SDK and has a much smaller request footprint. It may bypass both blockers. See [Pi as Alternative Harness](#pi-as-alternative-harness).

### Test Scripts

Test scripts used to isolate and verify these findings are available in the repository:

- `test-waf.ts` — Comprehensive test suite covering streaming, tool schema serialization debugging, body size thresholds, and full OpenCode-like setups with both `@ai-sdk/azure` and `@ai-sdk/openai-compatible` providers. Run with `BCGOV_AZURE_API_KEY=<key> bun run test-waf.ts`.

---

## Pi as Alternative Harness

[Pi](https://pi.dev/) (`@mariozechner/pi-coding-agent`) is a minimal, extensible terminal coding agent that may bypass both Azure OpenAI blockers because it does not depend on the Vercel AI SDK.

### Why Pi May Solve Our Blockers

**Blocker 1 (Tool schema bug):** Pi uses its own LLM layer (`@mariozechner/pi-ai`) which implements tool calling with [TypeBox](https://github.com/sinclairzx81/typebox) schemas and handles serialization directly. It does not use `@ai-sdk/provider-utils`, so it is not affected by [vercel/ai #7924](https://github.com/vercel/ai/issues/7924).

**Blocker 2 (PII redaction body size):** Pi was designed with a minimal system prompt — the author explicitly calls out other harnesses for their 10,000+ token system prompts. Pi ships with only 4 core tools (read, write, edit, bash) vs OpenCode's 12. The total request body could be dramatically smaller, potentially staying under the ~10-20KB PII scan limit. This needs to be verified with testing.

### Azure OpenAI Configuration for Pi

Pi has native Azure OpenAI support via the `azure-openai-responses` API:

```bash
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_BASE_URL=https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai
```

Or via custom models in `~/.pi/agent/models.json` using the `openai-completions` API:

```json
{
  "providers": {
    "bcgov-azure": {
      "baseUrl": "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/v1",
      "apiKey": "BCGOV_AZURE_API_KEY",
      "api": "openai-completions",
      "models": [
        {
          "id": "gpt-4.1",
          "name": "GPT-4.1",
          "reasoning": false,
          "input": ["text"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
          "contextWindow": 1047576,
          "maxTokens": 32768
        }
      ]
    }
  }
}
```

### Pi vs OpenCode Comparison

| Aspect                   | OpenCode                                    | Pi                                              |
| ------------------------ | ------------------------------------------- | ------------------------------------------------ |
| LLM layer                | Vercel AI SDK (`@ai-sdk/*`)                 | Own implementation (`@mariozechner/pi-ai`)       |
| Tool schema format       | Broken (AI SDK bug)                         | TypeBox — works correctly                        |
| Core tools               | 12 (bash, read, write, edit, glob, grep, webfetch, task, etc.) | 4 (read, write, edit, bash)           |
| System prompt size       | ~62KB with tools                            | Minimal — model determines agent behavior via RL |
| Sub-agents               | Built-in with `@mention`                    | Build via extensions or spawn tmux sessions      |
| Plan mode                | Built-in                                    | Build via extensions or use TODO files            |
| Permission gates         | Built-in (`allow`/`ask`/`deny`)             | Build via extensions or run in containers        |
| Extensibility            | JSON config + Markdown agents               | TypeScript extensions, skills, prompt templates  |
| Project context          | `opencode.json` + `OPENCODE.md`             | `AGENTS.md` + `SYSTEM.md`                        |

### Tradeoffs

Pi intentionally ships without sub-agents, plan mode, or permission gates. The philosophy is that these are built via the extension system or community packages rather than being baked into the core. This means less out of the box, but also less harness to fight against — which is relevant given that OpenCode's dependencies (the AI SDK) are the source of the current blockers.

The author's blog post notes that self-hosted models often don't work well with OpenCode specifically because of the Vercel AI SDK's tool calling issues, which aligns exactly with our findings.

### Next Steps

1. Install Pi: `npm i -g @mariozechner/pi-coding-agent`
2. Configure Azure endpoint with env vars above
3. Test tool calling against APIM gateway — verify tool schemas are serialized correctly
4. Measure request body size — verify it stays under PII redaction limit
5. If both pass, evaluate Pi as primary harness for Azure OpenAI coding tasks

---

## Connecting to OpenShift-Hosted Models

Models hosted on OpenShift (via vLLM, Ollama, text-generation-inference, or similar) typically expose an OpenAI-compatible API. OpenCode supports these through the `@ai-sdk/openai-compatible` provider.

### Configuration

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "openshift": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenShift Models",
      "options": {
        "baseURL": "https://your-openshift-model-endpoint.apps.cluster.example.com/v1"
      },
      "models": {
        "codellama-34b": {
          "name": "Code Llama 34B",
          "limit": {
            "context": 16384,
            "output": 4096
          }
        },
        "deepseek-coder-v2": {
          "name": "DeepSeek Coder V2",
          "limit": {
            "context": 128000,
            "output": 8192
          }
        }
      }
    }
  }
}
```

If authentication is required:

```jsonc
{
  "provider": {
    "openshift": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenShift Models",
      "options": {
        "baseURL": "https://your-endpoint.apps.cluster.example.com/v1",
        "apiKey": "{env:OPENSHIFT_MODEL_API_KEY}"
      },
      "models": {
        "codellama-34b": {
          "name": "Code Llama 34B",
          "limit": {
            "context": 16384,
            "output": 4096
          }
        }
      }
    }
  }
}
```

The `limit` fields tell OpenCode the context window and output limits of your models, which helps it manage context compaction and output truncation appropriately.

### Using LOCAL_ENDPOINT (Alternative)

For quick local testing, you can also use the `LOCAL_ENDPOINT` environment variable:

```bash
export LOCAL_ENDPOINT="https://your-endpoint.apps.cluster.example.com/v1"
```

OpenCode will automatically detect and load models from this endpoint.

---

## Creating Custom Agents

Agents are specialized AI assistants configured for specific tasks. Each agent can use a different model, have different tool permissions, and carry a custom system prompt.

### Agent Types

- **Primary agents** — The main agents you interact with directly. Switch between them with the **Tab** key. OpenCode ships with `build` (full access) and `plan` (read-only analysis).
- **Subagents** — Invoked by primary agents or manually via `@mention` (e.g., `@explorer find the auth middleware`). OpenCode ships with `general` and `explore`.

### Defining Agents in JSON

Add agents to your `opencode.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "description": "Primary coding agent for implementation work",
      "mode": "primary",
      "model": "openshift/codellama-34b",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      },
      "permission": {
        "edit": "allow",
        "bash": "allow"
      }
    },
    "plan": {
      "description": "Analysis and planning without making changes",
      "mode": "primary",
      "model": "openshift/codellama-34b",
      "tools": {
        "write": false,
        "edit": false,
        "bash": false
      }
    },
    "reviewer": {
      "description": "Code review with read-only access",
      "mode": "subagent",
      "model": "openshift/codellama-34b",
      "temperature": 0.1,
      "tools": {
        "write": false,
        "edit": false,
        "bash": false
      }
    },
    "explorer": {
      "description": "Fast codebase search and exploration",
      "mode": "subagent",
      "model": "openshift/codellama-34b",
      "tools": {
        "write": false,
        "edit": false,
        "bash": false
      }
    }
  }
}
```

### Defining Agents in Markdown

For agents with longer system prompts, use Markdown files placed in:

- **Global:** `~/.config/opencode/agents/`
- **Per-project:** `.opencode/agents/`

Example — `.opencode/agents/security-auditor.md`:

```markdown
---
description: Audits code for security vulnerabilities and compliance issues
mode: subagent
model: openshift/codellama-34b
temperature: 0.1
tools:
  write: false
  edit: false
  bash: true
---

You are a security auditor for BC Government applications. Focus on:

- OWASP Top 10 vulnerabilities
- Input validation and sanitization
- Authentication and authorization issues
- Sensitive data exposure
- BC Gov security policy compliance

When reviewing code, provide specific line references and severity ratings.
Do not make changes directly — report findings only.
```

The file name becomes the agent name (e.g., `security-auditor`). Invoke it with `@security-auditor review the auth module`.

### Creating Agents via CLI

OpenCode also provides an interactive command to scaffold agents:

```bash
opencode agents create
```

This walks you through selecting a name, description, model, and tool access, then creates the Markdown file for you.

### Key Agent Options


| Option        | Description                                                   |
| ------------- | ------------------------------------------------------------- |
| `description` | What the agent does (required)                                |
| `mode`        | `primary` or `subagent`                                       |
| `model`       | `provider/model-id` (e.g., `openshift/codellama-34b`)         |
| `prompt`      | System prompt (inline string or `{file:./path/to/prompt.md}`) |
| `temperature` | 0.0–1.0 (lower = more deterministic)                          |
| `tools`       | Enable/disable `write`, `edit`, `bash`, `webfetch`, etc.      |
| `permission`  | Set `allow`, `ask`, or `deny` for each tool                   |
| `maxSteps`    | Limit agentic iterations before forcing a text response       |


---

## Model Routing Strategy

### How Claude Code Does It

Claude Code internally routes tasks to different model tiers automatically:

- **Haiku** (lightweight) — codebase search, file indexing
- **Sonnet** (mid-tier) — code review, reading comprehension
- **Opus** (heavyweight) — complex implementation, multi-file refactoring

The developer doesn't choose which model handles which task — the system decides at runtime.

### How OpenCode Does It

OpenCode takes a **config-time routing** approach rather than runtime classification. Each agent is statically assigned a model, and the developer (or the calling agent) decides which agent to invoke.

This means routing is controlled by:

1. **Agent-to-model mapping** — defined in `opencode.json`
2. **Agent selection** — the developer switches agents with Tab or `@mentions` a subagent
3. **Subagent invocation** — primary agents can call subagents for specialized tasks based on their descriptions

### Recommended Routing Pattern

**Target state** (when Azure tool calling is unblocked):


| Task Type                        | Agent              | Model              | Provider  |
| -------------------------------- | ------------------ | ------------------ | --------- |
| Implementation / complex changes | `build`            | GPT-4.1 or o4-mini | Azure     |
| Planning / architecture analysis | `plan`             | GPT-4.1 Mini       | Azure     |
| Code review                      | `reviewer`         | GPT-4.1 Mini       | Azure     |
| Codebase search / exploration    | `explorer`         | Code Llama 34B     | OpenShift |
| Security audit                   | `security-auditor` | GPT-4.1            | Azure     |
| Quick questions / documentation  | `general`          | Code Llama 34B     | OpenShift |


**Current state** (Azure tool calling blocked):


| Task Type | Agent                 | Model          | Provider  |
| --------- | --------------------- | -------------- | --------- |
| All tasks | `build`, `plan`, etc. | Code Llama 34B | OpenShift |


Without Azure tool calling, the routing strategy is limited to whatever models are available on OpenShift. The multi-agent architecture still works — agents can be assigned different system prompts, tool permissions, and temperatures — but model diversity requires Azure tool calling to be unblocked (pending AI SDK bug fix + APIM policy changes, or successful Pi evaluation).

### Cost Considerations

- **Azure models** are billed per token through the subscription. When tool calling is unblocked, use them for tasks where quality matters (implementation, code review, security audit).
- **OpenShift models** have no per-token cost (infrastructure cost only). Currently the only option for coding agents, suitable for all tasks but with lower capability than Azure-hosted models like GPT-4.1.

---

## Recommended Configuration

Below is a working configuration using OpenShift-hosted models with a multi-agent setup. Azure provider config is included but tool calling will not work until the upstream AI SDK bug ([vercel/ai #7924](https://github.com/vercel/ai/issues/7924)) is fixed and APIM PII redaction limits are raised. If Pi testing succeeds, a Pi-specific configuration section will be added.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",

  // Default model
  "model": "openshift/codellama-34b",

  // Provider configuration
  "provider": {
    // Azure OpenAI — streaming works, tool calling blocked (AI SDK bug + PII redaction)
    // If Pi evaluation succeeds, use Pi for Azure instead
    "bcgov-azure": {
      "npm": "@ai-sdk/azure",
      "name": "BC Gov Azure",
      "options": {
        "baseURL": "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai",
        "apiKey": "{env:BCGOV_AZURE_API_KEY}"
      },
      "models": {
        "gpt-4.1": { "name": "GPT-4.1" },
        "gpt-4.1-mini": { "name": "GPT-4.1 Mini" },
        "o4-mini": { "name": "o4-mini (reasoning)" }
      }
    },
    "openshift": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenShift Models",
      "options": {
        "baseURL": "{env:OPENSHIFT_MODEL_ENDPOINT}"
      },
      "models": {
        "codellama-34b": {
          "name": "Code Llama 34B",
          "limit": {
            "context": 16384,
            "output": 4096
          }
        }
      }
    }
  },

  // Agent configuration — currently limited to OpenShift models
  // When Azure tool calling is unblocked (or Pi evaluation succeeds), reassign build/reviewer agents to Azure models
  "agent": {
    "build": {
      "description": "Primary coding agent for implementation",
      "mode": "primary",
      "model": "openshift/codellama-34b",
      "permission": {
        "edit": "allow",
        "bash": "allow"
      }
    },
    "plan": {
      "description": "Read-only analysis and planning",
      "mode": "primary",
      "model": "openshift/codellama-34b",
      "permission": {
        "edit": "ask",
        "bash": "ask"
      }
    },
    "explorer": {
      "description": "Fast codebase search and exploration",
      "mode": "subagent",
      "model": "openshift/codellama-34b",
      "tools": {
        "write": false,
        "edit": false
      }
    },
    "reviewer": {
      "description": "Code review focused on quality and security",
      "mode": "subagent",
      "model": "openshift/codellama-34b",
      "temperature": 0.1,
      "tools": {
        "write": false,
        "edit": false
      }
    }
  }
}
```

### Environment Variables

Add these to your shell profile or `.env` file:

```bash
export OPENSHIFT_MODEL_ENDPOINT="https://your-model-endpoint.apps.cluster.example.com/v1"
export BCGOV_AZURE_API_KEY="your-azure-api-key"

# For Pi (if evaluating as alternative harness):
export AZURE_OPENAI_API_KEY="$BCGOV_AZURE_API_KEY"
export AZURE_OPENAI_BASE_URL="https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai"
```

---

## Troubleshooting

### Azure OpenAI: Tool calls fail with `type: "None"` error

This is a known upstream bug in `@ai-sdk/provider-utils`. The SDK strips `type: "object"` and all property definitions from tool schemas during serialization. Azure rejects the empty schema with: `Invalid schema for function 'bash': schema must be a JSON Schema of 'type: "object"', got 'type: "None"'`. Affects both `@ai-sdk/azure` and `@ai-sdk/openai-compatible`. Tracked in [vercel/ai #7924](https://github.com/vercel/ai/issues/7924) and [#9761](https://github.com/vercel/ai/issues/9761). No fix available yet — must wait for upstream resolution or switch to Pi which uses its own tool serialization.

### Azure OpenAI: PII redaction blocks large requests

The APIM gateway's PII redaction policy (`fail_closed: true`) cannot scan request bodies larger than ~10-20KB. OpenCode sends ~62KB per request (system prompt + 12 tool definitions). Error: `PII redaction incomplete. Not all messages were scanned. Request blocked for data protection.` Contact the APIM team to disable PII redaction for the coding agent endpoint or increase scan limits. Pi's smaller footprint (4 tools, minimal system prompt) may fit under this limit.

### Azure OpenAI: Rate limit exceeded at small body sizes

The current rate limit is 1000 tokens/min, which triggers at approximately 10KB request bodies. This is far too low for interactive coding agent use. Request an increase from the APIM team (recommend 100K+ tokens/min).

### Azure OpenAI: 403 Forbidden from Application Gateway (resolved)

This was the original APIM gateway incompatibility where the gateway only accepted deployment-based URLs. The APIM team added a `/v1` endpoint, resolving this issue. If you still see 403 errors, verify you're using the correct base URL: `https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai` for `@ai-sdk/azure` or `https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/v1` for `@ai-sdk/openai-compatible`.

### "Model not found" when using Azure

Ensure the model key in your config matches your Azure deployment name exactly. Run `/models` in the TUI to see what OpenCode detected.

### Azure content filter blocking requests

Change the content filter from `DefaultV2` to `Default` in the Azure portal under your OpenAI resource.

### OpenShift model not responding

Verify the endpoint is reachable from your machine:

```bash
curl -s https://your-endpoint.apps.cluster.example.com/v1/models
```

You should get a JSON response listing available models.

### Agent not appearing in TUI

- JSON-defined agents: check for syntax errors in `opencode.json`
- Markdown-defined agents: ensure the file is in `~/.config/opencode/agents/` or `.opencode/agents/`
- Run `opencode agents list` to see all detected agents

### Context window errors with OpenShift models

If you're hitting context limits, set the `limit.context` value in your model config so OpenCode knows when to trigger context compaction. Smaller models on OpenShift may need lower values.

---

## References

- [OpenCode Documentation](https://opencode.ai/docs/)
- [OpenCode Agents](https://opencode.ai/docs/agents/)
- [OpenCode Providers](https://opencode.ai/docs/providers/)
- [OpenCode Models](https://opencode.ai/docs/models/)
- [Pi GitHub repo](https://github.com/badlogic/pi-mono) — Monorepo for coding agent, LLM API, TUI, and more
- [Pi (pi.dev)](https://pi.dev/) — Minimal terminal coding agent
- [Pi npm package](https://www.npmjs.com/package/@mariozechner/pi-coding-agent)
- [Pi blog post](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) — Design rationale and benchmarks
- [pi-ai LLM layer](https://www.npmjs.com/package/@mariozechner/pi-ai) — Multi-provider API with tool calling
- [AI SDK Azure Provider](https://ai-sdk.dev/providers/ai-sdk-providers/azure) — `baseURL` option documentation
- [AI SDK `jsonSchema()` Reference](https://ai-sdk.dev/docs/reference/ai-sdk-core/json-schema)
- [vercel/ai #7924](https://github.com/vercel/ai/issues/7924) — Tool schema serialization bug (openai-compatible)
- [vercel/ai #9761](https://github.com/vercel/ai/issues/9761) — Tool schema serialization bug (Google Vertex, same root cause)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
