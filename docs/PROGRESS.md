# TerraMorpheus Project Progress

This document tracks the development progress of the TerraMorpheus project, an AI assistant for petrophysicists using the `welly` library and connected via MCP to an LLM.

## Project Goal

The primary goal is to develop a Model Context Protocol (MCP) server that exposes the functionality of the `welly` library. This server is intended to be potentially suitable for contribution back to the main `welly` project, while also serving as the foundation for the TerraMorpheus petrophysical assistant.

## Development Plan

**Phase 1: Setup, Scaffolding, Tool Definition**

1.  [ ] **Environment Setup:**
    *   [ ] Install Python and `pip`.
    *   [ ] Install `welly[dev]`.
    *   [ ] Install MCP Python SDK (`pip install mcp`).
    *   [ ] Set up a virtual environment.
2.  [ ] **MCP Server Scaffolding:**
    *   [ ] Create `terramorpheus_server/` directory.
    *   [ ] Initialize basic MCP server application (Python SDK).
    *   [ ] Design basic state management approach (e.g., in-memory dict for loaded wells/projects).
    *   [ ] Implement a simple "ping" or "hello" tool for verification.
3.  [ ] **Expose Core Welly Functions as MCP Tools (Initial Set):**
    *   [ ] `load_las_well(path)`:
        *   [ ] Implement tool calling `Well.from_las`.
        *   [ ] Define input (path) / output (UWI, basic header info, success status) schema.
        *   [ ] Update server state with loaded `Well` object (using UWI as key).
    *   [ ] `get_well_curves(well_uwi)`:
        *   [ ] Implement tool retrieving `well.data.keys()` from state.
        *   [ ] Define input (UWI) / output (list of mnemonics) schema.
    *   [ ] `get_curve_stats(well_uwi, curve_mnemonic)`:
        *   [ ] Implement tool calling `well.get_curve(mnemonic).get_stats()`.
        *   [ ] Define input (UWI, mnemonic) / output (stats dict/JSON) schema.
    *   [ ] `plot_curve_track(well_uwi, curve_mnemonic, output_path)`:
        *   [ ] Implement tool calling `well.get_curve(mnemonic).plot()`.
        *   [ ] Handle saving plot to `output_path` (e.g., PNG). Consider temporary file handling.
        *   [ ] Define input (UWI, mnemonic, output_path) / output (file path, success status) schema.
    *   [ ] Focus on robust error handling for file loading and missing data.
4.  [ ] **Basic Client/Testing:**
    *   [ ] Create/use a simple MCP client (CLI).
    *   [ ] Test calling each defined `welly` tool via MCP.
    *   [ ] Verify state management (loading a well makes it available to other tools).
    *   [ ] Implement basic unit tests (`pytest`) for MCP tools (mocking `welly` objects might be necessary).

**Phase 2: LLM Integration and Workflow Orchestration**

1.  [ ] **LLM API Setup:**
    *   [ ] Choose LLM provider (Anthropic, Google, OpenAI, etc.).
    *   [ ] Set up API access and install client libraries.
2.  [ ] **Core Assistant Logic (Orchestrator):**
    *   [ ] Design the main application loop (CLI or simple web service using Flask/FastAPI).
    *   [ ] Implement user input handling.
    *   [ ] Implement LLM communication:
        *   [ ] Format prompts including user request and available MCP tool descriptions (schemas).
        *   [ ] Parse LLM response to identify requested tool calls and arguments.
    *   [ ] Implement MCP client logic within the orchestrator to call the MCP server tools.
    *   [ ] Handle results from MCP server (e.g., display stats, show plot image path).
    *   [ ] Manage conversation history/context for the LLM.
    *   [ ] Implement basic handling for multi-step tasks (e.g., "load well A", then "plot GR for it").
3.  [ ] **Refine and Expand MCP Tools:**
    *   [ ] `load_project_from_las(path_pattern)`: Implement project loading. Refine state management for projects vs wells.
    *   [ ] Add tools for basic curve math (`curve.Curve` operations like add, subtract, multiply).
    *   [ ] Add tools for `welly.quality` checks (e.g., `run_quality_tests(well_uwi, test_set_name)`).
    *   [ ] Add tools for resampling/basis unification (`well.unify_basis`, `curve.to_basis`).
    *   [ ] Improve plot tool(s): more options (multiple tracks via `well.plot`), better output handling (return image data directly?).
    *   [ ] Handle non-curve data (e.g., `Striplog` if needed).
4.  [ ] **Testing:**
    *   [ ] Develop integration tests for the full workflow (User -> Orchestrator -> LLM -> MCP -> Welly -> Orchestrator -> User).
    *   [ ] Test handling of common petrophysical requests.

**Phase 3: Enhancements and Deployment**

1.  [ ] **Advanced Features:**
    *   [ ] Implement more robust state management (persistent? session-based?).
    *   [ ] Improve prompt "engineering" for complex workflows and context understanding.
    *   [ ] Explore MCP Resources for accessing metadata without full object loading.
    *   [ ] Add comprehensive error handling, logging (as per custom instructions).
    *   [ ] Implement user feedback mechanisms (progress indicators).
    *   [ ] (Optional) Develop a web UI.
2.  [ ] **Testing and Documentation:**
    *   [ ] Increase test coverage (unit and integration).
    *   [ ] Write comprehensive user/developer documentation.
    *   [ ] Keep this `PROGRESS.md` updated.
3.  [ ] **Deployment Preparation:**
    *   [ ] Containerize MCP server and orchestrator application (Docker).
    *   [ ] Prepare deployment configurations (e.g., Docker Compose).
4.  [ ] **Digital Ocean Deployment:**
    *   [ ] Choose DO service (Droplet, App Platform).
    *   [ ] Deploy container(s).
    *   [ ] Configure networking, security (firewalls, HTTPS?).
    *   [ ] Set up monitoring/logging on DO.

**Phase 4: Contribution (Optional)**

1.  [ ] **Identify Contribution:** Determine changes/additions made to `welly` core.
2.  [ ] **Follow `welly` Guidelines:** If contributing to `welly`, adhere to `CONTRIBUTING.md`.
3.  [ ] **Share TerraMorpheus:** If open-sourcing the assistant/MCP server, create its own repository and license.

## Log

*   **2025 April 28th:** Initial simple and short plan created.