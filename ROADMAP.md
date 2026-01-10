# local_llm Roadmap

## Phase 0: Architectural Refactor

- [X] Refactor PowerShell scripts to a Portable Windows Application (OSS Only)
- [ ] Design for multi-stage Docker build to produce a minimal, self-contained final image. (Deferred to v0.2.0)

## Phase 1: Project Setup

- [X] Recreate missing directory structure (`scripts`, `recipes`).
- [X] Create placeholder PowerShell scripts (`setup.ps1`, `start.ps1`, `start_llm.ps1`, `stop_llm.ps1`, `start_miner.ps1`, `stop_miner.ps1`, `backup.ps1`).
- [X] Set up Python virtual environment and install dependencies.

## Phase 2: Core Functionality (LLM & Mining)

- [X] Implement actual LLM starting/stopping logic (simulated for now).
- [X] Integrate with local LLM APIs/libraries (simulated for now).
- [X] Implement actual miner starting/stopping logic.
- [X] Refactor to support multiple mining processes.
- [X] Enhance configuration management (CLI based).
- [X] Develop dashboard interface for monitoring system resources (GPU, CPU, RAM).

## Phase 3: Recipes & Extensibility

- [X] Develop initial LLM recipes in the `recipes` directory (boilerplate code, documentation, etc.).
- [X] Implement a mechanism to easily add and manage new recipes.

## Phase 4: Refinement & Distribution

- [X] Improve error handling and logging in start.ps1.
- [X] Improve error handling and logging in other scripts.
- [X] Implement robust temporary file cleanup.
- [X] Fix terminal scaling issue in main menu (start.ps1)

## Future Work

- [ ] Plan and implement a rescan of all repositories for compliance with LAW 33 (OSS Sovereignty).
