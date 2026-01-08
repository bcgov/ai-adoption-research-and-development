# LibreChat Setup Instructions

This is a short guide to setting up LibreChat with Ollama on a local system. It uses the containerized LibreChat option.

Assumptions:

- [Docker](https://www.docker.com/) or [Podman](https://podman.io/) is already installed on you system.
- [Git](https://git-scm.com/) is installed on your system.

## Install Instructions

1. Install [Ollama](https://ollama.com/). Once you have it installed, download a model of your choice using the CLI command `ollama pull <model-name>`. You can find model names in their [online repository](https://ollama.com/search).
1. Clone the LibreChat repository using `git clone https://github.com/danny-avila/LibreChat.git`.
1. If using Podman, comment out the following lines in the `docker-compose.yml` file under the `api` service. They are Docker-specific and do not work with Podman.

    ```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
    ```

1. Make a copy of `.env.example` and name it `.env`. No other changes needed.
1. Make a copy of `librechat.example.yaml` and name it `librechat.yaml`.
1. In the `librechat.yaml` file, add an entry for Ollama under `examples` -> `custom`. The default section does not appear to matter. It will recognize all downloaded Ollama models.

    ```yaml
    custom:
        - name: "Ollama"
          apiKey: "ollama"
          # use 'host.docker.internal' if using Docker instead of Podman
          baseURL: "http://host.containers.internal:11434/v1/" 
          models:
            default: [
              "gemma3"
              ]
            fetch: true
          titleConvo: true
          titleModel: "current_model"
          summarize: false
          summaryModel: "current_model"
          forcePrompt: false
          modelDisplayLabel: "Ollama"
    ```

1. Make a copy of the `docker-compose.override.yml.example`, name it `docker-compose.override.yml`, and uncomment the following lines:

    ```yaml
    # Without this, LibreChat will not read your config file.
    services:
      api:
        volumes:
          - type: bind
            source: ./librechat.yaml
            target: /app/librechat.yaml
    ```

1. Start the containers for LibreChat by running `podman-compose up -d` or `docker-compose up -d`.
1. Navigate to `localhost:3080` to see the LibreChat UI. Select Ollama and your model of choice from the dropdown menu along the top of the page.
