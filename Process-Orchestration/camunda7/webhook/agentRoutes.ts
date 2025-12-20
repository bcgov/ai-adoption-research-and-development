import { Router, Request, Response } from 'express';
import axios from 'axios';
import { CAMUNDA_ENGINE_URL, getCamundaAuth } from '../src/camunda';
import type { AgentChatRequest, AgentChatResponse } from '../src/types/agent';

const router = Router();

// Create axios client for Camunda API
const camundaClient = axios.create({
  baseURL: CAMUNDA_ENGINE_URL,
  auth: getCamundaAuth()
});

/**
 * POST /agent-chat
 * Start a conversation with the GitHub Agent
 * 
 * Request body:
 * {
 *   "message": "Show me the README.md from owner/repo",
 *   "conversationId": "optional-id-for-tracking",
 *   "context": {
 *     "owner": "optional-default-owner",
 *     "repo": "optional-default-repo"
 *   }
 * }
 */
router.post('/agent-chat', async (req: Request, res: Response): Promise<void> => {
  try {
    const { message, conversationId, context } = req.body as AgentChatRequest;

    console.log(`[AgentWebhook] Received chat request`);
    console.log(`[AgentWebhook] Message: "${message?.substring(0, 100)}..."`);

    // Validate request
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      res.status(400).json({
        success: false,
        error: 'Message is required and must be a non-empty string'
      } as AgentChatResponse);
      return;
    }

    // Generate conversation ID if not provided
    const convId = conversationId || `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    // Start the Camunda process
    const startResponse = await camundaClient.post(
      '/process-definition/key/github-agent-workflow/start',
      {
        variables: {
          userMessage: { value: message.trim(), type: 'String' },
          conversationId: { value: convId, type: 'String' },
          ...(context?.owner ? { githubOwner: { value: context.owner, type: 'String' } } : {}),
          ...(context?.repo ? { githubRepo: { value: context.repo, type: 'String' } } : {})
        }
      }
    );

    const processInstanceId = startResponse.data?.id;
    console.log(`[AgentWebhook] Started process instance: ${processInstanceId}`);

    // Poll for completion (with timeout)
    const maxWaitTime = 120000; // 2 minutes
    const pollInterval = 1000; // 1 second
    const startTime = Date.now();

    let agentResponse: string | undefined;
    let toolsUsed: string[] = [];
    let error: string | undefined;

    while (Date.now() - startTime < maxWaitTime) {
      // Check if process is complete
      const historyResponse = await camundaClient.get(
        `/history/process-instance/${processInstanceId}`
      );

      if (historyResponse.data?.state === 'COMPLETED') {
        // Get the output variables
        const variablesResponse = await camundaClient.get(
          `/history/variable-instance`,
          {
            params: {
              processInstanceId,
              variableName: 'agentResponse'
            }
          }
        );

        const toolsResponse = await camundaClient.get(
          `/history/variable-instance`,
          {
            params: {
              processInstanceId,
              variableName: 'toolsUsed'
            }
          }
        );

        const errorResponse = await camundaClient.get(
          `/history/variable-instance`,
          {
            params: {
              processInstanceId,
              variableName: 'error'
            }
          }
        );

        agentResponse = variablesResponse.data?.[0]?.value;
        const toolsUsedJson = toolsResponse.data?.[0]?.value;
        error = errorResponse.data?.[0]?.value;

        if (toolsUsedJson) {
          try {
            toolsUsed = JSON.parse(toolsUsedJson);
          } catch {
            toolsUsed = [];
          }
        }

        break;
      }

      // Check for failed state
      if (historyResponse.data?.state === 'EXTERNALLY_TERMINATED' || 
          historyResponse.data?.state === 'INTERNALLY_TERMINATED') {
        error = 'Process was terminated unexpectedly';
        break;
      }

      // Wait before polling again
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    // Check if we timed out
    if (!agentResponse && !error) {
      error = 'Request timed out waiting for agent response';
    }

    if (error) {
      console.error(`[AgentWebhook] Error: ${error}`);
      res.status(500).json({
        success: false,
        error,
        conversationId: convId,
        processInstanceId
      } as AgentChatResponse);
      return;
    }

    console.log(`[AgentWebhook] Response generated (${agentResponse?.length || 0} chars)`);

    res.json({
      success: true,
      response: agentResponse,
      conversationId: convId,
      processInstanceId,
      toolsUsed
    } as AgentChatResponse);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[AgentWebhook] Error processing chat request:', errorMessage);
    
    if (axios.isAxiosError(error)) {
      console.error('[AgentWebhook] Camunda response:', error.response?.data);
      
      // Check if the process definition doesn't exist
      if (error.response?.status === 404) {
        res.status(500).json({
          success: false,
          error: 'GitHub Agent workflow not deployed. Please deploy github-agent-workflow.bpmn first.'
        } as AgentChatResponse);
        return;
      }
    }

    res.status(500).json({
      success: false,
      error: errorMessage
    } as AgentChatResponse);
  }
});

/**
 * GET /agent-chat/status/:processInstanceId
 * Check the status of an agent conversation
 */
router.get('/agent-chat/status/:processInstanceId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { processInstanceId } = req.params;

    const historyResponse = await camundaClient.get(
      `/history/process-instance/${processInstanceId}`
    );

    const state = historyResponse.data?.state;

    if (state === 'COMPLETED') {
      // Get the output variables
      const variablesResponse = await camundaClient.get(
        `/history/variable-instance`,
        {
          params: {
            processInstanceId,
            variableName: 'agentResponse'
          }
        }
      );

      const toolsResponse = await camundaClient.get(
        `/history/variable-instance`,
        {
          params: {
            processInstanceId,
            variableName: 'toolsUsed'
          }
        }
      );

      const agentResponse = variablesResponse.data?.[0]?.value;
      const toolsUsedJson = toolsResponse.data?.[0]?.value;
      let toolsUsed: string[] = [];

      if (toolsUsedJson) {
        try {
          toolsUsed = JSON.parse(toolsUsedJson);
        } catch {
          toolsUsed = [];
        }
      }

      res.json({
        success: true,
        status: 'completed',
        response: agentResponse,
        toolsUsed,
        processInstanceId
      });
    } else if (state === 'ACTIVE') {
      res.json({
        success: true,
        status: 'processing',
        processInstanceId
      });
    } else {
      res.json({
        success: false,
        status: state?.toLowerCase() || 'unknown',
        processInstanceId
      });
    }

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[AgentWebhook] Error checking status:', errorMessage);

    res.status(500).json({
      success: false,
      error: errorMessage
    });
  }
});

export default router;




