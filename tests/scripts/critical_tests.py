import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger()


def run_critical_tests():
    # run only critical tests (should always happen)
    project_root = Path(__file__).parent.parent

    cmd = [
        sys.executable, "-m", "pytest",
        "critical/",
        "-v",
        "-s",
        "--tb=long",
        "--maxfail=1",
        "-x",
        "--durations=10"
    ]

    log.info("Running critical tests...")
    log.info("These tests prevent game corruption and must always pass.")
    log.info("=" * 60)

    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        log.info("All critical tests passed!")
        return True
    else:
        log.critical("CRITICAL TESTS FAILED!")
        log.critical("DO NOT COMMIT until these are fixed.")
        return False


if __name__ == "__main__":
    success = run_critical_tests()
    sys.exit(0 if success else 1)
