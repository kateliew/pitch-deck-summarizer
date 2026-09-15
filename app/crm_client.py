import logging
import os
import requests
from requests.exceptions import HTTPError

ZOHO_CLIENT_ID = os.environ["ZOHO_CLIENT_ID"]
ZOHO_CLIENT_SECRET = os.environ["ZOHO_CLIENT_SECRET"]
ZOHO_REFRESH_TOKEN = os.environ["ZOHO_REFRESH_TOKEN"]
ZOHO_LAYOUT_ID = os.environ.get("ZOHO_LAYOUT_ID", "")


def refresh_zoho_access_token() -> str | None:
    """Exchange the stored refresh token for a new Zoho CRM access token."""
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "refresh_token": ZOHO_REFRESH_TOKEN,
    }

    try:
        logging.info("Attempting to refresh Zoho access token...")
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        new_access_token = token_data.get("access_token")
        if not new_access_token:
            logging.error("Failed to fetch new access token from Zoho.")
            return None

        logging.info("Successfully refreshed Zoho access token.")
        return new_access_token

    except HTTPError as http_err:
        logging.error(f"HTTP error occurred while refreshing Zoho access token: {http_err}")
    except Exception as e:
        logging.error(f"Error refreshing Zoho access token: {str(e)}")
    return None


def forward_to_zoho(summaries: dict, access_token: str | None = None) -> str:
    """Push the generated summary fields to a Zoho CRM 'Targets' record."""
    access_token = access_token or refresh_zoho_access_token()
    if not access_token:
        logging.error("Failed to obtain Zoho access token.")
        return "Failed to obtain Zoho access token."

    module_api_name = "Targets"
    url = f"https://www.zohoapis.com/crm/v2/{module_api_name}"

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json",
    }

    data = {
        "data": [
            {
                "Name": summaries.get("Company Name", ""),
                "Designated_Industry": summaries.get("Designated Industry", ""),
                "Company_Summary": summaries.get("Company Summary", ""),
                "Executive_Summary": summaries.get("Executive Summary", ""),
                "Competitors_Competitive_Advantage": summaries.get(
                    "Competitors / Competitive Advantage", ""
                ),
                "Round_Overview": summaries.get("Round Overview", ""),
                "Customer_Problem": summaries.get("Customer Problem", ""),
                "Target_Market": summaries.get("Target Market", ""),
                "Customers": summaries.get("Customers", ""),
                "Products_Services": summaries.get("Products & Services", ""),
                "Business_Model": summaries.get("Business Model", ""),
                "Sales_Marketing_Strategy": summaries.get(
                    "Sales & Marketing Strategy", ""
                ),
                "Layout": {"id": ZOHO_LAYOUT_ID},
            }
        ],
        "trigger": ["approval", "workflow", "blueprint"],
    }

    try:
        logging.info("Sending data to Zoho CRM.")
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()

        if response.status_code == 401:
            logging.info("Unauthorized error. Attempting to refresh Zoho access token...")
            new_token = refresh_zoho_access_token()
            if new_token:
                headers["Authorization"] = f"Zoho-oauthtoken {new_token}"
                response = requests.post(url, headers=headers, json=data)
                response_data = response.json()

        if response.status_code == 201:
            logging.info("Successfully forwarded summary to Zoho CRM.")
            return "Successfully forwarded summary to Zoho CRM."

        logging.error(f"Failed to forward summary to Zoho CRM: {response_data}")
        return f"Failed to forward summary to Zoho CRM: {response_data}"

    except Exception as e:
        logging.error(f"Error forwarding to Zoho CRM: {str(e)}")
        return f"Error forwarding to Zoho CRM: {str(e)}"