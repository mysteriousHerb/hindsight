import json

filepath = 'hindsight-integrations/openclaw/openclaw.plugin.json'

with open(filepath, 'r') as f:
    data = json.load(f)

# Update isolationFields enum
props = data['configSchema']['properties']
if 'isolationFields' in props:
    current_enum = props['isolationFields']['items']['enum']
    if 'provider' not in current_enum:
        current_enum.append('provider')
        # Keep default as is, just add capability
        # props['isolationFields']['default'] = ["agent", "channel", "user"]

with open(filepath, 'w') as f:
    json.dump(data, f, indent=2)
