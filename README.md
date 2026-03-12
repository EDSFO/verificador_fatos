# News Curator (Curador de NotÃ­cias)

**NÃ­vel:** 1 (BÃ¡sico / IntrodutÃ³rio)  
**Projeto:** Asimov Academy

## Sobre o Projeto

Este projeto consiste na construÃ§Ã£o de um sistema de Agentes de InteligÃªncia Artificial capaz de fazer a **curadoria completa de notÃ­cias**. VocÃª informa um tema e o sistema pesquisa o cenÃ¡rio atual, cruza fontes diferentes, identifica informaÃ§Ãµes convergentes e contraditÃ³rias, verifica os fatos e por fim, entrega uma matÃ©ria jornalÃ­stica final estruturada, com devidas referÃªncias e rastreabilidade total.

O projeto foi criado primeiramente como uma ferramenta interna para monitoramento de notÃ­cias relevantes sobre IA e, agora, Ã© utilizado para ensinar os fundamentos arquiteturais de Agentes de IA na prÃ¡tica.

## Objetivos de Aprendizado

Ao final do desenvolvimento e acompanhamento deste projeto, vocÃª terÃ¡ desenvolvido um repertÃ³rio valioso sobre construÃ§Ã£o operacional de IAs autÃ´nomas, e compreenderÃ¡ conceitos chave do framework **Agno**:

- **Agent Skills**: Como fornecer ferramentas (como buscar arquivos ou pesquisar na web) que capacitam a aÃ§Ã£o do seu Agente.
- **Architectures Multi-Agents**: A evoluÃ§Ã£o de um agente individual (modo _standalone_) para equipes de Agentes (_Teams_) e **Workflows**.
- **ApuraÃ§Ã£o Automatizada**: EstratÃ©gias e Prompts para fazer cruzamento de fontes reais.

_Nota: Por se tratar de um projeto de NÃ­vel 1, o foco Ã© na arquitetura base e na exploraÃ§Ã£o da engine dos Agentes. Recursos complementares de Deploy, RAG e Layout ficarÃ£o para os nÃ­veis subsequentes (N2/N3)._

## Estrutura do CÃ³digo

A aprendizagem e o cÃ³digo sÃ£o estruturados de forma incremental, representados puramente pelos scripts `N0` atÃ© `N3`:

- `N0_news_curator_agent.py` - Nossa fundaÃ§Ã£o, explorando a criaÃ§Ã£o do curador utilizando apenas um Agente Ãšnico (Agente MonolÃ­tico).
- `N1`, `N2`, `N3_news_curator_agent.py` - Diferentes iteraÃ§Ãµes do mesmo projeto que vÃ£o evoluindo a arquitetura para Multi-Agentes, implementando a etapa de pesquisa, fact-checking e redaÃ§Ã£o como agentes segregados em equipe.
- `/skills` - ImplementaÃ§Ã£o isolada de ferramentas consumidas no projeto.

## Stack TecnolÃ³gica (DependÃªncias)

O projeto depende das seguintes bibliotecas principais presentes no `pyproject.toml`:

- **[Python](https://python.org/)** (v3.12.11)
- **[Agno](https://github.com/agno-agi/agno)** (v2.4.8) - Framework base de agentes.
- **OpenAI** - Engine de inferÃªncia (LLM).
- **DuckDuckGo Search (`ddgs`)** - Ferramenta de pesquisa automatizada em tempo real para os agentes coletarem as notÃ­cias.
- **FastAPI**

## Como Preparar o Ambiente

1. Garanta que vocÃª tenha o Python 3.12+ ou gerenciador similar (como o `uv`).
2. Instale as dependÃªncias listadas no `pyproject.toml`.
3. Configure as varÃ­aveis de ambiente atravÃ©s da criaÃ§Ã£o de um `.env` listando pelo menos:
   ```env
   ZAI_API_KEY="sua-chave-zai"
   ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4/"
   ZAI_MODEL="glm-4.7"
   ```
4. Execute os mÃ³dulos de N0 a N3 para explorar o Agente em aÃ§Ã£o!
   - Ative o ambiente virtual:
   ```bash
   source .venv/bin/activate
   ```
   - Instale as dependÃªncias:
   ```bash
   uv sync
   ```
   - Execute os mÃ³dulos:
   ```bash
   uv run N0_news_curator_agent.py
   ```

## Frontend Streamlit

Para executar um frontend web simples para o N3:

```bash
uv sync
uv run streamlit run app.py
```

Acesse o endereco exibido no terminal (normalmente `http://localhost:8501`).

Pre-requisito: arquivo `.env` com `ZAI_API_KEY`.

