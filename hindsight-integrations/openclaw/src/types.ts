// Moltbot plugin API types (minimal subset needed for this plugin)

export interface MoltbotPluginAPI {
  config: MoltbotConfig;
  registerService(config: ServiceConfig): void;
  // OpenClaw hook handler signature: (event, ctx?) where ctx contains channel/sender info
  on(event: string, handler: (event: any, ctx?: any) => void | Promise<void | { prependContext?: string }>): void;
  // Add more as needed
}

export interface MoltbotConfig {
  agents?: {
    defaults?: {
      models?: {
        [modelName: string]: {
          alias?: string;
        };
      };
    };
  };
  plugins?: {
    entries?: {
      [pluginId: string]: {
        enabled?: boolean;
        config?: PluginConfig;
      };
    };
  };
}

export interface PluginConfig {
  bankMission?: string;
  embedPort?: number;
  daemonIdleTimeout?: number; // Seconds before daemon shuts down (0 = never)
  embedVersion?: string; // hindsight-embed version (default: "latest")
  embedPackagePath?: string; // Local path to hindsight package (e.g. '/path/to/hindsight')
  llmProvider?: string; // LLM provider override (e.g. 'openai', 'anthropic', 'gemini', 'groq', 'ollama')
  llmModel?: string; // LLM model override (e.g. 'gpt-4o-mini', 'claude-3-5-haiku-20241022')
  llmApiKeyEnv?: string; // Env var name holding the API key (e.g. 'MY_CUSTOM_KEY')
  apiPort?: number; // Port for openclaw profile daemon (default: 9077)
  hindsightApiUrl?: string; // External Hindsight API URL (skips local daemon when set)
  hindsightApiToken?: string; // API token for external Hindsight API authentication
  dynamicBankId?: boolean; // Enable per-channel memory banks (default: true)
  isolationStrategy?: 'agent' | 'user' | 'channel' | 'agent_user' | 'agent_channel' | 'channel_user' | 'agent_channel_user';
  bankIdPrefix?: string; // Prefix for bank IDs (e.g. 'prod' -> 'prod-slack-C123')
  excludeProviders?: string[]; // Message providers to exclude from recall/retain (e.g. ['telegram', 'discord'])
  autoRecall?: boolean; // Auto-recall memories on every prompt (default: true). Set to false when agent has its own recall tool.
  recallBudget?: 'low' | 'mid' | 'high'; // Budget for recall (default: 'mid')
  recallMaxTokens?: number; // Max tokens for recall results (default: 1024)
  recallTimeoutMs?: number; // Timeout for recall (default: 10000)
  useReflect?: boolean; // Use reflect instead of recall for auto-recall (default: false)
  reflectBudget?: 'low' | 'mid' | 'high'; // Budget for reflect (default: 'mid')
  reflectMaxTokens?: number; // Max tokens for reflect response (default: 1024)
  reflectTimeoutMs?: number; // Timeout for reflect (default: 30000)
  autoRetain?: boolean; // Auto-retain memories after every interaction (default: true).
  llmBaseUrl?: string; // LLM base URL (e.g. 'https://api.openai.com/v1' or OpenRouter URL)
}

export interface ServiceConfig {
  id: string;
  start(): Promise<void>;
  stop(): Promise<void>;
}

// Hindsight API types

export interface RetainRequest {
  content: string;
  document_id?: string;
  metadata?: Record<string, unknown>;
}

export interface RetainResponse {
  message: string;
  document_id: string;
  memory_unit_ids: string[];
}

export interface RecallRequest {
  query: string;
  max_tokens?: number;
  budget?: 'low' | 'mid' | 'high';
}

export interface RecallResponse {
  results: MemoryResult[];
  entities: Record<string, unknown> | null;
  trace: unknown | null;
  chunks: unknown | null;
}

export interface ReflectRequest {
  query: string;
  budget?: 'low' | 'mid' | 'high';
  context?: string;
  max_tokens?: number;
}

export interface ReflectResponse {
  text: string;
  based_on?: {
    memories: MemoryResult[];
  };
  structured_output?: any;
}

export interface MemoryResult {
  id: string;
  text: string;
  type: string;
  entities: string[];
  context: string;
  occurred_start: string | null;
  occurred_end: string | null;
  mentioned_at: string | null;
  document_id: string | null;
  metadata: Record<string, unknown> | null;
  chunk_id: string | null;
  tags: string[];
}

export interface CreateBankRequest {
  name: string;
  background_context?: string;
}

export interface CreateBankResponse {
  bank_id: string;
  name: string;
  created_at: string;
}
