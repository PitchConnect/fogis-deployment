#!/usr/bin/env python3
"""
Event-driven match list processor with webhook support.
This version runs as a persistent service and processes matches only when triggered via webhook.
"""

import asyncio
import logging
import os
import signal
import sys
import threading
import time
from typing import Optional
from types import FrameType

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import the original app components
from src.config import settings
from src.core.data_manager import MatchDataManager
from src.core.match_comparator import MatchComparator
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.services.avatar_service import WhatsAppAvatarService
from src.services.phonebook_service import FogisPhonebookSyncService
from src.services.storage_service import GoogleDriveStorageService
from src.types import MatchDict_Dict
from src.utils.description_generator import generate_whatsapp_description
from src.services.health_service import HealthService

logger = logging.getLogger(__name__)


class EventDrivenMatchListProcessor:
    """Event-driven match list processor that waits for webhook triggers."""

    def __init__(self) -> None:
        """Initialize the application with all required services."""
        self.data_manager = MatchDataManager()
        self.api_client = DockerNetworkApiClient()
        self.avatar_service = WhatsAppAvatarService()
        self.storage_service = GoogleDriveStorageService()
        self.phonebook_service = FogisPhonebookSyncService()
        self.match_processor = MatchProcessor(
            self.avatar_service, self.storage_service, generate_whatsapp_description
        )
        self.health_service = HealthService(settings)

        # Service state
        self.running = True
        self.processing = False
        self.last_processing_time = None
        self.processing_count = 0

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Create FastAPI app
        self.app = self._create_app()

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with webhook and health endpoints."""
        app = FastAPI(
            title="Event-Driven Match List Processor",
            description="Processes matches when triggered via webhook",
            version="1.0.0"
        )

        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                health_status = await self.health_service.get_health_status()
                
                # Add event-driven specific status
                health_data = health_status.model_dump(mode="json")
                health_data.update({
                    "mode": "event-driven",
                    "processing": self.processing,
                    "last_processing_time": self.last_processing_time,
                    "processing_count": self.processing_count,
                    "running": self.running
                })

                status_code = 200 if health_status.status == "healthy" else 503
                return JSONResponse(status_code=status_code, content=health_data)
                
            except Exception as e:
                logger.exception("Health check failed")
                return JSONResponse(
                    status_code=503,
                    content={
                        "service_name": "match-list-processor",
                        "status": "unhealthy",
                        "mode": "event-driven",
                        "error": f"Health check failed: {str(e)}",
                        "timestamp": time.time()
                    }
                )

        @app.post("/process")
        async def process_matches():
            """Process matches when triggered by webhook."""
            if self.processing:
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "busy",
                        "message": "Processing already in progress"
                    }
                )

            try:
                # Start processing in background thread
                threading.Thread(target=self._process_matches_sync, daemon=True).start()
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "message": "Match processing triggered",
                        "processing_count": self.processing_count + 1
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to trigger processing: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": f"Failed to trigger processing: {str(e)}"
                    }
                )

        @app.get("/")
        async def root():
            """Root endpoint with service information."""
            return {
                "service": "match-list-processor",
                "mode": "event-driven",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/health",
                    "process": "/process (POST)"
                },
                "status": "running" if self.running else "shutting_down",
                "processing": self.processing
            }

        return app

    def _process_matches_sync(self) -> None:
        """Synchronous wrapper for match processing."""
        try:
            self.processing = True
            self.processing_count += 1
            self.last_processing_time = time.time()
            
            logger.info(f"Starting match processing (cycle #{self.processing_count})")
            
            # Sync contacts with phonebook
            sync_result = self.phonebook_service.sync_contacts()
            if not sync_result:
                logger.warning("Contact sync failed, but continuing with match processing.")

            # Load and parse previous matches
            previous_matches_dict = self._load_previous_matches()
            logger.info(f"Loaded previous matches data: {len(previous_matches_dict)} matches.")

            # Fetch current matches
            current_matches_dict = self._fetch_current_matches()
            if not current_matches_dict:
                logger.warning("Could not fetch current matches.")
                return

            logger.info(f"Fetched current matches data: {len(current_matches_dict)} matches.")

            # Compare matches and detect changes
            comparator = MatchComparator(previous_matches_dict, current_matches_dict)
            changes = comparator.compare_matches()

            if changes["has_changes"]:
                logger.info(f"Processing {len(changes['new_matches'])} new matches and {len(changes['updated_matches'])} updated matches")
                
                # Process new and updated matches
                all_matches_to_process = list(changes["new_matches"].values()) + list(changes["updated_matches"].values())
                
                for match in all_matches_to_process:
                    try:
                        self.match_processor.process_match(match)
                        logger.info(f"Successfully processed match {match.get('match_id', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Failed to process match {match.get('match_id', 'unknown')}: {e}")
            else:
                logger.info("No changes detected - no processing needed")

            # Save current matches as previous for next comparison
            self.data_manager.save_previous_matches_raw_json(
                self.data_manager.convert_list_to_raw_json(list(current_matches_dict.values()))
            )
            
            logger.info("Match processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error during match processing: {e}")
            logger.exception("Stack trace:")
        finally:
            self.processing = False

    def _load_previous_matches(self) -> MatchDict_Dict:
        """Load and parse previous matches from storage."""
        raw_json = self.data_manager.load_previous_matches_raw_json()
        match_list = self.data_manager.parse_raw_json_to_list(raw_json)
        return MatchComparator.convert_to_dict(match_list)

    def _fetch_current_matches(self) -> MatchDict_Dict:
        """Fetch current matches from API."""
        try:
            current_matches_list = self.api_client.get_matches()
            return MatchComparator.convert_to_dict(current_matches_list)
        except Exception as e:
            logger.error(f"Failed to fetch current matches: {e}")
            return {}

    def run(self) -> None:
        """Run the event-driven service."""
        logger.info("Starting event-driven match list processor...")
        logger.info("Service will wait for webhook triggers at /process endpoint")
        
        try:
            # Run FastAPI server
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("Event-driven match list processor stopped")


def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run the processor
    processor = EventDrivenMatchListProcessor()
    processor.run()


if __name__ == "__main__":
    main()
