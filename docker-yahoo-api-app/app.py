# Docker Image Code
from concurrent import futures
from google.cloud.pubsub_v1 import PublisherClient
from google.cloud.pubsub_v1.publisher.futures import Future
import logging
import requests
from time import sleep
import json
from apikey import api_key

# Used for running in local docker container i.e. Desktop. Comment '#' if in GPC
auth_json_file = 'your-access-google-key.json'

# IMPORTANT: Set project id as listed in GCP and the name of your topic as listed in GPC
project = 'egen-capstone-project'
topic_id = 'capstone-topic'


class PublishToPubshub:
    '''Class Provides Means for Submitting to Pub/Sub when 
    API is pulled. Message is processed to a acceptable format 
    for Pub/sub to receive.
    '''
    
    def __init__(self):
        self.project_id = project
        self.topic_id = topic_id
        # Used for running in local docker container i.e. Desktop. Comment '#' if in GPC
        #self.publisher_client = PublisherClient.from_service_account_json(auth_json_file)
        # Used for running in GPC Container Note: "apply --scopes compute-rw,gke-default" Comment '#' if in Local Docker
        self.publisher_client = PublisherClient()
        self.topic_path = self.publisher_client.topic_path(self.project_id, self.topic_id)
        self.publish_futures = []
        

    def get_crypto_ticker_data(self) -> str:
        """ Get Real Time API Data"""
        
        #url provide via yahoo api
        url = 'https://yfapi.net/v6/finance/quote?'

        # required headers & api key
        headers = {'accept': 'application/json', 'X-API-KEY': api_key}

        # for payload symbols max 10 stock or crypto
        payload = {'region' : 'US', 'lang' : 'en', 'symbols' : 'SHIB-USD,XRP-USD,DOGE-USD,BTC-USD,BNB-USD,ADA-USD,USDT-USD'}

        # Response connection perform 'GET' using 3 values above
        res = requests.get(url, headers=headers, params=payload)

        # converts response or res to json
        res_json = res.json()

        # adds a time stamp to json response for future indexing since api does not give a readable datetime format
        res_json['timeStamp']=res.headers['Date']

        # convert to text using json lib.
        res_text = json.dumps(res_json)

        # validates res is 200, successful, stores logging info per 200 or 400
        if 200 <= res.status_code < 400:
            logging.info(f"Response - {res.status_code}: Content type: {res.headers['Content-Type']} : Content Length: {res.headers['Content-Length']}")
            return res_text
        else:
            raise Exception(f"Failed to GET API json - {res.status_code}: {res.headers}: {res.text}")
            

    def get_callback(self, publish_future: Future, data: str) -> callable:
        def callback(publish_future):
            try:
                # Wait 30s for message to validate sending to confirm
                logging.info(publish_future.result(timeout=30))
            except futures.TimeoutError:
                logging.error(f"Sending {data} failed.")
        return callback
        
    
    def publish_message_to_topic(self, message: str) -> None:
        '''Publish data to pubsub '''
        
        #When you Publish message client returns future
        publish_future = self.publisher_client.publish(self.topic_path, message.encode("utf-8"))
        
        #Non-blocking, Publish failers are handled in the callback function
        publish_future.add_done_callback(self.get_callback(publish_future, message))
        self.publish_futures.append(publish_future)
        
        # Wait for all the publish futures to resolve before exiting
        futures.wait(self.publish_futures, return_when=futures.ALL_COMPLETED)
        
        logging.info(f"Published messages with error handler to {self.topic_path}")        

        
if __name__ == "__main__":
    
    # Starts logging and stores as app.log 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)   
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                              '%m-%d-%Y %H:%M:%S')

    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    

    while True:
        
        svc = PublishToPubshub()
        
        # Speeds up execution time.
        with futures.ThreadPoolExecutor(max_workers=4) as exe:
            future = exe.submit(svc.get_crypto_ticker_data)
            message = future.result()
            
        svc.publish_message_to_topic(message)
        
        # Queue Timer
        sleep(30)
   
    
        
        
        
    
