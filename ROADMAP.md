# local_llm Roadmap

## Phase 0: Architectural Refactor

- [ ] Refactor PowerShell scripts to a Portable Windows Application (OSS Only)
- [ ] Design for multi-stage Docker build to produce a minimal, self-contained final image.

## Phase 1: Project Setup

- [X] Recreate missing directory structure (`scripts`, `recipes`).
- [X] Create placeholder PowerShell scripts (`setup.ps1`, `start.ps1`, `start_llm.ps1`, `stop_llm.ps1`, `start_miner.ps1`, `stop_miner.ps1`, `backup.ps1`).
- [X] Set up Python virtual environment and install dependencies.

## Phase 2: Core Functionality (LLM & Mining)

- [ ] Implement actual LLM starting/stopping logic in `start_llm.ps1` and `stop_llm.ps1` (currently simulated).
- [ ] Integrate with local LLM APIs/libraries.
- [ ] Implement actual miner starting/stopping logic in `start_miner.ps1` and `stop_miner.ps1` (currently simulated).
- [ ] Enhance configuration management (e.g., UI for `config.json`).
- [ ] Develop dashboard interface for monitoring system resources (GPU, CPU, RAM).

## Phase 3: Recipes & Extensibility

- [ ] Develop initial LLM recipes in the `recipes` directory (boilerplate code, documentation, etc.).
- [ ] Implement a mechanism to easily add and manage new recipes.

## Phase 4: Refinement & Distribution

- [ ] Improve error handling and logging across all scripts.
- [ ] Implement robust temporary file cleanup.

## Future Work

- [ ] Plan and implement a rescan of all repositories for compliance with LAW 33 (OSS Sovereignty).
