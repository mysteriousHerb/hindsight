import { describe, it, expect } from 'vitest';
import { getPluginConfig } from './index.js';
import type { MoltbotPluginAPI } from './types.js';

describe('getPluginConfig robustness', () => {
  it('prefers camelCase but falls back to snake_case', () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                auto_recall: false,
                bank_id_prefix: 'test-prefix',
                llm_base_url: 'https://example.com'
              }
            }
          }
        }
      }
    } as unknown as MoltbotPluginAPI;

    const config = getPluginConfig(api);
    expect(config.autoRecall).toBe(false);
    expect(config.bankIdPrefix).toBe('test-prefix');
    expect(config.llmBaseUrl).toBe('https://example.com');
  });

  it('prefers camelCase over snake_case when both are present', () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                autoRecall: true,
                auto_recall: false
              }
            }
          }
        }
      }
    } as unknown as MoltbotPluginAPI;

    const config = getPluginConfig(api);
    expect(config.autoRecall).toBe(true);
  });

  it('handles nested objects and arrays correctly', () => {
    const api = {
      config: {
        plugins: {
          entries: {
            'hindsight-openclaw': {
              config: {
                exclude_providers: ['telegram']
              }
            }
          }
        }
      }
    } as unknown as MoltbotPluginAPI;

    const config = getPluginConfig(api);
    expect(config.excludeProviders).toEqual(['telegram']);
  });
});
