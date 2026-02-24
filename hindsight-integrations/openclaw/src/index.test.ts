import { describe, it, expect, vi } from 'vitest';
import { stripMemoryTags, extractRecallQuery, formatMemories } from './index.js';
import plugin from './index.js';
import type { MemoryResult } from './types.js';

// ---------------------------------------------------------------------------
// stripMemoryTags
// ---------------------------------------------------------------------------

describe('stripMemoryTags', () => {
  it('strips simple hindsight_memories tags', () => {
    const input =
      'User: Hello\n<hindsight_memories>\nRelevant memories here...\n</hindsight_memories>\nAssistant: How can I help?';
    expect(stripMemoryTags(input)).toBe('User: Hello\n\nAssistant: How can I help?');
  });

  it('strips relevant_memories tags', () => {
    const input = 'Before\n<relevant_memories>\nSome data\n</relevant_memories>\nAfter';
    expect(stripMemoryTags(input)).toBe('Before\n\nAfter');
  });

  it('strips multiple hindsight_memories blocks', () => {
    const input =
      'Start\n<hindsight_memories>\nBlock 1\n</hindsight_memories>\nMiddle\n<hindsight_memories>\nBlock 2\n</hindsight_memories>\nEnd';
    expect(stripMemoryTags(input)).toBe('Start\n\nMiddle\n\nEnd');
  });

  it('handles multiline memory blocks with JSON', () => {
    const input =
      'User: What is the weather?\n<hindsight_memories>\n[\n  {"memory": "User likes sunny weather"}\n]\n</hindsight_memories>\nAssistant: Let me check';
    const result = stripMemoryTags(input);
    expect(result).toBe('User: What is the weather?\n\nAssistant: Let me check');
  });

  it('preserves content without memory tags', () => {
    const input = 'User: Hello\nAssistant: Hi there!';
    expect(stripMemoryTags(input)).toBe(input);
  });

  it('strips both tag types in same content', () => {
    const input =
      'A\n<hindsight_memories>\nH mem\n</hindsight_memories>\nB\n<relevant_memories>\nR mem\n</relevant_memories>\nC';
    expect(stripMemoryTags(input)).toBe('A\n\nB\n\nC');
  });

  it('strips tags from a real-world agent conversation with injected memories', () => {
    const input =
      '[role: system]\n<hindsight_memories>\nRelevant memories:\n[{"text": "User prefers dark mode"}]\nUser message: How do I enable dark mode?\n</hindsight_memories>\n[system:end]\n\n[role: user]\nHow do I enable dark mode?\n[user:end]\n\n[role: assistant]\nLet me help you enable dark mode.\n[assistant:end]';

    const result = stripMemoryTags(input);

    expect(result).not.toContain('<hindsight_memories>');
    expect(result).not.toContain('</hindsight_memories>');
    expect(result).not.toContain('User prefers dark mode');
    expect(result).toContain('[role: user]');
    expect(result).toContain('How do I enable dark mode?');
    expect(result).toContain('[role: assistant]');
  });
});

// ---------------------------------------------------------------------------
// extractRecallQuery
// ---------------------------------------------------------------------------

describe('extractRecallQuery', () => {
  it('returns rawMessage when it is long enough', () => {
    expect(extractRecallQuery('What is my favorite food?', undefined)).toBe(
      'What is my favorite food?',
    );
  });

  it('returns null when rawMessage is too short and prompt is absent', () => {
    expect(extractRecallQuery('Hi', undefined)).toBeNull();
    expect(extractRecallQuery('', '')).toBeNull();
    expect(extractRecallQuery(undefined, undefined)).toBeNull();
  });

  it('returns null when both rawMessage and prompt are too short', () => {
    expect(extractRecallQuery('Hey', 'Hey')).toBeNull();
  });

  it('falls back to prompt when rawMessage is absent', () => {
    const result = extractRecallQuery(undefined, 'What programming language do I prefer?');
    expect(result).toBe('What programming language do I prefer?');
  });

  it('strips leading System: lines from prompt', () => {
    const prompt = 'System: You are an agent.\nSystem: Use tools wisely.\n\nWhat is my name?';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).not.toContain('System:');
    expect(result).toContain('What is my name?');
  });

  it('strips [Channel] envelope header and returns inner message', () => {
    const prompt = '[Telegram Chat]\nWhat is my favorite hobby?';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).toBe('What is my favorite hobby?');
  });

  it('strips [from: SenderName] footer from group chat prompts', () => {
    const prompt = '[Slack Channel #general]\nWhat should I eat for lunch?\n[from: Alice]';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).not.toContain('[from: Alice]');
    expect(result).toContain('What should I eat for lunch?');
  });

  it('handles full envelope with System lines, channel header, and from footer', () => {
    const prompt =
      'System: You are a helpful agent.\n\n[Discord Server]\nRemind me what I said about Python?\n[from: Bob]';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).not.toContain('System:');
    expect(result).not.toContain('[Discord');
    expect(result).not.toContain('[from: Bob]');
    expect(result).toContain('Remind me what I said about Python?');
  });

  it('strips session abort hint from prompt', () => {
    const prompt =
      'Note: The previous agent run was aborted by the user\n\n[Telegram]\nWhat is my cat\'s name?';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).not.toContain('Note: The previous agent run was aborted');
    expect(result).toContain("What is my cat's name?");
  });

  it('returns null when prompt reduces to < 5 chars after stripping', () => {
    // Envelope with almost-empty inner message
    const prompt = '[Telegram Chat]\nHi';
    const result = extractRecallQuery(undefined, prompt);
    expect(result).toBeNull();
  });

  it('prefers rawMessage over prompt even when prompt is longer', () => {
    const rawMessage = 'What do I like to eat?';
    const prompt = '[Telegram]\nWhat do I like to eat?\n[from: Alice]';
    const result = extractRecallQuery(rawMessage, prompt);
    // Should return the clean rawMessage verbatim
    expect(result).toBe(rawMessage);
    expect(result).not.toContain('[from: Alice]');
  });

  it('trims whitespace from result', () => {
    const result = extractRecallQuery('   What is my job?   ', undefined);
    expect(result).toBe('What is my job?');
  });
});

