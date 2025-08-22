
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from urllib.parse import quote

def get_trends_data_selenium(keywords, benchmark_keyword="business ideas", headless=True):
    """
    Fetches and rescales Google Trends data using Selenium to bypass request blocks.

    Args:
        keywords (list): A list of keywords to analyze.
        benchmark_keyword (str): A high-volume, stable keyword for scaling.
        headless (bool): Whether to run the browser in headless mode.

    Returns:
        pandas.DataFrame: A DataFrame with keywords and their rescaled trend scores.
    """
    # Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print("Error setting up WebDriver. Please ensure you have Google Chrome and chromedriver installed.")
        print(f"Error: {e}")
        return pd.DataFrame()

    # --- Keyword processing ---
    if benchmark_keyword in keywords:
        keywords.remove(benchmark_keyword)
    all_keywords = [benchmark_keyword] + keywords
    
    trends_data = {}
    processed_keywords = set()

    # --- Main loop ---
    for i in range(0, len(all_keywords), 5):
        batch = all_keywords[i:i+5]
        if not batch:
            continue

        print(f"Processing batch: {batch}")
        
        # URL-encode keywords for the query
        encoded_keywords = [quote(kw) for kw in batch]
        url = f"https://trends.google.com/trends/explore?q={','.join(encoded_keywords)}&date=today 12-m"

        try:
            driver.get(url)
            # Give the page time to load all the JavaScript and data
            time.sleep(5) 

            # The data is in a <script> tag. We find it, strip the junk, and parse the JSON.
            script_element = driver.find_element("xpath", "//script[contains(text(), 'widgets')] ")
            script_content = script_element.get_attribute('innerHTML')
            
            # Clean the string to be valid JSON
            json_str = script_content.split('=', 1)[1].strip()
            if json_str.endswith(';'):
                json_str = json_str[:-1]

            data = json.loads(json_str)
            
            # Navigate the complex JSON structure to get to the trend data
            timeline_data = data['widgets'][0]['reque_st']['comparisonItem']

            # Calculate mean interest for each keyword
            mean_interest = {}
            for item in timeline_data:
                keyword = item['keyword']
                # Take the average of the timeline values
                avg_value = sum(p['value'][0] for p in item['timelineData']) / len(item['timelineData'])
                mean_interest[keyword] = avg_value

            # --- Rescaling Logic ---
            benchmark_score = mean_interest.get(benchmark_keyword, 1)
            if benchmark_score == 0: benchmark_score = 1

            for keyword in batch:
                if keyword not in processed_keywords:
                    rescaled_score = (mean_interest.get(keyword, 0) / benchmark_score) * 100
                    trends_data[keyword] = rescaled_score
                    processed_keywords.add(keyword)

        except Exception as e:
            print(f"Could not process batch {batch}. Error: {e}")
            for kw in batch:
                if kw not in processed_keywords:
                    trends_data[kw] = -1 # Mark as error
                    processed_keywords.add(kw)
        
        time.sleep(2) # Politeness delay

    driver.quit()

    # --- Final DataFrame creation ---
    final_df = pd.DataFrame(list(trends_data.items()), columns=['keyword', 'google_trends_score'])
    final_df.sort_values(by='google_trends_score', ascending=False, inplace=True)
    
    return final_df

if __name__ == '__main__':
    keywords_to_analyze = [
        "a market analysis", "audience research tools", "best business ideas", 
        "best business startup ideas", "best business to start", "best small business ideas",
        "business ideas", "business research techniques", "competitors analysis",
        "conduct market research", "consumer research", "customer research",
        "customer research companies", "customer research methods", "customer research techniques",
        "customer research tools", "design research methodology", "different types of market research",
        "good business ideas", "good online business ideas", "good startup ideas", "idea validation",
        "market and research", "market reports", "market research", "market research analysis",
        "market research and analysis", "market research methodologies", "market research methods and techniques",
        "market research platforms", "market research reports", "market research techniques",
        "market research tools", "market segmentation analysis", "market study", "market survey",
        "market survey method", "marketing analysis", "marketing competitor analysis",
        "marketing research in marketing", "marketing research methodologies", "marketing research methods",
        "methods and techniques of marketing research", "methods for market research", "mvp development",
        "mvp viable product", "new business ideas", "new business startup ideas", "new ideas for startup",
        "new product ideas"
    ]

    benchmark = "business ideas"

    trends_df = get_trends_data_selenium(keywords_to_analyze, benchmark_keyword=benchmark)

    print("\n--- Final Google Trends Scores (Selenium) ---")
    print(trends_df)
