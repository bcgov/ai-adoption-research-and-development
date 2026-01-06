/**
 * Type definitions for GitHub Agent workflow
 */

// Agent Workflow Variables
export interface AgentWorkflowVariables {
  // Input variables
  userMessage: string;
  conversationId?: string;
  
  // GitHub context (optional defaults)
  githubOwner?: string;
  githubRepo?: string;
  
  // Output variables
  agentResponse?: string;
  toolsUsed?: string[];
  error?: string;
}

// Chat request/response types
export interface AgentChatRequest {
  message: string;
  conversationId?: string;
  context?: {
    owner?: string;
    repo?: string;
  };
}

export interface AgentChatResponse {
  success: boolean;
  response?: string;
  conversationId?: string;
  processInstanceId?: string;
  toolsUsed?: string[];
  error?: string;
}

// GitHub Tool Types
export interface GitHubRepoInfo {
  name: string;
  fullName: string;
  description: string | null;
  defaultBranch: string;
  private: boolean;
  htmlUrl: string;
  cloneUrl: string;
  language: string | null;
  stargazersCount: number;
  forksCount: number;
  openIssuesCount: number;
  createdAt: string;
  updatedAt: string;
  pushedAt: string;
}

export interface GitHubFileContent {
  name: string;
  path: string;
  sha: string;
  size: number;
  type: 'file' | 'dir' | 'symlink' | 'submodule';
  content?: string; // base64 encoded for files
  encoding?: string;
  htmlUrl: string;
  downloadUrl: string | null;
}

export interface GitHubCreateUpdateFileParams {
  owner: string;
  repo: string;
  path: string;
  message: string;
  content: string; // base64 encoded
  branch?: string;
  sha?: string; // required for updates
}

export interface GitHubCreateUpdateFileResult {
  content: {
    name: string;
    path: string;
    sha: string;
    htmlUrl: string;
  };
  commit: {
    sha: string;
    message: string;
    htmlUrl: string;
  };
}

export interface GitHubCreatePRParams {
  owner: string;
  repo: string;
  title: string;
  body?: string;
  head: string; // branch with changes
  base: string; // branch to merge into
  draft?: boolean;
}

export interface GitHubPullRequest {
  number: number;
  title: string;
  body: string | null;
  state: 'open' | 'closed';
  htmlUrl: string;
  head: {
    ref: string;
    sha: string;
  };
  base: {
    ref: string;
    sha: string;
  };
  createdAt: string;
  updatedAt: string;
  merged: boolean;
  mergeable: boolean | null;
}

// Tool definitions for Gemini function calling
export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, ToolParameter>;
    required: string[];
  };
}

export interface ToolParameter {
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  enum?: string[];
  items?: ToolParameter;
}

// Tool execution types
export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface ToolResult {
  name: string;
  result: unknown;
  error?: string;
}

// Agent conversation types
export interface ConversationMessage {
  role: 'user' | 'model' | 'function';
  content: string;
  functionCall?: ToolCall;
  functionResponse?: {
    name: string;
    response: unknown;
  };
}

export interface AgentState {
  messages: ConversationMessage[];
  toolsUsed: string[];
}




