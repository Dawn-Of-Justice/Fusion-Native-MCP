# Testing

Use the project virtual environment: activate it with `./.venv/Scripts/Activate.ps1`, or replace `python` below with `./.venv/Scripts/python.exe`. Run commands from the repository root.


From the project directory, using the environment containing test dependencies:

```powershell
python -m pytest tests -q
python tests/live_smoke.py --output validation/read-only
```

The following explicitly create demo documents and modify them:

```powershell
python tests/live_smoke.py --model --output validation/new-run
python tests/live_breadth.py
```

The breadth test expects the sample plate to be active with no prior CAM setup and writes `validation/breadth-report.json`. Use a new output directory for each modeling run to avoid overwriting STEP exports. Live tests do not run as part of pytest.

Additional opt-in v0.2 tests (each creates its own test document):

```powershell
python tests/live_features.py validation/my-feature-run
python tests/live_feature_kinds.py validation/my-kinds-run
python tests/live_existing.py validation/my-existing-run
python tests/live_reopen.py validation/my-existing-run/existing-report.json validation/my-reopen-run
```

The reopen test exports and closes **only its known generated fixture**, then reimports and edits that archive. Successful feature-suite steps are checkpointed for development recovery; use a fresh run directory for a clean acceptance run. Uncertain writes are never automatically acknowledged by that suite.


## CI scope

GitHub Actions runs the offline suite and builds wheel/source packages on Windows with Python 3.11 and 3.12. It does not launch Fusion or validate live geometry. CI execution on GitHub is separate from local test results.

Action usage follows the official [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) documentation.

Use synthetic fixtures for live tests. Keep raw reports, exported CAD, screenshots, and journals in the ignored `validation/` directory. Summarize public acceptance results without document identifiers or local paths in [validation.md](validation.md).
