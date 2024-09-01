# crawl4ai/crawl4ai/paper_scorer.py

import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI()

class PaperScore(BaseModel):
    title: str
    relevance_score: int = Field(..., ge=1, le=10)
    excitement_score: int = Field(..., ge=1, le=10)
    explanation: str

def score_papers(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to fetch papers
    query = """
    SELECT title, authors, abstract
    FROM papers
    ORDER BY id DESC
    LIMIT 30
    """

    # Execute the query
    cursor.execute(query)
    papers = cursor.fetchall()

    # Close the database connection
    conn.close()

    logging.info(f"Fetched {len(papers)} papers from the database")

    scored_papers = []

    for index, (title, authors, abstract) in enumerate(papers, 1):
        logging.info(f"Processing paper {index}/{len(papers)}: {title}")
        
        prompt = f"Please analyze the following paper abstract and provide scores from 1-10 for its relevance to AI research and excitement level the paper will create field of AI. Respond with a JSON object containing 'relevance_score', 'excitement_score', and a brief 'explanation'. Abstract: {abstract}"

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an expert AI researcher with extensive knowledge of the latest advancements in artificial intelligence, machine learning, and related fields. Your task is to critically evaluate research papers based on their abstracts. When analyzing a paper, consider the following aspects:

                        1. Novelty: How innovative is the proposed approach or idea?
                        2. Potential Impact: What are the possible applications and implications of this research?
                        3. Methodology: Is the approach scientifically sound and well-justified?
                        4. Clarity: How well is the abstract written and how clearly are the ideas presented?
                        5. Relevance: How closely does this research align with current trends and challenges in AI?

                        For each paper, provide a relevance score and an excitement score, both on a scale of 1-10. The relevance score should reflect how important this research is to the field of AI, while the excitement score should indicate how likely this paper is to generate interest and discussion among researchers.

                        In your explanation, briefly justify your scores and highlight the key strengths or weaknesses of the paper. Be objective and base your evaluation solely on the content of the abstract."""},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            response_content = json.loads(completion.choices[0].message.content)
            logging.info(f"API Response: {response_content}")
            
            paper_score = PaperScore(
                title=title,
                relevance_score=response_content['relevance_score'],
                excitement_score=response_content['excitement_score'],
                explanation=response_content['explanation']
            )
            scored_papers.append(paper_score)
            logging.info(f"Scored paper: {title} (Relevance: {paper_score.relevance_score}, Excitement: {paper_score.excitement_score})")
        except Exception as e:
            logging.error(f"Error scoring paper '{title}': {str(e)}")

    logging.info(f"Total papers scored: {len(scored_papers)}")
    return scored_papers

if __name__ == "__main__":
    db_path = 'arxiv_papers.db'
    scores = score_papers(db_path)
    
    # Filter papers with excitement score >= 9
    exciting_papers = [paper for paper in scores if paper.excitement_score >= 7]
    
    logging.info(f"Papers with excitement score >= 9: {len(exciting_papers)}")
    for paper in exciting_papers:
        logging.info(f"Exciting paper: {paper.title} (Excitement: {paper.excitement_score})")
    
    # Create a list of dict representations of the papers
    paper_dicts = [paper.model_dump() for paper in exciting_papers]
    
    # Save the filtered results to final_papers.json
    with open('final_papers.json', 'w') as f:
        json.dump(paper_dicts, f, indent=2)
    
    logging.info(f"Saved {len(exciting_papers)} exciting papers to final_papers.json")
