import { describe, it, expect } from 'vitest';
import { deriveBankId } from './index.js';
import type { PluginHookAgentContext, PluginConfig } from './types.js';

describe('deriveBankId', () => {
  const ctx: PluginHookAgentContext = {
    agentId: 'agent-123',
    channelId: 'channel-456',
    senderId: 'user-789',
    messageProvider: 'slack',
  };

  const baseConfig: PluginConfig = {
    dynamicBankId: true,
  };

  it('should use default isolation fields when not specified', () => {
    const bankId = deriveBankId(ctx, baseConfig);
    expect(bankId).toBe('agent-123-channel-456-user-789');
  });

  it('should support ["agent", "user"] isolation', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['agent', 'user'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('agent-123-user-789');
  });

  it('should support ["user"] isolation', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['user'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('user-789');
  });

  it('should support ["agent"] isolation', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['agent'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('agent-123');
  });

  it('should support ["channel"] isolation', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['channel'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('channel-456');
  });

  it('should support ["provider"] isolation', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['provider'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('slack');
  });

  it('should support mixed fields including provider', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: ['provider', 'user'] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('slack-user-789');
  });

  it('should prepend bankIdPrefix if set', () => {
    const config: PluginConfig = { ...baseConfig, bankIdPrefix: 'prod' };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('prod-agent-123-channel-456-user-789');
  });

  it('should use fallback values for missing context fields', () => {
    const partialCtx: PluginHookAgentContext = {
      agentId: 'agent-123',
    };
    const bankId = deriveBankId(partialCtx, baseConfig);
    expect(bankId).toBe('agent-123-unknown-anonymous');
  });

  it('should return "openclaw" if dynamicBankId is false', () => {
    const config: PluginConfig = { dynamicBankId: false };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('openclaw');
  });

  it('should handle undefined context with fallback values', () => {
    const config: PluginConfig = { dynamicBankId: true };
    const bankId = deriveBankId(undefined, config);
    expect(bankId).toBe('default-unknown-anonymous');
  });

  it('should handle empty isolationFields array', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: [] };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('');
  });

  it('should handle empty isolationFields with prefix', () => {
    const config: PluginConfig = { ...baseConfig, isolationFields: [], bankIdPrefix: 'prod' };
    const bankId = deriveBankId(ctx, config);
    expect(bankId).toBe('prod-');
  });
});
