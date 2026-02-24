import re

filepath = 'hindsight-integrations/openclaw/src/types.ts'

with open(filepath, 'r') as f:
    content = f.read()

# Update isolationFields comment
if "isolationFields?: string[]; // Subset of ['agent', 'channel', 'user']. Default: ['agent', 'channel', 'user']" in content:
    content = content.replace(
        "isolationFields?: string[]; // Subset of ['agent', 'channel', 'user']. Default: ['agent', 'channel', 'user']",
        "isolationFields?: string[]; // Subset of ['agent', 'provider', 'channel', 'user']. Default: ['agent', 'channel', 'user']"
    )

with open(filepath, 'w') as f:
    f.write(content)
