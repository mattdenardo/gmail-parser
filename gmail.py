"""
This script processes emails from daycare tagged in a user's Gmail Inbox in order to extract the 
linked photos and videos and save them by date.

Before running this script, the user should authenticate this script by following 
the link: https://developers.google.com/gmail/api/quickstart/python
and download client_secret.json to the same directory as this script.

Dependencies:
        Python 3
        Beautiful Soup 4: pip install beautifulsoup4
        Gmail API for Python: pip install --upgrade google-api-python-client
        lxml XML parser: pip install lxml

To do:
        pass in inbox tag as command line argument rather than hardcoding
        pass in save location/prefix as command line argument rather than hardcoding
"""

#import libraries
from __future__ import print_function
import httplib2
import os
import base64
import email
import time
import urllib.request

from bs4 import BeautifulSoup, SoupStrainer

from apiclient import discovery
from apiclient import errors

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gmail-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def ListLabels(service, user_id):
  """Get a list all labels in the user's mailbox.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.

  Returns:
    A list all Labels in the user's mailbox.
  """
  try:
    response = service.users().labels().list(userId=user_id).execute()
    labels = response['labels']
    #for label in labels:
      #print('Label id: %s - Label name: %s' % (label['id'], label['name']))
    return labels
  except errors.HttpError:#, error:
      print('An error occurred: %s' % error)

def ListMessagesWithLabels(service, user_id, label_ids=[]):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Messages with these labelIds applied.

  Returns:
    List of Messages that have all required Labels applied. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate id to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               labelIds=label_ids).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = service.users().messages().list(userId=user_id,
                                                 labelIds=label_ids,
                                                 pageToken=page_token).execute()
      messages.extend(response['messages'])

    return messages
  except errors.HttpError:#, error:
    print('An error occurred: %s' % error)

def GetMessage(service, user_id, msg_id):
  """Get a Message with given ID.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    msg_id: The ID of the Message required.

  Returns:
    A Message.
  """
  try:
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    #print('Message snippet: %s' % message['snippet'])
    return message
  except errors.HttpError:#, error:
    print('An error occurred: %s' % error)

def main():
    #authenticate and establish the API service
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    #look for the appropriate label in the inbox
    labels = ListLabels(service, 'me')
    for label in labels:
        if label['name'] == 'Ella daycare reports':
        #if label['name'] == 'Liev daycare reports':
            labelID = label['id']

    linkctr = 0
    #grab all the messages with the desired label ID
    msgs = ListMessagesWithLabels(service, 'me', labelID)
    for msg in msgs:
        msgId = msg['id']

        #grab each message with the desired message ID
        message = GetMessage(service, 'me', msgId)

        #get the date of each message
        epoch = int(message['internalDate'])
        date = time.strftime('%Y-%m-%d', time.localtime(epoch/1e3))

        #grab the payload of each message
        payload = message['payload']
        parts = payload['parts']
        part = parts[0]
        body = part['body']
        data = body['data']

        #convert from base64
        data = data.replace('-','+')
        data = data.replace('_','/')
        data = base64.b64decode(bytes(data, 'UTF-8'))

        #grab links for images or videos
        for link in BeautifulSoup(data, 'lxml', parse_only=SoupStrainer('a')):

            #get links by extension
            if link['href'][-3:]=='jpg' or link['href'][-3:]=='mp4':
                linkctr = linkctr + 1
                url = link['href']
                local = 'Ella_' + date + '_' + str(linkctr).zfill(4) + '.' + link['href'][-3:]
                #try:
                urllib.request.urlretrieve(url, local)
                #except urllib.error as e:
                    #print(e.reason)

            #in case file type changes, can try using link text
            #if link.string is not None:
                #if link.string[:7]=='Link to':
                    #print(link['href'])

if __name__ == '__main__':
    main()
