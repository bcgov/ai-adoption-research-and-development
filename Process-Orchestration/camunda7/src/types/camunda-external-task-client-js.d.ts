declare module 'camunda-external-task-client-js' {
  export interface ClientConfig {
    baseUrl: string;
    workerId?: string;
    asyncResponseTimeout?: number;
    maxTasks?: number;
    use?: unknown;
    basicAuth?: {
      username: string;
      password: string;
    };
  }

  export class Client {
    constructor(config: ClientConfig);
    subscribe(
      topic: string,
      handler: (args: { task: any; taskService: any }) => Promise<void> | void
    ): void;
    on(event: string, listener: (err: unknown) => void): void;
  }

  export class Variables {
    set(name: string, value: unknown): void;
    get<T = unknown>(name: string): T;
    getAll<T = Record<string, unknown>>(): T;
  }

  export const logger: unknown;
}


