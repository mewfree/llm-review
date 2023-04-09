import os
import pickle
import base64
from datetime import datetime
from string import Template
from email.message import EmailMessage

import google.auth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CREDENTIALS_FILE = "credentials.pickle"

today = datetime.today().strftime("%Y-%m-%d")

path_template = Template(os.path.expanduser("~") + "/meworg/journal/daily/$today.org")
path = path_template.substitute(today=today)

file = open(path, "r")
daily_journal = file.read()
file.close()

content_template = Template(
    "Here is my daily journal for today in a Markdown block:\n```\n$daily_journal\n```\nBased on this, how can I make my next day better?"
)
content = content_template.substitute(daily_journal=daily_journal)

chat = ChatOpenAI(temperature=0.5)
result = chat([HumanMessage(content=content)])


def get_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "rb") as f:
            creds = pickle.load(f)
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open(CREDENTIALS_FILE, "wb") as f:
            pickle.dump(creds, f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def gmail_send(content):
    creds = get_credentials()

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)

        message = EmailMessage()

        message.set_content(content)

        email = "damien.gonot@gmail.com"
        message["To"] = email
        message["From"] = email
        message["Subject"] = today + " review"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"message": {"raw": encoded_message}}
        # pylint: disable=E1101
        draft = (
            service.users().drafts().create(userId="me", body=create_message).execute()
        )

    except HttpError as error:
        print(f"An error occurred: {error}")
        draft = None

    service.users().drafts().send(userId="me", body={"id": draft["id"]}).execute()


gmail_send(result.content)
