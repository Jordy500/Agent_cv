from pymongo import MongoClient

class DatabaseHandler:
    def __init__(self, db_url):
        self.client = MongoClient(db_url)
        self.db = self.client['job_search_db']
    
    def get_cv_data(self):
        return self.db['cv_data'].find()
    
    def get_job_offers(self):
        return self.db['job_offers'].find()

