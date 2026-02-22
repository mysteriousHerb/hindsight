import { describe, it, expect } from 'vitest';
import { deriveBankId } from './index.js';
import type { PluginConfig } from './types.js';

describe('deriveBankId', () => {
  const defaultConfig: PluginConfig = {
    dynamicBankId: true,
  };

  it('includes agentId in the bank ID', () => {
    const ctx = {
      agentId: 'my-agent',
      messageProvider: 'slack',
      senderId: 'U123',
    };
    const bankId = deriveBankId(ctx, defaultConfig);
    expect(bankId).toBe('my-agent-slack-U123');
  });

  it('uses default when fields are missing', () => {
    const ctx = {};
    const bankId = deriveBankId(ctx, defaultConfig);
    expect(bankId).toBe('default-unknown-default');
  });

  it('uses prefix when configured', () => {
    const ctx = {
      agentId: 'agent1',
      messageProvider: 'discord',
      senderId: 'user456',
    };
    const config: PluginConfig = {
      ...defaultConfig,
      bankIdPrefix: 'prod',
    };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('prod-agent1-discord-user456');
  });

  it('returns static bank ID when dynamicBankId is disabled', () => {
    const ctx = {
      agentId: 'agent1',
      messageProvider: 'discord',
      senderId: 'user456',
    };
    const config: PluginConfig = {
      ...defaultConfig,
      dynamicBankId: false,
    };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('openclaw');
  });

  it('returns static bank ID with prefix when dynamicBankId is disabled', () => {
    const ctx = {
      agentId: 'agent1',
      messageProvider: 'discord',
      senderId: 'user456',
    };
    const config: PluginConfig = {
      ...defaultConfig,
      dynamicBankId: false,
      bankIdPrefix: 'my-app',
    };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('my-app-openclaw');
  });
});
