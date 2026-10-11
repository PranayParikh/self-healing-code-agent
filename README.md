# Self-Healing Code Sandbox

A system that fixes broken Python code by running tests in an isolated Docker container, sending the failure to an LLM, checking the patch, and retrying. It was built in phases, each one documented in its own folder.

| Phase | What it does | Result |
|---|---|---|
| [phase1](phase1/) | Heals one file at a time in a Docker sandbox (network disabled, memory capped), with a validity check before any patch is written | 5 test cases, all fixed; includes a real bug found and fixed (markdown fences breaking the validity check) |
| [phase2/2.1_networkx](phase2/2.1_networkx/) | Parses a multi-file repo with `ast` and builds a dependency graph with NetworkX | Correct graph and topological order on a 3-file toy repo |
| [phase3](phase3/) | LangGraph state machine: plans files in dependency order, heals each against its own test, passes dependency source to the Coder, then runs a final whole-repo check | Heals multiple broken files in one run; failures that led to design changes are documented |
| [phase4](phase4/) | LangSmith tracing, an automated bug catalog, and a controlled experiment | Removing the dependency source from the prompt dropped Pass@1 from 7/7 to 4/7, three runs each |

## The main finding

Passing tests did not mean a fix was right. Without access to the files it imports, the Coder invented attribute names that exist nowhere in the repo, and retrying did not help. Giving it the dependency source fixed this. The details and limits are in `phase4/README.md`.

## Not built

Phase 2.2 (Neo4j and hybrid embedding search) was deferred on purpose. In-memory NetworkX answers every question a three-file repo asks.

## Run it

```bash
python3 -m venv venv && source venv/bin/activate
pip install docker openai langgraph networkx pytest
cd phase1 && docker build -t self-healing-sandbox . && cd ..
export OPENAI_API_KEY=your_key
cd phase3 && python3 orchestrator.py
```

Docker Desktop must be running. Phase 4 also needs `LANGSMITH_TRACING` and `LANGSMITH_API_KEY` for tracing.

## Stack

Python, Docker SDK, pytest, `ast`, NetworkX, LangGraph, LangSmith, OpenAI API.