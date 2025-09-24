"""
Authentication module for the FOGIS API client.

This module handles authentication with the FOGIS API server.
"""
import logging
from typing import cast

import requests
from bs4 import BeautifulSoup

from fogis_api_client.internal.types import InternalCookieDict

logger = logging.getLogger(__name__)


def authenticate(session: requests.Session, username: str, password: str, base_url: str) -> InternalCookieDict:
    """
    Authenticate with the FOGIS API server.

    Args:
        session: The requests session to use for authentication
        username: The username to authenticate with
        password: The password to authenticate with
        base_url: The base URL of the FOGIS API server

    Returns:
        InternalCookieDict: The session cookies for authentication

    Raises:
        requests.exceptions.RequestException: If the authentication request fails
        ValueError: If the authentication fails due to invalid credentials
    """
    login_url = f"{base_url}/Login.aspx?ReturnUrl=%2fmdk%2f"
    logger.debug(f"Authenticating with {login_url}")

    # Set browser-like headers to avoid being blocked
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    # Get the login page to extract all form tokens
    response = session.get(login_url, timeout=(10, 30))
    response.raise_for_status()

    # Parse the HTML to extract all hidden form fields
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract all hidden form fields
    form_data = {}
    hidden_inputs = soup.find_all("input", {"type": "hidden"})
    for inp in hidden_inputs:
        name = inp.get("name", "")
        value = inp.get("value", "")
        if name:
            form_data[name] = value

    # Verify we have the required tokens
    if "__VIEWSTATE" not in form_data:
        logger.error("Failed to extract __VIEWSTATE token from login page")
        raise ValueError("Failed to extract __VIEWSTATE token from login page")

    if "__EVENTVALIDATION" not in form_data:
        logger.error("Failed to extract __EVENTVALIDATION token from login page")
        raise ValueError("Failed to extract __EVENTVALIDATION token from login page")

    # Prepare the login payload with all form fields
    login_payload = form_data.copy()
    login_payload.update({
        "ctl00$MainContent$UserName": username,
        "ctl00$MainContent$Password": password,
        "ctl00$MainContent$LoginButton": "Logga in",
    })

    # Submit the login form
    response = session.post(login_url, data=login_payload, allow_redirects=True, timeout=(10, 30))
    response.raise_for_status()

    # Check if login was successful
    if "FogisMobilDomarKlient.ASPXAUTH" not in session.cookies:
        logger.error("Authentication failed: Invalid credentials or login form changed")
        raise ValueError("Authentication failed: Invalid credentials or login form changed")

    # Extract the cookies
    cookies = cast(
        InternalCookieDict,
        {
            "FogisMobilDomarKlient.ASPXAUTH": session.cookies.get("FogisMobilDomarKlient.ASPXAUTH"),
            "ASP.NET_SessionId": session.cookies.get("ASP.NET_SessionId"),
        },
    )

    logger.debug("Authentication successful")
    return cookies
