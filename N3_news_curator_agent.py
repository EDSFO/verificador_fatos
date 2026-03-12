import os
import re
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.skills import LocalSkills, Skills
from agno.team import Team
from agno.tools.file import FileTools
from agno.tools.websearch import WebSearchTools
from agno.workflow import Loop, Step, Workflow
from agno.workflow.types import StepOutput

load_dotenv()
if not os.getenv("ZAI_API_KEY") and os.getenv("\ufeffZAI_API_KEY"):
    os.environ["ZAI_API_KEY"] = os.getenv("\ufeffZAI_API_KEY", "")

FAST_MODE = os.getenv("FAST_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
MIN_FONTES = int(os.getenv("MIN_FONTES", "2" if FAST_MODE else "3"))
MAX_TENTATIVAS_APURACAO = int(os.getenv("MAX_TENTATIVAS_APURACAO", "2" if FAST_MODE else "3"))
DEFAULT_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4/"
DEFAULT_ZAI_MODEL = "glm-4.7"
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1000" if FAST_MODE else "1400"))


def build_llm() -> OpenAILike:
    return OpenAILike(
        id=os.getenv("ZAI_MODEL", DEFAULT_ZAI_MODEL),
        api_key=os.getenv("ZAI_API_KEY"),
        base_url=os.getenv("ZAI_BASE_URL", DEFAULT_ZAI_BASE_URL),
        provider="Z.AI",
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.2,
    )


skills_dir = Path(__file__).parent / "skills"
shared_skills = Skills(loaders=[LocalSkills(str(skills_dir))])

output_dir = Path(__file__).parent / "output/N3/"
output_dir.mkdir(parents=True, exist_ok=True)

file_tools = FileTools(
    base_dir=output_dir,
    enable_save_file=True,
    enable_read_file=True,
    enable_list_files=True,
)


pesquisador = Agent(
    name="Pesquisador",
    model=build_llm(),
    skills=shared_skills,
    instructions=[
        "Voce e um pesquisador de noticias.",
        "Carregue instrucoes da skill com get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' e siga o formato definido nela.",
        "Priorize velocidade: no maximo 5 consultas web nesta etapa.",
        "Salve o resultado da pesquisa em arquivo.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


time_research = Team(
    name="Research",
    model=build_llm(),
    members=[pesquisador],
    instructions=[
        "Voce lidera a equipe de pesquisa.",
        "Coordene a busca por noticias recentes e relevantes sobre o tema.",
        "Garanta uso correto da skill 'pesquisa-noticias'.",
    ],
    add_datetime_to_context=True,
    markdown=True,
)


apurador = Agent(
    name="Apurador de Fontes",
    model=build_llm(),
    skills=shared_skills,
    instructions=[
        "Voce e um apurador de fontes jornalisticas.",
        "Carregue instrucoes da skill com get_skill_instructions.",
        "Receba a saida da pesquisa e execute a skill 'apuracao-fontes'.",
        f"Encontre no minimo {MIN_FONTES} fontes distintas.",
        "Sempre inclua nome do veiculo em negrito e URL completa.",
        "Se faltar fonte, busque em veiculos diferentes e idiomas diferentes.",
        "Priorize velocidade: limite a 6 consultas web por iteracao.",
        "Salve o resultado da apuracao em arquivo.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


verificador = Agent(
    name="Verificador Factual",
    model=build_llm(),
    skills=shared_skills,
    instructions=[
        "Voce e um verificador factual.",
        "Carregue instrucoes da skill com get_skill_instructions.",
        "Receba o dossie da apuracao e execute a skill 'verificacao-factual'.",
        "Priorize velocidade: seja objetivo e evite buscas redundantes.",
        "Salve o resultado da verificacao em arquivo.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


posicionador = Agent(
    name="Analista de Fake News",
    model=build_llm(),
    skills=shared_skills,
    instructions=[
        "Voce e um analista de desinformacao.",
        "Carregue instrucoes da skill com get_skill_instructions.",
        "Receba o relatorio da verificacao e execute a skill 'posicionamento-fake-news'.",
        "Classifique em: VERDADEIRO, ENGANOSO, FALSO, IMPRECISO ou INCONCLUSIVO.",
        "Informe nivel de confianca de 0 a 100 com justificativa objetiva.",
        "Salve o posicionamento final em arquivo.",
    ],
    tools=[file_tools],
    markdown=True,
)


redator = Agent(
    name="Redator",
    model=build_llm(),
    skills=shared_skills,
    instructions=[
        "Voce e um redator jornalistico profissional.",
        "Carregue instrucoes da skill com get_skill_instructions.",
        "Receba o relatorio do posicionador e execute a skill 'redacao-jornalistica'.",
        "Inclua secao obrigatoria '## Posicionamento de Veracidade' com classificacao, confianca e justificativa curta.",
        "Inclua secao obrigatoria '## Imagem de Evidencia' com uma URL de imagem publicada por uma das reportagens referenciadas e indique a fonte da imagem.",
        "Se nao houver imagem valida nas fontes, escreva explicitamente: 'Imagem nao encontrada nas fontes verificadas'.",
        f"Se houver menos de {MIN_FONTES} fontes independentes, inclua aviso claro no inicio do texto.",
        "Use citacoes numericas [1], [2], [3] no corpo sempre que citar fatos de fontes.",
        "Inclua secao final '## Referencias' com lista numerada e URLs completas.",
        "Em modo rapido, mantenha texto entre 220 e 320 palavras.",
        "Salve obrigatoriamente a materia em arquivo .md e confirme o nome do arquivo salvo.",
    ],
    tools=[file_tools],
    markdown=True,
)


def contar_fontes(texto: str) -> int:
    secao = texto
    match = re.search(r"##\s*FONTES COLETADAS(.*?)(##|$)", texto, re.DOTALL | re.IGNORECASE)
    if match:
        secao = match.group(1)

    fontes_por_marcador = re.findall(r"^-\s+\*\*", secao, re.MULTILINE)
    urls = set(re.findall(r"https?://[^\s\)]+", secao))
    return max(len(fontes_por_marcador), len(urls))


def fontes_suficientes(outputs: List[StepOutput]) -> bool:
    if not outputs:
        return False
    latest = outputs[-1]
    content = str(latest.content or "")
    return contar_fontes(content) >= MIN_FONTES


pesquisa_step = Step(
    name="pesquisa",
    description="Pesquisa de noticias sobre o tema",
    team=time_research,
)

apuracao_step = Step(
    name="apuracao",
    description="Apuracao multi-fonte com verificacao de fontes",
    agent=apurador,
)

apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuracao ate atingir o minimo de fontes",
    steps=[apuracao_step],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
)

verificacao_step = Step(
    name="verificacao",
    description="Verificacao factual do dossie",
    agent=verificador,
)

posicionamento_step = Step(
    name="posicionamento",
    description="Posicionamento final sobre veracidade da noticia",
    agent=posicionador,
)

redacao_step = Step(
    name="redacao",
    description="Redacao jornalistica final",
    agent=redator,
)


news_curator_workflow = Workflow(
    name="News Curator Pipeline",
    description="Pesquisa -> Apuracao (loop) -> Verificacao Factual -> Posicionamento -> Redacao",
    steps=[pesquisa_step, apuracao_loop, verificacao_step, posicionamento_step, redacao_step],
)


if __name__ == "__main__":
    news_curator_workflow.print_response(
        "Novas tarifas dos EUA entram em vigor com taxa de 10%",
        stream=True,
        markdown=True,
    )
