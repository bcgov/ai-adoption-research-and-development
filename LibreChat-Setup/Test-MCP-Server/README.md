# Using MCP with LibreChat

This assumes you've already followed the instructions in the README file for `LibreChat-Setup`.

1. Edit the `librechat.yaml` file. It must include entries for each MCP server as if it were setup by the administrator when building the LibreChat container. `mcpServers` is a top-level property in the file.

    ```yaml
    mcpServers:
      weather-server:
        type: streamable-http
        url: http://host.docker.internal:8002/mcp/
      calendar-server:
        type: streamable-http
        url: http://host.docker.internal:8001/mcp/
    ```

1. Start the two included MCP servers. Use two different terminal windows to observe, but use the following commands:
    - `fastmcp run calendar_server.py:mcp --transport http --port 8001`
    - `fastmcp run weather_server.py:mcp --transport http --port 8002`

1. Restart/rebuild the LibreChat container.
    - `podman-compose down`
    - `podman-compose up -d --build`

1. Open LibreChat UI and ensure the MCP servers are selected in the text input area.

## Simple MCP

The two examples of MCP servers are plain, but they were created to demonstrate how a prompt to the AI agent may require both of the servers to be utilized. 

In this case, I tested with prompts like:

> I live in Vancouver and I wish to go for a picnic this weekend. Find a period of time with no rain and create the event in my calendar.

This requires the agent to use both MCP servers and interpret their results.

Local Ollama-provided models that worked well with this:

- `qwen3:4b`: Slow, lots of unnecessary thinking, but it came to the correct results where I can also see the logic it took and when it made the tool calls.
- `mistral-small3.2:24b`: Also slow, but no thinking shown. Shows tool calls though and formats the final result the best.
- `mistral:7b`: The fastest of the three tested, but it doesn't format the results for some reason. It reads more like a play, where it always specifies what it's saying and what the tool reported (raw).

## Authentication

As of 2026-01-14, I've yet to find a good method of utilizing our SSO (Keyclock) authentication with both FastMCP and LibreChat.

FastMCP doesn't seem to have a natural way to protecting the tool calls. Every method that I've found and tested suggests it is protecting it, but it lets me get the results either way.

For LibreChat, it's not clear how to specify the authentication variables in the `librechat.yaml` file. The ideal flow would be to have it open a browser window for sign-in, but it may not be possible at this time.
