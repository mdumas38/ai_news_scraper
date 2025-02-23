import re
import os
import sys
import requests
from datetime import datetime
import PyPDF2
import tempfile
from dotenv import load_dotenv
import json
from bs4 import BeautifulSoup
import logging
import sqlite3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

class AcademicWebCrawler:
    def __init__(self):
        self.pdf_dir = '/Users/masondumas/Desktop/Projects/Data_Extraction/ai_news_scraper/crawl4ai/paper_pdfs'
        os.makedirs(self.pdf_dir, exist_ok=True)
        logging.info(f"PDF directory set to: {self.pdf_dir}")
        self.db_path = '/Users/masondumas/Desktop/Projects/Data_Extraction/ai_news_scraper/crawl4ai/paper_pdfs/arxiv_papers.db'
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.init_database()
        logging.info("AcademicWebCrawler initialized")

    def init_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                date_saved DATE,
                pdf_path TEXT,
                pdf_url TEXT
            )
        ''')
        self.conn.commit()
        logging.info("Database initialized or existing table confirmed")

    def save_to_database(self, paper):
        self.cursor.execute('''
            INSERT OR REPLACE INTO papers (id, title, authors, abstract, date_saved, pdf_path, pdf_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper['id'],
            paper['title'],
            paper['authors'],
            paper['abstract'],
            paper['date_saved'],
            paper.get('pdf_path'),
            paper.get('pdf_url')  # Make sure this is included
        ))
        self.conn.commit()
        logging.info(f"Saved paper to database: {paper['title']} with PDF URL: {paper.get('pdf_url')}")

    def save_paper(self, paper, pdf_content):
        paper_id = paper['id']
        today_date = datetime.now().strftime('%Y-%m-%d')
        date_folder = os.path.join(self.pdf_dir, today_date)
        os.makedirs(date_folder, exist_ok=True)
        
        pdf_filename = f"{paper_id}.pdf"
        pdf_path = os.path.join(date_folder, pdf_filename)

        try:
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            logging.info(f"PDF saved: {pdf_path}")

            paper['pdf_path'] = pdf_path
            self.save_to_database(paper)
            logging.info(f"Paper metadata saved to database: {paper['title']}")
        except Exception as e:
            logging.error(f"Error saving paper {paper_id}: {e}", exc_info=True)

    def parse_academic_page(self, url):
        logging.info(f"Parsing academic page: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Log page title and URL
            logging.info(f"Page Title: {soup.title.string if soup.title else 'No title found'}")
            logging.info(f"URL: {url}")

            # Log a snippet of the HTML
            logging.info(f"HTML Snippet:\n{soup.prettify()[:1000]}")

            # Save full HTML to a file
            os.makedirs('debug_output', exist_ok=True)
            with open(f'debug_output/page_source_{url.split("/")[-1]}.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())

            if 'arxiv.org' in url:
                logging.info("Using arXiv parser")
                papers = self.parse_arxiv(soup)
            elif 'semanticscholar.org' in url:
                logging.info("Using Semantic Scholar parser")
                papers = self.parse_semantic_scholar(soup)
            elif 'scholar.google.com' in url:
                logging.info("Using Google Scholar parser")
                papers = self.parse_google_scholar(soup)
            else:
                logging.warning(f"No parser found for URL: {url}")
                return []

            logging.info(f"Found {len(papers)} papers on {url}")
            return papers
        except requests.RequestException as e:
            logging.error(f"Failed to fetch content from {url}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error parsing {url}: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            logging.error(f"Error details: {e.args}")
            logging.error(f"Traceback:", exc_info=True)
            return []

    def parse_arxiv(self, soup):
        papers = []
        main_content = soup.find('div', id='content')
        
        if not main_content:
            logging.warning("Could not find the main content div")
            return papers

        today_date = datetime.now().strftime('%Y-%m-%d')

        for dl_element in main_content.find_all('dl'):
            for dt, dd in zip(dl_element.find_all('dt'), dl_element.find_all('dd')):
                try:
                    paper_id_element = dt.find('a', {'title': 'Abstract'})
                    if not paper_id_element:
                        logging.warning("Could not find paper ID element")
                        continue
                    paper_id = paper_id_element.text.strip()

                    # Check if paper already exists in database
                    self.cursor.execute("SELECT id FROM papers WHERE id = ?", (paper_id,))
                    result = self.cursor.fetchone()
                    logging.debug(f"Checking for paper ID {paper_id} in database")
                    logging.debug(f"Database query result: {result}")
                    logging.debug(f"Current database path: {os.path.abspath(self.db_path)}")

                    if result:
                        logging.info(f"Paper {paper_id} already exists in database. Skipping.")
                        continue

                    logging.info(f"Processing new paper with ID: {paper_id}")

                    title_element = dd.find('div', class_='list-title')
                    if not title_element:
                        logging.warning(f"Could not find title for paper {paper_id}")
                        continue
                    title = title_element.text.replace('Title:', '').strip()

                    authors_element = dd.find('div', class_='list-authors')
                    authors = authors_element.text.replace('Authors:', '').strip() if authors_element else "Authors not found"

                    abstract = None
                    
                    paper_data = {
                        'id': paper_id,
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'date_saved': today_date,
                        'pdf_path': None,
                        'pdf_url': None
                    }
                    
                    logging.debug(f"Paper data before PDF download: {paper_data}")
                    
                    # Update this part to more reliably find the PDF URL
                    pdf_link = dt.find('a', {'title': 'Download PDF'})
                    if pdf_link and 'href' in pdf_link.attrs:
                        pdf_url = f"https://arxiv.org{pdf_link['href']}"
                        paper_data['pdf_url'] = pdf_url.replace('abs', 'pdf')  # Ensure we get the direct PDF link
                        logging.info(f"Found PDF URL: {paper_data['pdf_url']}")
                        pdf_content = self.download_pdf(paper_data['pdf_url'])
                        if pdf_content:
                            extracted_abstract = self.extract_abstract_from_pdf(pdf_content)
                            if extracted_abstract:
                                paper_data['abstract'] = extracted_abstract
                            self.save_paper(paper_data, pdf_content)
                            logging.debug(f"Paper data after save_paper: {paper_data}")
                        else:
                            logging.warning(f"Failed to download PDF for paper: {paper_data['title']}")
                    else:
                        logging.warning(f"Could not find PDF link for paper: {paper_data['title']}")
                    
                    # If we couldn't get the abstract from the PDF, try to get it from the abstract page
                    if not paper_data['abstract']:
                        abstract_url = f"https://arxiv.org/abs/{paper_id}"
                        abstract_response = requests.get(abstract_url)
                        if abstract_response.status_code == 200:
                            abstract_soup = BeautifulSoup(abstract_response.content, 'html.parser')
                            abstract_element = abstract_soup.find('blockquote', class_='abstract')
                            if abstract_element:
                                paper_data['abstract'] = abstract_element.text.strip()
                    
                    # Make sure to save to database even if PDF download fails
                    self.save_to_database(paper_data)
                    papers.append(paper_data)
                    logging.info(f"Processed and saved arXiv paper: {title}")
                except AttributeError as e:
                    logging.error(f"Failed to parse paper: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error parsing paper: {e}", exc_info=True)

        logging.info(f"Found and processed {len(papers)} new papers on arXiv")
        return papers

    def parse_semantic_scholar(self, soup):
        papers = []
        for paper in soup.find_all('div', class_='search-result-item'):
            title = paper.find('a', class_='search-result-title').text.strip()
            authors = paper.find('span', class_='author-list').text.strip()
            abstract = paper.find('span', class_='abstract').text.strip()
            date = paper.find('span', class_='year').text.strip()
            
            paper_data = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'date': date,
            }
            papers.append(paper_data)
            logging.info(f"Processed Semantic Scholar paper: {title}")

        return papers

    def parse_google_scholar(self, soup):
        papers = []
        for paper in soup.find_all('div', class_='gs_r'):
            title = paper.find('h3', class_='gs_rt').text.strip()
            authors = paper.find('div', class_='gs_a').text.strip()
            abstract = paper.find('div', class_='gs_rs').text.strip()
            
            paper_data = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'date': '',  # Google Scholar doesn't always provide a clear date
            }
            papers.append(paper_data)
            logging.info(f"Processed Google Scholar paper: {title}")

        return papers

    def download_pdf(self, pdf_url):
        try:
            response = requests.get(pdf_url)
            if response.status_code == 200:
                logging.info(f"PDF downloaded successfully: {pdf_url}")
                return response.content
            else:
                logging.error(f"Failed to download PDF: HTTP {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error downloading PDF: {e}")
            return None

    def extract_abstract_from_pdf(self, pdf_content):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name

            with open(temp_file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages[:5]:  # Read only first 5 pages
                    text += page.extract_text()

            os.unlink(temp_file_path)

            # Find the abstract
            abstract_start = text.lower().find("abstract")
            if abstract_start != -1:
                possible_ends = ["introduction", "keywords", "1.", "i.", "1 introduction"]
                abstract_end = len(text)
                for end_marker in possible_ends:
                    end_index = text.lower().find(end_marker, abstract_start)
                    if end_index != -1 and end_index < abstract_end:
                        abstract_end = end_index

                abstract = text[abstract_start:abstract_end].strip()
            else:
                # If no abstract found, use the first 500 words
                words = text.split()[:500]
                abstract = ' '.join(words)

            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)  # Remove extra whitespace
            abstract = abstract.replace('Abstract', '', 1).strip()  # Remove 'Abstract' header

            logging.info("Abstract extracted successfully from PDF")
            return abstract

        except Exception as e:
            logging.error(f"Error extracting abstract from PDF: {e}")
            return None

    def clear_database(self):
        try:
            self.cursor.execute("DROP TABLE IF EXISTS papers")
            self.conn.commit()
            logging.info("Existing 'papers' table dropped.")
            
            self.cursor.execute('''
                CREATE TABLE papers (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    date_saved DATE,
                    pdf_path TEXT,
                    pdf_url TEXT
                )
            ''')
            self.conn.commit()
            logging.info("New 'papers' table created.")
        except sqlite3.Error as e:
            logging.error(f"Error clearing database: {e}")

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

class AcademicPaperFilter:
    def __init__(self, keywords=None, authors=None, start_date=None, end_date=None):
        self.keywords = keywords or []
        self.authors = authors or []
        self.start_date = start_date
        self.end_date = end_date
        logging.info("AcademicPaperFilter initialized")

    def filter_papers(self, papers):
        filtered_papers = []
        for paper in papers:
            if self.match_keywords(paper) and self.match_authors(paper) and self.match_date(paper):
                filtered_papers.append(paper)
        logging.info(f"Filtered {len(filtered_papers)} papers out of {len(papers)}")
        return filtered_papers

    def match_keywords(self, paper):
        if not self.keywords:
            return True
        return any(keyword.lower() in paper['title'].lower() or keyword.lower() in paper['abstract'].lower() for keyword in self.keywords)

    def match_authors(self, paper):
        if not self.authors:
            return True
        return any(author.lower() in paper['authors'].lower() for author in self.authors)

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
            logging.warning(f"Invalid date format for paper: {paper['title']}")
            return True

def crawl_academic_websites(urls):
    logging.info(f"Initializing the academic crawler for {len(urls)} URLs")
    crawler = AcademicWebCrawler()
    
    all_papers = []
    for url in urls:
        logging.info(f"Crawling URL: {url}")
        papers = crawler.parse_academic_page(url)
        all_papers.extend(papers)
        
        logging.info(f"Papers found on this URL: {len(papers)}")

    logging.info("All crawling tasks completed!")
    logging.info(f"Total papers found and saved: {len(all_papers)}")
    return all_papers

if __name__ == "__main__":
    url = "https://arxiv.org/list/cs.AI/new"
    papers = crawl_academic_websites([url])
    print(json.dumps(papers, indent=2))
    logging.info("Crawling process completed successfully")