import subprocess
import sys
from pathlib import Path


def run_critical_tests():
    # run only critical tests (should always happen)
    project_root = Path(__file__).parent.parent

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/critical/",
        "-v",
        "--tb=short",
        "--maxfail=1",
        "-x",
        "--durations=10"
    ]

    print("Running critical tests...")
    print("These tests prevent game corruption and must always pass.")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        print("All critical tests passed!")
        return True
    else:
        print("CRITICAL TESTS FAILED!")
        print("DO NOT COMMIT until these are fixed.")
        return False


if __name__ == "__main__":
    success = run_critical_tests()
    sys.exit(0 if success else 1)