#!/usr/bin/env python3
"""Persistent service implementation for match-list-change-detector.

This module provides a long-running service mode with internal scheduling,
HTTP server for health checks and manual triggers, and configurable cron patterns.

This addresses the restart loop issues by running the service continuously
instead of the oneshot execution model.

For contributing guidelines, see CONTRIBUTING.md in the repository root.
"""

import asyncio
import signal
import sys
import threading
import time
from datetime import datetime
from types import FrameType
from typing import Any, Dict, Optional

import uvicorn

# Import existing modules
from config import get_config
from croniter import croniter
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from logging_config import get_logger

logger = get_logger("persistent_service")


class PersistentMatchListChangeDetectorService:
    """Persistent service implementation for match list change detection."""

    def __init__(self) -> None:
        """Initialize the persistent service application."""
        # Get configuration
        self.config = get_config()

        # Service configuration - read directly from environment variables to ensure they're picked up
        import os

        self.run_mode = os.environ.get("RUN_MODE", "oneshot").lower()
        self.cron_schedule = os.environ.get(
            "CRON_SCHEDULE", os.environ.get("MATCH_DETECTOR_CRON_SCHEDULE", "0 * * * *")
        )
        self.health_server_port = int(os.environ.get("HEALTH_SERVER_PORT", "8000"))
        self.health_server_host = os.environ.get(
            "HEALTH_SERVER_HOST", "0.0.0.0"
        )  # nosec B104

        # Service state
        self.running = True
        self.last_execution: Optional[datetime] = None
        self.next_execution: Optional[datetime] = None
        self.execution_count = 0
        self.start_time = time.time()

        # Initialize HTTP server
        self.app = self._create_fastapi_app()
        self.server_thread: Optional[threading.Thread] = None
        self._server: Optional[uvicorn.Server] = None

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Validate cron schedule
        self._validate_cron_schedule()

    def _validate_cron_schedule(self) -> None:
        """Validate the cron schedule format."""
        try:
            cron = croniter(self.cron_schedule, datetime.now())
            self.next_execution = cron.get_next(datetime)
            logger.info(
                f"Cron schedule '{self.cron_schedule}' is valid. "
                f"Next execution: {self.next_execution}"
            )
        except Exception as e:
            logger.error(f"Invalid cron schedule '{self.cron_schedule}': {e}")
            raise ValueError(f"Invalid cron schedule: {e}")

    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with health and trigger endpoints."""
        app = FastAPI(
            title="Match List Change Detector",
            description="Persistent service for detecting changes in FOGIS match lists",
            version="1.0.0",
        )

        @app.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            status = "healthy" if self.running else "unhealthy"

            health_data = {
                "service_name": "match-list-change-detector",
                "status": status,
                "run_mode": self.run_mode,
                "cron_schedule": self.cron_schedule,
                "last_execution": self.last_execution.isoformat()
                if self.last_execution
                else None,
                "next_execution": self.next_execution.isoformat()
                if self.next_execution
                else None,
                "execution_count": self.execution_count,
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": datetime.now().isoformat(),
            }

            status_code = 200 if status == "healthy" else 503
            return JSONResponse(status_code=status_code, content=health_data)

        @app.post("/trigger")
        async def manual_trigger() -> Dict[str, str]:
            """Manual trigger endpoint for immediate execution."""
            if not self.running:
                raise HTTPException(status_code=503, detail="Service is not running")

            try:
                logger.info("Manual trigger received, executing change detection...")
                await self._execute_change_detection()
                return {
                    "status": "success",
                    "message": "Change detection executed successfully",
                }
            except Exception as e:
                logger.error(f"Manual trigger failed: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Execution failed: {str(e)}"
                )

        @app.get("/status")
        async def service_status() -> Dict[str, Any]:
            """Detailed service status endpoint."""
            return {
                "service_name": "match-list-change-detector",
                "run_mode": self.run_mode,
                "running": self.running,
                "cron_schedule": self.cron_schedule,
                "last_execution": self.last_execution.isoformat()
                if self.last_execution
                else None,
                "next_execution": self.next_execution.isoformat()
                if self.next_execution
                else None,
                "execution_count": self.execution_count,
                "uptime_seconds": time.time() - self.start_time,
                "configuration": {
                    "health_server_port": self.health_server_port,
                    "health_server_host": self.health_server_host,
                    "fogis_username": self.config.get("FOGIS_USERNAME", "NOT_SET"),
                    "fogis_password_set": bool(self.config.get("FOGIS_PASSWORD")),
                },
            }

        return app

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.shutdown()
        sys.exit(0)

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down match list change detector...")
        self.running = False

        if self._server:
            self._server.should_exit = True

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
            logger.info("HTTP server stopped")

    async def _execute_change_detection(self) -> bool:
        """Execute the change detection logic."""
        try:
            self.last_execution = datetime.now()
            self.execution_count += 1

            logger.info(f"Starting change detection cycle #{self.execution_count}")

            # Import and run the main detection logic
            from match_list_change_detector import main as run_detection

            # Run the change detection in a thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(None, run_detection)

            logger.info(
                f"Change detection cycle #{self.execution_count} completed successfully"
            )

            # Update next execution time if running in service mode
            if self.run_mode == "service":
                cron = croniter(self.cron_schedule, self.last_execution)
                self.next_execution = cron.get_next(datetime)
                logger.info(f"Next scheduled execution: {self.next_execution}")

            return result

        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            logger.exception("Change detection stack trace:")
            raise

    def _start_http_server(self) -> None:
        """Start the HTTP server in a separate thread."""

        def run_server() -> None:
            try:
                config = uvicorn.Config(
                    self.app,
                    host=self.health_server_host,
                    port=self.health_server_port,
                    log_level="info",
                    access_log=False,
                )
                self._server = uvicorn.Server(config)
                asyncio.run(self._server.serve())
            except Exception as e:
                logger.exception(f"HTTP server failed: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(
            f"HTTP server started on {self.health_server_host}: {self.health_server_port}"
        )

    def run(self) -> None:
        """Run the main application logic."""
        logger.info(f"Starting match list change detector in {self.run_mode} mode...")
        logger.info(f"Cron schedule: {self.cron_schedule}")

        # Start HTTP server
        self._start_http_server()

        # Give server time to start
        time.sleep(2)

        if self.run_mode == "service":
            self._run_as_service()
        else:
            self._run_once()

    def _run_as_service(self) -> None:
        """Run as a persistent service with cron-based scheduling."""
        logger.info(
            f"Running as persistent service with cron schedule: {self.cron_schedule}"
        )

        while self.running:
            try:
                now = datetime.now()

                # Check if it's time to execute
                if self.next_execution and now >= self.next_execution:
                    logger.info(
                        "Scheduled execution time reached, running change detection..."
                    )
                    asyncio.run(self._execute_change_detection())

                # Sleep for 1 second and check again
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                logger.exception("Service loop stack trace:")
                # Continue running even if one cycle fails
                time.sleep(30)  # Wait 30 seconds before retrying

        logger.info("Service mode stopped")

    def _run_once(self) -> None:
        """Run once and exit (original behavior)."""
        try:
            logger.info("Running in oneshot mode...")
            asyncio.run(self._execute_change_detection())
            logger.info("Match list change detection completed successfully")
        except Exception as e:
            logger.error(f"Oneshot execution failed: {e}")
            logger.exception("Oneshot execution stack trace:")
            sys.exit(1)


def main() -> None:
    """Run the persistent service entry point."""
    # Check if we should run in persistent service mode - read directly from environment
    import os

    run_mode = os.environ.get("RUN_MODE", "oneshot").lower()

    if run_mode == "service":
        # Run as persistent service
        service = PersistentMatchListChangeDetectorService()
        service.run()
    else:
        # Run original oneshot mode
        from match_list_change_detector import main as original_main

        original_main()


if __name__ == "__main__":
    main()
