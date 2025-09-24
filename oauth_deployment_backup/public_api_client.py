"""
Public API client for the FOGIS API.

This module provides a client for interacting with the FOGIS API.
It uses the internal API layer to communicate with the server,
but presents a simpler, more user-friendly interface.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, cast

import requests

from fogis_api_client.internal.adapters import (
    convert_event_to_internal,
    convert_internal_to_event,
    convert_internal_to_match,
    convert_internal_to_match_result,
    convert_internal_to_official,
    convert_internal_to_player,
    convert_match_participant_to_internal,
    convert_match_result_to_internal,
    convert_official_action_to_internal,
)
from fogis_api_client.internal.api_client import InternalApiClient, InternalApiError
from fogis_api_client.internal.auth import authenticate
from fogis_api_client.types import (
    CookieDict,
    EventDict,
    MatchDict,
    MatchListResponse,
    MatchParticipantDict,
    MatchResultDict,
    OfficialActionDict,
    OfficialDict,
    PlayerDict,
    TeamPlayersResponse,
)


class FogisApiError(Exception):
    """Base exception for all FOGIS API errors."""

    pass


class FogisLoginError(FogisApiError):
    """Exception raised when login fails."""

    pass


class FogisAPIRequestError(FogisApiError):
    """Exception raised when an API request fails."""

    pass


class FogisDataError(FogisApiError):
    """Exception raised when data validation fails."""

    pass


class PublicApiClient:
    """
    A client for interacting with the FOGIS API.

    This client implements lazy login, meaning it will automatically authenticate
    when making API requests if not already logged in. You can also explicitly call
    login() if you want to pre-authenticate.

    Attributes:
        BASE_URL (str): The base URL for the FOGIS API
        logger (logging.Logger): Logger instance for this class
        username (Optional[str]): FOGIS username if provided
        password (Optional[str]): FOGIS password if provided
        session (requests.Session): HTTP session for making requests
        cookies (Optional[CookieDict]): Session cookies for authentication
        internal_client (InternalApiClient): Internal API client for server communication
    """

    BASE_URL: str = "https://fogis.svenskfotboll.se/mdk"
    # For tests, this can be overridden with an environment variable
    import os
    if os.environ.get("FOGIS_API_BASE_URL"):
        BASE_URL = os.environ.get("FOGIS_API_BASE_URL")
    logger: logging.Logger = logging.getLogger("fogis_api_client.api")

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cookies: Optional[CookieDict] = None,
    ) -> None:
        """
        Initializes the PublicApiClient with either login credentials or session cookies.

        There are two ways to authenticate:
        1. Username and password: Authentication happens automatically on the first
           API request (lazy login),
           or you can call login() explicitly if needed.
        2. Session cookies: Provide cookies obtained from a previous session or external source.

        Args:
            username: FOGIS username. Required if cookies are not provided.
            password: FOGIS password. Required if cookies are not provided.
            cookies: Session cookies for authentication.
                If provided, username and password are not required.

        Raises:
            ValueError: If neither valid credentials nor cookies are provided
        """
        self.username: Optional[str] = username
        self.password: Optional[str] = password
        self.session: requests.Session = requests.Session()
        self.cookies: Optional[CookieDict] = None

        # Initialize the internal API client
        self.internal_client = InternalApiClient(self.session)

        # Set cookies if provided
        if cookies:
            self.logger.debug("Using provided cookies for authentication")
            self.cookies = cookies
            # Set cookies in the session
            for key, value in cookies.items():
                self.session.cookies.set(key, value)
        elif not (username and password):
            error_msg = "Either username and password or cookies must be provided"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def login(self) -> CookieDict:
        """
        Authenticate with the FOGIS API.

        This method is called automatically when needed, but you can also call it
        explicitly if you want to pre-authenticate.

        Returns:
            CookieDict: The session cookies for authentication

        Raises:
            FogisLoginError: If login fails
        """
        # If cookies are already set, return them without logging in again
        if self.cookies:
            self.logger.debug("Already authenticated, using existing cookies")
            return self.cookies

        # If no username/password provided, we can't log in
        if not (self.username and self.password):
            error_msg = "Login failed: No credentials provided and no cookies available"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg)

        try:
            # Authenticate with the FOGIS API
            self.cookies = authenticate(
                self.session, self.username, self.password, self.BASE_URL
            )
            return self.cookies
        except (requests.exceptions.RequestException, ValueError) as e:
            error_msg = f"Login failed: {e}"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg) from e

    def fetch_matches_list_json(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> MatchListResponse:
        """
        Fetch the list of matches for the logged-in referee.

        Args:
            filter_params: Filter parameters for the match list.
                If None, default filter parameters will be used.

        Returns:
            MatchListResponse: The match list response

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Use default filter parameters if none provided
        if filter_params is None:
            # Default to matches for the next 7 days
            today = datetime.now().strftime("%Y-%m-%d")
            next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            filter_params = {
                "datumFran": today,
                "datumTill": next_week,
                "datumTyp": 1,  # Match date
                "status": ["Ej rapporterad", "Påbörjad rapportering"],
            }

        try:
            # Use the internal API client to fetch the match list
            response_data = self.internal_client.get_matches_list(filter_params)

            # Convert to the public format
            return cast(MatchListResponse, response_data)
        except InternalApiError as e:
            error_msg = f"Failed to fetch match list: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_match_json(self, match_id: Union[int, str]) -> MatchDict:
        """
        Fetch detailed information for a specific match.

        Args:
            match_id: The ID of the match

        Returns:
            MatchDict: The match details

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to fetch the match details
            internal_match = self.internal_client.get_match(match_id_int)

            # Convert to the public format
            return convert_internal_to_match(internal_match)
        except InternalApiError as e:
            error_msg = f"Failed to fetch match details: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_match_players_json(self, match_id: Union[int, str]) -> Dict[str, List[PlayerDict]]:
        """
        Fetch player information for a specific match.

        Args:
            match_id: The ID of the match

        Returns:
            Dict[str, List[PlayerDict]]: Player information for the match

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to fetch the match players
            internal_players = self.internal_client.get_match_players(match_id_int)

            # Convert to the public format
            result: Dict[str, List[PlayerDict]] = {}
            for key, players in internal_players.items():
                result[key] = [convert_internal_to_player(player) for player in players]

            return result
        except InternalApiError as e:
            error_msg = f"Failed to fetch match players: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_match_officials_json(self, match_id: Union[int, str]) -> Dict[str, List[OfficialDict]]:
        """
        Fetch officials information for a specific match.

        Args:
            match_id: The ID of the match

        Returns:
            Dict[str, List[OfficialDict]]: Officials information for the match

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to fetch the match officials
            internal_officials = self.internal_client.get_match_officials(match_id_int)

            # Convert to the public format
            result: Dict[str, List[OfficialDict]] = {}
            for key, officials in internal_officials.items():
                result[key] = [convert_internal_to_official(official) for official in officials]

            return result
        except InternalApiError as e:
            error_msg = f"Failed to fetch match officials: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_match_events_json(self, match_id: Union[int, str]) -> List[EventDict]:
        """
        Fetch events information for a specific match.

        Args:
            match_id: The ID of the match

        Returns:
            List[EventDict]: Events information for the match

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to fetch the match events
            internal_events = self.internal_client.get_match_events(match_id_int)

            # Convert to the public format
            return [convert_internal_to_event(event) for event in internal_events]
        except InternalApiError as e:
            error_msg = f"Failed to fetch match events: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_team_players_json(self, team_id: Union[int, str]) -> TeamPlayersResponse:
        """
        Fetch player information for a specific team.

        Args:
            team_id: The ID of the team

        Returns:
            TeamPlayersResponse: Player information for the team

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert team_id to int if it's a string
        team_id_int = int(team_id) if isinstance(team_id, str) else team_id

        try:
            # Use the internal API client to fetch the team players
            internal_players = self.internal_client.get_team_players(team_id_int)

            # For now, just cast to the public format since they're the same
            return cast(TeamPlayersResponse, internal_players)
        except InternalApiError as e:
            error_msg = f"Failed to fetch team players: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def report_match_event(self, event_data: EventDict) -> Dict[str, Any]:
        """
        Report a match event to the FOGIS API.

        Args:
            event_data: The event data to report

        Returns:
            Dict[str, Any]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
            ValueError: If required fields are missing
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Validate required fields
        required_fields = [
            "matchid",
            "matchhandelsetypid",
            "matchminut",
            "matchlagid",
            "period"
        ]
        for field in required_fields:
            if field not in event_data:
                error_msg = f"Missing required field '{field}' in event data"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        try:
            # Convert to the internal format
            internal_event = convert_event_to_internal(event_data)

            # Use the internal API client to report the match event
            response_data = self.internal_client.save_match_event(internal_event)

            return response_data
        except InternalApiError as e:
            error_msg = f"Failed to report match event: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_match_result_json(self, match_id: Union[int, str]) -> Union[MatchResultDict, List[Dict[str, Any]]]:
        """
        Fetch the match results for a given match ID.

        Args:
            match_id: The ID of the match

        Returns:
            Union[MatchResultDict, List[Dict[str, Any]]]: The match results

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to fetch the match result
            internal_result = self.internal_client.get_match_result(match_id_int)

            # Convert to the public format
            return convert_internal_to_match_result(internal_result)
        except InternalApiError as e:
            error_msg = f"Failed to fetch match result: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def report_match_result(self, result_data: Union[MatchResultDict, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Report match results to the FOGIS API.

        Args:
            result_data: The match result data to report.
                Can be in either flat format (with hemmamal/bortamal) or
                nested format (with matchresultatListaJSON).

        Returns:
            Dict[str, Any]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
            ValueError: If required fields are missing
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Validate required fields for flat format
        if "matchresultatListaJSON" not in result_data:
            required_fields = ["matchid", "hemmamal", "bortamal"]
            for field in required_fields:
                if field not in result_data:
                    error_msg = f"Missing required field '{field}' in result data"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)

        try:
            # Convert to the internal format
            internal_result = convert_match_result_to_internal(result_data)

            # Use the internal API client to report the match result
            response_data = self.internal_client.save_match_result(internal_result)

            return response_data
        except InternalApiError as e:
            error_msg = f"Failed to report match result: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def delete_match_event(self, event_id: Union[int, str]) -> Dict[str, Any]:
        """
        Delete a match event from the FOGIS API.

        Args:
            event_id: The ID of the event to delete

        Returns:
            Dict[str, Any]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert event_id to int if it's a string
        event_id_int = int(event_id) if isinstance(event_id, str) else event_id

        try:
            # Use the internal API client to delete the match event
            response_data = self.internal_client.delete_match_event(event_id_int)

            return response_data
        except InternalApiError as e:
            error_msg = f"Failed to delete match event: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def report_team_official_action(self, action_data: OfficialActionDict) -> Dict[str, Any]:
        """
        Report a team official action to the FOGIS API.

        Args:
            action_data: The team official action data to report

        Returns:
            Dict[str, Any]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
            ValueError: If required fields are missing
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Validate required fields
        required_fields = ["matchid", "matchlagid", "matchlagledareid", "matchlagledaretypid"]
        for field in required_fields:
            if field not in action_data:
                error_msg = f"Missing required field '{field}' in action data"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        try:
            # Convert to the internal format
            internal_action = convert_official_action_to_internal(action_data)

            # Use the internal API client to report the team official action
            response_data = self.internal_client.save_team_official_action(internal_action)

            return response_data
        except InternalApiError as e:
            error_msg = f"Failed to report team official action: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def fetch_team_officials_json(self, team_id: Union[int, str]) -> List[OfficialDict]:
        """
        Fetch officials information for a specific team.

        Args:
            team_id: The ID of the team

        Returns:
            List[OfficialDict]: Officials information for the team

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert team_id to int if it's a string
        team_id_int = int(team_id) if isinstance(team_id, str) else team_id

        try:
            # Use the internal API client to fetch the team officials
            internal_officials = self.internal_client.get_team_officials(team_id_int)

            # Convert to the public format
            return [convert_internal_to_official(official) for official in internal_officials]
        except InternalApiError as e:
            error_msg = f"Failed to fetch team officials: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def save_match_participant(self, participant_data: MatchParticipantDict) -> Dict[str, Any]:
        """
        Save a match participant to the FOGIS API.

        Args:
            participant_data: The match participant data to save

        Returns:
            Dict[str, Any]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
            ValueError: If required fields are missing
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Validate required fields
        required_fields = ["matchdeltagareid", "trojnummer", "lagdelid"]
        for field in required_fields:
            if field not in participant_data:
                error_msg = f"Missing required field '{field}' in participant data"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        try:
            # Convert to the internal format
            internal_participant = convert_match_participant_to_internal(participant_data)

            # Use the internal API client to save the match participant
            url = f"{self.BASE_URL}/MatchWebMetoder.aspx/SparaMatchdeltagare"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            }

            response = self.session.post(url, json=internal_participant, headers=headers)
            response.raise_for_status()

            # Parse the JSON response
            response_data = response.json()

            # Extract the 'd' field if it exists
            if isinstance(response_data, dict) and "d" in response_data:
                try:
                    return json.loads(response_data["d"])
                except (json.JSONDecodeError, TypeError):
                    return response_data["d"]

            return response_data
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to save match participant: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def clear_match_events(self, match_id: Union[int, str]) -> Dict[str, bool]:
        """
        Clear all events for a match.

        Args:
            match_id: The ID of the match

        Returns:
            Dict[str, bool]: The response from the API

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid
        """
        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to clear the match events
            return self.internal_client.clear_match_events(match_id_int)
        except InternalApiError as e:
            error_msg = f"Failed to clear match events: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def get_cookies(self) -> Optional[CookieDict]:
        """
        Get the current session cookies.

        Returns:
            Optional[CookieDict]: The current session cookies, or None if not logged in
        """
        if self.cookies:
            self.logger.debug("Returning current session cookies")
        else:
            self.logger.debug("No cookies available to return")
        return self.cookies

    def hello_world(self) -> str:
        """
        Simple test method.

        Returns:
            str: A greeting message
        """
        self.logger.debug("Hello world method called")
        return "Hello, brave new world!"

    def mark_reporting_finished(self, match_id: Union[int, str]) -> Dict[str, bool]:
        """
        Mark match reporting as finished.

        Args:
            match_id: The ID of the match

        Returns:
            Dict[str, bool]: The response from the FOGIS API, typically containing a success status

        Raises:
            FogisLoginError: If not logged in
            FogisAPIRequestError: If there's an error with the API request
            FogisDataError: If the response data is invalid or not a dictionary
            ValueError: If match_id is empty or invalid
        """
        # Validate match_id
        if not match_id:
            error_msg = "match_id cannot be empty"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Ensure we're logged in
        if not self.cookies:
            self.login()

        # Convert match_id to int if it's a string
        match_id_int = int(match_id) if isinstance(match_id, str) else match_id

        try:
            # Use the internal API client to mark reporting as finished
            url = f"{self.BASE_URL}/MatchWebMetoder.aspx/SparaMatchGodkannDomarrapport"
            payload = {"matchid": match_id_int}

            # For now, use the _api_request method directly since we don't have an internal method for this
            response_data = self.session.post(url, json=payload, headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            })
            response_data.raise_for_status()

            # Parse the JSON response
            response_json = response_data.json()

            # Extract the 'd' field if it exists
            if isinstance(response_json, dict) and "d" in response_json:
                try:
                    result = json.loads(response_json["d"])
                    return cast(Dict[str, bool], result)
                except (json.JSONDecodeError, TypeError):
                    return {"success": True}

            return {"success": True}
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to mark reporting as finished: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e
