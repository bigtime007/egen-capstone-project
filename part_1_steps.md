# Capstone Project Part 1


### Setup Project and Configure Services.

Run this cmd to create a isolated project.

 

`gcloud projects create egen-capstone-project`

Now Set the project 
  
`gcloud config set project egen-capstone-project`
  

**We also need to enable billing. At the top right below "Show Info Pannel" you should see a button: "ENABLE BILLING"**

*This step is required for Proceeding*
  
  
  
  
  
 In order to make project deployment go smooth its best to active the api's ahead of time. 
    
Now you can list every api that google will allow however thats alot

`gcloud services list --available`




**Instead we need only these API for now. Also APIs for Part2 will be actived now as well**

`gcloud services enable appengine.googleapis.com bigquery.googleapis.com bigquerystorage.googleapis.com composer.googleapis.com`

`gcloud services enable cloudapis.googleapis.com cloudbuild.googleapis.com cloudfunctions.googleapis.com `

`gcloud services enable container.googleapis.com  containerfilesystem.googleapis.com containerregistry.googleapis.com`

`gcloud services enable iam.googleapis.com  iamcredentials.googleapis.com logging.googleapis.com storage.googleapis.com`

`gcloud services enable monitoring.googleapis.com pubsub.googleapis.com storage-api.googleapis.com storage-component.googleapis.com `

Also lets set our region and zone for now

`gcloud config set compute/region us-central1`

`gcloud config set compute/zone us-central1-f`

### Configure Storage

The first thing we need a place to store our csv files, so lets make a bucket.

Store this as varible in you cloud cli enviroment 

`BUCKET_NAME=capstone-project-yahoo-api-raw-data`

Now when making the bucket I'm choosing to make my bucket loc: us-central1 so if we decide download files from Big Query we can use a folder in this bucket.

`gsutil mb -l us-central1 gs://$BUCKET_NAME`

We also need to grant Permissions to the Cloud Function via IAM

`gsutil iam ch serviceAccount:egen-capstone-project@appspot.gserviceaccount.com:admin gs://$BUCKET_NAME`

Verify:

`gsutil iam get gs://capstone-project-yahoo-api-raw-data`

You should get:

`{
  "bindings": [
    {
      "members": [
        "serviceAccount:egen-capstone-project@appspot.gserviceaccount.com"
      ],
      "role": "roles/storage.admin"
    },`

### Configure Messaging Service: Pub/Sub

**First we need to make a topic** 

`gcloud pubsub topics create capstone-topic`

**Second we need a Trigger Cloud Function**

Navigate to the "cloud-function" folder

`cd ~/egen-capstone-project/pub-sub-trigger-function/function-source-code`

Run the list command to verify everything is there: requirements.txt main.py etc.. 

`ls`

Now we are going to deploy the function from the cli using the following. Every time a message is recieved from our container, Pub/Sub will trigger our funcition to read the message by executing the 'process' function in the python code file 'main.py'.

`gcloud functions deploy capstone-pubsub-trigger --trigger-topic capstone-topic --runtime python39 --entry-point process`

You should see the following *`Deploying function (may take a while - up to 2 minutes)...⠹`*  Once its done deploying you should see ouput letting you know bulid id, runtime, lablels, status, versionID, etc..

When the trigger function is deployed it will also create a subscription for the topic. Example: subscriptions/gcf-capstone-pubsub-trigger-us-central1-capstone-topic

### Deploy a docker image w/GKE

We will be using Google GKE for the container service. I will also give instructions at the bottom for document for how deploy docker locally assuming you've installed docker desktop. 

**First**

`gcloud container clusters create capstone-micro-service --num-nodes 1 --scopes pubsub,gke-default`

Your should see: *`Creating cluster capstone-micro-service in us-central1-f... Cluster is being configured...⠏`*

Once the cluster is created verfy the following:

`gcloud compute instances list`

**Second**
Locate the go the folder that contains: Dockerfile, requirement.txt, app.py, etc..

In the file named apikey.py. Insert your api key for yahoo. Save it before committing to google builds.

Run the following command

`gcloud builds submit   --tag gcr.io/$GOOGLE_CLOUD_PROJECT/yahoo-api-pubsub-v1` 

Once the image is created we need to deploy it.

`kubectl create deployment capstone-app --image gcr.io/$GOOGLE_CLOUD_PROJECT/yahoo-api-pubsub-v1`

Expose your GKE deployment. Pub/sub and the API use the 443 port.

`kubectl expose deployment capstone-app --type=LoadBalancer --port 443 --target-port 443`

Verify everything...also note the container-name.

`kubectl get pods,deployments,rs`

If you want to see the log files, ssh by..

`kubectl exec -it <container-name> bash`



By now if your log files are showing a 200 response you should have files in your bucket shortly.
















