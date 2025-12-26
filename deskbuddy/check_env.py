import sys
try:
    import PySide6
    import yaml
    import apscheduler
    import flask
    with open("env_check.txt", "w") as f:
        f.write("SUCCESS")
except ImportError as e:
    with open("env_check.txt", "w") as f:
        f.write(f"ERROR: {e}")
except Exception as e:
    with open("env_check.txt", "w") as f:
        f.write(f"EXCEPTION: {e}")

