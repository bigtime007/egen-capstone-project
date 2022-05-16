import pandas
import os
from datetime import datetime
from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from google.cloud import bigquery
from google.cloud import storage


#Varibles & Creating working dir
working_dir = '/home/airflow/gcs/data/process/'

if os.path.exists(working_dir) == False:
    os.mkdir(working_dir)
    print(f'Added: {working_dir} folder')

key_working_dir = '/home/airflow/gcs/data/temp-key/'

credentials = f'{key_working_dir}egen-capstone-project-bucket-bq.json'

bucket_name = 'capstone-project-yahoo-api-raw-data'

bucket_prefix = 'yahoo-api-bin'

combined_csv_file = f'{working_dir}combined_files.csv'

table_id ='egen-capstone-project.capstone_dataset.yahoo_btc_table' 

query_csv = f'{working_dir}compare.csv'

clean_csv_file = f'{working_dir}cleaned-records.csv'

column_lst = ['fromCurrency',
'timeStamp',
'regularMarketPrice',
'regularMarketChange',
'regularMarketChangePercent',
'regularMarketTime',
'regularMarketDayLow',
'regularMarketDayHigh',
'regularMarketDayRange',
'regularMarketVolume',
'volume24Hr',
'volumeAllCurrencies',
'averageDailyVolume3Month',
'averageDailyVolume10Day',
'fiftyTwoWeekLowChange',
'fiftyTwoWeekLowChangePercent',
'fiftyTwoWeekRange',
'fiftyTwoWeekHighChange',
'fiftyTwoWeekHighChangePercent',
'fiftyTwoWeekLow',
'fiftyTwoWeekHigh',
'fiftyDayAverage',
'fiftyDayAverageChange',
'fiftyDayAverageChangePercent',
'twoHundredDayAverage',
'twoHundredDayAverageChange',
'twoHundredDayAverageChangePercent',
'marketCap',
'priceHint',
'circulatingSupply']

# Task Functions

def get_combined_records():
    
    storage_client = storage.Client.from_service_account_json(credentials)
    bucket = storage_client.get_bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=bucket_prefix)
    combined_df = pandas.DataFrame()


    for blob in blobs:
        filename = blob.path.replace('/', '_')
        print(f"Downloading file {filename}")

        if filename == '_b_capstone-project-yahoo-api-raw-data_o_yahoo-api-bin%2F':
            pass

        else:    
            blob.download_to_filename(f'{working_dir}{filename}')
            print(f"Concat...{filename} together into one dataframe")
            file_df = pandas.read_csv(f'{working_dir}{filename}')
            combined_df = combined_df.append(file_df)
            print(f'deleting file{filename}')
            blob.delete()
        
    if len(combined_df) > 0:
        combined_file_name = f"combined_files.csv"
        combined_df.to_csv(f'{working_dir}{combined_file_name}', index=False)
        print("found files moving to next step..")
        return "clean_and_process_records_task"

    else:
        print('No files found during run')
        return "end task at hand"


def clean_and_process_records():
    
    df = pandas.read_csv(combined_csv_file)
    print("Reading combined Records")
    df = df.fillna("").astype(str)

    # Grap all entries that have BTC
    df = df[df["fromCurrency"] == 'BTC']
    print("Separating Sorting only by BTC")
    
    # Sort all values
    df.sort_values("timeStamp", inplace=True)
    new_df = df[column_lst].copy()
    new_df.columns = column_lst
    print("Cleaned Data w/BTC only")

    print('Calculating Simple Moving Avg.')
    df_smavg = new_df.apply(
    lambda row: float(row["regularMarketPrice"]) + float(row["fiftyDayAverage"]) + float(row["twoHundredDayAverage"]), axis=1
    )/3
    new_df.insert(5, "simpleMovingAVG", None)
    new_df["simpleMovingAVG"] = df_smavg
    print("Inserting simpleMovingAVG in Column 5")

    new_df.to_csv(clean_csv_file, index=False)
    print("Saving DataFrame to CSV file, Cleaning Done!")


def upload_df_to_bq(): #clean_csv_file, credentials, table_id
    '''Uploads a dataframe to Big Query
        - Creates dataframe by reading local file in airflow
        - loads client table info from id
        - creates job from table.schema
        - loads job to big query with dataframe, destination table, and job_config
        - returns 
    '''

    df = pandas.read_csv(clean_csv_file)
    client = bigquery.Client.from_service_account_json(credentials)
    table = client.get_table(table_id)
    job_config = bigquery.LoadJobConfig(schema=table.schema, write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
    load_job = client.load_table_from_dataframe(dataframe=df, destination=table_id, job_config=job_config)
    output = load_job.result()
    return f'upload output: {output}'

            
def delete_download_files():
    '''Deletes file in local Airflow workding dir as given varible:working_dir'''

    for filename in os.listdir(working_dir):
        print(f"Removing local file: {filename}")
        os.remove(working_dir + filename)


def validate_bq_info(): #credentials, table_id, local_clean_csv_file, query_csv
    '''Validate the BQ Entry was place in acending order'''

    client = bigquery.Client.from_service_account_json(credentials)
    df2 = pandas.read_csv(clean_csv_file)
    query_time_first = df2["timeStamp"].iloc[0]
    query_time_last = df2["timeStamp"].iloc[-1]
    print(f'Validating from interval.. first: {query_time_first} last: {query_time_last}')
    query_string = f"SELECT * FROM `{table_id}` WHERE timeStamp BETWEEN '{query_time_first}' AND '{query_time_last}';"    
    table_query = client.query(query_string)
    print("Loading Data to Compare for Validation...")
    results = table_query.result()
    df1 = results.to_dataframe()
    df1 = df1.sort_values('timeStamp')
    df1.to_csv(query_csv, index=False)
    df1 = pandas.read_csv(query_csv)
    
    if df1.equals(df2) == True:
        print('Big Query Entry was Validated!')
        delete_download_files()
        print("Validation Task Complete!")
        
    if df1.equals(df2) == False:
        raise ValueError("LAST: Big Query Entry does not match cleaned records") 




with DAG("final_capstone_dag", start_date=datetime(2021, 1, 1), schedule_interval="*/3 * * * *", catchup=False, description="final_capstone_dag", max_active_runs=1) as dag:


    get_combined_records_task = BranchPythonOperator(task_id="get_combined_records_task", retries=1, python_callable=get_combined_records)

    clean_and_process_records_task = PythonOperator(task_id='clean_and_process_records_task', retries=1, python_callable=clean_and_process_records)

    upload_df_to_bq_task = PythonOperator(task_id='upload_df_to_bq_task', retries=1, python_callable=upload_df_to_bq)

    validate_bq_info_task = PythonOperator(task_id='validate_bq_info_task', retries=1, python_callable=validate_bq_info)

    
    get_combined_records_task >> clean_and_process_records_task >> upload_df_to_bq_task >> validate_bq_info_task

