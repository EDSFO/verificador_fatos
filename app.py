import html
import os
import re
from pathlib import Path
from urllib.parse import quote

import streamlit as st
from dotenv import load_dotenv

from news_curator_service import run_news_curator
from N3_news_curator_agent import FAST_MODE, output_dir

load_dotenv()

VEREDITO_META = {
    "VERDADEIRO": {"score": 96, "label": "VERIFICADO: FATO", "kind": "ok"},
    "FALSO": {"score": 15, "label": "ALERTA: FALSO", "kind": "danger"},
    "ENGANOSO": {"score": 38, "label": "ENGANOSO", "kind": "warn"},
    "IMPRECISO": {"score": 42, "label": "IMPRECISO", "kind": "warn"},
    "INCONCLUSIVO": {"score": 52, "label": "INCONCLUSIVO", "kind": "neutral"},
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #f4f5f9;
            --surface: #ffffff;
            --text: #0f172a;
            --muted: #64748b;
            --line: #dbe2ef;
            --primary: #1f2fd4;
            --ok: #16a34a;
            --danger: #dc2626;
            --warn: #d97706;
        }

        html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 15% 0%, #eef2ff 0%, var(--bg) 40%);
            padding-top: max(0.75rem, env(safe-area-inset-top));
        }
        [data-testid="stSidebar"] { display: none; }

        .block-container {
            max-width: 760px;
            padding-top: clamp(2rem, 4.2vh, 3.2rem) !important;
            padding-bottom: 4rem;
        }

        .top-shell {
            background: rgba(255,255,255,0.86);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.8rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.25rem;
            margin-bottom: 0.9rem;
        }

        .brand { display: flex; align-items: center; gap: 0.65rem; color: var(--text); font-size: 1.7rem; font-weight: 800; }
        .brand .icon {
            width: 40px; height: 40px; border-radius: 12px;
            display: inline-flex; align-items: center; justify-content: center;
            background: #e3e8ff; color: var(--primary);
            font-size: 22px;
        }

        .status-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.7rem 0.9rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.9rem;
        }

        .status-chip { border-radius: 999px; padding: 0.22rem 0.65rem; font-weight: 700; }
        .status-chip.ok { background: #d1fae5; color: #047857; }
        .status-chip.off { background: #fee2e2; color: #991b1b; }

        .input-shell {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }

        .section-title { margin: 0; font-size: 1.75rem; font-weight: 800; color: var(--text); }
        .section-sub { margin: 0.45rem 0 0; color: var(--muted); line-height: 1.55; }

        [data-testid="stTextArea"] textarea {
            min-height: 220px;
            border-radius: 14px !important;
            border: 1px solid var(--line) !important;
            background: #fbfcff !important;
            color: #24344f !important;
            font-size: 1rem !important;
        }

        [data-testid="stSelectbox"] > div > div {
            border-radius: 12px !important;
            border: 1px solid var(--line) !important;
            min-height: 48px;
            background: #ffffff;
        }

        [data-testid="stButton"] button {
            border: none;
            border-radius: 14px;
            min-height: 54px;
            font-weight: 800;
        }

        .cta-row [data-testid="stButton"] button {
            width: 100%;
            background: linear-gradient(100deg, #2333de, #151bb8);
            color: #fff;
            box-shadow: 0 8px 22px rgba(31, 47, 212, 0.26);
        }

        .confidence {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.85rem 0.9rem;
            margin-bottom: 0.9rem;
        }

        .confidence-top {
            display: flex; justify-content: space-between;
            font-size: 0.9rem; font-weight: 700; color: var(--muted);
            margin-bottom: 0.45rem;
        }

        .bar { width: 100%; height: 11px; border-radius: 999px; background: #e8edf6; overflow: hidden; }
        .bar > span { display: block; height: 100%; border-radius: 999px; }
        .bar.ok > span { background: var(--ok); }
        .bar.danger > span { background: var(--danger); }
        .bar.warn > span { background: var(--warn); }
        .bar.neutral > span { background: #64748b; }

        .mode-pill {
            display: inline-flex; align-items: center; gap: 0.4rem;
            border-radius: 999px; padding: 0.25rem 0.7rem;
            font-size: 0.8rem; font-weight: 700;
            border: 1px solid #cbd5e1;
            background: #fff;
            color: #334155;
        }

        .article-image { border-radius: 14px; overflow: hidden; border: 1px solid var(--line); }

        .veredito-box {
            margin-top: 0.8rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.85rem;
            background: #f9fafb;
        }
        .veredito-box.ok { background: #ecfdf3; border-color: #9ae6b4; }
        .veredito-box.danger { background: #fff1f2; border-color: #fecaca; }
        .veredito-box.warn { background: #fff7ed; border-color: #fed7aa; }

        .tag {
            display: inline-flex; align-items: center; gap: 0.4rem;
            border-radius: 999px; padding: 0.24rem 0.7rem;
            color: #fff; font-weight: 800; font-size: 0.83rem;
        }
        .tag.ok { background: var(--ok); }
        .tag.danger { background: var(--danger); }
        .tag.warn { background: var(--warn); }
        .tag.neutral { background: #64748b; }

        .meta { margin-top: 0.65rem; margin-bottom: 0.3rem; color: #4f46e5; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
        .article-title { margin: 0.1rem 0 0.65rem; font-size: 2rem; line-height: 1.2; color: var(--text); font-weight: 800; }

        .facts-box {
            background: #f8fafc;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.8rem 0.95rem;
            margin-bottom: 1rem;
        }

        .tip {
            background: #eef2ff;
            border: 1px solid #c7d2fe;
            border-radius: 14px;
            padding: 0.75rem 0.9rem;
            color: #334155;
            font-size: 0.95rem;
        }

        .share-box {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: #ffffff;
            padding: 0.9rem;
            margin: 0.8rem 0 1rem;
        }
        .share-title {
            margin: 0 0 0.65rem;
            font-size: 0.95rem;
            font-weight: 700;
            color: #334155;
        }
        .share-row { display: flex; gap: 0.55rem; flex-wrap: wrap; }
        .share-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            border-radius: 11px;
            padding: 0.55rem 0.85rem;
            font-size: 0.9rem;
            font-weight: 700;
            color: #fff !important;
        }
        .share-btn.wa { background: #16a34a; }
        .share-btn.tg { background: #0284c7; }
        .no-image {
            border: 1px dashed #cbd5e1;
            border-radius: 14px;
            padding: 1.4rem 1rem;
            text-align: center;
            color: #64748b;
            background: #f8fafc;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def extract_section(text: str, pattern: str) -> str:
    if not text:
        return ""
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_posicionamento(text: str) -> str:
    patterns = [
        r"(##\s*Posicionamento de Veracidade.*?)(?=\n##\s|\Z)",
        r"(##\s*Posicionamento.*?)(?=\n##\s|\Z)",
        r"(##\s*VEREDITO.*?)(?=\n##\s|\Z)",
    ]
    for pattern in patterns:
        section = extract_section(text, pattern)
        if section:
            return section
    return ""


def parse_classificacao(text: str) -> str:
    if not text:
        return "INCONCLUSIVO"
    match = re.search(r"Classifica(?:cao|ção)\s*:\s*([A-ZÇÃÕ]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()

    text_up = text.upper()
    for key in VEREDITO_META:
        if key in text_up:
            return key
    return "INCONCLUSIVO"


def parse_resumo_fatos(text: str) -> list[str]:
    section = extract_section(text, r"##\s*O QUE E SUSTENTADO POR EVIDENCIA(.*?)(?=\n##\s|\Z)")
    if not section:
        section = extract_section(text, r"##\s*An[áa]lise dos Fatos(.*?)(?=\n##\s|\Z)")

    lines: list[str] = []
    for raw in section.splitlines():
        line = raw.strip(" -*\t")
        if line:
            lines.append(line)
    return lines[:4]


def is_noisy_text(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    noise_tokens = [
        "workflow information",
        "step 1:",
        "step 2:",
        "step 3:",
        "completed)",
        "error   ",
        "insufficient balance",
    ]
    if any(token in lowered for token in noise_tokens):
        return True
    special_count = sum(text.count(ch) for ch in ("|", "┏", "┃", "┗", "╭", "╰"))
    if special_count > 40:
        return True
    if special_count / max(len(text), 1) > 0.02:
        return True
    return False


def strip_generated_reference_sections(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"\n##\s*Refer[eê]ncias.*$",
        r"\n##\s*Imagem de Evid[eê]ncia.*?(?=\n##\s|\Z)",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = re.findall(r"https?://[^\s\)\]>\"']+", text)
    unique: list[str] = []
    seen = set()
    for url in urls:
        normalized = url.strip().rstrip(".,;")
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def build_share_links(theme: str, title: str, meta: dict, result: dict) -> tuple[str, str, str]:
    source_url = result.get("primary_source_url") or ""

    share_text_lines = [
        "Verificador de Fatos",
        f"Tema: {title or theme}",
        f"Veredito: {meta['label']} ({meta['score']}%)",
    ]
    if source_url:
        share_text_lines.append(f"Fonte: {source_url}")
    share_text_lines.append("Analise automatica de noticias e boatos.")
    share_text = "\n".join(share_text_lines)

    wa_link = f"https://wa.me/?text={quote(share_text)}"
    if source_url:
        tg_link = f"https://t.me/share/url?url={quote(source_url)}&text={quote(share_text)}"
    else:
        tg_link = f"https://t.me/share/url?text={quote(share_text)}"
    return wa_link, tg_link, share_text


def extract_title(markdown_text: str, fallback: str) -> str:
    if markdown_text:
        for regex in [r"^#\s+(.+)$", r"^##\s+(.+)$"]:
            match = re.search(regex, markdown_text, flags=re.MULTILINE)
            if match:
                title = match.group(1).strip()
                if len(title) > 8:
                    return title
    return fallback.strip()[:120]


def render_top_shell(api_ok: bool) -> None:
    mode_badge = "MODO RAPIDO" if FAST_MODE else "MODO COMPLETO"
    status_chip = '<span class="status-chip ok">OK</span>' if api_ok else '<span class="status-chip off">OFF</span>'
    st.markdown(
        f"""
        <div class="top-shell">
            <div class="brand"><span class="icon">✓</span> Verificador de Fatos</div>
            <span class="mode-pill">{mode_badge}</span>
        </div>
        <div class="status-card">
            <div style="color:#64748b;font-weight:600;">ZAI_API_KEY</div>
            {status_chip}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_confidence_card(meta: dict, waiting: bool) -> None:
    value = "Aguardando entrada" if waiting else f"{meta['score']}%"
    width = 0 if waiting else int(meta["score"])
    st.markdown(
        f"""
        <div class="confidence">
            <div class="confidence-top">
                <span>Nivel de confianca</span>
                <span style="color:#1f2fd4;">{value}</span>
            </div>
            <div class="bar {meta['kind']}"><span style="width:{width}%;"></span></div>
            <div style="display:flex;justify-content:space-between;font-size:0.86rem;color:#64748b;margin-top:0.3rem;">
                <span>Fake</span>
                <span>Fato</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result(theme: str, result: dict) -> None:
    article_content = result.get("article_content") or ""
    raw_output_parts = [
        result.get("workflow_response") or "",
        result.get("console_output") or "",
    ]
    raw_output = "\n\n".join(part for part in raw_output_parts if part.strip()).strip() or "Sem resposta."
    raw_output_is_noisy = is_noisy_text(raw_output)
    source = article_content or ("" if raw_output_is_noisy else raw_output)
    posicionamento = extract_posicionamento(source)
    classif = parse_classificacao(posicionamento or source)
    meta = VEREDITO_META.get(classif, VEREDITO_META["INCONCLUSIVO"])
    facts = parse_resumo_fatos(source)
    title = extract_title(article_content, theme)

    evidence_image_url = result.get("evidence_image_url")
    evidence_source_url = result.get("evidence_source_url")
    validated_sources = result.get("validated_sources") or []
    display_article = strip_generated_reference_sections(article_content)

    if evidence_image_url:
        st.markdown(
            f"""
            <div class="article-image">
                <img src="{evidence_image_url}" style="width:100%;display:block;" alt="Imagem de evidencia"/>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="no-image">Nao foi possivel localizar imagem contextual nas reportagens encontradas.</div>',
            unsafe_allow_html=True,
        )

    if evidence_source_url:
        st.caption(f"Imagem obtida de pagina encontrada para este tema: {evidence_source_url}")
    else:
        st.caption("Imagem de evidencia nao encontrada nas fontes da materia.")

    st.markdown(
        f"""
        <div class="veredito-box {meta['kind']}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <span class="tag {meta['kind']}">{meta['label']}</span>
                <span style="font-size:0.78rem;font-weight:700;color:#475569;">ANALISE POR IA</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.35rem;">
                <span style="font-size:0.88rem;color:#334155;font-weight:700;">Barra de Credibilidade</span>
                <span style="font-size:0.95rem;font-weight:800;color:#0f172a;">{meta['score']}%</span>
            </div>
            <div class="bar {meta['kind']}"><span style="width:{meta['score']}%;"></span></div>
        </div>
        <div class="meta">Mundo • leitura estimada</div>
        <h2 class="article-title">{html.escape(title)}</h2>
        """,
        unsafe_allow_html=True,
    )

    if validated_sources:
        wa_link, tg_link, share_text = build_share_links(theme, title, meta, result)
        st.markdown(
            f"""
            <div class="share-box">
                <div class="share-title">Compartilhar resultado</div>
                <div class="share-row">
                    <a class="share-btn wa" href="{wa_link}" target="_blank">WhatsApp</a>
                    <a class="share-btn tg" href="{tg_link}" target="_blank">Telegram</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area("Mensagem de compartilhamento", share_text, height=120)

        sources_md = "\n".join(
            f"{index}. [{item['title']}]({item['url']})"
            for index, item in enumerate(validated_sources, start=1)
        )
        st.subheader("Fontes validadas")
        st.markdown(sources_md)
    else:
        st.warning("Nenhuma fonte foi validada automaticamente para este tema. O resultado nao deve ser compartilhado como conclusivo.")

    if facts:
        items = "".join(f"<li>{html.escape(item)}</li>" for item in facts)
        st.markdown(f'<div class="facts-box"><h4>Analise dos Fatos</h4><ul>{items}</ul></div>', unsafe_allow_html=True)

    if posicionamento and not is_noisy_text(posicionamento):
        st.subheader("Posicionamento")
        st.markdown(posicionamento)

    if display_article:
        st.subheader("Materia")
        st.markdown(display_article)

        article_path = result.get("article_path")
        file_name = Path(article_path).name if article_path else "materia.md"
        st.download_button("Baixar .md", data=display_article, file_name=file_name, mime="text/markdown")
    else:
        st.subheader("Saida")
        if raw_output_is_noisy:
            st.warning("Nao foi possivel gerar uma materia final limpa nesta execucao. Exibindo saida tecnica.")
        st.text_area("Resultado bruto", raw_output, height=340)


def ensure_state() -> None:
    st.session_state.setdefault("screen_mode", "analise")
    st.session_state.setdefault("last_result", {})
    st.session_state.setdefault("last_theme", "")


def render_mode_selector() -> None:
    label_map = {
        "analise": "Tela de Analise",
        "resultado": "Tela de Resultado",
    }
    reverse = {v: k for k, v in label_map.items()}

    current_label = label_map.get(st.session_state["screen_mode"], "Tela de Analise")
    selected_label = st.radio(
        "Modo",
        options=["Tela de Analise", "Tela de Resultado"],
        index=0 if current_label == "Tela de Analise" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["screen_mode"] = reverse[selected_label]


def render_analysis_screen(api_key_ok: bool) -> None:
    st.markdown(
        '<div class="input-shell"><h2 class="section-title">Nova Investigacao</h2>'
        '<p class="section-sub">Cole links de noticias, manchetes ou boatos suspeitos para verificacao.</p></div>',
        unsafe_allow_html=True,
    )

    placeholder = "Cole aqui a URL da noticia ou o texto suspeito para analise profunda..."
    tema = st.text_area("Tema", value=st.session_state.get("draft_theme", ""), height=240, label_visibility="collapsed", placeholder=placeholder)
    st.session_state["draft_theme"] = tema

    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    options = [""] + [f.name for f in files]
    selected = st.selectbox("Select Recent Topic or File", options=options, format_func=lambda x: "Choose from history..." if not x else x)

    if selected:
        selected_path = output_dir / selected
        st.session_state["saved_article_name"] = selected_path.name
        st.session_state["saved_article_content"] = selected_path.read_text(encoding="utf-8", errors="replace")

    last_result = st.session_state.get("last_result", {})
    last_source = (last_result.get("article_content") or last_result.get("workflow_response") or last_result.get("console_output") or "")
    last_class = parse_classificacao(extract_posicionamento(last_source) or last_source)
    meta_now = VEREDITO_META.get(last_class, VEREDITO_META["INCONCLUSIVO"])
    render_confidence_card(meta_now, waiting=not bool(last_source))

    st.markdown('<div class="cta-row">', unsafe_allow_html=True)
    run_clicked = st.button("Analisar Noticia", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if run_clicked:
        if not tema.strip():
            st.warning("Informe um tema antes de executar.")
            return
        if not api_key_ok:
            st.error("ZAI_API_KEY nao encontrada. Crie um .env com sua chave para executar.")
            return

        st.session_state["last_result"] = {}
        st.session_state["last_theme"] = tema.strip()

        with st.spinner("Executando workflow... isso pode levar alguns minutos."):
            try:
                result = run_news_curator(tema, stream=False, markdown=True)
                st.session_state["last_result"] = result
                st.session_state["last_theme"] = tema.strip()
                st.session_state["screen_mode"] = "resultado"
                st.rerun()
            except Exception as exc:
                message = str(exc)
                st.session_state["last_result"] = {}
                if "saldo/pacote" in message.lower() or "insufficient balance" in message.lower():
                    st.error(message)
                    st.info("No .env, confirme ZAI_MODEL e ZAI_BASE_URL. Para Coding Plan, use /api/coding/paas/v4/.")
                else:
                    st.error(f"Falha na execucao: {message}")

    st.markdown('<div class="tip">Dica: o modo rapido reduz tempo de busca com menor profundidade de apuracao.</div>', unsafe_allow_html=True)


def render_result_screen() -> None:
    result = st.session_state.get("last_result", {})
    has_result_payload = bool(result.get("article_content") or result.get("workflow_response") or result.get("console_output"))

    if not has_result_payload:
        st.info("Nenhum resultado pronto. Rode uma analise para visualizar esta tela.")
        if st.button("Ir para Tela de Analise", use_container_width=True):
            st.session_state["screen_mode"] = "analise"
            st.rerun()
        return

    theme_for_result = st.session_state.get("last_theme") or st.session_state.get("draft_theme", "")
    if result.get("article_path"):
        st.caption(f"Arquivo final: {result['article_path']}")

    render_result(theme_for_result, result)

    if st.button("Nova Analise", use_container_width=True):
        st.session_state["screen_mode"] = "analise"
        st.rerun()


st.set_page_config(page_title="Verificador de Fatos", layout="wide")
inject_styles()
ensure_state()

api_key_ok = bool(os.getenv("ZAI_API_KEY"))
render_top_shell(api_key_ok)
render_mode_selector()

if st.session_state["screen_mode"] == "analise":
    render_analysis_screen(api_key_ok)
else:
    render_result_screen()

if st.session_state.get("saved_article_content"):
    with st.expander("Ultima materia carregada da timeline", expanded=False):
        st.caption(st.session_state.get("saved_article_name", "arquivo"))
        st.markdown(st.session_state["saved_article_content"])
