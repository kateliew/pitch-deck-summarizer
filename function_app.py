import logging
import os
import azure.functions as func
import openai
from app.crm_client import forward_to_zoho
from app.pdf_parser import parse_pdf
from app.summarizer import generate_summary

openai.api_key = os.environ["OPENAI_API_KEY"]

app = func.FunctionApp()


@app.function_name(name="PitchSummary")
@app.route(route="PitchSummary", auth_level=func.AuthLevel.ANONYMOUS)
def PitchSummary(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function endpoint: accepts a pitch deck PDF, summarizes it via
    OpenAI, and forwards the structured summary to Zoho CRM."""
    logging.info("Python HTTP trigger function processed a request.")
    try:
        file = req.files.get("file")
        if not file:
            logging.error("No file received in the request.")
            return func.HttpResponse(
                "Please pass a file in the request body", status_code=400
            )

        file_path = "/tmp/uploaded_file.pdf"
        with open(file_path, "wb") as f:
            f.write(file.read())

        document_text = parse_pdf(file_path)
        if not document_text:
            logging.error("Failed to extract text from PDF.")
            return func.HttpResponse("Failed to extract text from PDF", status_code=500)

        summaries = generate_summary(document_text)
        logging.info(f"Summaries before sending to Zoho: {summaries}")

        if any("Error" in summary for summary in summaries.values()):
            logging.error("Failed to generate summaries for some fields.")
            return func.HttpResponse(
                "Failed to generate summaries for some fields.", status_code=500
            )

        forward_result = forward_to_zoho(summaries)
        if "error" in forward_result.lower():
            logging.error(f"Error forwarding summary to Zoho CRM: {forward_result}")
            return func.HttpResponse(forward_result, status_code=500)

        return func.HttpResponse(forward_result, status_code=200)

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(f"Error processing request: {str(e)}", status_code=500)