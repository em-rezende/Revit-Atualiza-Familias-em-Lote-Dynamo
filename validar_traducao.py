# -*- coding: utf-8 -*-
"""
validar_traducao.py
---------------------------------------------------------------------------
Valida, FORA do Revit, a traducao dos nomes de vista de
batch_format_families.py (chave_nome_vista + traduzir_nome_vista).

O modulo depende da API do Revit (import clr/RevitAPI no topo), por isso este
script NAO o importa: extrai apenas o trecho de dados (tabela de acentos,
chave_nome_vista, dicionario, regras e traduzir_nome_vista) e o executa.

Uso (qualquer Python 3, inclusive o do Dynamo):

    python validar_traducao.py

Codigo de saida 0 = tudo certo; 1 = falhas (detalhadas na saida).
"""
import io
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PY = os.path.join(AQUI, "batch_format_families.py")
CAMINHO_DYN = os.path.join(AQUI, "Atualiza Familias em Lote.dyn")

# O trecho aproveitado do script principal tem de ser "Python puro" (nao pode
# tocar na API do Revit). Sao duas fatias:
#   1. da tabela de acentos ate o fim de REGRAS_NOMES_VISTAS_PT_BR (dicionario,
#      chave normalizada, regras);
#   2. de traduzir_nome_vista ate antes de renomear_vistas_pt_br.
# No meio delas ficam as rotinas que usam a API (nome_da_vista, renomear_vista,
# rotinas da vista 3D), que nao rodam fora do Revit.
MARCA_INICIO = "_ACENTOS_PARA_ASCII = {"
MARCA_REGRAS = "REGRAS_NOMES_VISTAS_PT_BR = ("
MARCA_TRADUCAO = "def traduzir_nome_vista"
MARCA_FIM = "def renomear_vistas_pt_br"

falhas = []


def conferir(descricao, obtido, esperado):
    """Registra a falha (se houver) e devolve True quando bate."""
    if obtido == esperado:
        return True
    falhas.append("{0}: obtido {1!r}, esperado {2!r}".format(descricao, obtido, esperado))
    return False


def carregar_trecho():
    """Executa as fatias de dados/traducao do script principal (sem Revit)."""
    with io.open(CAMINHO_PY, encoding="utf-8") as arquivo:
        origem = arquivo.read().replace("\r\n", "\n").replace("\r", "\n")

    for marca in (MARCA_INICIO, MARCA_REGRAS, MARCA_TRADUCAO, MARCA_FIM):
        if marca not in origem:
            raise SystemExit("Marcador nao encontrado em batch_format_families.py: " + marca)

    inicio = origem.index(MARCA_INICIO)
    regras = re.search(re.escape(MARCA_REGRAS) + r".*?\n\)\n", origem, re.S)
    if regras is None:
        raise SystemExit("Nao encontrei o fim de REGRAS_NOMES_VISTAS_PT_BR")

    trecho = (origem[inicio:regras.end()] + "\n\n" +
              origem[origem.index(MARCA_TRADUCAO):origem.index(MARCA_FIM)])

    espaco = {"re": re, "__name__": "trecho_traducao"}
    exec(compile(trecho, "batch_format_families.py:trecho", "exec"), espaco)
    return espaco, origem


def conferir_dyn(origem):
    """
    Confere se o Python embutido no .dyn e igual ao do .py. O Dynamo executa o
    codigo que esta DENTRO do .dyn: se o .dyn nao for sincronizado
    (sincronizar_dyn.ps1), as alteracoes no .py simplesmente nao acontecem -
    e' a causa mais comum de "mudei o dicionario e nada mudou".
    """
    if not os.path.isfile(CAMINHO_DYN):
        print("(.dyn nao encontrado: conferencia ignorada)")
        return

    with io.open(CAMINHO_DYN, encoding="utf-8-sig") as arquivo:
        grafo = json.load(arquivo)

    for no in grafo.get("Nodes", []):
        if no.get("NodeType") == "PythonScriptNode" and "Code" in no:
            embutido = no["Code"].replace("\r\n", "\n").replace("\r", "\n")
            conferir("Python embutido no .dyn (rode sincronizar_dyn.ps1)",
                     embutido.rstrip(), origem.rstrip())
            return

    falhas.append(".dyn sem PythonScriptNode com campo Code")


