from crawl_service import crawl_academic_websites

url = "https://arxiv.org/list/cs.AI/recent"  # Example URL
papers = crawl_academic_websites(url)

print(f"Total papers found: {len(papers)}")
if papers:
    print("Sample paper:")
    print(papers[0])