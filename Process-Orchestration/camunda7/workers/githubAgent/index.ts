import 'dotenv/config';
import { Variables } from 'camunda-external-task-client-js';
import client from '../client';
import { runAgent } from './agent';
import type { AgentWorkflowVariables } from '../../src/types/agent';

// Type for external task handler args (same pattern as other workers)
interface ExternalTaskHandlerArgs {
  task: {
    id?: string;
    variables: {
      getAll<T = AgentWorkflowVariables>(): T;
      get<T = unknown>(name: string): T;
    };
  };
  taskService: {
    complete: (task: unknown, variables?: unknown) => Promise<void>;
    handleFailure: (
      task: unknown,
      errorMessage: string,
      retries: number,
      retryTimeout: number
    ) => Promise<void>;
  };
}

/**
 * Worker for processing chat messages with the AI Agent.
 * Subscribes to the 'process-with-ai-agent' topic.
 */
client.subscribe(
  'process-with-ai-agent',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const variables = task.variables.getAll<AgentWorkflowVariables>();
    const { userMessage, githubOwner, githubRepo, conversationId } = variables;

    console.log(`[GitHubAgent] Processing task ${task.id}`);
    console.log(`[GitHubAgent] User message: "${userMessage?.substring(0, 100)}..."`);

    if (!userMessage) {
      const errorMessage = 'No user message provided in process variables';
      console.error(`[GitHubAgent] Error: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
      return;
    }

    try {
      // Run the agent with the user message
      const { response, toolsUsed } = await runAgent(userMessage, {
        owner: githubOwner,
        repo: githubRepo
      });

      console.log(`[GitHubAgent] Agent response generated (${response.length} chars)`);
      console.log(`[GitHubAgent] Tools used: ${toolsUsed.join(', ') || 'none'}`);

      // Complete the task with output variables
      const outputVariables = new Variables();
      outputVariables.set('agentResponse', response);
      outputVariables.set('toolsUsed', JSON.stringify(toolsUsed));
      if (conversationId) {
        outputVariables.set('conversationId', conversationId);
      }

      await taskService.complete(task, outputVariables);
      console.log(`[GitHubAgent] Task ${task.id} completed successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`[GitHubAgent] Error processing task: ${errorMessage}`);
      
      // Set error in variables and fail the task
      const outputVariables = new Variables();
      outputVariables.set('error', errorMessage);
      
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[GitHubAgent] Worker started. Waiting for tasks on topic "process-with-ai-agent"...');