# (nome como o Revit grava no idioma instalado, traducao esperada em pt-BR)
CASOS = (
    # ------------------------------------------------------------- ingles (EN)
    ("{3D}", "Vista 3D"),
    ("3D View", "Vista 3D"),
    ("Default 3D View", "Vista 3D"),
    ("Ref. Level", "Nível de Referência"),
    ("Ref Level", "Nível de Referência"),
    ("Reference Level", "Nível de Referência"),
    ("Ref. Plane", "Nível de Referência"),
    ("Ground Floor", "Piso Térreo"),
    ("Ground Level", "Piso Térreo"),
    ("Front", "Parte Frontal"),
    ("Back", "Parte Posterior"),
    ("Rear", "Parte Posterior"),
    ("Left", "Esquerda"),
    ("Right", "Direita"),
    ("Top", "Superior"),
    ("Bottom", "Inferior"),
    ("North", "Norte"),
    ("South", "Sul"),
    ("East", "Leste"),
    ("West", "Oeste"),
    ("Exterior", "Exterior"),
    ("Interior", "Interior"),
    ("Floor Plan", "Planta de Piso"),
    ("Ceiling Plan", "Planta de Forro"),
    ("Site Plan", "Planta de Implantação"),
    ("Area Plan", "Planta de Área"),
    ("Structural Plan", "Planta Estrutural"),
    ("Ceiling", "Forro"),
    ("Legend", "Legenda"),
    ("Walkthrough", "Passeio"),
    ("Thumbnail", "Miniatura"),
    ("Section", "Corte"),
    ("Elevation", "Elevação"),
    ("Detail", "Detalhe"),
    ("View 2", "Vista 2"),
    ("Level 1", "Nível 1"),
    ("Level -1", "Nível -1"),
    ("Section 3", "Corte 3"),
    ("Detail 2", "Detalhe 2"),
    ("Elevation 1", "Elevação 1"),
    ("Plan 1", "Planta 1"),

    # ----------------------------------------------------------- frances (FR)
    ("Vue 3D", "Vista 3D"),
    ("Vue 3D 2", "Vista 3D 2"),
    ("Vue 1", "Vista 1"),
    ("Niveau de Référence", "Nível de Referência"),
    ("Niveau de réf.", "Nível de Referência"),
    ("NIVEAU DE RÉF.", "Nível de Referência"),
    ("niveau de ref", "Nível de Referência"),
    ("Réf. Niveau", "Nível de Referência"),
    ("Face avant", "Parte Frontal"),
    ("Élévation avant", "Parte Frontal"),
    ("Face arrière", "Parte Posterior"),
    ("Élévation arrière", "Parte Posterior"),
    ("Face gauche", "Esquerda"),
    ("Face droite", "Direita"),
    ("Vue de dessus", "Superior"),
    ("Vue de dessous", "Inferior"),
    ("Nord", "Norte"),
    ("Sud", "Sul"),
    ("Est", "Leste"),
    ("Ouest", "Oeste"),
    ("Plan d'étage", "Planta de Piso"),
    (u"Plan d\u2019étage", "Planta de Piso"),      # apostrofo tipografico
    ("Plan de plafond", "Planta de Forro"),
    ("Plafond", "Forro"),
    ("Plan de masse", "Planta de Implantação"),
    ("Plan d'implantation", "Planta de Implantação"),
    ("Plan de surface", "Planta de Área"),
    ("Légende", "Legenda"),
    ("Promenade", "Passeio"),
    ("Coupe", "Corte"),
    ("Coupe 2", "Corte 2"),
    ("Niveau 1", "Nível 1"),
    ("Élévation 1", "Elevação 1"),
    ("Détail 3", "Detalhe 3"),
    ("Vue en plan 2", "Planta 2"),
    ("Vue en plan", "Planta de Piso"),
    ("Extérieur", "Exterior"),
    ("Intérieur", "Interior"),
    ("  VUE   3D  ", "Vista 3D"),                  # caixa alta + espacos extras

    # ---------------------------------------------------------- espanhol (ES)
    ("Vista 3D", "Vista 3D"),
    ("Vista 3D {3D}", "Vista 3D"),
    ("Vista 1", "Vista 1"),
    ("Nivel de Referencia", "Nível de Referência"),
    ("Nivel de Ref.", "Nível de Referência"),
    ("Nivel Ref.", "Nível de Referência"),
    ("Ref. Nivel", "Nível de Referência"),
    ("Frontal", "Parte Frontal"),
    ("Frente", "Parte Frontal"),
    ("Alzado frontal", "Parte Frontal"),
    ("Posterior", "Parte Posterior"),
    ("Atrás", "Parte Posterior"),
    ("Detrás", "Parte Posterior"),
    ("Alzado posterior", "Parte Posterior"),
    ("Izquierda", "Esquerda"),
    ("Izquierdo", "Esquerda"),
    ("Alzado izquierdo", "Esquerda"),
    ("Derecha", "Direita"),
    ("Derecho", "Direita"),
    ("Alzado derecho", "Direita"),
    ("Superior", "Superior"),
    ("Inferior", "Inferior"),
    ("Norte", "Norte"),
    ("Sur", "Sul"),
    ("Este", "Leste"),
    ("Oeste", "Oeste"),
    ("Planta de piso", "Planta de Piso"),
    ("Planta baja", "Piso Térreo"),
    ("Planta de techo", "Planta de Forro"),
    ("Planta de emplazamiento", "Planta de Implantação"),
    ("Planta de área", "Planta de Área"),
    ("Planta de estructura", "Planta Estrutural"),
    ("Techo", "Forro"),
    ("Leyenda", "Legenda"),
    ("Recorrido", "Passeio"),
    ("Sección", "Corte"),
    ("Sección 2", "Corte 2"),
    ("Alzado", "Elevação"),
    ("Alzado 1", "Elevação 1"),
    ("Detalle 4", "Detalhe 4"),
    ("Vista 2", "Vista 2"),
    ("Nivel 2", "Nível 2"),

    # ------------------ nomes fora do padrao (nao devem ser tocados: None)
    ("Projeto Estrutural", None),
    ("Fachada Norte", None),
    ("Corte A", None),
    ("Nivelamento", None),
    ("Vue", None),
    ("Level", None),
    ("Vista", None),
    ("", None),
    ("   ", None),
    ("...", None),
    ("Planta de Piso 3", None),
)

