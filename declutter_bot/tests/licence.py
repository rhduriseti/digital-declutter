from anthropic import Anthropic
import httpx

http_client = httpx.Client(verify=False)
client = Anthropic(
    api_key="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",
    http_client=http_client
)

prompt = "Who are you?"
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=300,
    messages=[
        {"role": "user", "content": prompt}
    ]
)