# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that connects Claude with the Intervals.icu API. It enables Claude to retrieve and analyze athlete training data including activities, events, workouts, and wellness metrics.

## Key Commands

### Setup and Dependencies
- **Install dependencies**: `uv sync --all-extras`
- **Create virtual environment**: `uv venv --python 3.12`
- **Activate environment**: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)

### Development and Testing
- **Run server locally**: `mcp run src/intervals_mcp_server/server.py`
- **Run tests**: `pytest` or `pytest -v` (verbose)
- **Run specific test**: `pytest tests/test_server.py`
- **Linting**: `ruff .` or `ruff check .`
- **Type checking**: `mypy src tests`
- **Format code**: `ruff format .`

### Production
- **Install for Claude Desktop**: `mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env`

## Architecture

### Core Structure

**Main Server**: `src/intervals_mcp_server/server.py`
- Contains all MCP tool implementations (decorated with `@mcp.tool()`)
- Manages shared `httpx.AsyncClient` via lifespan context manager
- All API communication flows through `make_intervals_request()` function
- Comprehensive error handling with user-friendly HTTP status messages

**Utilities**: `src/intervals_mcp_server/utils/`
- `formatting.py`: Data formatting utilities using the `Section` context manager pattern
- `types.py`: Type definitions (e.g., `WorkoutDoc`)

**Tests**: `tests/`
- Organized by functionality: `test_server.py`, `test_formatting.py`, `test_make_intervals_request.py`
- `sample_data.py`: Mock data for testing
- Uses pytest-asyncio for async testing, pytest-mock for HTTP mocking

### API Communication Pattern

All Intervals.icu API calls follow this pattern:

1. **Authentication**: HTTP Basic Auth with username "API_KEY" and API key as password
2. **Single Request Function**: `make_intervals_request(url, api_key, params, method, data)`
   - Returns `dict[str, Any] | list[dict[str, Any]]`
   - Handles errors by returning `{"error": True, "status_code": int, "message": str}`
3. **URL Format**: Relative paths like `/athlete/{id}/activities`
4. **Timeout**: 30 seconds for all requests

### MCP Tool Pattern

When implementing MCP tools:
1. Validate parameters and provide defaults
2. Use provided `api_key`/`athlete_id` or fall back to global constants
3. Call `make_intervals_request()` with appropriate parameters
4. Check for `{"error": True}` in response and return formatted error message
5. Use formatting utilities from `utils/formatting.py` for output
6. Support both numeric and i-prefixed athlete IDs (pattern: `r"i?\d+"`)
7. For binary data (like ZWO files), use base64 decoding to extract file content

### Environment Variables

**Required** (validated on startup):
- `API_KEY`: Intervals.icu API key (cannot be empty)
- `ATHLETE_ID`: Must match pattern `r"i?\d+"` (digits or i-prefixed digits)

**Optional**:
- `INTERVALS_API_BASE_URL`: Defaults to `https://intervals.icu/api/v1`
- `LOG_LEVEL`: Defaults to INFO

## Code Quality Standards

### Before Committing
All three checks must pass:
```bash
ruff .        # Linting
mypy src tests  # Type checking
pytest         # Unit tests
```

### Python Conventions
- **Type hints**: All function signatures must have type hints
- **Async patterns**: All MCP tools are async, use `async/await` consistently
- **Error handling**: Catch specific exceptions (`httpx.HTTPStatusError`, `httpx.RequestError`)
- **Logging**: Use lazy `%` formatting: `logger.debug("val=%s", val)`
- **No global variables**: Except for validated constants (`API_KEY`, `ATHLETE_ID`)

### Testing Patterns
- Use `@pytest.mark.asyncio` for async tests
- Mock HTTP requests with pytest-mock (`MockerFixture`)
- Test both success and error paths
- Use realistic test data from `tests/sample_data.py`

## Formatting Utilities

The `Section` context manager in `utils/formatting.py` provides conditional formatting:
- Only adds headings if content is actually written
- Skips lines when values are None
- Manages indentation automatically
- Use for all formatted output to maintain consistency

## Workout Management

When working with workouts via `add_or_update_event()`:
- Steps use `WorkoutDoc` type with nested structure
- Support for intervals, ramps, repeats, power/HR/pace zones
- Ramps must use `"ramp": True` property (not `"ramp": "True"` - this is a common error)
- Feel values are on scale 1-5 where **lower is better**

## Speed/Pace Formatting

The `speed_formatter()` utility handles sport-specific speed display:
- **Run**: min/km pace
- **Ride**: km/h speed
- **Swim**: min/100m pace
- **Default**: m/s

Always use the activity type to get the appropriate formatter.

## Downloading Workout Files

The `download_workout_zwo()` tool retrieves workout files in Zwift format:
- Uses query parameters `ext=zwo` and `resolve=true` to request formatted output
- API returns `workout_file_base64` field containing base64-encoded file content
- Decode using `base64.b64decode()` and convert to UTF-8 string
- Works only for workout events (not races or other event types)

## Common Patterns

### Adding a New MCP Tool
1. Create async function decorated with `@mcp.tool()`
2. Add comprehensive docstring (required by FastMCP)
3. Add type hints for all parameters
4. Use `make_intervals_request()` for API calls
5. Add formatting utilities to `utils/formatting.py` if needed
6. Write unit tests in appropriate test file

### Dependency Changes
1. Edit `pyproject.toml`
2. Run `uv lock` (or `uv sync`)
3. Commit both `pyproject.toml` and `uv.lock` together
4. CI runs `uv lock --check` to ensure sync

### PR Requirements
- Concise commit messages
- PR title format: `[intervals-mcp-server] <brief description>`
- Document manual testing steps
- Confirm ruff, mypy, and pytest all pass
