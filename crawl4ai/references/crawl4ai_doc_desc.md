Quick Start Guide 🚀
Welcome to the Crawl4AI Quickstart Guide! In this tutorial, we'll walk you through the basic usage of Crawl4AI with a friendly and humorous tone. We'll cover everything from basic usage to advanced features like chunking and extraction strategies. Let's dive in! 🌟

Getting Started 🛠️

First, let's create an instance of WebCrawler and call the warmup() function. This might take a few seconds the first time you run Crawl4AI, as it loads the required model files.

from crawl4ai import WebCrawler

def create_crawler():
    crawler = WebCrawler(verbose=True)
    crawler.warmup()
    return crawler

crawler = create_crawler()
Basic Usage

Simply provide a URL and let Crawl4AI do the magic!

result = crawler.run(url="https://www.nbcnews.com/business")
print(f"Basic crawl result: {result}")
Taking Screenshots 📸

Let's take a screenshot of the page!

result = crawler.run(url="https://www.nbcnews.com/business", screenshot=True)
with open("screenshot.png", "wb") as f:
    f.write(base64.b64decode(result.screenshot))
print("Screenshot saved to 'screenshot.png'!")
Understanding Parameters 🧠

By default, Crawl4AI caches the results of your crawls. This means that subsequent crawls of the same URL will be much faster! Let's see this in action.

First crawl (caches the result):

result = crawler.run(url="https://www.nbcnews.com/business")
print(f"First crawl result: {result}")
Force to crawl again:

result = crawler.run(url="https://www.nbcnews.com/business", bypass_cache=True)
print(f"Second crawl result: {result}")
Adding a Chunking Strategy 🧩

Let's add a chunking strategy: RegexChunking! This strategy splits the text based on a given regex pattern.

from crawl4ai.chunking_strategy import RegexChunking

result = crawler.run(
    url="https://www.nbcnews.com/business",
    chunking_strategy=RegexChunking(patterns=["\n\n"])
)
print(f"RegexChunking result: {result}")
You can also use NlpSentenceChunking which splits the text into sentences using NLP techniques.

from crawl4ai.chunking_strategy import NlpSentenceChunking

result = crawler.run(
    url="https://www.nbcnews.com/business",
    chunking_strategy=NlpSentenceChunking()
)
print(f"NlpSentenceChunking result: {result}")
Adding an Extraction Strategy 🧠

Let's get smarter with an extraction strategy: CosineStrategy! This strategy uses cosine similarity to extract semantically similar blocks of text.

from crawl4ai.extraction_strategy import CosineStrategy

result = crawler.run(
    url="https://www.nbcnews.com/business",
    extraction_strategy=CosineStrategy(
        word_count_threshold=10, 
        max_dist=0.2, 
        linkage_method="ward", 
        top_k=3
    )
)
print(f"CosineStrategy result: {result}")
You can also pass other parameters like semantic_filter to extract specific content.

result = crawler.run(
    url="https://www.nbcnews.com/business",
    extraction_strategy=CosineStrategy(
        semantic_filter="inflation rent prices"
    )
)
print(f"CosineStrategy result with semantic filter: {result}")
Using LLMExtractionStrategy 🤖

Time to bring in the big guns: LLMExtractionStrategy without instructions! This strategy uses a large language model to extract relevant information from the web page.

from crawl4ai.extraction_strategy import LLMExtractionStrategy
import os

result = crawler.run(
    url="https://www.nbcnews.com/business",
    extraction_strategy=LLMExtractionStrategy(
        provider="openai/gpt-4o", 
        api_token=os.getenv('OPENAI_API_KEY')
    )
)
print(f"LLMExtractionStrategy (no instructions) result: {result}")
You can also provide specific instructions to guide the extraction.

