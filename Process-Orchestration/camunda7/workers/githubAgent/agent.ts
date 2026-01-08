import { GoogleGenerativeAI, FunctionDeclarationsTool, Part, SchemaType } from '@google/generative-ai';
import { githubToolDefinitions, executeGitHubTool } from './tools/github';
import { buildSystemPrompt } from './prompts';
import type { ToolResult, AgentState } from '../../src/types/agent';

// Initialize Gemini
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');

// Maximum iterations to prevent infinite loops
const MAX_ITERATIONS = 10;

/**
 * Map our type strings to Gemini SchemaType
 */
function mapToSchemaType(type: string): SchemaType {
  switch (type) {
    case 'string': return SchemaType.STRING;
    case 'number': return SchemaType.NUMBER;
    case 'boolean': return SchemaType.BOOLEAN;
    case 'array': return SchemaType.ARRAY;
    case 'object': return SchemaType.OBJECT;
    default: return SchemaType.STRING;
  }
}

/**
 * Convert our tool definitions to Gemini's format
 */
function getGeminiTools(): FunctionDeclarationsTool[] {
  return [{
    functionDeclarations: githubToolDefinitions.map(tool => ({
      name: tool.name,
      description: tool.description,
      parameters: {
        type: SchemaType.OBJECT,
        properties: Object.fromEntries(
          Object.entries(tool.parameters.properties).map(([key, value]) => [
            key,
            {
              type: mapToSchemaType(value.type),
              description: value.description,
              ...(value.enum ? { enum: value.enum } : {})
            }
          ])
        ),
        required: tool.parameters.required
      }
    }))
  }];
}

/**
 * Execute a tool call and return the result
 */
async function executeTool(
  toolName: string,
  args: Record<string, unknown>
): Promise<ToolResult> {
  console.log(`[Agent] Executing tool: ${toolName}`, args);
  
  try {
    const result = await executeGitHubTool(toolName, args);
    console.log(`[Agent] Tool ${toolName} succeeded`);
    return { name: toolName, result };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[Agent] Tool ${toolName} failed:`, errorMessage);
    return { name: toolName, result: null, error: errorMessage };
  }
}

/**
 * Run the agent with the given user message
 * Implements an agentic loop that continues until the model stops calling functions
 */
export async function runAgent(
  userMessage: string,
  context?: { owner?: string; repo?: string }
): Promise<{ response: string; toolsUsed: string[] }> {
  if (!process.env.GEMINI_API_KEY) {
    throw new Error('GEMINI_API_KEY environment variable is not set');
  }

  // Build system prompt with optional context
  let additionalContext = '';
  if (context?.owner && context?.repo) {
    additionalContext = `Default Repository: ${context.owner}/${context.repo}`;
  }
  const systemPrompt = buildSystemPrompt(additionalContext);

  // Initialize the model
  const model = genAI.getGenerativeModel({
    model: 'gemini-1.5-flash',
    systemInstruction: systemPrompt,
    tools: getGeminiTools()
  });

  // Start a chat session
  const chat = model.startChat({
    history: []
  });

  // Track state
  const state: AgentState = {
    messages: [],
    toolsUsed: []
  };

  // Send the initial user message
  console.log(`[Agent] Processing user message: "${userMessage.substring(0, 100)}..."`);
  let response = await chat.sendMessage(userMessage);
  let candidate = response.response.candidates?.[0];

  // Agentic loop - continue while the model wants to call functions
  let iterations = 0;
  while (candidate && iterations < MAX_ITERATIONS) {
    iterations++;
    
    // Check if there are function calls in the response
    const functionCalls = candidate.content?.parts?.filter(
      (part): part is Part & { functionCall: { name: string; args: Record<string, unknown> } } =>
        'functionCall' in part && part.functionCall !== undefined
    );

    if (!functionCalls || functionCalls.length === 0) {
      // No more function calls, we're done
      break;
    }

    console.log(`[Agent] Iteration ${iterations}: Processing ${functionCalls.length} function call(s)`);

    // Execute all function calls
    const functionResponses: Part[] = [];
    for (const part of functionCalls) {
      const { name, args } = part.functionCall;
      state.toolsUsed.push(name);
      
      const result = await executeTool(name, args || {});
      
      functionResponses.push({
        functionResponse: {
          name,
          response: result.error 
            ? { error: result.error }
            : { result: result.result }
        }
      });
    }

    // Send function results back to the model
    response = await chat.sendMessage(functionResponses);
    candidate = response.response.candidates?.[0];
  }

  if (iterations >= MAX_ITERATIONS) {
    console.warn(`[Agent] Reached maximum iterations (${MAX_ITERATIONS})`);
  }

  // Extract the final text response
  const textParts = candidate?.content?.parts?.filter(
    (part): part is Part & { text: string } => 'text' in part && typeof part.text === 'string'
  );
  
  const finalResponse = textParts?.map(p => p.text).join('\n') || 
    'I apologize, but I was unable to generate a response.';

  console.log(`[Agent] Completed with ${state.toolsUsed.length} tool call(s)`);

  return {
    response: finalResponse,
    toolsUsed: [...new Set(state.toolsUsed)] // deduplicate
  };
}

