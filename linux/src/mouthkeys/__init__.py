"""MouthKeys Linux. No telemetry, cloud transcription, or automatic updates."""

import os

# Set before importing any model/download libraries, including from the CLI.
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"