# Grupos que devem ter a MESMA traducao (mesma chave normalizada): pega erro de
# acento, apostrofo, ponto final ou espaco no cadastro do dicionario.
EQUIVALENTES = (
    ("Niveau de Référence", "niveau de réf.", "Niveau ref.", "NIVEAU DE RÉF."),
    ("Ref. Level", "ref level", "REFERENCE LEVEL", "  Ref. Level  "),
    ("Détail", "DÉTAIL", "Detail"),
    ("Sección", "seccion", "SECCIÓN"),
    ("Planta de área", "PLANTA DE ÁREA", "planta de area"),
)


def main():
    espaco, origem = carregar_trecho()
    chave_nome_vista = espaco["chave_nome_vista"]
    traduzir_nome_vista = espaco["traduzir_nome_vista"]
    dicionario = espaco["NOMES_VISTAS_PT_BR"]
    normalizados = espaco["NOMES_VISTAS_PT_BR_NORMALIZADOS"]
    regras = espaco["REGRAS_NOMES_VISTAS_PT_BR"]

    # 1) Duas chaves cruas diferentes nao podem gerar a MESMA chave normalizada
    #    com traducoes diferentes (a ultima sobrescreveria a outra em silencio).
    por_chave = {}
    for cru, traducao in dicionario.items():
        chave = chave_nome_vista(cru)
        if chave in por_chave and por_chave[chave][1] != traducao:
            falhas.append("conflito em {0!r}: {1!r}->{2!r} x {3!r}->{4!r}".format(
                chave, por_chave[chave][0], por_chave[chave][1], cru, traducao))
        por_chave[chave] = (cru, traducao)

    conferir("entradas de NOMES_VISTAS_PT_BR_NORMALIZADOS",
             len(normalizados), len(por_chave))

    # 2) Funcao de normalizacao
    exemplos_chave = (
        ("Niveau de Référence", "niveau de reference"),
        ("NIVEAU DE RÉF.", "niveau de ref"),
        ("  Vue   3D  ", "vue 3d"),
        ("Sección", "seccion"),
        ("Detrás", "detras"),
        (u"Plan d\u2019étage", "plan d'etage"),
        ("Plan d'étage", "plan d'etage"),
        (u"Élévation\u00a0avant", "elevation avant"),
        ("{3D}", "{3d}"),
        ("Ref. Level", "ref. level"),
        ("Intérieur", "interieur"),
        ("", ""),
        (None, ""),
    )
    for entrada, esperado in exemplos_chave:
        conferir("chave_nome_vista({0!r})".format(entrada),
                 chave_nome_vista(entrada), esperado)

    # 3) Casos completos
    for nome, esperado in CASOS:
        conferir("traduzir_nome_vista({0!r})".format(nome),
                 traduzir_nome_vista(nome), esperado)

    # 4) Equivalentes: nomes do mesmo grupo precisam dar a mesma traducao
    for grupo in EQUIVALENTES:
        traducao = traduzir_nome_vista(grupo[0])
        for nome in grupo[1:]:
            conferir("equivalente {0!r} (grupo {1!r})".format(nome, grupo[0]),
                     traduzir_nome_vista(nome), traducao)

    # 5) .dyn em sincronia com o .py (o Dynamo executa o codigo do .dyn)
    conferir_dyn(origem)

    # 6) Relatorio
    print("Dicionario: {0} entradas | regras: {1} | casos: {2}".format(
        len(dicionario), len(regras), len(CASOS) + len(exemplos_chave)))
    if falhas:
        print("")
        print("FALHAS ({0}):".format(len(falhas)))
        for falha in falhas:
            print("  - " + falha)
        return 1

    print("OK: todas as traducoes esperadas foram confirmadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
