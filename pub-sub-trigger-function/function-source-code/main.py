
import logging
from base64 import b64decode
from json import loads
from pandas import DataFrame
from google.cloud import storage
from concurrent import futures

#bucket = 'my-storage-bucket'
bucket = 'capstone-project-yahoo-api-raw-data'

svc = None
message = None
root = None 
upload_df = None
payload_timestamp = None




class LoadToStorage:
    def __init__(self, event, context, bucket):
        self.event = event
        self.context = context
        self.bucket_name = bucket
        
    def get_message_data(self) -> str:
        '''Extract data from pubsub message'''
        
        logging.info(
            f"This function was triggered by messageID {self.context.event_id} published at {self.context.timestamp}"
            f"to {self.context.resource['name']}"                                                                                                                                                                                        
        )
        
        if 'data' in self.event:
            pubsub_message = b64decode(self.event['data']).decode('utf-8')
            logging.info(pubsub_message)
            return pubsub_message
        
        else:
            logging.error("improper format")
            return
        
        
    def transform_payload_to_data_frame(self, message: str) -> DataFrame:

        '''Tranform json message to dataframe'''

        try:
            message_json = loads(message)
            message_time = message_json['timeStamp']
            message_body = message_json['quoteResponse']['result']
            df = DataFrame(message_body)
            n = df.shape[0]
            df.insert(0, 'timeStamp', ([message_time] * n))
            if not df.empty:
                logging.info(f"Created a Dataframe with {df.shape[0]} rows and {df.shape[1]} columns")

            else: 
                logging.warning(f'Created Empty Data Frame')
            return df
        except Exception as e:
            logging.error(f'Encountered error creating DataFrame - {str(e)}')
            raise

    def upload_to_bucket(self, df: DataFrame, file_name: str = "payload") -> None:
        """Upload bucket as csv to GCS Bucket"""
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob('yahoo-api-bin/' + f'{file_name}.csv')

        blob.upload_from_string(data=df.to_csv(index=False), content_type='text/csv')

        logging.info(f"File uploaded to {self.bucket_name}")









def process(event, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This generic function logs relevant data when a file is changed,
       and works for all Cloud Storage CRUD operations.
    Args:
        event (dict):  The dictionary with data specific to this type of event.
                       The `data` field contains a description of the event in
                       the Cloud Storage `object` format described here:
                       https://cloud.google.com/storage/docs/json_api/v1/objects#resource
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Cloud Logging
    """

    #print('Event ID: {}'.format(context.event_id))
    #print('Event type: {}'.format(context.event_type))
    #print('Bucket: {}'.format(event['bucket']))
    #print('File: {}'.format(event['name']))
    #print('Metageneration: {}'.format(event['metageneration']))
    #print('Created: {}'.format(event['timeCreated']))
    #print('Updated: {}'.format(event['updated']))
    global svc, message, root, upload_df, payload_timestamp, bucket

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    svc = LoadToStorage(event, context, bucket)

    message = svc.get_message_data()
    upload_df = svc.transform_payload_to_data_frame(message)
    payload_timestamp = upload_df["regularMarketTime"].unique().tolist()[0]

    svc.upload_to_bucket(upload_df, 'yahoo-crypto-data' + str(payload_timestamp))
   
    