result = crawler.run(
    url="https://www.nbcnews.com/business",
    extraction_strategy=LLMExtractionStrategy(
        provider="openai/gpt-4o",
        api_token=os.getenv('OPENAI_API_KEY'),
        instruction="I am interested in only financial news"
    )
)
print(f"LLMExtractionStrategy (with instructions) result: {result}")
Targeted Extraction 🎯

Let's use a CSS selector to extract only H2 tags!

result = crawler.run(
    url="https://www.nbcnews.com/business",
    css_selector="h2"
)
print(f"CSS Selector (H2 tags) result: {result}")
Interactive Extraction 🖱️

Passing JavaScript code to click the 'Load More' button!

js_code = """
const loadMoreButton = Array.from(document.querySelectorAll('button')).find(button => button.textContent.includes('Load More'));
loadMoreButton && loadMoreButton.click();
"""

result = crawler.run(
    url="https://www.nbcnews.com/business",
    js=js_code
)
print(f"JavaScript Code (Load More button) result: {result}")
Using Crawler Hooks 🔗

Let's see how we can customize the crawler using hooks!

import time

from crawl4ai.web_crawler import WebCrawler
from crawl4ai.crawler_strategy import *

def delay(driver):
    print("Delaying for 5 seconds...")
    time.sleep(5)
    print("Resuming...")

def create_crawler():
    crawler_strategy = LocalSeleniumCrawlerStrategy(verbose=True)
    crawler_strategy.set_hook('after_get_url', delay)
    crawler = WebCrawler(verbose=True, crawler_strategy=crawler_strategy)
    crawler.warmup()
    return crawler

crawler = create_crawler()
result = crawler.run(url="https://www.nbcnews.com/business", bypass_cache=True)
check Hooks for more examples.

Congratulations! 🎉

You've made it through the Crawl4AI Quickstart Guide! Now go forth and crawl the web like a pro! 🕸️

Research Assistant Example

This example demonstrates how to build a research assistant using Chainlit and Crawl4AI. The assistant will be capable of crawling web pages for information and answering questions based on the crawled content. Additionally, it integrates speech-to-text functionality for audio inputs.

Step-by-Step Guide

Install Required Packages

Ensure you have the necessary packages installed. You need chainlit, groq, requests, and openai.

bash pip install chainlit groq requests openai

Import Libraries

Import all the necessary modules and initialize the OpenAI client.

```python import os import time from openai import AsyncOpenAI import chainlit as cl import re import requests from io import BytesIO from chainlit.element import ElementBased from groq import Groq

from concurrent.futures import ThreadPoolExecutor

client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))

Instrument the OpenAI client
cl.instrument_openai() ```

Set Configuration

Define the model settings for the assistant.

python settings = { "model": "llama3-8b-8192", "temperature": 0.5, "max_tokens": 500, "top_p": 1, "frequency_penalty": 0, "presence_penalty": 0, }

Define Utility Functions

Extract URLs from Text: Use regex to find URLs in messages.

python def extract_urls(text): url_pattern = re.compile(r'(https?://\S+)') return url_pattern.findall(text)

Crawl URL: Send a request to Crawl4AI to fetch the content of a URL.

python def crawl_url(url): data = { "urls": [url], "include_raw_html": True, "word_count_threshold": 10, "extraction_strategy": "NoExtractionStrategy", "chunking_strategy": "RegexChunking" } response = requests.post("https://crawl4ai.com/crawl", json=data) response_data = response.json() response_data = response_data['results'][0] return response_data['markdown']

Initialize Chat Start Event

Set up the initial chat message and user session.

python @cl.on_chat_start async def on_chat_start(): cl.user_session.set("session", { "history": [], "context": {} }) await cl.Message( content="Welcome to the chat! How can I assist you today?" ).send()

Handle Incoming Messages

Process user messages, extract URLs, and crawl them concurrently. Update the chat history and system message.