// ---------------------------------------------------------------------------
// formatMemories
// ---------------------------------------------------------------------------

describe('formatMemories', () => {
  it('formats memories as bullet list with only text and date', () => {
    const memories: MemoryResult[] = [
      {
        id: 'mem_1',
        text: 'User likes pizza',
        type: 'fact',
        entities: ['pizza'],
        context: 'conversation',
        occurred_start: '2023-01-01T10:00:00Z',
        occurred_end: '2023-01-01T10:00:00Z',
        mentioned_at: '2023-01-01T10:00:00Z',
        document_id: 'doc_1',
        metadata: { foo: 'bar' },
        chunk_id: 'chunk_1',
        tags: ['food'],
      },
    ];

    const result = formatMemories(memories);

    expect(result).toBe('- User likes pizza (2023-01-01T10:00:00Z)');
    expect(result).not.toContain('mem_1');
    expect(result).not.toContain('fact');
    expect(result).not.toContain('bar');
  });

  it('omits date when mentioned_at is null', () => {
    const memories: MemoryResult[] = [
      {
        id: 'mem_2',
        text: 'User prefers dark mode',
        type: 'fact',
        entities: [],
        context: '',
        occurred_start: null,
        occurred_end: null,
        mentioned_at: null,
        document_id: null,
        metadata: null,
        chunk_id: null,
        tags: [],
      },
    ];

    expect(formatMemories(memories)).toBe('- User prefers dark mode');
  });

  it('handles empty results', () => {
    expect(formatMemories([])).toBe('');
  });
});

// ---------------------------------------------------------------------------
// autoRecall = false test
// ---------------------------------------------------------------------------

