import ollama

filename = "Insider_risk.pptx"
folder = "/Users/radhika/Documents_DD/DTEX/Insider_risk.pptx"

prompt = f"""You are a school file organiser.
Given this filename: "{filename}"
From this folder: "{folder}"

What school subject does this file belong to?
Reply in this exact format:
Subject: <subject name>
Confidence: <0.0 to 1.0>

Choose only from: math, biology, chemistry, physics, english,
history, geography, computer science, economics, psychology,
spanish, french, art, music, pe, other"""

response = ollama.chat(
    model="gemma3:4b",
    messages=[{"role": "user", "content": prompt}]
)

text = response["message"]["content"]
print("Raw response:")
print(text)
