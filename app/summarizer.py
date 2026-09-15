import logging
import openai

# Each entry maps a summary field to the system prompt used to extract it.
SUMMARY_FIELDS = {
    "Company Name": "Provide the name of the company within 20 characters.",
    "Designated Industry": (
        "Classify the company into one of the following industries (just the "
        "industry title, nothing more): AgTech-Food Supply, Automotive, "
        "Consumer, Energy & Natural Resources, Financial Services, Healthcare, "
        "Insurance, IT Hardware, Life Sciences, Manufacturing, Media, Other."
    ),
    "Company Summary": (
        "Provide a short summary of the company's purpose, mission, and "
        "product, within 2000 characters."
    ),
    "Executive Summary": (
        "Categorize the company into one of these sectors: Life Sciences, "
        "Healthcare, Food Supply/AgTech, Manufacturing, Energy/Natural "
        "Resources, Public Safety/Cybersecurity. Identify the 'Ask' and other "
        "deal information: $ amount, company valuation, within 2000 characters."
    ),
    "Competitors / Competitive Advantage": (
        "Provide a short summary of the company's competitive edge in "
        "100-150 characters."
    ),
    "Round Overview": (
        "Provide the investment this company seeks, as well as which "
        "investment round the company is currently in, 100-150 characters."
    ),
    "Customer Problem": (
        "Identify the problem this company seeks to solve in 100-150 characters."
    ),
    "Target Market": "Identify the company's target market in 100-150 characters.",
    "Customers": (
        "Identify the company's target customer profile in 100-150 characters."
    ),
    "Products & Services": (
        "Identify the products/services this company offers in 100-150 characters."
    ),
    "Business Model": (
        "Identify the company's business model in 100-150 characters."
    ),
    "Sales & Marketing Strategy": (
        "Identify the company's sales/marketing strategy in 100-150 characters."
    ),
}


def generate_summary(document_text: str) -> dict:
    """Run each configured field prompt against the pitch deck text via OpenAI."""
    summaries = {}
    for field, prompt in SUMMARY_FIELDS.items():
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": document_text},
        ]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.0,
                max_tokens=150,
            )
            summaries[field] = response["choices"][0]["message"]["content"].strip()
            logging.info(f"Generated summary for {field}: {summaries[field]}")
        except openai.error.OpenAIError as e:
            logging.error(f"Error generating summary for {field}: {str(e)}")
            summaries[field] = f"Error generating summary for {field}: {str(e)}"
    return summaries