# Repository Instructions

## Preferred Commands

- Initial setup: `./scripts/bootstrap.sh`
- Run the web app: `./scripts/dev.sh`
- Run tests: `./scripts/test.sh`
- Run a local smoke check: `./scripts/smoke.sh`

## Notes

- The active application is the FastAPI-based v2 app under `app/`.
- The old script-based implementation is archived under `legacy/` and should not be extended.
- If a task changes the crawler or image pipeline, run `./scripts/test.sh` before finishing.
- For end-of-session cleanup in this repo, prefer the global skill `book-crawling-code-cleanup` at `/Users/mark/.codex/skills/book-crawling-code-cleanup/SKILL.md`.
