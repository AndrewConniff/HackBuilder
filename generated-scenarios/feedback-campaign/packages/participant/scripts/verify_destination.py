"""Destination guard only; no account or agent installation in starter."""
from cloud_io import verify_target
if __name__ == "__main__":
    verify_target()
    print("Explicit isolated destination verified; agent remains learner-built.")
