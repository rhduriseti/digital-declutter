#!/bin/bash
# Reset Claire to a clean state — removes all indexes, OAuth tokens, and local data.
# Useful for testing the onboarding flow from scratch.
# Run from anywhere: bash installer/reset_claire.sh

echo "Resetting Claire..."

rm -f ~/.declutter/*_index.json
rm -f ~/.declutter/drive_accounts/*.json
rm -f ~/.declutter/ollama_ready

# Clear folders from settings but keep GOOGLE_API_KEY and other keys
if [ -f ~/.declutter/settings.json ]; then
  python3 -c "
import json, pathlib
p = pathlib.Path('$HOME/.declutter/settings.json')
data = json.loads(p.read_text())
data.pop('folders', None)
p.write_text(json.dumps(data, indent=2))
"
fi

echo "Done. Then clear localStorage in the app (Cmd+Option+I → Console → localStorage.clear()), and you'll be back to the onboarding screen."