describe('autoRecall disabled', () => {
  it('respects autoRecall = false and skips recall', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex',
                autoRecall: false
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    // Load plugin
    plugin(api);

    // Get the hook handler
    const beforeAgentStartHook = api.on.mock.calls.find(call => call[0] === 'before_agent_start')?.[1];
    expect(beforeAgentStartHook).toBeDefined();

    // Call the hook
    const result = await beforeAgentStartHook({ rawMessage: 'test', prompt: 'test' }, { agentId: 'agent' });

    // Result should be undefined (nothing prepended)
    expect(result).toBeUndefined();
  });

  it('respects auto_recall = false (snake_case) and skips recall', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex',
                auto_recall: false
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    // Load plugin
    plugin(api);

    // Get the hook handler
    const beforeAgentStartHook = api.on.mock.calls.find(call => call[0] === 'before_agent_start')?.[1];

    // Call the hook
    const result = await beforeAgentStartHook({ rawMessage: 'test', prompt: 'test' }, { agentId: 'agent' });

    expect(result).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// agent_end hook robustness
// ---------------------------------------------------------------------------

describe('agent_end robustness', () => {
  it('handles lenient success and fallback messages', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex'
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    // Load plugin
    plugin(api);

    // Get the agent_end hook handler
    const agentEndHook = api.on.mock.calls.find(call => call[0] === 'agent_end')?.[1];
    expect(agentEndHook).toBeDefined();

    // Mock client
    const mockClient = {
      retain: vi.fn().mockResolvedValue({}),
      setBankId: vi.fn(),
    };
    (global as any).__hindsightClient = {
      waitForReady: vi.fn().mockResolvedValue(undefined),
      getClientForContext: vi.fn().mockResolvedValue(mockClient),
    };

    // Test case: success is undefined, messages in context
    const event = {
      // success: undefined
      context: {
        sessionEntry: {
          messages: ['Hello world']
        }
      }
    };

    await agentEndHook(event, { agentId: 'agent1' });

    expect(mockClient.retain).toHaveBeenCalled();
    const retainArgs = mockClient.retain.mock.calls[0][0];
    expect(retainArgs.content).toContain('Hello world');
  });

  it('handles string messages vs object messages', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex'
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    plugin(api);
    const agentEndHook = api.on.mock.calls.find(call => call[0] === 'agent_end')?.[1];

    const mockClient = {
      retain: vi.fn().mockResolvedValue({}),
      setBankId: vi.fn(),
    };
    (global as any).__hindsightClient = {
      waitForReady: vi.fn().mockResolvedValue(undefined),
      getClientForContext: vi.fn().mockResolvedValue(mockClient),
    };

    // Test case: mixed format messages
    const event = {
      success: true,
      messages: [
        'String message',
        { role: 'assistant', content: 'Object message' },
        { role: 'user', text: 'Text property message' }
      ]
    };

    await agentEndHook(event, { agentId: 'agent1' });

    expect(mockClient.retain).toHaveBeenCalled();
    const retainArgs = mockClient.retain.mock.calls[0][0];
    expect(retainArgs.content).toContain('String message');
    expect(retainArgs.content).toContain('Object message');
    expect(retainArgs.content).toContain('Text property message');
  });

  it('retains only messages starting from the last user message (duplication fix)', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex'
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    plugin(api);
    const agentEndHook = api.on.mock.calls.find(call => call[0] === 'agent_end')?.[1];

    const mockClient = {
      retain: vi.fn().mockResolvedValue({}),
      setBankId: vi.fn(),
    };
    (global as any).__hindsightClient = {
      waitForReady: vi.fn().mockResolvedValue(undefined),
      getClientForContext: vi.fn().mockResolvedValue(mockClient),
    };

    // Test case: Conversation history [User1, Asst1, User2, Asst2]
    // Should retain [User2, Asst2] only.
    const event = {
      success: true,
      messages: [
        { role: 'user', content: 'Turn 1 User' },
        { role: 'assistant', content: 'Turn 1 Asst' },
        { role: 'user', content: 'Turn 2 User' },
        { role: 'assistant', content: 'Turn 2 Asst' }
      ]
    };

    await agentEndHook(event, { agentId: 'agent1' });

    expect(mockClient.retain).toHaveBeenCalled();
    const retainArgs = mockClient.retain.mock.calls[0][0];
    const content = retainArgs.content;

    // Should contain Turn 2
    expect(content).toContain('Turn 2 User');
    expect(content).toContain('Turn 2 Asst');

    // Should NOT contain Turn 1
    expect(content).not.toContain('Turn 1 User');
    expect(content).not.toContain('Turn 1 Asst');
  });
});

describe('autoReflect', () => {
  it('calls reflect when useReflect is true', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex',
                useReflect: true,
                reflectBudget: 'high',
                reflectMaxTokens: 2048,
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    plugin(api);
    const beforeAgentStartHook = api.on.mock.calls.find(call => call[0] === 'before_agent_start')?.[1];

    const mockClient = {
      recall: vi.fn().mockResolvedValue({ results: [] }),
      reflect: vi.fn().mockResolvedValue({ text: 'Reflected context', based_on: { memories: [] } }),
      setBankId: vi.fn(),
    };
    (global as any).__hindsightClient = {
      waitForReady: vi.fn().mockResolvedValue(undefined),
      getClientForContext: vi.fn().mockResolvedValue(mockClient),
    };

    const event = { rawMessage: 'What do I like?', prompt: 'What do I like?' };
    const result = await beforeAgentStartHook(event, { agentId: 'agent1' });

    expect(mockClient.reflect).toHaveBeenCalled();
    const reflectArgs = mockClient.reflect.mock.calls[0][0];
    expect(reflectArgs.query).toBe('What do I like?');
    expect(reflectArgs.budget).toBe('high');
    expect(reflectArgs.max_tokens).toBe(2048); // Uses configured max_tokens

    expect(mockClient.recall).not.toHaveBeenCalled();

    expect(result.prependContext).toContain('Reflected context');
  });

  it('calls recall when useReflect is false (default)', async () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                llmProvider: 'openai-codex',
                useReflect: false
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as any;

    plugin(api);
    const beforeAgentStartHook = api.on.mock.calls.find(call => call[0] === 'before_agent_start')?.[1];

    const mockClient = {
      recall: vi.fn().mockResolvedValue({ results: [{ text: 'Memory 1', mentioned_at: '2023-01-01' }] }),
      reflect: vi.fn(),
      setBankId: vi.fn(),
    };
    (global as any).__hindsightClient = {
      waitForReady: vi.fn().mockResolvedValue(undefined),
      getClientForContext: vi.fn().mockResolvedValue(mockClient),
    };

    const event = { rawMessage: 'What do I like?', prompt: 'What do I like?' };
    const result = await beforeAgentStartHook(event, { agentId: 'agent1' });

    expect(mockClient.recall).toHaveBeenCalled();
    const recallArgs = mockClient.recall.mock.calls[0][0];
    expect(recallArgs.max_tokens).toBe(1024); // Verify reduced max_tokens

    expect(mockClient.reflect).not.toHaveBeenCalled();
    expect(result.prependContext).toContain('Memory 1');
  });
});