```python @cl.on_message async def on_message(message: cl.Message): user_session = cl.user_session.get("session")

# Extract URLs from the user's message
urls = extract_urls(message.content)

futures = []
with ThreadPoolExecutor() as executor:
    for url in urls:
        futures.append(executor.submit(crawl_url, url))

results = [future.result() for future in futures]

for url, result in zip(urls, results):
    ref_number = f"REF_{len(user_session['context']) + 1}"
    user_session["context"][ref_number] = {
        "url": url,
        "content": result
    }

user_session["history"].append({
    "role": "user",
    "content": message.content
})

# Create a system message that includes the context
context_messages = [
    f'<appendix ref="{ref}">\n{data["content"]}\n</appendix>'
    for ref, data in user_session["context"].items()
]
if context_messages:
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful bot. Use the following context for answering questions. "
            "Refer to the sources using the REF number in square brackets, e.g., [1], only if the source is given in the appendices below.\n\n"
            "If the question requires any information from the provided appendices or context, refer to the sources. "
            "If not, there is no need to add a references section. "
            "At the end of your response, provide a reference section listing the URLs and their REF numbers only if sources from the appendices were used.\n\n"
            "\n\n".join(context_messages)
        )
    }
else:
    system_message = {
        "role": "system",
        "content": "You are a helpful assistant."
    }

msg = cl.Message(content="")
await msg.send()

# Get response from the LLM
stream = await client.chat.completions.create(
    messages=[
        system_message,
        *user_session["history"]
    ],
    stream=True,
    **settings
)

assistant_response = ""
async for part in stream:
    if token := part.choices[0].delta.content:
        assistant_response += token
        await msg.stream_token(token)

# Add assistant message to the history
user_session["history"].append({
    "role": "assistant",
    "content": assistant_response
})
await msg.update()

# Append the reference section to the assistant's response
reference_section = "\n\nReferences:\n"
for ref, data in user_session["context"].items():
    reference_section += f"[{ref.split('_')[1]}]: {data['url']}\n"

msg.content += reference_section
await msg.update()
```

Handle Audio Input

Capture and transcribe audio input. Store the audio buffer and transcribe it when the audio ends.

```python @cl.on_audio_chunk async def on_audio_chunk(chunk: cl.AudioChunk): if chunk.isStart: buffer = BytesIO() buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}" cl.user_session.set("audio_buffer", buffer) cl.user_session.set("audio_mime_type", chunk.mimeType)

cl.user_session.get("audio_buffer").write(chunk.data)
@cl.step(type="tool") async def speech_to_text(audio_file): cli = Groq() response = await client.audio.transcriptions.create( model="whisper-large-v3", file=audio_file ) return response.text

@cl.on_audio_end async def on_audio_end(elements: list[ElementBased]): audio_buffer: BytesIO = cl.user_session.get("audio_buffer") audio_buffer.seek(0) audio_file = audio_buffer.read() audio_mime_type: str = cl.user_session.get("audio_mime_type")

start_time = time.time()
transcription = await speech_to_text((audio_buffer.name, audio_file, audio_mime_type))
end_time = time.time()
print(f"Transcription took {end_time - start_time} seconds")

user_msg = cl.Message(
    author="You", 
    type="user_message",
    content=transcription
)
await user_msg.send()
await on_message(user_msg)
```

Run the Chat Application

Start the Chainlit application.

python if __name__ == "__main__": from chainlit.cli import run_chainlit run_chainlit(__file__)

Explanation

Libraries and Configuration: Import necessary libraries and configure the OpenAI client.
Utility Functions: Define functions to extract URLs and crawl them.
Chat Start Event: Initialize chat session and welcome message.
Message Handling: Extract URLs, crawl them concurrently, and update chat history and context.
Audio Handling: Capture, buffer, and transcribe audio input, then process the transcription as text.
Running the Application: Start the Chainlit server to interact with the assistant.
This example showcases how to create an interactive research assistant that can fetch, process, and summarize web content, along with handling audio inputs for a seamless user experience.