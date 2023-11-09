import unittest
from crrscraper import FitchCollector

class TestGetListByCompany(unittest.TestCase):
    collector = FitchCollector()
    results = collector.get_latest_fitch_reports_list_by_company('Amazon')
    assert(len(results) > 0)
