import os
import sys
import requests
from datetime import datetime
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from crawl4ai import WebCrawler
from crawl4ai.chunking_strategy import RegexChunking
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import json
import logging
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

class AcademicWebCrawlerLLM:
    def __init__(self):
        self.init_pinecone()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.crawler = WebCrawler(verbose=True)
        self.crawler.warmup()
        logging.info("AcademicWebCrawlerLLM initialized")

    def init_pinecone(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if index_name not in self.pc.list_indexes().names():
            print(f"Index '{index_name}' not found. Creating new index...")
            self.pc.create_index(
                name=index_name,
                dimension=384,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            print(f"Index '{index_name}' created successfully.")
            logging.info(f"Pinecone index '{index_name}' initialized")
        
        self.index = self.pc.Index(index_name)

    def save_paper(self, paper):
        paper_id = paper.get('id', '')
        if not paper_id:
            paper_id = hashlib.md5((paper.get('title', '') + paper.get('url', '')).encode()).hexdigest()
        
        if not paper_id:
            logging.warning(f"Unable to generate paper_id for paper: {paper}")
            return  # Skip this paper

        metadata = {
            'title': paper.get('title', ''),
            'authors': ', '.join(paper.get('authors', [])),
            'abstract': paper.get('abstract', ''),
            'url': paper.get('url', '')
        }
        embedding = self.model.encode(f"{paper['title']} {' '.join(paper['authors'])} {paper['abstract']}").tolist()

        try:
            self.index.upsert([(paper_id, embedding, metadata)])
            logging.info(f"Saved paper: {paper.get('title', 'Unknown Title')}")
        except Exception as e:
            logging.error(f"Error upserting paper {paper_id}: {e}")
            logging.error(f"Paper details: {paper}")

    def parse_academic_page(self, url):
        logging.info(f"Parsing academic page: {url}")
        llm_instruction = """
        Extract academic paper information from the given web page. For each paper, provide:
        1. Title
         2. Authors (as a comma-separated list)
         3. Abstract (limited to 3 sentences)
         4. Publication date (if available)
         5. URL of the paper (if available)

        Format the output as a JSON array of paper objects. If no papers are found, return an empty array [].
        """

        try:
            result = self.crawler.run(
                url=url,
                chunking_strategy=RegexChunking(patterns=["\n\n"]),
                extraction_strategy=LLMExtractionStrategy(
                    provider="openai/gpt-4o",
                    api_token=os.getenv('OPENAI_API_KEY'),
                    instruction=llm_instruction
                )
            )
            logging.info(f"Crawler result type: {type(result)}")
            logging.info(f"Crawler result: {result}")
            logging.info(f"Extracted content type: {type(result.extracted_content)}")
            logging.info(f"Extracted content: {result.extracted_content}")
        except Exception as e:
            logging.error(f"Error during crawling: {e}")
            return []

        papers = self.process_extracted_data(result.extracted_content, url)
        logging.info(f"Processed {len(papers)} papers from {url}")
        return papers

    def process_extracted_data(self, extracted_content, url):
        logging.info("Processing extracted data")
        papers = []
        
        logging.info(f"Raw extracted content type: {type(extracted_content)}")
        logging.info(f"Raw extracted content: {extracted_content}")
        
        if isinstance(extracted_content, str):
            try:
                extracted_data = json.loads(extracted_content)
                logging.info(f"Parsed JSON data: {extracted_data}")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse extracted content as JSON: {e}")
                logging.error(f"Raw content: {extracted_content}")
                return papers
        elif isinstance(extracted_content, list):
            extracted_data = extracted_content
        else:
            logging.error(f"Unexpected data type for extracted_content: {type(extracted_content)}")
            return papers

        if not extracted_data:
            logging.warning(f"No papers extracted from {url}")
            return papers

        for paper_data in extracted_data:
            logging.info(f"Processing paper: {paper_data}")
            if not isinstance(paper_data, dict):
                logging.warning(f"Skipping invalid paper data: {paper_data}")
                continue
            paper = {
                'id': paper_data.get('id', ''),
                'title': paper_data.get('title', ''),
                'authors': paper_data.get('authors', '').split(', ') if isinstance(paper_data.get('authors'), str) else [],
                'abstract': paper_data.get('abstract', ''),
                'date': paper_data.get('date', ''),
                'url': paper_data.get('url', url)
            }
            if any(paper.values()):  # Only add paper if at least one field is non-empty
                papers.append(paper)
                self.save_paper(paper)
            else:
                logging.warning(f"Skipping empty paper: {paper}")
        
        return papers

class AcademicPaperFilter:
    def __init__(self, keywords=None, authors=None, start_date=None, end_date=None):
        self.keywords = None
        self.authors = None
        self.start_date = None
        self.end_date = None

    def filter_papers(self, papers):
        filtered_papers = []
        for paper in papers:
            if self.match_keywords(paper) and self.match_authors(paper) and self.match_date(paper):
                filtered_papers.append(paper)
        return filtered_papers

    def match_keywords(self, paper):
        if not self.keywords:
            return True
        return any(keyword.lower() in paper['title'].lower() or keyword.lower() in paper['abstract'].lower() for keyword in self.keywords)

    def match_authors(self, paper):
        if not self.authors:
            return True
        return any(author.lower() in ' '.join(paper['authors']).lower() for author in self.authors)

    def match_date(self, paper):
        if not self.start_date and not self.end_date:
            return True
        try:
            paper_date = datetime.strptime(paper['date'], '%Y-%m-%d')
            if self.start_date and paper_date < self.start_date:
                return False
            if self.end_date and paper_date > self.end_date:
                return False
            return True
        except ValueError:
            return True

def crawl_academic_websites(urls):
    logging.info(f"Starting crawl for {len(urls)} URLs")
    crawler = AcademicWebCrawlerLLM()
    
    all_papers = []
    for url in urls:
        logging.info(f"Crawling URL: {url}")
        papers = crawler.parse_academic_page(url)
        logging.info(f"Found {len(papers)} papers on {url}")
        all_papers.extend(papers)
        
        logging.info(f"Papers found on this URL: {len(papers)}")

    logging.info(f"Crawling completed. Total papers found: {len(all_papers)}")
    return all_papers

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        logging.error("OPENAI_API_KEY is not set in environment variables")
        sys.exit(1)
    
    urls = sys.argv[1:]
    
    logging.info("Starting academic web crawler")
    crawled_papers = crawl_academic_websites(urls)
    
    # Log all crawled papers without filtering
    logging.info(f"\nTotal papers crawled: {len(crawled_papers)}")
    for paper in crawled_papers:
        logging.info(f"Title: {paper['title']}")
        logging.info(f"Authors: {', '.join(paper['authors'])}")
        logging.info(f"Date: {paper['date']}")
        logging.info(f"URL: {paper['url']}")
        logging.info("---")
