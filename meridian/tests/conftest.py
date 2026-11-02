"""Keep tests away from the user's real settings and saved work."""

import os
import tempfile

os.environ["MERIDIAN_HOME"] = tempfile.mkdtemp(prefix="meridian-tests-")
