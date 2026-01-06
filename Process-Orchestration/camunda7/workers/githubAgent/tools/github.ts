import { Octokit } from '@octokit/rest';
import type {
  GitHubRepoInfo,
  GitHubFileContent,
  GitHubCreateUpdateFileParams,
  GitHubCreateUpdateFileResult,
  GitHubCreatePRParams,
  GitHubPullRequest,
  ToolDefinition
} from '../../../src/types/agent';

// Initialize Octokit with GitHub token
const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN
});

// Default owner/repo from environment
const defaultOwner = process.env.GITHUB_DEFAULT_OWNER;
const defaultRepo = process.env.GITHUB_DEFAULT_REPO;

/**
 * Tool definitions for Gemini function calling
 */
export const githubToolDefinitions: ToolDefinition[] = [
  {
    name: 'get_repo_info',
    description: 'Get information about a GitHub repository including name, description, default branch, stars, forks, and other metadata.',
    parameters: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'The owner (user or organization) of the repository'
        },
        repo: {
          type: 'string',
          description: 'The name of the repository'
        }
      },
      required: ['owner', 'repo']
    }
  },
  {
    name: 'get_file',
    description: 'Get the contents of a file from a GitHub repository. Returns the file content decoded from base64.',
    parameters: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'The owner (user or organization) of the repository'
        },
        repo: {
          type: 'string',
          description: 'The name of the repository'
        },
        path: {
          type: 'string',
          description: 'The file path relative to the repository root (e.g., "src/index.ts" or "README.md")'
        },
        ref: {
          type: 'string',
          description: 'Optional branch, tag, or commit SHA to get the file from. Defaults to the default branch.'
        }
      },
      required: ['owner', 'repo', 'path']
    }
  },
  {
    name: 'create_or_update_file',
    description: 'Create a new file or update an existing file in a GitHub repository. For updates, the SHA of the existing file is required.',
    parameters: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'The owner (user or organization) of the repository'
        },
        repo: {
          type: 'string',
          description: 'The name of the repository'
        },
        path: {
          type: 'string',
          description: 'The file path where the file should be created/updated'
        },
        content: {
          type: 'string',
          description: 'The new content for the file (plain text, will be base64 encoded automatically)'
        },
        message: {
          type: 'string',
          description: 'The commit message describing the change'
        },
        branch: {
          type: 'string',
          description: 'Optional branch name. Defaults to the default branch. Will create the branch if it does not exist.'
        },
        sha: {
          type: 'string',
          description: 'Required for updates: the SHA of the file being replaced. Get this from get_file first.'
        }
      },
      required: ['owner', 'repo', 'path', 'content', 'message']
    }
  },
  {
    name: 'create_pull_request',
    description: 'Create a new pull request to merge changes from one branch into another.',
    parameters: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'The owner (user or organization) of the repository'
        },
        repo: {
          type: 'string',
          description: 'The name of the repository'
        },
        title: {
          type: 'string',
          description: 'The title of the pull request'
        },
        body: {
          type: 'string',
          description: 'The description/body of the pull request'
        },
        head: {
          type: 'string',
          description: 'The name of the branch containing the changes you want to merge'
        },
        base: {
          type: 'string',
          description: 'The name of the branch you want to merge changes into (e.g., "main")'
        },
        draft: {
          type: 'boolean',
          description: 'Whether to create the PR as a draft. Defaults to false.'
        }
      },
      required: ['owner', 'repo', 'title', 'head', 'base']
    }
  }
];

/**
 * Get repository information
 */
export async function getRepoInfo(
  owner: string = defaultOwner || '',
  repo: string = defaultRepo || ''
): Promise<GitHubRepoInfo> {
  if (!owner || !repo) {
    throw new Error('Owner and repo are required. Set GITHUB_DEFAULT_OWNER and GITHUB_DEFAULT_REPO or provide them explicitly.');
  }

  const { data } = await octokit.repos.get({ owner, repo });

  return {
    name: data.name,
    fullName: data.full_name,
    description: data.description,
    defaultBranch: data.default_branch,
    private: data.private,
    htmlUrl: data.html_url,
    cloneUrl: data.clone_url,
    language: data.language,
    stargazersCount: data.stargazers_count,
    forksCount: data.forks_count,
    openIssuesCount: data.open_issues_count,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    pushedAt: data.pushed_at
  };
}

