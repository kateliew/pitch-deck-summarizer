import logging
import os
import time
from io import BytesIO
import msal
import requests
from fpdf import FPDF
from PIL import Image
from PyPDF4 import PdfFileMerger

# Azure AD app registration (set as environment variables, never hardcoded)
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
TENANT_ID = os.environ["AZURE_TENANT_ID"]

# Shared mailbox that receives inbound pitch decks
SHARED_MAILBOX = os.environ["SHARED_MAILBOX"]

# Azure Function App endpoint that runs the summarization pipeline
AZURE_FUNCTION_URL = os.environ["AZURE_FUNCTION_URL"]

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))


def get_access_token() -> str:
    """Acquire a Microsoft Graph access token via client credentials flow."""
    authority_url = f"https://login.microsoftonline.com/{TENANT_ID}"
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority_url, client_credential=CLIENT_SECRET
    )
    scopes = ["https://graph.microsoft.com/.default"]
    result = msal_app.acquire_token_silent(scopes, account=None)

    if not result:
        result = msal_app.acquire_token_for_client(scopes=scopes)

    if "access_token" in result:
        return result["access_token"]
    raise Exception("Could not obtain access token")


def get_new_emails(access_token: str) -> list:
    """Fetch unread messages from the shared mailbox inbox."""
    headers = {"Authorization": "Bearer " + access_token}
    endpoint = (
        f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}"
        f"/mailFolders/Inbox/messages?$filter=isRead eq false"
    )
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json().get("value", [])


def mark_email_as_read(access_token: str, message_id: str) -> None:
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    endpoint = f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}/messages/{message_id}"
    data = {"isRead": True}
    response = requests.patch(endpoint, headers=headers, json=data)
    response.raise_for_status()


def email_body_to_pdf(body_content: str, output_filename: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, body_content)
    pdf.output(output_filename)


def download_attachments(access_token: str, message_id: str) -> list:
    headers = {"Authorization": "Bearer " + access_token}
    endpoint = (
        f"https://graph.microsoft.com/v1.0/users/{SHARED_MAILBOX}"
        f"/messages/{message_id}/attachments"
    )
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    attachments = response.json().get("value", [])
    attachment_files = []

    for attachment in attachments:
        if attachment["@odata.type"] == "#microsoft.graph.fileAttachment":
            attachment_name = attachment["name"]
            content_bytes = attachment["contentBytes"]
            attachment_filename = f"attachment_{attachment_name}"
            with open(attachment_filename, "wb") as f:
                f.write(BytesIO(content_bytes.encode("utf-8")).read())
            attachment_files.append(attachment_filename)

    return attachment_files


def convert_to_pdf(input_filename: str) -> str | None:
    """Convert a downloaded attachment to PDF so it can be merged and summarized."""
    file_ext = os.path.splitext(input_filename)[1].lower()
    output_filename = f"{os.path.splitext(input_filename)[0]}.pdf"

    if file_ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
        image = Image.open(input_filename)
        pdf_bytes = BytesIO()
        image.save(pdf_bytes, format="PDF")
        with open(output_filename, "wb") as f:
            f.write(pdf_bytes.getvalue())

    elif file_ext in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
        os.system(f'libreoffice --headless --convert-to pdf "{input_filename}" --outdir .')

    elif file_ext == ".pdf":
        output_filename = input_filename

    else:
        logging.warning(f"Unsupported file type: {file_ext}")
        return None

    return output_filename


def concatenate_pdfs(pdf_files: list, output_filename: str) -> None:
    merger = PdfFileMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(output_filename)
    merger.close()


def send_pdf_to_azure(pdf_filename: str) -> None:
    with open(pdf_filename, "rb") as f:
        files = {"file": (pdf_filename, f, "application/pdf")}
        response = requests.post(AZURE_FUNCTION_URL, files=files)
        response.raise_for_status()


def process_emails() -> None:
    """Poll the shared mailbox once: convert each unread email + attachments
    into a single PDF and hand it off to the summarization Azure Function."""
    access_token = get_access_token()
    emails = get_new_emails(access_token)

    for email in emails:
        message_id = email["id"]
        body_content = email["body"]["content"]
        email_pdf = "email_body.pdf"
        email_body_to_pdf(body_content, email_pdf)
        pdf_files = [email_pdf]

        if email.get("hasAttachments", False):
            attachment_files = download_attachments(access_token, message_id)
            for attachment in attachment_files:
                pdf_file = convert_to_pdf(attachment)
                if pdf_file:
                    pdf_files.append(pdf_file)
                os.remove(attachment)

        final_pdf = f"final_{message_id}.pdf"
        concatenate_pdfs(pdf_files, final_pdf)
        send_pdf_to_azure(final_pdf)
        mark_email_as_read(access_token, message_id)

        for pdf in pdf_files:
            os.remove(pdf)
        os.remove(final_pdf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            process_emails()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)