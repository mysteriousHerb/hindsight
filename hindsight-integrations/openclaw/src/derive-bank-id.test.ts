import { describe, it, expect } from 'vitest';
import { deriveBankId } from './index.js';
import type { PluginConfig } from './types.js';

describe('deriveBankId', () => {
  const defaultConfig: PluginConfig = {
    dynamicBankId: true,
  };

  const testCtx = {
    agentId: 'my-agent',
    messageProvider: 'slack',
    channelId: 'C123',
    senderId: 'U456',
  };

  it('includes agentId in the bank ID (default legacy behavior)', () => {
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

  it('handles normalized config properties', () => {
    const ctx = {
      agentId: 'agent1',
      messageProvider: 'discord',
      senderId: 'user456',
    };
    const config: PluginConfig = {
      dynamicBankId: true,
      bankIdPrefix: 'prod',
    };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('prod-agent1-discord-user456');
  });

  it('supports "agent" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'agent' };
    expect(deriveBankId(testCtx, config)).toBe('my-agent');
  });

  it('supports "user" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'user' };
    expect(deriveBankId(testCtx, config)).toBe('U456');
  });

  it('supports "channel" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'channel' };
    expect(deriveBankId(testCtx, config)).toBe('C123');
  });

  it('supports "agent_user" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'agent_user' };
    expect(deriveBankId(testCtx, config)).toBe('my-agent-U456');
  });

  it('supports "agent_channel" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'agent_channel' };
    expect(deriveBankId(testCtx, config)).toBe('my-agent-C123');
  });

  it('supports "channel_user" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'channel_user' };
    expect(deriveBankId(testCtx, config)).toBe('C123-U456');
  });

  it('supports "agent_channel_user" isolation strategy', () => {
    const config: PluginConfig = { ...defaultConfig, isolationStrategy: 'agent_channel_user' };
    expect(deriveBankId(testCtx, config)).toBe('my-agent-slack-U456');
  });

  it('uses prefix with isolation strategy', () => {
    const config: PluginConfig = {
      ...defaultConfig,
      isolationStrategy: 'channel',
      bankIdPrefix: 'prod',
    };
    expect(deriveBankId(testCtx, config)).toBe('prod-C123');
  });
});