/**
 * Get file contents from a repository
 */
export async function getFile(
  owner: string = defaultOwner || '',
  repo: string = defaultRepo || '',
  path: string,
  ref?: string
): Promise<GitHubFileContent & { decodedContent?: string }> {
  if (!owner || !repo) {
    throw new Error('Owner and repo are required.');
  }

  const { data } = await octokit.repos.getContent({
    owner,
    repo,
    path,
    ...(ref ? { ref } : {})
  });

  // Handle file response (not directory)
  if (Array.isArray(data)) {
    throw new Error(`Path "${path}" is a directory, not a file. Use a specific file path.`);
  }

  if (data.type !== 'file') {
    throw new Error(`Path "${path}" is not a file (type: ${data.type}).`);
  }

  // Decode base64 content
  let decodedContent: string | undefined;
  if (data.content && data.encoding === 'base64') {
    decodedContent = Buffer.from(data.content, 'base64').toString('utf-8');
  }

  return {
    name: data.name,
    path: data.path,
    sha: data.sha,
    size: data.size,
    type: data.type,
    content: data.content,
    encoding: data.encoding,
    htmlUrl: data.html_url || '',
    downloadUrl: data.download_url,
    decodedContent
  };
}

/**
 * Create or update a file in a repository
 */
export async function createOrUpdateFile(
  params: GitHubCreateUpdateFileParams
): Promise<GitHubCreateUpdateFileResult> {
  const { owner, repo, path, message, content, branch, sha } = params;

  if (!owner || !repo) {
    throw new Error('Owner and repo are required.');
  }

  // Base64 encode the content
  const encodedContent = Buffer.from(content).toString('base64');

  const { data } = await octokit.repos.createOrUpdateFileContents({
    owner,
    repo,
    path,
    message,
    content: encodedContent,
    ...(branch ? { branch } : {}),
    ...(sha ? { sha } : {})
  });

  return {
    content: {
      name: data.content?.name || path.split('/').pop() || '',
      path: data.content?.path || path,
      sha: data.content?.sha || '',
      htmlUrl: data.content?.html_url || ''
    },
    commit: {
      sha: data.commit.sha || '',
      message: data.commit.message || message,
      htmlUrl: data.commit.html_url || ''
    }
  };
}

/**
 * Create a pull request
 */
export async function createPullRequest(
  params: GitHubCreatePRParams
): Promise<GitHubPullRequest> {
  const { owner, repo, title, body, head, base, draft } = params;

  if (!owner || !repo) {
    throw new Error('Owner and repo are required.');
  }

  const { data } = await octokit.pulls.create({
    owner,
    repo,
    title,
    body: body || '',
    head,
    base,
    draft: draft || false
  });

  return {
    number: data.number,
    title: data.title,
    body: data.body,
    state: data.state as 'open' | 'closed',
    htmlUrl: data.html_url,
    head: {
      ref: data.head.ref,
      sha: data.head.sha
    },
    base: {
      ref: data.base.ref,
      sha: data.base.sha
    },
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    merged: data.merged,
    mergeable: data.mergeable
  };
}

/**
 * Execute a GitHub tool by name
 */
export async function executeGitHubTool(
  toolName: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (toolName) {
    case 'get_repo_info':
      return getRepoInfo(
        (args.owner as string) || defaultOwner,
        (args.repo as string) || defaultRepo
      );

    case 'get_file':
      return getFile(
        (args.owner as string) || defaultOwner,
        (args.repo as string) || defaultRepo,
        args.path as string,
        args.ref as string | undefined
      );

    case 'create_or_update_file':
      return createOrUpdateFile({
        owner: (args.owner as string) || defaultOwner || '',
        repo: (args.repo as string) || defaultRepo || '',
        path: args.path as string,
        message: args.message as string,
        content: args.content as string,
        branch: args.branch as string | undefined,
        sha: args.sha as string | undefined
      });

    case 'create_pull_request':
      return createPullRequest({
        owner: (args.owner as string) || defaultOwner || '',
        repo: (args.repo as string) || defaultRepo || '',
        title: args.title as string,
        body: args.body as string | undefined,
        head: args.head as string,
        base: args.base as string,
        draft: args.draft as boolean | undefined
      });

    default:
      throw new Error(`Unknown GitHub tool: ${toolName}`);
  }
}

