# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

News Curator is an AI-powered news curation system that researches topics, crosses references, identifies contradictions, verifies facts, and produces structured journalistic articles. Built with the Agno framework for multi-agent orchestration.

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install/ sync dependencies
uv sync

# Run specific agent versions
uv run N0_news_curator_agent.py  # Single agent foundation
uv run N1_news_curator_agent.py # Multi-agent iteration 1
uv run N2_news_curator_agent.py # Multi-agent iteration 2
uv run N3_news_curator_agent.py # Multi-agent iteration 3 (full)

# Run Streamlit frontend
uv run streamlit run app.py

# API server (FastAPI)
uv run uvicorn app:app --reload
```

## Environment Variables

Required in `.env`:
- `ZAI_API_KEY` - API key for LLM inference
- `ZAI_BASE_URL` - Base URL for API endpoint
- `ZAI_MODEL` - Model name (e.g., `glm-4.7`)

## Architecture

### Agent Structure (N0-N3 progression)
- `N0_news_curator_agent.py` - Single monolithic agent (foundation)
- `N1_news_curator_agent.py` - Multi-agent iteration with research, fact-checking, and writing as separate agents
- `N2_news_curator_agent.py` - Enhanced multi-agent with source validation
- `N3_news_curator_agent.py` - Full production multi-agent system

### Skills (Agent Tools)
- `skills/pesquisa-noticias/` - Real-time news search using DuckDuckGo
- `skills/apuracao-fontes/` - Source verification and cross-referencing
- `skills/verificacao-factual/` - Fact-checking capabilities
- `skills/redacao-jornalistica/` - Journalistic writing and formatting
- `skills/posicionamento-fake-news/` - Fake news detection and positioning

### Frontend
- `app.py` - Streamlit web interface for N3 agent

### Core Services
- `news_curator_service.py` - Main service orchestration
- `N3_news_curator_agent.py` - Agent definition and team configuration

## Development Rules

All code changes must follow these practices:

### Planning Protocol
Before any implementation, present a detailed execution plan:
- Objective and current analysis
- Dependency analysis identifying affected components
- Step-by-step implementation
- Potential risks and mitigation
- List of files to be modified
- Success criteria and testing strategy

**Wait for explicit user approval before executing.**

### Anchor Comments
Use structured comments for complex code:
```python
# AIDEV-NOTE: [purpose/context]
# AIDEV-TODO: [pending task]
# AIDEV-QUESTION: [clarification needed]
# AIDEV-PERF: [performance consideration]
# AIDEV-SECURITY: [security aspect]
```

### Sacred Files (Never modify without explicit permission)
- `.env` - Environment variables
- `migrations/*` - Database migrations
- `docker-compose.prod.yml`, `k8s/*.yaml` - Production configs
- `.github/workflows/*` - CI/CD pipelines

### Testing Requirements
- Unit tests for business logic
- Integration tests for API/external connections
- E2E tests for critical user flows

### Error Handling
Use standardized error hierarchy:
```python
class ApplicationError(Exception):
    """Base application error"""

class ValidationError(ApplicationError):  # 4xx - client error
    """Input validation error"""

class SystemError(ApplicationError):      # 5xx - internal error
    """Internal system error"""
```

## Code Style

- Use Python 3.12.11
- Follow existing naming conventions in the codebase
- Keep functions focused on single responsibility
- Add explanatory comments for non-obvious logic
- Use type hints where beneficial

## Git Conventions

Commits should follow this format:
```
feat: implement feature name [AI]

# Description of what was done
# Human validation notes
```
