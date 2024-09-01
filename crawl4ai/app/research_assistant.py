import os
import re
import requests
from typing import List, Dict
from openai import AsyncOpenAI
import chainlit as cl
from concurrent.futures import ThreadPoolExecutor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawl_service import AcademicWebCrawler, AcademicPaperFilter

# Initialize the OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Instrument the OpenAI client
cl.instrument_openai()

# Model settings
settings = {
    "model": "gpt-4-turbo-preview",
    "temperature": 0.5,
    "max_tokens": 500,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}

def extract_urls(text: str) -> List[str]:
    url_pattern = re.compile(r'(https?://\S+)')
    return url_pattern.findall(text)

academic_crawler = AcademicWebCrawler()

def crawl_url(url: str) -> List[Dict]:
    papers = academic_crawler.parse_academic_page(url)
    return papers

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("session", {
        "history": [],
        "context": {}
    })
    await cl.Message(content="Welcome to the research assistant! How can I help you today?").send()

@cl.on_message
async def on_message(message: cl.Message):
    user_session = cl.user_session.get("session")
    
    # Extract URLs from the user's message
    urls = extract_urls(message.content)
    
    # Crawl URLs concurrently
    futures = []
    with ThreadPoolExecutor() as executor:
        for url in urls:
            futures.append(executor.submit(crawl_url, url))
    
    all_papers = []
    for future in futures:
        all_papers.extend(future.result())
    
    # Update context with crawled content
    for i, paper in enumerate(all_papers):
        ref_number = f"REF_{len(user_session['context']) + i + 1}"
        user_session["context"][ref_number] = {
            "title": paper['title'],
            "authors": paper['authors'],
            "abstract": paper['abstract'],
            "date": paper['date']
        }
    
    # Add user message to history
    user_session["history"].append({
        "role": "user",
        "content": message.content
    })
    
    # Create system message with context
    context_messages = [
        f'<appendix ref="{ref}">\nTitle: {data["title"]}\nAuthors: {data["authors"]}\nDate: {data["date"]}\nAbstract: {data["abstract"]}\n</appendix>'
        for ref, data in user_session["context"].items()
    ]
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful research assistant specializing in academic papers. Use the following context for answering questions. "
            "Refer to the sources using the REF number in square brackets, e.g., [1], only if the source is given in the appendices below.\n\n"
            "If the question requires any information from the provided appendices or context, refer to the sources. "
            "If not, there is no need to add a references section. "
            "At the end of your response, provide a reference section listing the paper titles and their REF numbers only if sources from the appendices were used.\n\n"
            "\n\n".join(context_messages)
        )
    }
    
    # Send initial message
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
    references = list(user_session["context"].keys())
    reference_section = "\n\nReferences:\n"
    for ref in references:
        if 'url' in user_session["context"][ref]:
            reference_section += f"[{ref.split('_')[1]}]: {user_session['context'][ref]['url']}\n"
        else:
            reference_section += f"[{ref.split('_')[1]}]: URL not available\n"
    
    msg.content += reference_section
    await msg.update()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)