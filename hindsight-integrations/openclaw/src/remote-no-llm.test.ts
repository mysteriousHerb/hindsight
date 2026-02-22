import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getPluginConfig } from './index.js';
import plugin from './index.js';
import type { MoltbotPluginAPI } from './types.js';

describe('Remote Hindsight Service (No LLM Config)', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    // Clear any standard LLM env vars
    delete process.env.OPENAI_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.GEMINI_API_KEY;
    delete process.env.GROQ_API_KEY;
    delete process.env.HINDSIGHT_API_LLM_PROVIDER;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should initialize successfully with external API URL even if LLM config is missing', () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                hindsight_api_url: 'https://api.hindsight.example.com'
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as unknown as MoltbotPluginAPI;

    // This should NOT throw
    expect(() => plugin(api)).not.toThrow();
    expect(api.registerService).toHaveBeenCalled();
  });

  it('should throw if neither external API nor LLM config is present', () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                // empty config
              }
            }
          }
        }
      },
      registerService: vi.fn(),
      on: vi.fn(),
    } as unknown as MoltbotPluginAPI;

    expect(() => plugin(api)).toThrow(/No LLM configuration found/);
  });
});
