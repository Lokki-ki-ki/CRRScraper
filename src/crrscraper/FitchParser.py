from bs4 import BeautifulSoup
import pandas as pd
import re
import logging



class FitchParser:
    """
    This module is used to parse the html file from Fitch website and extract the key rating drivers.
    Multiple Usage:
        1. For Fitch Collector
        2. For Later AIDF Project Used
    """

    def __init__(self) -> None:
        pass

    def parse_html(self, html):
        """
        Input: html
        Output: dictionary of {sub_title1: [content1, content2, ...], ...}
        """
        soup = BeautifulSoup(html, 'html.parser')
        h3_elements = soup.find_all('h3', class_='heading--6', dir='auto')
        ## In the case no h3 elements found, try to extract from old version format
        if not h3_elements:
            logging.info("No h3 elements found, trying to extract from old version")
            p_elements = self._extract_key_rating_contents_from_old_version(soup)
            data = {"Key Rating Drivers": p_elements}
        ## Normal case will extract from h3 elements
        p_elements = self._find_p_under_key_rating_drivers(h3_elements)
        data = self._extract_dictionary_from_p_elements(p_elements)
        return data
    
    def convert_to_df(self, data):
        """
        Input: dictionary of {sub_title1: [content1, content2, ...], ...}
        Output: dataframe
        """
        items = [
            (topic_key, item)
            for topic_key, content in data.items()
            for item in content if item != '' and item != None
        ]
        df = pd.DataFrame(items, columns=['subtitle', 'content'])
        df['paranumber'] = df.index
        return df

    def _extract_key_rating_contents_from_old_version(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.find_all('div', {'class': 'RAC'})
        if not elements:
            return []
        plain_text = str(elements[0])
        start_res = re.search(r'<BR/>KEY RATING DRIVERS<BR/>', plain_text.upper())
        end_res = re.search(r'<BR/>RATING SENSITIVITIES<BR/>', plain_text.upper())
        if start_res and end_res:
            content = plain_text[start_res.end():end_res.start()]
            results = content.split('<br/>')
            return list(filter(lambda x: x != '', results))
        return []
    
    def _find_p_under_key_rating_drivers(self, h3_elements):
        """
        Input: list of h3_elements
        Output: list of p_elements under the h3 element with text 'Key Rating Drivers'
        """
        p_elements = []
        for h3 in h3_elements:
            if 'Key Rating Drivers' not in h3.text.title():
                continue
            for sibling in h3.find_next_siblings():
                # find the part right after the h3 element found
                if sibling.name == 'h3':
                    break
                if sibling.get('dir') == 'auto':
                    p_elements.append(sibling) if sibling.find_all('p') == [] else p_elements.extend(sibling.find_all('p'))
        return p_elements
    
    def _extract_dictionary_from_p_elements(self, p_elements):
        """
        Input: list of p_elements
        Output: dictionary of {sub_title1: [content1, content2, ...], ...}
        """
        results = {}
        last_sub_title = ''
        for p in p_elements:
            if p.findAll('b'):
                last_sub_title = "".join(list(map(lambda x: x.text, p.findAll('b'))))
                content = p.text.replace(last_sub_title, "")
                results[last_sub_title] = [content]
            elif len(p.text) < 100:
                last_sub_title = p.text
            elif last_sub_title:
                if last_sub_title not in results:
                    results[last_sub_title] = [p.text]
                else:
                    results[last_sub_title].append(p.text)
            else:
                logging.info("No bold sub_title found")
                last_sub_title = "No Sub Title Extracted"
                results[last_sub_title] = [p.text]
        return results
    

if __name__ == "__main__":
    with open("./FitchModule/test_html.html", "r") as f:
        html = f.read()
        f.close()
    # print(html)

    ## test parse_html
    parser = FitchParser()
    data = parser.parse_html(html)
    print(data)