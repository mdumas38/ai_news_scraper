# crawl4ai/crawl4ai/paper_scorer.py

import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI()

class PaperScore(BaseModel):
    title: str
    relevance_score: float = Field(..., ge=1.0, le=10.0)
    excitement_score: float = Field(..., ge=1.0, le=10.0)
    explanation: str
    pdf_url: str
    scored_at: datetime = Field(default_factory=datetime.utcnow)

def ensure_score_columns(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(papers)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'excitement_score' not in columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN excitement_score REAL")
    if 'relevance_score' not in columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN relevance_score REAL")
    
    conn.commit()
    conn.close()

def score_papers(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to fetch papers from today
    query = """
    SELECT id, title, authors, abstract, pdf_url
    FROM papers
    WHERE date(date_saved) = date('now')
    ORDER BY id DESC
    """

    # Execute the query
    cursor.execute(query)
    papers = cursor.fetchall()

    # After scoring, update the database with the scores
    update_query = """
    UPDATE papers
    SET excitement_score = ?, relevance_score = ?
    WHERE id = ?
    """

    scored_papers = []

    for paper_id, title, authors, abstract, pdf_url in papers:
        logging.info(f"Processing paper: {title}")
        
        prompt = f"Please analyze the following paper abstract and provide scores from 1.0 to 10.0 (with one decimal place) for its relevance to AI research and excitement level the paper will create in the field of AI. Respond with a JSON object containing 'relevance_score', 'excitement_score', and a brief 'explanation'. Abstract: {abstract}"

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

                        For each paper, provide a relevance score and an excitement score, both on a scale of 1.0 to 10.0, using one decimal place (e.g., 7.3, 8.5). The relevance score should reflect how important this research is to the field of AI, while the excitement score should indicate how likely this paper is to generate interest and discussion among researchers.

                        In your explanation, briefly justify your scores and highlight the key strengths or weaknesses of the paper. Be objective and base your evaluation solely on the content of the abstract."""},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.9,
            )

            response_content = json.loads(completion.choices[0].message.content)
            logging.info(f"API Response: {response_content}")
            
            paper_score = PaperScore(
                title=title,
                relevance_score=round(float(response_content['relevance_score']), 1),
                excitement_score=round(float(response_content['excitement_score']), 1),
                explanation=response_content['explanation'],
                pdf_url=pdf_url
            )
            scored_papers.append(paper_score)

            # Update the database with the scores
            cursor.execute(update_query, (paper_score.excitement_score, paper_score.relevance_score, paper_id))
            
            logging.info(f"Scored and updated paper: {title} (Relevance: {paper_score.relevance_score:.1f}, Excitement: {paper_score.excitement_score:.1f})")
        except Exception as e:
            logging.error(f"Error scoring paper '{title}': {str(e)}")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    logging.info(f"Total papers scored and updated: {len(scored_papers)}")
    return scored_papers

def datetime_to_isoformat(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

if __name__ == "__main__":
    db_path = '/Users/masondumas/Desktop/Projects/Data_Extraction/ai_news_scraper/crawl4ai/paper_pdfs/arxiv_papers.db'
    ensure_score_columns(db_path)
    scores = score_papers(db_path)
    
    # Filter papers with excitement score >= 8.0
    exciting_papers = [paper for paper in scores if paper.excitement_score >= 8.5]
    
    logging.info(f"Papers with excitement score >= 8.5: {len(exciting_papers)}")
    for paper in exciting_papers:
        logging.info(f"Exciting paper: {paper.title} (Excitement: {paper.excitement_score:.1f})")
    
    if not exciting_papers:
        logging.warning("No papers with excitement score >= 8.5 found.")
    else:
        # Create a list of dict representations of the papers
        paper_dicts = [paper.model_dump() for paper in exciting_papers]
        
        # Save the filtered results to final_papers.json
        try:
            logging.info(f"Attempting to save {len(paper_dicts)} papers to final_papers.json")
            with open('/Users/masondumas/Desktop/Projects/Data_Extraction/ai_news_scraper/crawl4ai/final_papers.json', 'w') as f:
                json.dump(paper_dicts, f, indent=2, default=datetime_to_isoformat)
            logging.info(f"Successfully saved {len(exciting_papers)} exciting papers to final_papers.json")
        except IOError as e:
            logging.error(f"IOError while writing to final_papers.json: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error while saving final_papers.json: {str(e)}")

    # Verify file contents
    try:
        with open('/Users/masondumas/Desktop/Projects/Data_Extraction/ai_news_scraper/crawl4ai/final_papers.json', 'r') as f:
            saved_papers = json.load(f)
        logging.info(f"Verified: final_papers.json contains {len(saved_papers)} papers")
    except FileNotFoundError:
        logging.error("final_papers.json was not created")
    except json.JSONDecodeError:
        logging.error("final_papers.json is empty or contains invalid JSON")
    except Exception as e:
        logging.error(f"Error verifying final_papers.json: {str(e)}")

