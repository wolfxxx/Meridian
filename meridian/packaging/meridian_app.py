"""Entry point for the packaged Meridian app (Meridian.exe)."""

import multiprocessing

from meridian.app.launcher import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
