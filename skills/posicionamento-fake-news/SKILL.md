---
name: posicionamento-fake-news
description: Gerar um posicionamento final de veracidade sobre uma noticia, com classificacao, confianca e justificativa baseada nas evidencias do dossie e da verificacao factual.
metadata:
  version: "1.0.0"
  tags: ["fake-news", "veredito", "fact-check"]
---

# Posicionamento de Veracidade

Use esta skill para produzir um veredito final sobre o tema analisado.

## Entrada esperada

- Relatorio de verificacao factual
- Dossie de fontes e contradicoes

## Classificacoes permitidas

- VERDADEIRO
- ENGANOSO
- FALSO
- IMPRECISO
- INCONCLUSIVO

## Processo

1. Revise fatos confirmados, disputados e nao verificados.
2. Pese qualidade e independencia das fontes.
3. Determine o risco de desinformacao para o leitor.
4. Defina uma classificacao unica e um nivel de confianca (0-100).

## Formato de saida obrigatorio

```markdown
## VEREDITO
Classificacao: <VERDADEIRO|ENGANOSO|FALSO|IMPRECISO|INCONCLUSIVO>
Confianca: <0-100>
Resumo: <2-4 frases objetivas>

## O QUE E SUSTENTADO POR EVIDENCIA
- Itens curtos com referencias de fontes.

## O QUE NAO FOI COMPROVADO
- Itens curtos com lacunas e contradicoes.

## RISCO DE DESINFORMACAO
- Baixo, Medio ou Alto, com justificativa.

## RECOMENDACAO EDITORIAL
- O que pode ser afirmado com seguranca.
- O que deve ser publicado com ressalva.
- O que nao deve ser afirmado como fato.
```

## Regras

- Nunca invente fatos.
- Sempre explicite incertezas e limites das fontes.
- Seja objetivo e acionavel.
- Se a evidencia for fraca, priorize INCONCLUSIVO ou IMPRECISO.