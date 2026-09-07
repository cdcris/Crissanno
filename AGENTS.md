# Repository Guidelines

## Project Structure & Module Organization

ServeScan is a Python/Tkinter camera application organized by feature. `main.py` is the executable entry point, while `app.py` connects the UI and feature controllers. Keep camera lifecycle and recording code in `capture/`, object detection in `detection/`, marker conversion and persistence in `marker/`, uploaded-video playback in `upload/`, reusable error handling in `shared/`, and widgets and styling in `ui/`. Automated tests live in `tests/` and mirror these modules with files such as `test_capture.py`. Runtime output belongs in `captures/` and `logs/`; sample videos are in `vid/`. The bundled YOLO weights and NCNN files are model assets, not application source.

## Build, Test, and Development Commands

This project has no separate build step. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

The first three commands create a local environment and install dependencies. `python main.py` starts the GUI; the final command runs the complete test suite. Run one module with `python -m unittest -v tests.test_capture`. Use `python3` instead of `python` where required.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation. Use `snake_case` for modules, functions, methods, and variables; `PascalCase` for classes; and uppercase names for constants in `config.py`. Preserve the existing type hints and short responsibility-focused docstrings. Keep the architecture direction `UI -> controller -> hardware/storage`; hardware and storage classes must not manipulate Tkinter widgets. No formatter or linter is configured, so keep imports grouped and changes consistent with nearby code.

## Testing Guidelines

Tests use the standard-library `unittest` framework and `unittest.mock`. Name files `test_<feature>.py`, classes `<Subject>Tests`, and methods `test_<behavior>`. Prefer fake cameras, frames, and video writers so tests remain deterministic and do not require hardware. Add regression tests for bug fixes. There is currently no enforced coverage threshold.

## Commit & Pull Request Guidelines

Git history is not available in this repository snapshot, so no established commit convention can be verified. Use short, imperative subjects such as `Fix upload playback timing`, and keep each commit focused. Pull requests should explain the user-visible change, list test commands and results, link relevant issues, and include screenshots for UI changes. Do not commit generated captures, logs, cache files, local virtual environments, or incidental changes to `marker_position.json`.
