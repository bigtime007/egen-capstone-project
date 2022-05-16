# Capstone Project Part 1

### Make Big Query table

Ref: via CLI: bq help

### Step 1

Make dataset 

`bq mk capstone_dataset`

### Step 2

ref: bq mk new_dataset.new_table with schema

**Change to folder that has BQ Schema:** 

`cd ~/egen-capstone-project/big-query-config`

`bq mk --table egen-capstone-project:capstone_dataset.yahoo_btc_table ./capstone-schema.json`

*Schema Ref: https://cloud.google.com/bigquery/docs/schemas#specifying_a_json_schema_file*


**Verfiy dataset/tables**

`bq ls capstone_dataset`

### Google Cloud Composer:

**Part A:**

gcloud config set project <your-project-id>

`gcloud config set composer/location us-central1`

`gcloud services enable composer.googleapis.com`

*Ref: https://cloud.google.com/sdk/gcloud/reference/composer/environments/create*

`gcloud composer environments create capstone-airflow --location us-central1 --node-count 3 --machine-type=n1-standard-1 --disk-size 30 --image-version composer-1.18.7-airflow-2.2.3 --scheduler-count=1 --python-version 3 --zone us-central1-a`

*Ref: https://cloud.google.com/composer/docs/how-to/accessing/airflow-web-interface*
*gcloud composer environments describe ENVIRONMENT_NAME --location LOCATION*

**Lookup URL of aphache airflow**

`gcloud composer environments describe capstone-airflow --location us-central1 | grep "airflowUri:"

Lookup DAG Bucket:

`gcloud composer environments describe capstone-airflow --location us-central1 | grep "dagGcsPrefix:"`



**Part B:**

**Step 1**
    
Add Service Acct for Composer
    
`gcloud iam service-accounts create composer-8675309 \`
    `--description="Used to access bq and buckets" \`
    `--display-name="composer-project-role"`

**Step 2**
    
name: roles/bigquery.admin
name: roles/storage.admin
    
First add bigquery access admin
    
`gcloud projects add-iam-policy-binding egen-capstone-project \
    --member="serviceAccount:composer-8675309@egen-capstone-project.iam.gserviceaccount.com" \
    --role="roles/bigquery.admin"`

 Second add storage admin access
    
`gcloud projects add-iam-policy-binding egen-capstone-project \
    --member="serviceAccount:composer-8675309@egen-capstone-project.iam.gserviceaccount.com" \
    --role="roles/storage.admin"`

**Step 3**
    
#Create a key
    
`gcloud iam service-accounts keys create egen-capstone-project-bucket-bq.json \
    --iam-account=composer-8675309@egen-capstone-project.iam.gserviceaccount.com`



*Ref: https://cloud.google.com/storage/docs/gsutil/commands/cp*

**Step 4**
    
**Copy key while still in folder**

AF_BUCKET = <your-active-composer-bucket
                                           
`AF_BUCKET=`
                                           
`gsutil cp egen-capstone-project-bucket-bq.json $AF_BUCKET/data/temp-key/`


**Step 5**
                                           
**Copy DAG file to bucket/dags folder**
                                           
`gsutil cp final_capstone_dag.py $AF_BUCKET/dags/`



