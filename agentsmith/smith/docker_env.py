"""SWE-bench container life cycle (docker CLI).

The container is started with ``--network none`` by default: the agent can
only explore the repository that is inside the image, never the internet
(no PR / issue lookups possible). It is ALWAYS removed on exit.
"""
from __future__ import annotations

import logging
import subprocess
import uuid
from typing import Optional

log = logging.getLogger("smith.docker")


class DockerError(RuntimeError):
    pass


def _docker(*args: str, timeout: float = 120, check: bool = True) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise DockerError("docker CLI not found") from e
    except subprocess.TimeoutExpired as e:
        raise DockerError(f"docker {args[0]} timed out") from e
    if check and r.returncode != 0:
        raise DockerError(f"docker {' '.join(args[:2])} failed: {r.stderr.strip()[-500:]}")
    return r


class SWEContainer:
    def __init__(self, image: str, instance_id: str, network: bool = False, pull_timeout: float = 1800):
        self.image = image
        self.name = f"smith-{instance_id.lower().replace('__', '-')[:40]}-{uuid.uuid4().hex[:6]}"
        self.network = network
        self.pull_timeout = pull_timeout
        self.container_id: Optional[str] = None

    def ensure_image(self) -> None:
        if _docker("image", "inspect", self.image, check=False, timeout=60).returncode == 0:
            return
        log.info("pulling %s ...", self.image)
        _docker("pull", self.image, timeout=self.pull_timeout)

    def start(self) -> str:
        self.ensure_image()
        args = ["run", "-d", "--name", self.name, "--label", "agent_smith=1"]
        if not self.network:
            args += ["--network", "none"]
        args += [self.image, "tail", "-f", "/dev/null"]
        self.container_id = _docker(*args, timeout=120).stdout.strip()
        log.info("container %s started (%s)", self.name, self.container_id[:12])
        return self.container_id

    def cleanup(self) -> None:
        if not self.container_id:
            return
        try:
            _docker("rm", "-f", self.container_id, timeout=60, check=False)
            log.info("container %s removed", self.name)
        except DockerError as e:
            log.error("container cleanup failed: %s", e)
        self.container_id = None

    def __enter__(self) -> "SWEContainer":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()
