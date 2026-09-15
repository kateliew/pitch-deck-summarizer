# Pitch Deck Summarizer

Automated pipeline that watches a shared inbox for incoming pitch decks, extracts
and summarizes them with an LLM, and pushes the structured summary into a CRM
for deal-flow triage.

## Architecture

```
email_ingestion/email_retriever.py    Polls a shared mailbox (Microsoft Graph)
        │                             for unread mail, converts the email body
        │                             and any attachments to a single PDF.
        ▼
function_app.py (Azure Function)      Receives the PDF over HTTP.
        │
        ├── app/pdf_parser.py         Extracts raw text from the PDF.
        ├── app/summarizer.py         Sends the text to OpenAI, field by field,
        │                             to produce a structured deal summary.
        └── app/crm_client.py         Forwards the structured summary to
                                       Zoho CRM (with OAuth token refresh).
```

## Stack

- Azure Functions (Python programming model)
- OpenAI Chat Completions (`openai==0.28.1` — legacy pre-1.0 SDK syntax)
- Microsoft Graph API + MSAL (mailbox polling)
- Zoho CRM REST API v2
- PyPDF2 / PyPDF4, Pillow, fpdf for document handling

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own credentials, never commit this file
```

Run the Azure Function locally with the [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local):

```bash
func start
```

Run the mailbox poller separately:

```bash
python email_ingestion/email_retriever.py
```

## Notes

- All credentials are read from environment variables — see `.env.example`
  for the full list. Nothing is hardcoded in source.
- This was originally a working prototype; the `openai==0.28.1` API surface
  used here predates OpenAI's `>=1.0` SDK.