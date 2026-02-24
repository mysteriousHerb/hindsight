import re

filepath = 'hindsight-integrations/openclaw/src/index.ts'

with open(filepath, 'r') as f:
    content = f.read()

# New function definition
new_derive_bank_id = """export function deriveBankId(ctx: PluginHookAgentContext | undefined, pluginConfig: PluginConfig): string {
  if (!pluginConfig.dynamicBankId) return 'openclaw';

  const fields = pluginConfig.isolationFields || ['agent', 'channel', 'user'];

  const fieldMap: Record<string, string> = {
    agent: ctx?.agentId || 'default',
    channel: ctx?.channelId || 'unknown',
    user: ctx?.senderId || 'anonymous',
    provider: ctx?.messageProvider || 'unknown',
  };

  const baseBankId = fields
    .map(f => fieldMap[f] || 'unknown')
    .join('-');

  return pluginConfig.bankIdPrefix
    ? `${pluginConfig.bankIdPrefix}-${baseBankId}`
    : baseBankId;
}"""

# Find and replace the old function
# The old function has:
#   const fieldMap: Record<string, string> = {
#     agent: ctx?.agentId || 'default',
#     channel: ctx?.channelId || 'unknown',
#     user: ctx?.senderId || 'anonymous',
#   };

start_marker = "export function deriveBankId(ctx: PluginHookAgentContext | undefined, pluginConfig: PluginConfig): string {"
end_marker = "return pluginConfig.bankIdPrefix"

start_pos = content.find(start_marker)
if start_pos == -1:
    print("Could not find function start")
    exit(1)

# Find end of function (naive)
# It ends after `return ... : baseBankId;\n}`
end_pos = content.find(": baseBankId;\n}", start_pos)
if end_pos == -1:
    print("Could not find function end")
    exit(1)

end_pos += len(": baseBankId;\n}")

content = content[:start_pos] + new_derive_bank_id + content[end_pos:]

with open(filepath, 'w') as f:
    f.write(content)
