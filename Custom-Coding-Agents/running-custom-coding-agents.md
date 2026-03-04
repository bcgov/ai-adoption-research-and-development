# Running Custom Coding Agents

Findings and guide for setting up AI coding agents using OpenCode with Azure OpenAI and OpenShift-hosted models.

> **Status:** OpenCode works with OpenShift-hosted (local) models and supports multi-agent routing. Azure OpenAI connectivity is **blocked** due to incompatibilities between the AI SDK's URL construction and the BC Gov APIM gateway. See [Connecting to Azure OpenAI](#connecting-to-azure-openai) for details.

## Table of Contents

- [Overview](#overview)
- [Harness Comparison](#harness-comparison)
- [Prerequisites](#prerequisites)
- [Setting Up OpenCode](#setting-up-opencode)
- [Connecting to Azure OpenAI](#connecting-to-azure-openai)
- [Connecting to OpenShift-Hosted Models](#connecting-to-openshift-hosted-models)
- [Creating Custom Agents](#creating-custom-agents)
- [Model Routing Strategy](#model-routing-strategy)
- [Recommended Configuration](#recommended-configuration)
- [Troubleshooting](#troubleshooting)

---

## Findings Summary


| Capability                 | Status    | Notes                                                  |
| -------------------------- | --------- | ------------------------------------------------------ |
| OpenCode as harness        | ✅ Working | Preferred over Claude Code for our use case            |
| OpenShift-hosted models    | ✅ Working | Via `@ai-sdk/openai-compatible` provider               |
| Azure OpenAI connectivity  | ❌ Blocked | APIM gateway incompatible with AI SDK URL construction |
| Multi-agent model routing  | ✅ Working | Config-time routing via agent-to-model mapping         |
| Per-agent model assignment | ✅ Working | Each agent can target a different provider/model       |


---

## Harness Comparison


| Feature                     | OpenCode                                                                                                                 | Claude Code                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Provider support            | 75+ providers (OpenAI, Azure, Anthropic, local, etc.)                                                                    | Anthropic API only                                                           |
| Azure OpenAI                | Native support via `@ai-sdk/azure`, but **blocked by BC Gov APIM gateway** (see [findings](#connecting-to-azure-openai)) | Requires proxy to translate API formats                                      |
| OpenAI-compatible endpoints | Native support via `@ai-sdk/openai-compatible`                                                                           | Not supported natively                                                       |
| Per-agent model assignment  | Yes — each agent can target a different provider/model                                                                   | Internal only (Haiku for search, Sonnet for review, Opus for implementation) |
| Custom agents               | Full control via JSON config or Markdown files                                                                           | Limited to model selection                                                   |
| Agent types                 | Primary agents + subagents with `@mention` invocation                                                                    | Single agent workflow                                                        |
| Open source                 | Yes                                                                                                                      | No                                                                           |


**Why OpenCode for our use case:** OpenCode's native support for OpenAI-compatible endpoints and its multi-agent architecture make it the best harness for connecting to OpenShift-hosted models with per-task model routing. Azure OpenAI support exists in the SDK but is currently blocked by our APIM gateway configuration.

---

## Prerequisites

- **OpenCode CLI** installed
- Access to **OpenShift** running OpenAI-compatible model endpoints
- OpenShift model **endpoint URL**
- *(When Azure is unblocked)* Access to BC Gov **Azure OpenAI** subscription with API key

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

> **⚠️ BLOCKED:** Azure OpenAI connectivity through OpenCode does not currently work with the BC Gov APIM gateway. The issue is a fundamental incompatibility in how the AI SDK constructs API request URLs. Direct API access (e.g., via `curl` or application code) works fine — the problem is specific to OpenCode's provider layer.

### What Works (Direct API Access)

Our Azure OpenAI models are accessible through the APIM gateway at:

```
https://test.aihub.gov.bc.ca/sdpr-invoice-automation
```

Authentication uses `api-key` header with a subscription key. The gateway expects Azure-style deployment URLs:

```
{base}/openai/deployments/{deployment}/chat/completions?api-version={version}
```

This works correctly from application code and `curl`:

```bash
curl "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai/deployments/gpt-4.1/chat/completions?api-version=2024-12-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: $BCGOV_AZURE_API_KEY" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
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


### Why It Fails in OpenCode

OpenCode uses the [Vercel AI SDK](https://ai-sdk.dev/) (`@ai-sdk/azure` package) to communicate with Azure OpenAI. The SDK constructs API URLs internally, and the format it generates does not match what the BC Gov APIM gateway expects.

**The problem:** The `@ai-sdk/azure` package (v6) defaults to the newer Responses API URL format:

```
{baseURL}/v1/chat/completions
```

Our APIM gateway requires the legacy deployment-based format:

```
{baseURL}/openai/deployments/{deployment}/chat/completions?api-version={version}
```

The SDK exposes a `useDeploymentBasedUrls` option to switch to the legacy format, but OpenCode's provider configuration layer does not pass this option through to the SDK. Only standard options like `baseURL`, `apiKey`, and `headers` are forwarded.

### What Was Attempted

1. **Built-in Azure OpenAI provider** — Uses `AZURE_RESOURCE_NAME` to construct `https://{name}.openai.azure.com/...`. Overriding `baseURL` doesn't help because the SDK still uses the v1 URL pattern.
2. **Custom provider with `@ai-sdk/azure`** — Allows `baseURL` override but `useDeploymentBasedUrls` and `apiVersion` options are not forwarded by OpenCode, so the SDK still constructs the wrong URL pattern.
3. **Custom provider with `@ai-sdk/openai-compatible`** — Constructs OpenAI-style URLs (`{baseURL}/chat/completions`) which the APIM gateway does not recognize, returning `403 Forbidden` from the Azure Application Gateway.

All three approaches result in a `403 Forbidden` response from `Microsoft-Azure-Application-Gateway/v2` because the request URL doesn't match any route the gateway recognizes.

### Path Forward

To resolve this, one of the following would need to happen:

- **OpenCode adds passthrough for `useDeploymentBasedUrls` and `apiVersion`** — File a feature request or PR against the OpenCode repo to forward these options to `@ai-sdk/azure`.
- **APIM gateway adds support for the v1 URL format** — The gateway would need to accept the newer `{baseURL}/v1/chat/completions` pattern and route it to the correct deployment.
- **Custom OpenCode plugin** — Write a plugin that creates the Azure provider instance directly with the correct options, bypassing OpenCode's config layer.
- **Proxy/middleware** — Deploy a lightweight reverse proxy that translates the v1 URL format to the deployment-based format before forwarding to the APIM gateway.

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

**Target state** (when Azure connectivity is resolved):


| Task Type                        | Agent              | Model              | Provider  |
| -------------------------------- | ------------------ | ------------------ | --------- |
| Implementation / complex changes | `build`            | GPT-4.1 or o4-mini | Azure     |
| Planning / architecture analysis | `plan`             | GPT-4.1 Mini       | Azure     |
| Code review                      | `reviewer`         | GPT-4.1 Mini       | Azure     |
| Codebase search / exploration    | `explorer`         | Code Llama 34B     | OpenShift |
| Security audit                   | `security-auditor` | GPT-4.1            | Azure     |
| Quick questions / documentation  | `general`          | Code Llama 34B     | OpenShift |


**Current state** (Azure blocked):


| Task Type | Agent                 | Model          | Provider  |
| --------- | --------------------- | -------------- | --------- |
| All tasks | `build`, `plan`, etc. | Code Llama 34B | OpenShift |


Without Azure models, the routing strategy is limited to whatever models are available on OpenShift. The multi-agent architecture still works — agents can be assigned different system prompts, tool permissions, and temperatures — but model diversity requires Azure connectivity.

### Cost Considerations

- **Azure models** are billed per token through the subscription. When connectivity is resolved, use them for tasks where quality matters (implementation, code review, security audit).
- **OpenShift models** have no per-token cost (infrastructure cost only). Currently the only option for OpenCode, suitable for all tasks but with lower capability than Azure-hosted models like GPT-4.1.

---

## Recommended Configuration

Below is a working configuration using OpenShift-hosted models with a multi-agent setup. Azure models are commented out pending resolution of the APIM gateway compatibility issue.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",

  // Default model
  "model": "openshift/codellama-34b",

  // Provider configuration
  "provider": {
    // BLOCKED: Azure OpenAI via APIM gateway — see findings
    // "bcgov-azure": {
    //   "npm": "@ai-sdk/azure",
    //   "name": "BC Gov Azure",
    //   "options": {
    //     "baseURL": "https://test.aihub.gov.bc.ca/sdpr-invoice-automation/openai",
    //     "apiKey": "{env:BCGOV_AZURE_API_KEY}",
    //     "apiVersion": "2024-12-01-preview",
    //     "useDeploymentBasedUrls": true  // <-- not forwarded by OpenCode
    //   },
    //   "models": {
    //     "gpt-4.1": { "name": "GPT-4.1" },
    //     "gpt-4.1-mini": { "name": "GPT-4.1 Mini" },
    //     "o4-mini": { "name": "o4-mini (reasoning)" }
    //   }
    // },
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
  // When Azure is unblocked, reassign build/reviewer agents to Azure models
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

# For when Azure connectivity is resolved:
# export BCGOV_AZURE_API_KEY="your-azure-api-key"
```

---

## Troubleshooting

### Azure OpenAI: 403 Forbidden from Application Gateway

This is the known APIM gateway incompatibility. The `@ai-sdk/azure` package constructs URLs using the v1 Responses API format (`{baseURL}/v1/chat/completions`), but the BC Gov APIM gateway only recognizes the legacy deployment-based format (`{baseURL}/openai/deployments/{model}/chat/completions?api-version=...`). The SDK's `useDeploymentBasedUrls` option would fix this, but OpenCode does not forward it to the provider. See [Connecting to Azure OpenAI](#connecting-to-azure-openai) for the full analysis and path forward.

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
- [AI SDK Azure Provider](https://ai-sdk.dev/providers/ai-sdk-providers/azure) — `useDeploymentBasedUrls` option documentation
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

