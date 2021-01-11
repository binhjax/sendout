from flask import Flask, request, render_template
import sendgrid
import json
import os
# import hashlib

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from sendgrid.helpers.mail import Mail

from google.cloud import storage

app = Flask(__name__)

# storage_client = storage.Client()
storage_client = storage.Client.from_service_account_json('credentials.json')

bucket_name = os.environ.get('BUCKET', 'testsendout')
request_folder =  os.environ.get('REQUEST_FOLDER', 'requests')
public_folder =  os.environ.get('PUBLIC_FOLDER', 'sendout')

def public_request(id, user):
   prefix = '{}/request_{}/'.format(request_folder,id)
   blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

   files = []
   for blob in blobs:
       filename = blob.name
       pfilename = public_file(user, filename)
       files.append(pfilename)
   return files


def public_file(user, filename):
    user_public_folder = public_folder + '/' + user

    source_bucket = storage_client.bucket(bucket_name)
    destination_bucket = storage_client.bucket(bucket_name)

    #Copy to destination
    source_blob = source_bucket.blob(filename)

    destination_blob_name = filename.replace(request_folder,user_public_folder)
    blob_copy = source_bucket.copy_blob(
        source_blob, destination_bucket, destination_blob_name
    )
    blob_copy.acl.
    return blob_copy.name

def create_queue_task(task_name, data):
    client = tasks_v2.CloudTasksClient()

    PROJECT_ID = os.environ.get('PROJECT_ID', 'loyalty-272605')
    LOCATION = os.environ.get('LOCATION', 'us-central1')
    QUEUE = os.environ.get('QUEUE', 'my-appengine-queue')

    parent = client.queue_path(PROJECT_ID, LOCATION, QUEUE)

    task = {
            'app_engine_http_request': {  # Specify the type of request.
                'http_method': 'POST',
                'relative_uri': '/execute_queue_task'
            }
    }
    payload = {
        'task_name': task_name,
        'data': data
    }
    task['app_engine_http_request']['body'] = json.dumps(payload).encode()
    return client.create_task(parent, task)

def send_result(state,id, recipients,  files):
    if state == 'accept':
        subject = 'Request {} send data to outside accepted'.format(id)
    else:
        subject = 'Request {} send data to outside denied'.format(id)

    storage_url = 'https://storage.cloud.google.com/{}'.format(bucket_name)
    html_content = render_template('list.html', files=files, url=storage_url)

    data = {
        'recipient': recipients,
        'subject': subject,
        'content': html_content
    }
    return create_queue_task('send_mail', data)

def send_mail(recipient, subject, html_content):

    SENDGRID_SENDER = os.environ.get('SENDGRID_SENDER', 'sendout@teko.vn')
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')

    message = Mail(
        from_email=SENDGRID_SENDER,
        to_emails='{},'.format(recipient),
        subject=subject,
        html_content=html_content
        )
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    return response

@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    dummy_times = [1,5,6,8,9]
    return render_template('index.html', times=dummy_times)


@app.route('/requests')
def list_requests():
    """List all requests."""
    prefix = '{}/'.format(request_folder)
    blobs = storage_client.list_blobs(bucket_name,prefix=prefix)
    list = []
    for blob in blobs:
        if blob.name.endswith('/'):
            list.append(blob.name)
    return json.dumps(list)

@app.route('/request/<id>')
def detail_request(id):
    """List all requests."""
    prefix = '{}/request_{}/'.format(request_folder,id)
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    list = []
    for blob in blobs:
        filename = blob.name.replace(prefix,"")
        if filename:
            list.append(filename)

    return json.dumps(list)

@app.route('/publish/<id>/<user>')
def publish_request(id,user):
    list = public_request(id, user)
    return json.dumps(list)

@app.route('/action/<state>/<id>/<email>')
def feedback(state,id,email):
    print("Task: {}, {}, {} ".format(id, state, email))
    parts = email.split('@')
    user = parts[0];

    #1. Move data to public bucket
    files = []
    if state == 'accept':
        files = public_request(id, user)

    #2. Send email
    response = send_result(state,id, email, files)

    print("Create task: {}".format(response.name))

    if state == 'accept':
        message = 'You are acccepted request {} from {} '.format(id, email)
    else:
        message = 'You denied request {} from {} '.format(id, email)

    return render_template('feedback.html', message = message)


@app.route('/execute_queue_task', methods=['POST'])
def execute_queue_task():
    payload = request.get_data(as_text=True) or '(empty payload)'
    print('Received task with payload: {}'.format(payload))

    obj = json.loads(payload)
    method = obj.get('task_name',None)
    data = obj.get('data',None)

    msg = ''
    if method:
        if method == 'send_mail' and data:
            recipient = data.get('recipient',None)
            subject = data.get('subject',None)
            html_content = data.get('content',None)
            if recipient:
                response = send_mail(recipient, subject, html_content)
                msg = response.body
            else:
                msg = 'Not find receipient in data '
        else:
            msg = 'Find other method:  ' + method
    else:
        msg = 'Method is none '
    print('Result: {}'.format(msg))
    return 'Ret: {}'.format(msg)


if __name__ == '__main__':
    app.run(debug=True)
