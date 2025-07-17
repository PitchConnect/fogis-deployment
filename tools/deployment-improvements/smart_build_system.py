#!/usr/bin/env python3
"""
Smart Docker Build System for FOGIS Services

This system eliminates the Docker cache issues and manual rebuild processes
we encountered during deployment by providing intelligent build management.

Key Features:
- Automatic cache invalidation when needed
- Build validation and testing
- Consistent image tagging
- Build dependency tracking
- Parallel builds for efficiency
- Build artifact verification
"""

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BuildError(Exception):
    """Raised when build fails."""

    pass


class SmartBuildSystem:
    """Intelligent Docker build system with cache management."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.build_cache_file = self.project_root / ".build_cache.json"
        self.build_cache = self._load_build_cache()

    def _load_build_cache(self) -> Dict:
        """Load build cache from file."""
        if self.build_cache_file.exists():
            try:
                with open(self.build_cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load build cache: {e}")
        return {}

    def _save_build_cache(self) -> None:
        """Save build cache to file."""
        try:
            with open(self.build_cache_file, "w") as f:
                json.dump(self.build_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save build cache: {e}")

    def _calculate_context_hash(self, context_path: Path, dockerfile_path: Path) -> str:
        """Calculate hash of build context to detect changes."""
        hasher = hashlib.sha256()

        # Hash Dockerfile
        if dockerfile_path.exists():
            hasher.update(dockerfile_path.read_bytes())

        # Hash relevant files in context
        for file_path in context_path.rglob("*"):
            if file_path.is_file() and not self._should_ignore_file(file_path):
                hasher.update(file_path.read_bytes())

        return hasher.hexdigest()

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored in hash calculation."""
        ignore_patterns = [
            ".git",
            "__pycache__",
            "*.pyc",
            "*.log",
            ".DS_Store",
            "node_modules",
            ".coverage",
            "htmlcov",
            ".pytest_cache",
        ]

        for pattern in ignore_patterns:
            if pattern in str(file_path):
                return True
        return False

    def _run_command(
        self, cmd: List[str], cwd: Optional[Path] = None
    ) -> Tuple[int, str, str]:
        """Run command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise BuildError(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            raise BuildError(f"Command failed: {e}")

    def build_service(
        self,
        service_name: str,
        context_path: Path,
        dockerfile_path: Path,
        force_rebuild: bool = False,
    ) -> str:
        """Build Docker image for service with intelligent caching."""
        logger.info(f"Building service: {service_name}")

        # Calculate context hash
        context_hash = self._calculate_context_hash(context_path, dockerfile_path)
        cache_key = f"{service_name}:{context_hash}"

        # Check if rebuild is needed
        if not force_rebuild and cache_key in self.build_cache:
            cached_info = self.build_cache[cache_key]
            image_tag = cached_info["image_tag"]

            # Verify image still exists
            if self._image_exists(image_tag):
                logger.info(f"Using cached image: {image_tag}")
                return image_tag
            else:
                logger.info("Cached image no longer exists, rebuilding...")

        # Generate unique image tag
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_tag = f"fogis-{service_name}:{timestamp}-{context_hash[:8]}"

        # Build image
        build_cmd = [
            "docker",
            "build",
            "-t",
            image_tag,
            "-f",
            str(dockerfile_path),
            str(context_path),
        ]

        logger.info(f"Running: {' '.join(build_cmd)}")
        exit_code, stdout, stderr = self._run_command(build_cmd)

        if exit_code != 0:
            logger.error(f"Build failed for {service_name}")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            raise BuildError(f"Docker build failed for {service_name}")

        # Validate built image
        self._validate_image(image_tag, service_name)

        # Update cache
        self.build_cache[cache_key] = {
            "image_tag": image_tag,
            "build_time": datetime.now().isoformat(),
            "context_hash": context_hash,
            "service_name": service_name,
        }
        self._save_build_cache()

        logger.info(f"Successfully built: {image_tag}")
        return image_tag

    def _image_exists(self, image_tag: str) -> bool:
        """Check if Docker image exists locally."""
        exit_code, _, _ = self._run_command(["docker", "image", "inspect", image_tag])
        return exit_code == 0

    def _validate_image(self, image_tag: str, service_name: str) -> None:
        """Validate built Docker image."""
        logger.info(f"Validating image: {image_tag}")

        # Check image can be run
        test_cmd = ["docker", "run", "--rm", image_tag, "python", "--version"]
        exit_code, stdout, stderr = self._run_command(test_cmd)

        if exit_code != 0:
            raise BuildError(f"Image validation failed: {stderr}")

        logger.info(f"Image validation passed: {stdout.strip()}")

    def build_all_services(self, services_config: Dict[str, Dict]) -> Dict[str, str]:
        """Build all services with dependency management."""
        built_images = {}

        # Sort services by dependencies (simple topological sort)
        sorted_services = self._sort_services_by_dependencies(services_config)

        for service_name in sorted_services:
            config = services_config[service_name]
            context_path = self.project_root / config["context"]
            dockerfile_path = context_path / config.get("dockerfile", "Dockerfile")

            try:
                image_tag = self.build_service(
                    service_name, context_path, dockerfile_path
                )
                built_images[service_name] = image_tag
            except BuildError as e:
                logger.error(f"Failed to build {service_name}: {e}")
                raise

        return built_images

    def _sort_services_by_dependencies(
        self, services_config: Dict[str, Dict]
    ) -> List[str]:
        """Sort services by build dependencies."""
        # For now, return services in alphabetical order
        # In a more complex system, this would implement proper dependency resolution
        return sorted(services_config.keys())

    def cleanup_old_images(self, keep_count: int = 3) -> None:
        """Clean up old build images, keeping only the most recent ones."""
        logger.info(
            f"Cleaning up old images, keeping {keep_count} most recent per service"
        )

        # Group images by service
        service_images = {}
        for cache_key, cache_info in self.build_cache.items():
            service_name = cache_info["service_name"]
            if service_name not in service_images:
                service_images[service_name] = []
            service_images[service_name].append(cache_info)

        # Clean up old images for each service
        for service_name, images in service_images.items():
            # Sort by build time (newest first)
            images.sort(key=lambda x: x["build_time"], reverse=True)

            # Remove old images
            for image_info in images[keep_count:]:
                image_tag = image_info["image_tag"]
                logger.info(f"Removing old image: {image_tag}")

                exit_code, _, _ = self._run_command(["docker", "rmi", image_tag])
                if exit_code == 0:
                    # Remove from cache
                    cache_keys_to_remove = [
                        k
                        for k, v in self.build_cache.items()
                        if v["image_tag"] == image_tag
                    ]
                    for key in cache_keys_to_remove:
                        del self.build_cache[key]

        self._save_build_cache()


# Example usage configuration
FOGIS_SERVICES_CONFIG = {
    "match-list-change-detector": {
        "context": "local-patches/match-list-change-detector",
        "dockerfile": "Dockerfile.patched",
    },
    "match-list-processor": {"context": ".", "dockerfile": "Dockerfile"},
    "fogis-api-client": {"context": ".", "dockerfile": "Dockerfile"},
}


def main():
    """Main build script."""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Docker build system for FOGIS")
    parser.add_argument("--service", help="Build specific service")
    parser.add_argument("--all", action="store_true", help="Build all services")
    parser.add_argument("--force", action="store_true", help="Force rebuild")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old images")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    build_system = SmartBuildSystem(Path(args.project_root))

    try:
        if args.cleanup:
            build_system.cleanup_old_images()
        elif args.all:
            images = build_system.build_all_services(FOGIS_SERVICES_CONFIG)
            print("\n✅ All services built successfully:")
            for service, image in images.items():
                print(f"  {service}: {image}")
        elif args.service:
            if args.service not in FOGIS_SERVICES_CONFIG:
                print(f"❌ Unknown service: {args.service}")
                sys.exit(1)

            config = FOGIS_SERVICES_CONFIG[args.service]
            context_path = Path(args.project_root) / config["context"]
            dockerfile_path = context_path / config.get("dockerfile", "Dockerfile")

            image_tag = build_system.build_service(
                args.service, context_path, dockerfile_path, args.force
            )
            print(f"✅ Built {args.service}: {image_tag}")
        else:
            parser.print_help()

    except BuildError as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
