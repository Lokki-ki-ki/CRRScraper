from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from datetime import datetime
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import Levenshtein



logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)


class FitchCollector:
    def __init__(self, pathtosave="") -> None:
        """
        Initialize the Chrome Driver and set the path to save the articles.
        Input: pathtosave: str
        """
        self.pathtosave = pathtosave
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")
        self.options.add_argument('--enable-javascript')
        logger.info("Initializing Chrome Driver...")
        self.driver = webdriver.Chrome(options=self.options, service=ChromeService(ChromeDriverManager().install()))
        logger.info("Chrome Driver initialized.")

    def __handle_accept_cookies(self) -> None:
        """
        Handle the accept cookies pop-up
        """
        try:
            wait = WebDriverWait(self.driver, 20, 2)
            wait.until(EC.presence_of_element_located((By.ID, "_evidon-accept-button")))
            self.driver.find_element(By.ID, "_evidon-accept-button").click()
            logger.info("Cookies accepted")
        except TimeoutException as e:
            logger.info(f"Error handling accept cookies")
        finally:
            time.sleep(5)
   
    def get_latest_fitch_reports_list_by_company(self, company_name, full_list=False) -> pd.DataFrame or None:
        """
        INPUT: Company Name
        OUTPUT: Dataframe of entities found in Fitch using comapany_name as keywords, in the format of [Entity, Link]
        """
        ## TODO: search in the database first
        results = self.__find_entities(company_name)
        if not results:
            logger.info(f"No entities found for {company_name}")
            return None
        
        if full_list:
            return pd.DataFrame(results, columns=['Entity', 'Link'])
        
        ## Find the most similar entity
        max_ratio = 0.5
        max_item = {}
        for result in results:
            ratio = Levenshtein.ratio(company_name, result[0])
            if ratio > max_ratio:
                max_ratio = max(max_ratio, ratio)
                max_item["Entity"] = result[0]
                max_item["Link"] = result[1]

        ## If the most similar entity is not similar enough, return None
        if max_ratio <= 0.5:
            logger.info(f"No entities found for {company_name}")
            return None
        
        return max_item

    def __find_entities(self, company_name) -> list:
        """
        Input: Company Name
        Output: List of entities found in Fitch using comapany_name as keywords, in the format of [(entity1, link1), (entity2, link2),...]
        """
        ## Search for the entities in Fitch
        keywords = company_name.replace(' ', '%20')
        entities_url = f'https://www.fitchratings.com/search/?expanded=entity&query={keywords}&viewType=data'
        self.driver.get(entities_url)
        self.driver.implicitly_wait(5)
        self.__handle_accept_cookies()

        ## Find the entities in html
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        entity_data_list = soup.find_all('div', {'class': 'column__four column--merge-a entity-data'})
        result = []
        for element in entity_data_list[1:]:
            title = element.find('div', {'class': 'entity-data--title'})
            com_name = title.find('h3').text
            link = "https://fitchratings.com" + title.find('a').get('href')
            result.append((com_name, link))
        return result
    
    def fetch_reports_link_based_on_company(self, url):
        """
        Input: company name
        Output: list of (title, url, date) for single report
        """
        self.driver.get(url)
        self.__handle_accept_cookies()
        
        try:
            WebDriverWait(self.driver, 60, 2).until(EC.presence_of_element_located((By.ID, "rating-actions")))
        except TimeoutException as e:
            logger.info(f"Error loading page: {url}")
            return None

        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.find('section', {'id': 'rating-actions'})
        rating_actions = section.find_all('article', {'class': 'rating-highlight'})
        article_list = []
        for rating_item in rating_actions:
            title = rating_item.find('h3').text
            url = "https://www.fitchratings.com" + rating_item.find('a').get('href')
            date = self.__find_date_in_action_item(rating_item.find('div', {'class': 'heading--sub'}).text)
            date = datetime.strptime(date, '%d %b, %Y').strftime('%Y-%m-%d')
            article_list.append((title, url, date))
        return article_list

    # ## Helper Function for Feature3
    def __find_date_in_action_item(self, text):
        """
        Input: a text containing date in the format of "Mon 21 Dec, 2009"
        Output: date in the format of "Fri 21 Dec, 2009"
        """
        re_group = re.search(r'\d{2} (\b[A-Za-z]{3}\b), \d{4}', text)
        return re_group.group(0) if re_group else None
    
    def fetch_article_based_on_single_link(self, link):
        """
        Input: link to the article
        Output: html
        """
        data = {}
        logging.info("Fetching article from link: " + link)
        self.driver.get(link)
        self.__handle_accept_cookies()
        self.driver.implicitly_wait(5)
        html = self.driver.page_source
        return html

    ## Feature1-3 Aggregate Function: to fetch latest {num_of_reports} fitch reports for {company_name}
    def fetch_latest_fitch_reports_list_and_links_by_company(self, company_name, num_of_reports):
        company_found = self.get_latest_fitch_reports_list_by_company(company_name)
        if company_found is None:
            logging.info(f"No entities found for {company_name}")
            return None
        
        # Default Fetch for first entity
        company = company_found['Entity']
        company_url = company_found['Link']
        logging.info(f"Fetching reports links for {company}")
        article_links = self.fetch_reports_link_based_on_company(company_url)

        # Fetch for num_of_reports entities
        result = {}
        for i in range(0, min(num_of_reports, len(article_links))):
            time.sleep(2)
            logging.info(f"Fetching No. {i} reports for {company}")
            article_url = article_links[i][1]
            article_date = article_links[i][2]
            html = self.fetch_article_based_on_single_link(article_url)
            result[article_date] = html
        
        return result
    

if __name__ == "__main__":
    fitch = FitchCollector(os.getcwd() + "/src/FitchModule/Results")

    ## Test for Feature 1
    ## TODO: Check cannot found company for error handling
    # company_lst = fitch.get_latest_fitch_reports_list_by_company("Goldman Sachs")
    # company_lst.to_csv("fitch_reports_list.csv")
    # print(company_lst)

    ## Test for Feature 3
    # test_url = "https://www.fitchratings.com/entity/green-apple-2019-i-nhg-bv-96756517"
    # # test_url = company_lst['Link'].iloc[0]
    # article_links = fitch.fetch_reports_link_based_on_company(test_url)
    # print(article_links)

    ## Test for Feature 2
    # article_url = article_links[0][1]
    # article_url = "https://www.fitchratings.com/research/structured-finance/fitch-rates-green-apple-2019-i-aaasf-stable-outlook-26-06-2019"
    # article = fitch.fetch_article_based_on_single_link(article_url)
    # print(article)
    # df = fitch.convert_dict_to_df(article)
    # print(df.head())

    ## Test for Aggregation
    final_result = fitch.fetch_latest_fitch_reports_list_and_links_by_company("Ford Motor", 3)
    print(final_result)





