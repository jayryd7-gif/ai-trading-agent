import anthropic

# The key is supplied by GitHub (a "secret"), never written in the code
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say hello in five words."}],
)
print(message.content[0].text)
