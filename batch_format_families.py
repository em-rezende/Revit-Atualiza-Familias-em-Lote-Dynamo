# -*- coding: utf-8 -*-
# =============================================================================
#  ATUALIZA FAMILIAS EM LOTE - REVIT 2026
#  Atualizacao / formatacao em lote de familias (.rfa)
# -----------------------------------------------------------------------------
#  Para CADA familia (.rfa) encontrada na pasta informada em IN[0], o script:
#    1) Abre a familia em segundo plano (abrir + salvar no Revit 2026 atualiza
#       o formato do arquivo para a versao atual)
#    2) Configura as "Unidades do projeto" para o Sistema Internacional (metrico)
#    3) Executa "Eliminar Nao Utilizados" (Purge Unused) em LOOP ate limpar tudo
#    4) Padroniza a VISTA usada como PREVIEW/MINIATURA (nome/direcao/estilo/
#       categorias ocultas) - veja "ENTRADAS DO DYNAMO (IN[1..3])" abaixo
#    5) Renomeia as vistas cujo nome ainda esta no padrao do Revit para pt-BR
#    6) SALVA a familia no MESMO caminho usando Document.Save(SaveOptions)
#    7) RESPONDE "OK" sozinho nas janelas de aviso do Revit que exigiriam um
#       clique do usuario
#
#  ENTRADAS DO DYNAMO (IN[1..3]) - "BOTOES DE SELECAO" PELO USUARIO
#  -----------------------------------------------------------------
#  O editor do Dynamo nao permite criar botoes/dropdowns a partir do Python:
#  quem cria os nos de UI (Dropdown / Select from List / etc.) e' o proprio
#  usuario, arrastando-os no canvas. Por isso as escolhas sao expostas como
#  ENTRADAS IN[1], IN[2] e IN[3] - conecte um Dropdown a cada uma no grafo.
#  Todas sao OPCIONAIS: se nao vier (ou vier vazia/None), vale a constante de
#  configuracao correspondente. Se vier um valor DESCONHECIDO, cai no padrao e
#  registra aviso no OUT (nunca quebra o lote).
#
#  IN[1] - TIPO DE VISTA que sera gravada como preview/miniatura:
#     "Vista 3D"  (padrao)   - usa/cria/cria a vista 3D, orienta e renomeia
#                              para NOME_VISTA_3D ("Vista 1")
#     "Planta"               - usa (ou cria) uma vista de Planta
#     "Corte"                - usa (ou cria) uma vista de Corte
#     "Detalhe"              - usa (ou cria) uma vista de Detalhe
#     "Elevação"/"Elevacao"  - usa (ou cria) uma vista de Elevação
#  ATENCAO: as vistas nao-3D nao aceitam ViewOrientation3D; a direcao so e'
#  aplicada quando o tipo escolhido for "Vista 3D". O estilo visual e as
#  categorias ocultas valem para QUALQUER tipo escolhido.
#  Se a vista do tipo escolhido nao existir, o script tenta cria-la (com
#  ViewPlan.Create / ViewSection.CreateSection / ViewDrafting.Create) e
#  registra avisos; se nao conseguir, usa a vista 3D como fallback.
#
#  IN[2] - DIRECAO da vista 3D (aplicada somente quando IN[1] = "Vista 3D").
#  Reune DUAS familias de vistas do ViewCube:
#    - ORTOGRAFICAS (camera alinhada a um eixo):
#        "Topo" / "Frontal" / "Esquerda" / "Direita" / "Posterior" / "Inferior"
#    - ISOMETRICAS (camera na diagonal, um canto do cubo):
#        "Frente-Superior-Direita" / "Frente-Superior-Esquerda"
#        "Tras-Superior-Direita"   / "Tras-Superior-Esquerda"
#        "Frente-Inferior-Direita" / "Frente-Inferior-Esquerda"
#  Tambem aceita as chaves internas (FSD, FSE, TSD, TSE, FID, FIE) e os
#  apelidos antigos ("SE Isometric" -> FSD, "SO Isometric" -> FSE,
#  "NE Isometric" -> TSD, "NO Isometric" -> TSE).
#
#  IN[3] - ESTILO VISUAL (View.DisplayStyle) da vista escolhida em IN[1]:
#     "Wireframe"          -> DisplayStyle.Wireframe
#     "Hidden Lines"       -> DisplayStyle.HLR
#     "Shading"            -> DisplayStyle.Shading
#     "Shading With Edges" -> DisplayStyle.ShadingWithEdges
#     "Flat Colors"        -> DisplayStyle.FlatColors
#     "Realistic"          -> DisplayStyle.Realistic
#     "Realistic With Edges" -> DisplayStyle.RealisticWithEdges
#  Aceita tambem as chaves internas ("SOMBREADO", "REALISTA"...) e os apelidos
#  ja existentes (_APELIDOS_ESTILO_VISUAL). O ajuste MOSTRAR_ARESTAS_VISTA_3D
#  continua valendo: se True e o estilo escolhido for SOMBREADO ou REALISTA, a
#  variante COM arestas e' aplicada (a menos que o proprio IN[3] ja peca a
#  variante com arestas).
#
#  DEMAIS SECOES: identicas ao script anterior (unidades SI, purge, vista 3D,
#  preview, traducao de nomes de vista, janelas do Revit respondidas com OK).
# =============================================================================

import clr
import io
import os
import re
import shutil

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

clr.AddReference('RevitAPIUI')

clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager

from System.Collections.Generic import HashSet, List

# -----------------------------------------------------------------------------
#  CONFIGURACAO
# -----------------------------------------------------------------------------
SALVAR_NO_MESMO_ARQUIVO = True   # True  = sobrescreve o .rfa original (com backup)
PASTA_DESTINO = r""              # Usada somente se SALVAR_NO_MESMO_ARQUIVO = False
FAZER_BACKUP = True              # Copia o .rfa original antes de sobrescrever
PASTA_BACKUP = "_backup_upgrade"

IGNORAR_JA_ATUALIZADAS = False   # True = pula familias ja salvas no Revit atual

SISTEMA_METRICO_COMPLETO = True  # True  = cria Units(UnitSystem.Metric)

ACCURACY_COMPRIMENTO = 0.001     # Precisao do comprimento na unidade de exibicao
USAR_AGRUPAMENTO_UNIDADES = True

MAX_PASSES_PURGE = 30

ESCREVER_LOG = True
NOME_LOG = "_log_atualiza_familias.txt"       # log legivel (uma linha por familia)
NOME_LOG_CSV = "_log_atualiza_familias.csv"   # log estruturado (Excel / pandas)
ESCREVER_LOG_CSV = True                       # True = grava tambem o .csv

# --- Respostas automaticas nas janelas de aviso do Revit ---------------------
RESPONDER_DIALOGOS_COM_OK = True
RESULTADO_OK = 1                 # TaskDialogResult.Ok / IDOK
IDS_DIALOGOS_IGNORADOS = ()      # ex.: ("TaskDialog_Save",)
REGISTRAR_DIALOGOS = True

# --- Formato brasileiro/internacional: 123.456.789,00 ------------------------
SYMBOL_DECIMAL = DecimalSymbol.Comma
SYMBOL_AGRUPAMENTO = DigitGroupingSymbol.Dot

# --- Unidades metricas aplicadas explicitamente ------------------------------
UNIDADE_COMPRIMENTO = UnitTypeId.Millimeters
UNIDADE_AREA = UnitTypeId.SquareMeters
UNIDADE_VOLUME = UnitTypeId.CubicMeters

# --- VISTA PADRAO (nome, direcao e preview/miniatura) ------------------------
NOME_VISTA_3D = "Vista 1"        # Nome imposto a vista 3D salva no arquivo.

CRIAR_VISTA_3D_SE_FALTAR = True  # True = cria vista 3D isometrica se nao houver

DIRECAO_VISTA_3D = "FSD"  # Direcao padrao da vista 3D (veja DIRECOES_VISTA_3D)
FATOR_DISTANCIA_VISTA_3D = 2.0
TAMANHO_MINIMO_VISTA_3D = 3.0

GRAVAR_ORIENTACAO_VISTA_3D = True

# Nomes tipicos da vista 3D criada automaticamente pelo Revit.
NOMES_PADRAO_VISTA_3D = (
    "view 1", "vista 1", "vista 3d", "vista 3d {3d}", "3d view", "{3d}",
    "vue 1", "vue 3d", "vue 3d {3d}",
)

# --- VISTA 3D: direcoes (as 6 vistas de um cubo pelo ViewCube) ---------------
# Cada direcao e' (forward, up) - vetores de ViewOrientation3D.
# O par PRECISA ser ortogonal (forward . up == 0), senao o Revit lanca
# "up vector is not perpendicular to the view direction".
# FSD/FSE/TSD/TSE: camera ACIMA do modelo (up com Z > 0).
# FID/FIE: camera ABAIXO do modelo (up com Z < 0) - olhando de baixo para cima.
# As 4 primeiras tem os mesmos vetores do SE/SO/NE/NO antigos: os nomes antigos
# continuam aceitos (veja DIRECOES_VISTA_3D_APELIDOS) para nao quebrar grafos
# que ja usavam os rotulos "SE Isometric" etc.

DIRECOES_VISTA_3D = {
    # ---------------------------------------------------------------------
    #  ORTOGRAFICAS (camera alinhada a um dos 6 eixos do ViewCube)
    # ---------------------------------------------------------------------
    # Topo: camera acima, olhando para baixo (Z-), +Y para cima na tela
    "TOPO":      ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    # Frontal: camera em -Y, olhando para +Y, +Z para cima
    "FRONTAL":   ((0.0, 1.0, 0.0),  (0.0, 0.0, 1.0)),
    # Esquerda: camera em -X, olhando para +X, +Z para cima
    "ESQUERDA":  ((1.0, 0.0, 0.0),  (0.0, 0.0, 1.0)),
    # Direita: camera em +X, olhando para -X, +Z para cima
    "DIREITA":   ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    # Posterior: camera em +Y, olhando para -Y, +Z para cima
    "POSTERIOR": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    # Inferior: camera abaixo, olhando para cima (Z+), +Y para cima na tela
    "INFERIOR":  ((0.0, 0.0, 1.0),  (0.0, 1.0, 0.0)),

    # ---------------------------------------------------------------------
    #  ISOMETRICAS (camera na diagonal, um canto do cubo por vez)
    # ---------------------------------------------------------------------
    # Frente-Superior-Direita (canto SE, acima) - era "SE Isometric"
    "FSD": ((-1.0, 1.0, -1.0), (-1.0, 1.0, 2.0)),
    # Frente-Superior-Esquerda (canto SO, acima) - era "SO Isometric"
    "FSE": ((1.0, 1.0, -1.0), (1.0, 1.0, 2.0)),
    # Tras-Superior-Direita (canto NE, acima) - era "NE Isometric"
    "TSD": ((-1.0, -1.0, -1.0), (-1.0, -1.0, 2.0)),
    # Tras-Superior-Esquerda (canto NO, acima) - era "NO Isometric"
    "TSE": ((1.0, -1.0, -1.0), (1.0, -1.0, 2.0)),
    # Frente-Inferior-Direita (canto SE, ABAIXO)
    "FID": ((-1.0, 1.0, 1.0), (-1.0, 1.0, -2.0)),
    # Frente-Inferior-Esquerda (canto SO, ABAIXO)
    "FIE": ((1.0, 1.0, 1.0), (1.0, 1.0, -2.0)),
}

# Direcao padrao (usada quando IN[2] nao vem ou nao e' reconhecido).
DIRECAO_VISTA_3D_PADRAO = "FSD"

# --- ENTRADAS DO DYNAMO: mapa de "rotulo" -> "chave interna" -----------------
# IN[1]: tipo de vista que sera gravada como preview.
TIPOS_VISTA_PREVIEW = {
    "VISTA 3D": "VISTA_3D",
    "3D": "VISTA_3D",
    "PLANTA": "PLANTA",
    "CORTE": "CORTE",
    "DETALHE": "DETALHE",
    "ELEVACAO": "ELEVACAO",
    "ELEVAÇÃO": "ELEVACAO",
}

# Apelidos aceitos em IN[2] (Custom Selection) -> chave de DIRECOES_VISTA_3D.
# Os nomes antigos (SE/SO/NE/NO Isometric) continuam aceitos como atalho para
# as direcoes correspondentes: sao as MESMAS que FSD/FSE/TSD/TSE.
DIRECOES_VISTA_3D_APELIDOS = {
    # ---------------------------------------------------------------------
    #  ORTOGRAFICAS (rotulos do ViewCube)
    # ---------------------------------------------------------------------
    "TOPO":      "TOPO",
    "TOP":       "TOPO",
    "FRONTAL":   "FRONTAL",
    "FRONT":     "FRONTAL",
    "FRENTE":    "FRONTAL",
    "ESQUERDA":  "ESQUERDA",
    "LEFT":      "ESQUERDA",
    "DIREITA":   "DIREITA",
    "RIGHT":     "DIREITA",
    "POSTERIOR": "POSTERIOR",
    "BACK":      "POSTERIOR",
    "TRAS":      "POSTERIOR",
    "INFERIOR":  "INFERIOR",
    "BOTTOM":    "INFERIOR",
    "BASE":      "INFERIOR",

    # ---------------------------------------------------------------------
    #  ISOMETRICAS
    # ---------------------------------------------------------------------
    # --- as 6 vistas do cubo (nomes por extenso, como aparecem no Custom Selection)
    "FRENTE-SUPERIOR-DIREITA":  "FSD",
    "FRENTE-SUPERIOR-ESQUERDA": "FSE",
    "TRAS-SUPERIOR-DIREITA":    "TSD",
    "TRAS-SUPERIOR-ESQUERDA":   "TSE",
    "FRENTE-INFERIOR-DIREITA":  "FID",
    "FRENTE-INFERIOR-ESQUERDA": "FIE",
    # --- variacoes sem hifen / com underline (o normalizador acima ja tira
    #     espacos, mas nao hifens: aqui garantimos as duas grafias)
    "FRENTE SUPERIOR DIREITA":  "FSD",
    "FRENTE SUPERIOR ESQUERDA": "FSE",
    "TRAS SUPERIOR DIREITA":    "TSD",
    "TRAS SUPERIOR ESQUERDA":   "TSE",
    "FRENTE INFERIOR DIREITA":  "FID",
    "FRENTE INFERIOR ESQUERDA": "FIE",
    "FSD": "FSD", "FSE": "FSE", "TSD": "TSD",
    "TSE": "TSE", "FID": "FID", "FIE": "FIE",
    # --- apelidos antigos (SE/SO/NE/NO Isometric) -> mesmas direcoes
    "SE ISOMETRIC": "FSD",
    "SO ISOMETRIC": "FSE",
    "NE ISOMETRIC": "TSD",
    "NO ISOMETRIC": "TSE",
    "SE_ISOMETRIC": "FSD",
    "SO_ISOMETRIC": "FSE",
    "NE_ISOMETRIC": "TSD",
    "NO_ISOMETRIC": "TSE",
}

# IN[3]: rotulo -> chave de ESTILOS_VISUAIS_VISTA_3D (o que nao estiver aqui
# cai em _APELIDOS_ESTILO_VISUAL / na propria chave, via chave_do_estilo_visual)
ESTILOS_VISUAIS_APELIDOS = {
    "WIREFRAME": "ESTRUTURA_ARAME",
    "HIDDEN LINES": "LINHAS_OCULTAS",
    "HIDDEN_LINES": "LINHAS_OCULTAS",
    "SHADING": "SOMBREADO",
    "SHADING WITH EDGES": "SOMBREADO_COM_ARESTAS",
    "SHADING_WITH_EDGES": "SOMBREADO_COM_ARESTAS",
    "FLAT COLORS": "CORES_CONSISTENTES",
    "FLAT_COLORS": "CORES_CONSISTENTES",
    "REALISTIC": "REALISTA",
    "REALISTIC WITH EDGES": "REALISTA_COM_ARESTAS",
    "REALISTIC_WITH_EDGES": "REALISTA_COM_ARESTAS",
}

# --- VISTA 3D: estilo visual (View.DisplayStyle) -----------------------------
ESTILO_VISUAL_VISTA_3D = "SOMBREADO"

ESTILOS_VISUAIS_VISTA_3D = {
    "ESTRUTURA_ARAME": DisplayStyle.Wireframe,
    "LINHAS_OCULTAS": DisplayStyle.HLR,
    "SOMBREADO": DisplayStyle.Shading,
    "CORES_CONSISTENTES": DisplayStyle.FlatColors,
    "REALISTA": DisplayStyle.Realistic,
}

for _chave, _nome_do_valor in (("SOMBREADO_COM_ARESTAS", "ShadingWithEdges"),
                               ("REALISTA_COM_ARESTAS", "RealisticWithEdges")):
    _valor = getattr(DisplayStyle, _nome_do_valor, None)
    if _valor is not None:
        ESTILOS_VISUAIS_VISTA_3D[_chave] = _valor
del _chave, _nome_do_valor, _valor

_APELIDOS_ESTILO_VISUAL = {
    "WIREFRAME": "ESTRUTURA_ARAME",
    "ESTRUTURA_DE_ARAME": "ESTRUTURA_ARAME",
    "HLR": "LINHAS_OCULTAS",
    "HIDDEN_LINES": "LINHAS_OCULTAS",
    "SHADING": "SOMBREADO",
    "SHADED": "SOMBREADO",
    "SHADING_WITH_EDGES": "SOMBREADO_COM_ARESTAS",
    "SHADED_WITH_EDGES": "SOMBREADO_COM_ARESTAS",
    "FLAT_COLORS": "CORES_CONSISTENTES",
    "FLATCOLORS": "CORES_CONSISTENTES",
    "REALISTIC": "REALISTA",
    "REALISTIC_WITH_EDGES": "REALISTA_COM_ARESTAS",
}

# --- Arestas visiveis ("Sombreado com arestas") ------------------------------
# True (padrao, como no README): SOMBREADO/REALISTA sao trocados pela variante
# COM arestas; False: vale exatamente o estilo escolhido em IN[3].
MOSTRAR_ARESTAS_VISTA_3D = True

_ESTILOS_COM_ARESTAS = {
    "SOMBREADO": "SOMBREADO_COM_ARESTAS",
    "REALISTA": "REALISTA_COM_ARESTAS",
}

# --- Categorias ocultas na vista (por categoria) -----------------------------
OCULTAR_CATEGORIAS_VISTA_3D = True

# Lista PADRAO de categorias ocultas. Vale como fallback quando o tipo efetivo
# do preview nao esta em CATEGORIAS_OCULTAS_POR_TIPO (ou quando o script caiu
# no fallback da Vista 3D por algum motivo). Mantida por compatibilidade com
# versoes anteriores deste arquivo.
CATEGORIAS_OCULTAS_VISTA_3D = (
    "OST_Dimensions",
    "OST_TextNotes",
    "OST_GenericAnnotation",
    "OST_Levels",
    "OST_Grids",
    "OST_CLines",
    "OST_ReferenceLines",
    "OST_ReferencePoints",
    "OST_Walls",
    "OST_Floors",
    "OST_Ceilings",
    "OST_Roofs",
)

# Lista POR TIPO de vista de preview. Faz sentido ocultar de forma diferente
# em cada tipo: numa PLANTA os niveis e eixos costumam ser uteis (a lista
# abaixo os mantem); numa VISTA 3D de preview eles sujam a miniatura (a lista
# abaixo os esconde). A categoria da propria familia NUNCA e ocultada, seja
# qual for a lista (garantido em ocultar_categorias_vista_3d()).
CATEGORIAS_OCULTAS_POR_TIPO = {
    # Vista 3D: preview "limpo" - cotas, textos, niveis, eixos, refs, contexto
    "VISTA_3D": (
        "OST_Dimensions", "OST_TextNotes", "OST_GenericAnnotation",
        "OST_Levels", "OST_Grids", "OST_CLines",
        "OST_ReferenceLines", "OST_ReferencePoints",
        "OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs",
    ),
    # Planta: mantem niveis e eixos (uteis no contexto); tira anotacao e refs
    "PLANTA": (
        "OST_Dimensions", "OST_TextNotes", "OST_GenericAnnotation",
        "OST_CLines", "OST_ReferenceLines", "OST_ReferencePoints",
        "OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs",
    ),
    # Corte: mesma logica da planta (niveis/eixos tem valor no corte)
    "CORTE": (
        "OST_Dimensions", "OST_TextNotes", "OST_GenericAnnotation",
        "OST_CLines", "OST_ReferenceLines", "OST_ReferencePoints",
        "OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs",
    ),
    # Elevacao: sem eixos (que nao aparecem de frente), mas mantem niveis
    "ELEVACAO": (
        "OST_Dimensions", "OST_TextNotes", "OST_GenericAnnotation",
        "OST_Levels", "OST_CLines",
        "OST_ReferenceLines", "OST_ReferencePoints",
        "OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs",
    ),
    # Detalhe: vista de desenho - praticamente nada a ocultar
    "DETALHE": (
        "OST_CLines", "OST_ReferenceLines", "OST_ReferencePoints",
    ),
}

# --- Comparacao dos nomes de vista -------------------------------------------
_ACENTOS_PARA_ASCII = {
    u"á": u"a", u"à": u"a", u"â": u"a", u"ã": u"a", u"ä": u"a", u"å": u"a",
    u"é": u"e", u"è": u"e", u"ê": u"e", u"ë": u"e",
    u"í": u"i", u"ì": u"i", u"î": u"i", u"ï": u"i",
    u"ó": u"o", u"ò": u"o", u"ô": u"o", u"õ": u"o", u"ö": u"o",
    u"ú": u"u", u"ù": u"u", u"û": u"u", u"ü": u"u",
    u"ç": u"c", u"ñ": u"n", u"ý": u"y", u"ÿ": u"y",
    u"ª": u"a", u"º": u"o",
    u"\u2018": u"'", u"\u2019": u"'", u"\u02bc": u"'", u"\u00b4": u"'",
    u"`": u"'",
    u"\u2013": u"-", u"\u2014": u"-", u"\u2212": u"-",
}
_TABELA_ACENTOS = str.maketrans(_ACENTOS_PARA_ASCII)


def chave_nome_vista(nome):
    """Chave normalizada de um nome de vista."""
    chave = (nome or "").strip().lower()
    chave = chave.translate(_TABELA_ACENTOS)
    chave = re.sub(r"[\s\u00a0\u202f]+", " ", chave)
    return chave.strip(" .")


# --- Nomes de vistas em portugues (Brasil) -----------------------------------
RENOMEAR_VISTAS_PT_BR = True
RELATAR_VISTAS_NAO_TRADUZIDAS = False

NOMES_VISTAS_PT_BR = {
    # --- Ingles ---
    "{3d}": "Vista 3D",
    "3d view": "Vista 3D",
    "default 3d view": "Vista 3D",
    "ref. level": "Nível de Referência",
    "ref level": "Nível de Referência",
    "reference level": "Nível de Referência",
    "ref. plane": "Nível de Referência",
    "ref plane": "Nível de Referência",
    "ground floor": "Piso Térreo",
    "ground level": "Piso Térreo",
    "front": "Parte Frontal",
    "back": "Parte Posterior",
    "rear": "Parte Posterior",
    "left": "Esquerda",
    "right": "Direita",
    "top": "Superior",
    "bottom": "Inferior",
    "north": "Norte",
    "south": "Sul",
    "east": "Leste",
    "west": "Oeste",
    "exterior": "Exterior",
    "interior": "Interior",
    "floor plan": "Planta de Piso",
    "ceiling plan": "Planta de Forro",
    "site plan": "Planta de Implantação",
    "area plan": "Planta de Área",
    "structural plan": "Planta Estrutural",
    "ceiling": "Forro",
    "legend": "Legenda",
    "walkthrough": "Passeio",
    "thumbnail": "Miniatura",
    "section": "Corte",
    "elevation": "Elevação",
    "detail": "Detalhe",
    # --- Frances ---
    "vue 3d": "Vista 3D",
    "vue 3d {3d}": "Vista 3D",
    "vue 1": "Vista 1",
    "niveau de référence": "Nível de Referência",
    "niveau de réf.": "Nível de Referência",
    "niveau ref.": "Nível de Referência",
    "ref. niveau": "Nível de Referência",
    "face avant": "Parte Frontal",
    "élévation avant": "Parte Frontal",
    "avant": "Parte Frontal",
    "face arrière": "Parte Posterior",
    "élévation arrière": "Parte Posterior",
    "arrière": "Parte Posterior",
    "face gauche": "Esquerda",
    "gauche": "Esquerda",
    "face droite": "Direita",
    "droite": "Direita",
    "dessus": "Superior",
    "vue de dessus": "Superior",
    "dessous": "Inferior",
    "vue de dessous": "Inferior",
    "nord": "Norte",
    "sud": "Sul",
    "est": "Leste",
    "ouest": "Oeste",
    "extérieur": "Exterior",
    "intérieur": "Interior",
    "plan d'étage": "Planta de Piso",
    "vue en plan": "Planta de Piso",
    "plan de plafond": "Planta de Forro",
    "plafond": "Forro",
    "plan de masse": "Planta de Implantação",
    "plan d'implantation": "Planta de Implantação",
    "plan de surface": "Planta de Área",
    "légende": "Legenda",
    "promenade": "Passeio",
    "coupe": "Corte",
    # --- Espanhol ---
    "vista 3d": "Vista 3D",
    "vista 3d {3d}": "Vista 3D",
    "vista 1": "Vista 1",
    "nivel de referencia": "Nível de Referência",
    "nivel de ref.": "Nível de Referência",
    "nivel ref.": "Nível de Referência",
    "ref. nivel": "Nível de Referência",
    "frontal": "Parte Frontal",
    "frente": "Parte Frontal",
    "alzado frontal": "Parte Frontal",
    "posterior": "Parte Posterior",
    "atrás": "Parte Posterior",
    "detrás": "Parte Posterior",
    "alzado posterior": "Parte Posterior",
    "izquierda": "Esquerda",
    "izquierdo": "Esquerda",
    "alzado izquierdo": "Esquerda",
    "alzado izquierda": "Esquerda",
    "derecha": "Direita",
    "derecho": "Direita",
    "alzado derecho": "Direita",
    "alzado derecha": "Direita",
    "superior": "Superior",
    "inferior": "Inferior",
    "norte": "Norte",
    "sur": "Sul",
    "este": "Leste",
    "oeste": "Oeste",
    "planta de piso": "Planta de Piso",
    "planta baja": "Piso Térreo",
    "planta de techo": "Planta de Forro",
    "planta de emplazamiento": "Planta de Implantação",
    "planta de área": "Planta de Área",
    "planta de estructura": "Planta Estrutural",
    "techo": "Forro",
    "leyenda": "Legenda",
    "recorrido": "Passeio",
    "sección": "Corte",
    "alzado": "Elevação",
    "detalle": "Detalhe",
}

NOMES_VISTAS_PT_BR_NORMALIZADOS = {
    chave_nome_vista(nome): traducao for nome, traducao in NOMES_VISTAS_PT_BR.items()
}

REGRAS_NOMES_VISTAS_PT_BR = (
    (re.compile(r"^view\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^level\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^section\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^detail\s+(\d+)$"), "Detalhe {0}"),
    (re.compile(r"^elevation\s+(\d+)$"), "Elevação {0}"),
    (re.compile(r"^plan\s+(\d+)$"), "Planta {0}"),
    (re.compile(r"^vue\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^niveau\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^coupe\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^vue en plan\s+(\d+)$"), "Planta {0}"),
    (re.compile(r"^vista\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^nivel\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^seccion\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^detalle\s+(\d+)$"), "Detalhe {0}"),
    (re.compile(r"^alzado\s+(\d+)$"), "Elevação {0}"),
    (re.compile(r"^(?:vue|vista)\s+3d\s+(\d+)$"), "Vista 3D {0}"),
)

app = DocumentManager.Instance.CurrentUIApplication.Application


# -----------------------------------------------------------------------------
#  ENTRADAS DO DYNAMO (IN[1..3]) - resolucao das escolhas do usuario
# -----------------------------------------------------------------------------
def _normalizar_escolha(valor):
    """
    String de escolha: strip + espacos internos reduzidos (caixa preservada -
    quem compara em caixa alta e' o _resolver_entrada()).
    Tambem troca '_' e '-' por espaco, para que "Frente-Superior-Direita",
    "Frente Superior Direita" e "FRENTE_SUPERIOR_DIREITA" caiam na mesma
    chave de busca (o dicionario de apelidos usa a forma com hifen).
    """
    if valor is None:
        return None
    if not isinstance(valor, str):
        return None
    texto = " ".join(valor.replace("_", " ").replace("-", " ").split()).strip()
    if not texto:
        return None
    return texto


def _resolver_entrada(valor_bruto, padrao, mapa, descricao, avisos):
    """
    Resolve uma entrada IN[x] do Dynamo:
      - None / vazio          -> devolve 'padrao' (constante de configuracao)
      - chave/rotulo valido   -> devolve a chave interna
      - valor desconhecido    -> devolve 'padrao' + aviso em 'avisos'

    A busca e feita em duas etapas:
      1) a propria string (com '-'/'_' -> espaco e caixa alta);
      2) as chaves internas do dicionario (valores), para que a string
         "FSD", "SOMBREADO" etc. tambem funcione sem estar no mapa.
    """
    escolha = _normalizar_escolha(valor_bruto)
    if escolha is None:
        return padrao
    chave = escolha.upper()

    # 1) bate em algum rotulo/apelido do mapa?
    if chave in mapa:
        return mapa[chave]
    # 2) e' uma chave interna valida (valor do mapa)?
    if chave in mapa.values():
        return chave
    # 3) e' o proprio padrao?
    if chave == padrao:
        return chave
    avisos.append("{0}: valor desconhecido '{1}' - usando padrao '{2}'".format(
        descricao, escolha, padrao))
    return padrao


def _ler_in(indice):
    """Le IN[indice] com seguranca (IN pode ter menos elementos)."""
    try:
        return IN[indice]
    except Exception:
        return None


def _resolver_entradas_dynamo():
    """
    Le IN[1..3] (opcionais) e devolve (tipo_vista, direcao3d, estilo_visual),
    ja com fallback para as constantes de configuracao e avisos das escolhas
    invalidas. Devolve TAMBEM a lista de avisos (para entrar no OUT).
    """
    avisos = []

    tipo_vista = _resolver_entrada(
        _ler_in(1), "VISTA_3D", TIPOS_VISTA_PREVIEW,
        "IN[1] (tipo de vista do preview)", avisos)

    # Como o _normalizar_escolha agora troca '-'/'_' por espaco, as chaves dos
    # apelidos tambem precisam ser procuradas nessa forma normalizada. Por isso
    # montamos um dicionario com as chaves ja normalizadas (uma vez, na carga).
    apelidos_normalizados = {
        " ".join(chave.replace("_", " ").replace("-", " ").split()).upper(): valor
        for chave, valor in DIRECOES_VISTA_3D_APELIDOS.items()
    }
    direcao = _resolver_entrada(
        _ler_in(2), DIRECAO_VISTA_3D, apelidos_normalizados,
        "IN[2] (isometrica da vista 3D)", avisos)
    if direcao not in DIRECOES_VISTA_3D:
        avisos.append("IN[2] (isometrica): '{0}' nao existe em DIRECOES_VISTA_3D "
                      "- usando '{1}'".format(direcao, DIRECAO_VISTA_3D))
        direcao = DIRECAO_VISTA_3D

    estilo_bruto = _ler_in(3)
    estilo_padrao = ESTILO_VISUAL_VISTA_3D
    if _normalizar_escolha(estilo_bruto) is None:
        estilo = estilo_padrao
    else:
        escolha = _normalizar_escolha(estilo_bruto).upper()
        # Resolve rotulos amigaveis ("Shading With Edges") para as chaves
        # internas antes de entregar para chave_do_estilo_visual().
        estilo = ESTILOS_VISUAIS_APELIDOS.get(escolha, escolha)
        if chave_do_estilo_visual(estilo) is None:
            avisos.append("IN[3] (estilo visual): valor desconhecido '{0}' "
                          "- usando padrao '{1}'".format(estilo_bruto, estilo_padrao))
            estilo = estilo_padrao

    return tipo_vista, direcao, estilo, avisos


# -----------------------------------------------------------------------------
#  FUNCOES AUXILIARES
# -----------------------------------------------------------------------------
def silenciar_avisos(transacao, avisos=None):
    """Instala um IFailuresPreprocessor para descartar avisos e evitar modais."""
    try:
        def anotar(texto):
            if avisos is None:
                return
            try:
                texto = " ".join(str(texto).split())
            except Exception:
                texto = ""
            if texto:
                avisos.append("Revit: {0} (transacao desfeita)".format(texto))

        class _SemAvisos(IFailuresPreprocessor):
            def PreprocessFailures(self, acessor):
                try:
                    acessor.DeleteAllWarnings()
                except Exception:
                    pass
                try:
                    for falha in acessor.GetFailureMessages():
                        if falha.GetSeverity() == FailureSeverity.Error:
                            anotar(falha.GetDescriptionText())
                            return FailureProcessingResult.ProceedWithRollBack
                except Exception:
                    pass
                return FailureProcessingResult.Continue

        opcoes = transacao.GetFailureHandlingOptions()
        opcoes.SetFailuresPreprocessor(_SemAvisos())
        opcoes.SetClearAfterRollback(True)
        transacao.SetFailureHandlingOptions(opcoes)
    except Exception:
        pass


# -----------------------------------------------------------------------------
#  RESPOSTAS AUTOMATICAS NAS JANELAS DE AVISO DO REVIT
# -----------------------------------------------------------------------------
_handler_dialogos = None
_dialogos_respondidos = []


def _atributo_janela(argumentos, atributo):
    try:
        return str(getattr(argumentos, atributo) or "")
    except Exception:
        return ""


def _ao_mostrar_dialogo(remetente, argumentos):
    identificador = _atributo_janela(argumentos, "DialogId")
    if identificador in IDS_DIALOGOS_IGNORADOS:
        return

    mensagem = " ".join(_atributo_janela(argumentos, "Message").split())
    try:
        argumentos.OverrideResult(RESULTADO_OK)
        if REGISTRAR_DIALOGOS:
            _dialogos_respondidos.append("JANELA | OK: {0}{1}".format(
                identificador if identificador else "(sem id)",
                " | " + mensagem if mensagem else ""))
    except Exception as ex:
        if REGISTRAR_DIALOGOS:
            _dialogos_respondidos.append(
                "AVISO  | janela do Revit '{0}' nao pode ser respondida: {1}".format(
                    identificador if identificador else "(sem id)", ex))


def ativar_respostas_automaticas():
    global _handler_dialogos
    if not RESPONDER_DIALOGOS_COM_OK:
        return False
    try:
        _handler_dialogos = _ao_mostrar_dialogo
        DocumentManager.Instance.CurrentUIApplication.DialogBoxShowing += _handler_dialogos
        return True
    except Exception as ex:
        _handler_dialogos = None
        _dialogos_respondidos.append(
            "AVISO  | nao foi possivel assinar o evento de janelas do Revit "
            "(responda manualmente): {0}".format(ex))
        return False


def desativar_respostas_automaticas():
    global _handler_dialogos
    if _handler_dialogos is None:
        return
    try:
        DocumentManager.Instance.CurrentUIApplication.DialogBoxShowing -= _handler_dialogos
    except Exception:
        pass
    _handler_dialogos = None


# -----------------------------------------------------------------------------
#  UNIDADES
# -----------------------------------------------------------------------------
def aplicar_formato(units, spec, tipo_unidade, accuracy, avisos):
    try:
        # No Revit 2026 o IsModifiableSpec(ForgeTypeId) foi alterado e lanca
        # "No method matches given arguments". Ele e' apenas uma PRECAUCAO:
        # se o spec nao for modificavel, o proprio SetFormatOptions abaixo
        # reclama. Por isso tentamos a checagem e, se ela nao existir/ falhar,
        # seguimos direto para a aplicacao.
        try:
            if not units.IsModifiableSpec(spec):
                return
        except Exception:
            pass   # IsModifiableSpec indisponivel nesta versao: segue em frente

        opcoes = units.GetFormatOptions(spec)
        try:
            if opcoes.UseDefault:
                opcoes.UseDefault = False
        except Exception:
            pass
        opcoes.SetUnitTypeId(tipo_unidade)
        try:
            opcoes.UseDigitGrouping = USAR_AGRUPAMENTO_UNIDADES
        except Exception:
            pass
        if accuracy is not None:
            opcoes.Accuracy = accuracy
        units.SetFormatOptions(spec, opcoes)
    except Exception as ex:
        avisos.append("{0}: {1}".format(spec.TypeId, ex))


def configurar_unidades(doc, avisos):
    t = Transaction(doc, "Configurar unidades (SI)")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        if SISTEMA_METRICO_COMPLETO:
            units = Units(UnitSystem.Metric)
        else:
            units = doc.GetUnits()

        units.DecimalSymbol = SYMBOL_DECIMAL
        units.DigitGroupingSymbol = SYMBOL_AGRUPAMENTO
        try:
            units.DigitGroupingAmount = DigitGroupingAmount.Three
        except Exception:
            pass

        aplicar_formato(units, SpecTypeId.Length, UNIDADE_COMPRIMENTO,
                        ACCURACY_COMPRIMENTO, avisos)
        aplicar_formato(units, SpecTypeId.Area, UNIDADE_AREA, None, avisos)
        aplicar_formato(units, SpecTypeId.Volume, UNIDADE_VOLUME, None, avisos)

        doc.SetUnits(units)
        t.Commit()
        return True
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Unidades: {0}".format(ex))
        return False


def contar(itens):
    if itens is None:
        return 0
    try:
        return len(itens)
    except Exception:
        pass
    try:
        return int(itens.Count)
    except Exception:
        pass
    try:
        return int(itens.Count())
    except Exception:
        return 0


# -----------------------------------------------------------------------------
#  PURGE UNUSED
# -----------------------------------------------------------------------------
def purgar_nao_utilizados(doc, avisos):
    total = 0
    for _passada in range(MAX_PASSES_PURGE):
        try:
            nao_utilizados = doc.GetUnusedElements(HashSet[ElementId]())
        except Exception as ex:
            avisos.append("Purge (consulta): {0}".format(ex))
            break

        if contar(nao_utilizados) == 0:
            break

        ids = List[ElementId]()
        for elemento_id in nao_utilizados:
            ids.Add(elemento_id)

        t = Transaction(doc, "Eliminar nao utilizados")
        silenciar_avisos(t, avisos)
        t.Start()
        try:
            removidos = doc.Delete(ids)
            estado = t.Commit()
        except Exception as ex:
            try:
                t.RollBack()
            except Exception:
                pass
            avisos.append("Purge (exclusao): {0}".format(ex))
            break

        if estado != TransactionStatus.Committed:
            avisos.append("Purge: exclusao desfeita pelo Revit ({0})".format(estado))
            break

        quantidade = contar(removidos)
        total += quantidade
        if quantidade == 0:
            break

    return total


# -----------------------------------------------------------------------------
#  VISTAS: auxiliares
# -----------------------------------------------------------------------------
def nome_da_vista(vista):
    if vista is None:
        return "nao"
    try:
        return vista.Name
    except Exception:
        return "nao"


def nome_vista_em_uso(doc, nome):
    try:
        for vista in FilteredElementCollector(doc).OfClass(View):
            try:
                if vista.Name == nome:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def renomear_vista(doc, vista, novo_nome, avisos):
    atual = nome_da_vista(vista)
    if vista is None or atual == "nao" or not novo_nome:
        return False
    if atual == novo_nome:
        return True

    t = Transaction(doc, "Renomear vista")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        vista.Name = novo_nome
        t.Commit()
        return True
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Renomear vista '{0}' -> '{1}': {2}".format(atual, novo_nome, ex))
        return False


def vista_valida_para_preview(doc, vista):
    """True se a vista pode ser usada como PreviewViewId (checagem da API)."""
    if vista is None:
        return False
    try:
        return bool(doc.GetDocumentPreviewSettings().IsViewIdValidForPreview(vista.Id))
    except Exception:
        return False


# -----------------------------------------------------------------------------
#  VISTA 3D: obtencao, criacao, nome, direcao
# -----------------------------------------------------------------------------
def obter_vista_3d(doc, avisos=None):
    if avisos is None:
        avisos = []

    vistas = []
    try:
        for vista in FilteredElementCollector(doc).OfClass(View3D):
            try:
                if not vista.IsTemplate:
                    vistas.append(vista)
            except Exception:
                continue
    except Exception:
        pass

    for vista in vistas:
        if nome_da_vista(vista) == NOME_VISTA_3D:
            return vista

    candidatas = []
    try:
        preview = doc.GetDocumentPreviewSettings()
        for vista in vistas:
            try:
                if preview.IsViewIdValidForPreview(vista.Id):
                    candidatas.append(vista)
            except Exception:
                continue
    except Exception:
        candidatas = []

    if not candidatas:
        candidatas = vistas

    def preferencia(vista):
        nome = chave_nome_vista(nome_da_vista(vista))
        if nome in NOMES_PADRAO_VISTA_3D:
            return (0, NOMES_PADRAO_VISTA_3D.index(nome))
        return (1, 0)

    if candidatas:
        return sorted(candidatas, key=preferencia)[0]

    if CRIAR_VISTA_3D_SE_FALTAR:
        return criar_vista_3d(doc, avisos)

    return None


def tipo_vista_3d(doc):
    try:
        for tipo in FilteredElementCollector(doc).OfClass(ViewFamilyType):
            try:
                if tipo.ViewFamily == ViewFamily.ThreeDimensional:
                    return tipo
            except Exception:
                continue
    except Exception:
        pass
    return None


def criar_vista_3d(doc, avisos):
    tipo = tipo_vista_3d(doc)
    if tipo is None:
        avisos.append("Vista 3D: nao existe tipo de vista 3D para criar a vista")
        return None

    t = Transaction(doc, "Criar vista 3D")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        vista = View3D.CreateIsometric(doc, tipo.Id)
        t.Commit()
        return vista
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Vista 3D (criacao): {0}".format(ex))
        return None


def padronizar_nome_vista_3d(doc, vista, avisos):
    atual = nome_da_vista(vista)
    if vista is None or atual == "nao":
        return False
    if atual == NOME_VISTA_3D:
        return True
    if nome_vista_em_uso(doc, NOME_VISTA_3D):
        avisos.append("Vista 3D: o nome '{0}' ja e usado por outra vista".format(NOME_VISTA_3D))
        return False
    return renomear_vista(doc, vista, NOME_VISTA_3D, avisos)


def centro_e_tamanho_do_modelo(doc, vista):
    minimo = None
    maximo = None
    try:
        for elemento in FilteredElementCollector(doc).WhereElementIsNotElementType():
            caixa = None
            for alvo in (vista, None):
                try:
                    caixa = elemento.get_BoundingBox(alvo)
                except Exception:
                    caixa = None
                if caixa is not None and caixa.Min is not None and caixa.Max is not None:
                    break
            if caixa is None or caixa.Min is None or caixa.Max is None:
                continue

            if minimo is None:
                minimo = caixa.Min
                maximo = caixa.Max
            else:
                minimo = XYZ(min(minimo.X, caixa.Min.X),
                             min(minimo.Y, caixa.Min.Y),
                             min(minimo.Z, caixa.Min.Z))
                maximo = XYZ(max(maximo.X, caixa.Max.X),
                             max(maximo.Y, caixa.Max.Y),
                             max(maximo.Z, caixa.Max.Z))
    except Exception:
        pass

    if minimo is None:
        return XYZ(0.0, 0.0, 0.0), TAMANHO_MINIMO_VISTA_3D

    centro = minimo.Add(maximo).Multiply(0.5)
    diagonal = maximo.Subtract(minimo).GetLength()
    return centro, max(diagonal, TAMANHO_MINIMO_VISTA_3D)


def orientar_vista_3d(doc, vista, avisos, direcao_chave):
    """
    Orienta a vista 3D na direcao escolhida (IN[2]). 'direcao_chave' e' a chave
    de DIRECOES_VISTA_3D (ex.: "SE_ISOMETRIC"). Aplica a orientacao TEMPORARIA
    (SetOrientation) e, se GRAVAR_ORIENTACAO_VISTA_3D, converte para SALVA
    (SaveOrientation) - so funciona porque a vista 3D foi renomeada antes.
    """
    direcao = DIRECOES_VISTA_3D.get(direcao_chave)
    if vista is None or direcao is None:
        return False

    try:
        if vista.IsLocked:
            vista.Unlock()
    except Exception:
        pass

    centro, tamanho = centro_e_tamanho_do_modelo(doc, vista)
    frente = XYZ(direcao[0][0], direcao[0][1], direcao[0][2]).Normalize()
    cima = XYZ(direcao[1][0], direcao[1][1], direcao[1][2]).Normalize()
    olho = centro.Subtract(frente.Multiply(tamanho * FATOR_DISTANCIA_VISTA_3D))

    t = Transaction(doc, "Orientar vista 3D ({0})".format(direcao_chave))
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        vista.SetOrientation(ViewOrientation3D(olho, cima, frente))
        if GRAVAR_ORIENTACAO_VISTA_3D:
            try:
                if vista.CanSaveOrientation():
                    vista.SaveOrientation()
                else:
                    avisos.append("Vista 3D: a orientacao nao pode ser gravada "
                                  "(a vista ainda e a vista 3D padrao do arquivo)")
            except Exception as ex:
                avisos.append("Vista 3D (gravar orientacao): {0}".format(ex))
        t.Commit()
        return True
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Vista 3D (orientacao): {0}".format(ex))
        return False


# -----------------------------------------------------------------------------
#  VISTAS NAO-3D: obtencao / criacao (Planta, Corte, Detalhe, Elevacao)
# -----------------------------------------------------------------------------
def _vista_por_familia(doc, view_family):
    """Primeira View nao-template com ViewFamily == 'view_family'."""
    try:
        for vista in FilteredElementCollector(doc).OfClass(View):
            try:
                if vista.IsTemplate:
                    continue
                if vista.ViewType == ViewType.ThreeD:
                    continue
                if vista.ViewFamily == view_family:
                    return vista
            except Exception:
                continue
    except Exception:
        pass
    return None


def _tipo_vista(doc, view_family):
    """ViewFamilyType para 'view_family' (o primeiro que existir)."""
    try:
        for tipo in FilteredElementCollector(doc).OfClass(ViewFamilyType):
            try:
                if tipo.ViewFamily == view_family:
                    return tipo
            except Exception:
                continue
    except Exception:
        pass
    return None


def obter_ou_criar_vista_planta(doc, avisos):
    """ViewPlan (Planta de Piso). Devolve a vista ou None."""
    vista = _vista_por_familia(doc, ViewFamily.FloorPlan)
    if vista is not None:
        return vista

    tipo = _tipo_vista(doc, ViewFamily.FloorPlan)
    if tipo is None:
        avisos.append("Planta: nao existe ViewFamilyType de planta")
        return None

    # Nivel: usa o primeiro nivel do documento (se houver).
    nivel = None
    try:
        for elemento in FilteredElementCollector(doc).OfClass(Level):
            nivel = elemento
            break
    except Exception:
        nivel = None
    if nivel is None:
        avisos.append("Planta: nao existe nivel no documento para criar a vista")
        return None

    t = Transaction(doc, "Criar vista de planta")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        nova = ViewPlan.Create(doc, tipo.Id, nivel.Id)
        t.Commit()
        return nova
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Planta (criacao): {0}".format(ex))
        return None


def obter_ou_criar_vista_corte(doc, avisos):
    """
    ViewSection (Corte). Se nao existir, tenta criar um corte pela BoundingBox
    da geometria. Devolve a vista ou None.
    """
    vista = _vista_por_familia(doc, ViewFamily.Section)
    if vista is not None:
        return vista

    tipo = _tipo_vista(doc, ViewFamily.Section)
    if tipo is None:
        avisos.append("Corte: nao existe ViewFamilyType de corte")
        return None

    # Caixa do modelo -> retangulo do corte (BoundingBoxXYZ).
    try:
        caixa = BoundingBoxXYZ()
        minimo = None
        maximo = None
        for elemento in FilteredElementCollector(doc).WhereElementIsNotElementType():
            try:
                cx = elemento.get_BoundingBox(None)
            except Exception:
                cx = None
            if cx is None or cx.Min is None or cx.Max is None:
                continue
            if minimo is None:
                minimo, maximo = cx.Min, cx.Max
            else:
                minimo = XYZ(min(minimo.X, cx.Min.X),
                             min(minimo.Y, cx.Min.Y),
                             min(minimo.Z, cx.Min.Z))
                maximo = XYZ(max(maximo.X, cx.Max.X),
                             max(maximo.Y, cx.Max.Y),
                             max(maximo.Z, cx.Max.Z))
        if minimo is None:
            avisos.append("Corte: a familia nao tem geometria para enquadrar")
            return None

        # Caixa do corte: secciona ao longo do eixo X (olhando para -X).
        caixa.Min = XYZ(minimo.X, minimo.Y - 1.0, minimo.Z - 1.0)
        caixa.Max = XYZ(minimo.X, maximo.Y + 1.0, maximo.Z + 1.0)
        # Direcao da vista do corte (para a esquerda), com up +Z.
        caixa.Transform = Transform.Identity
    except Exception as ex:
        avisos.append("Corte (caixa): {0}".format(ex))
        return None

    t = Transaction(doc, "Criar vista de corte")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        nova = ViewSection.CreateSection(doc, tipo.Id, caixa)
        t.Commit()
        return nova
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Corte (criacao): {0}".format(ex))
        return None


def obter_ou_criar_vista_detalhe(doc, avisos):
    """
    ViewDrafting (Detalhe). ViewDrafting.Create(doc, tipo.Id).
    """
    vista = _vista_por_familia(doc, ViewFamily.Detail)
    if vista is not None:
        return vista

    tipo = _tipo_vista(doc, ViewFamily.Detail)
    if tipo is None:
        avisos.append("Detalhe: nao existe ViewFamilyType de detalhe")
        return None

    t = Transaction(doc, "Criar vista de detalhe")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        nova = ViewDrafting.Create(doc, tipo.Id)
        t.Commit()
        return nova
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Detalhe (criacao): {0}".format(ex))
        return None


def obter_ou_criar_vista_elevacao(doc, avisos):
    """
    ViewSection (Elevacao). O Revit NAO tem ViewFamily.Elevation como tipo
    de ViewFamilyType utilizavel em ViewSection.CreateSection: elevacao e'
    criada por ElevationMarker ou por um ViewFamilyType de Section. Aqui
    usamos um ViewFamilyType de Section (mesmo caminho do corte) - o que muda
    e' a orientacao da caixa (olhando de frente, ao longo de -Y).
    """
    vista = _vista_por_familia(doc, ViewFamily.Elevation)
    if vista is not None:
        return vista

    # Fallback: aceita um tipo de Section (que ViewSection.CreateSection aceita)
    tipo = _tipo_vista(doc, ViewFamily.Elevation)
    if tipo is None:
        tipo = _tipo_vista(doc, ViewFamily.Section)
    if tipo is None:
        avisos.append("Elevacao: nao existe ViewFamilyType de elevacao nem de corte")
        return None

    try:
        caixa = BoundingBoxXYZ()
        minimo = None
        maximo = None
        for elemento in FilteredElementCollector(doc).WhereElementIsNotElementType():
            try:
                cx = elemento.get_BoundingBox(None)
            except Exception:
                cx = None
            if cx is None or cx.Min is None or cx.Max is None:
                continue
            if minimo is None:
                minimo, maximo = cx.Min, cx.Max
            else:
                minimo = XYZ(min(minimo.X, cx.Min.X),
                             min(minimo.Y, cx.Min.Y),
                             min(minimo.Z, cx.Min.Z))
                maximo = XYZ(max(maximo.X, cx.Max.X),
                             max(maximo.Y, cx.Max.Y),
                             max(maximo.Z, cx.Max.Z))
        if minimo is None:
            avisos.append("Elevacao: a familia nao tem geometria para enquadrar")
            return None

        # Elevacao: secao perpendicular a -Y (olhando de frente para o modelo).
        caixa.Min = XYZ(minimo.X - 1.0, minimo.Y, minimo.Z - 1.0)
        caixa.Max = XYZ(maximo.X + 1.0, minimo.Y, maximo.Z + 1.0)
        caixa.Transform = Transform.Identity
    except Exception as ex:
        avisos.append("Elevacao (caixa): {0}".format(ex))
        return None

    t = Transaction(doc, "Criar vista de elevacao")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        nova = ViewSection.CreateSection(doc, tipo.Id, caixa)
        t.Commit()
        return nova
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Elevacao (criacao): {0}".format(ex))
        return None


def obter_vista_preview(doc, tipo_vista, direcao3d, avisos):
    """
    Devolve a vista que sera usada como PREVIEW, de acordo com IN[1]:
      VISTA_3D -> obter_vista_3d + padroniza nome + orienta em direcao3d
      PLANTA   -> ViewPlan (existe ou criada)
      CORTE    -> ViewSection
      DETALHE  -> ViewDrafting
      ELEVACAO -> ViewSection (elevacao)

    Vistas nao-3D NAO aceitam ViewOrientation3D; nesses casos a direcao3d e'
    simplesmente ignorada. Se a vista do tipo escolhido nao existir/criar,
    cai no fallback da vista 3D (com aviso).
    """
    if tipo_vista == "VISTA_3D":
        vista = obter_vista_3d(doc, avisos)
        padronizar_nome_vista_3d(doc, vista, avisos)
        orientar_vista_3d(doc, vista, avisos, direcao3d)
        return vista, "VISTA_3D"

    if tipo_vista == "PLANTA":
        vista = obter_ou_criar_vista_planta(doc, avisos)
    elif tipo_vista == "CORTE":
        vista = obter_ou_criar_vista_corte(doc, avisos)
    elif tipo_vista == "DETALHE":
        vista = obter_ou_criar_vista_detalhe(doc, avisos)
    elif tipo_vista == "ELEVACAO":
        vista = obter_ou_criar_vista_elevacao(doc, avisos)
    else:
        vista = None

    if vista is None:
        avisos.append(
            "IN[1] (tipo de vista): nao foi possivel obter/criar uma vista "
            "de '{0}' - usando a vista 3D como fallback".format(tipo_vista))
        vista = obter_vista_3d(doc, avisos)
        padronizar_nome_vista_3d(doc, vista, avisos)
        orientar_vista_3d(doc, vista, avisos, direcao3d)
        return vista, "VISTA_3D"

    # Em familia, o corte/detalhe/elevacao nao podem ser preview em muitos
    # casos; validar aqui evita erro no Save().
    if not vista_valida_para_preview(doc, vista):
        avisos.append(
            "IN[1]: a vista '{0}' nao e' valida como preview - "
            "usando a vista 3D".format(nome_da_vista(vista)))
        vista = obter_vista_3d(doc, avisos)
        padronizar_nome_vista_3d(doc, vista, avisos)
        orientar_vista_3d(doc, vista, avisos, direcao3d)
        return vista, "VISTA_3D"

    return vista, tipo_vista


# -----------------------------------------------------------------------------
#  ESTILO VISUAL
# -----------------------------------------------------------------------------
def chave_do_estilo_visual(valor):
    """
    Chave de ESTILOS_VISUAIS_VISTA_3D correspondente a 'valor', ou None.
    Aceita chave ("SOMBREADO"), apelido ("SHADING", "Shaded",
    "SHADING_WITH_EDGES"...), rotulo do Revit ("Sombreado com arestas") e o
    proprio valor do enum (DisplayStyle.Shading).
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        chave = "_".join(valor.split()).upper()
        if not chave:
            return None
        chave = _APELIDOS_ESTILO_VISUAL.get(chave, chave)
        # Chave/apelido/rotulo do Revit que nao corresponde a nenhum estilo de
        # ESTILOS_VISUAIS_VISTA_3D (ex.: valor digitado errado em IN[3]) -> None,
        # para o chamador poder avisar e cair no estilo padrao.
        if chave in ESTILOS_VISUAIS_VISTA_3D:
            return chave
        return None
    for chave, candidato in ESTILOS_VISUAIS_VISTA_3D.items():
        if candidato is valor or candidato == valor:
            return chave
    return None


def chave_estilo_visual():
    """
    Chave do estilo que sera REALMENTE aplicado: o estilo pedido em
    ESTILO_VISUAL_VISTA_3D ja ajustado por MOSTRAR_ARESTAS_VISTA_3D.
    """
    chave = chave_do_estilo_visual(ESTILO_VISUAL_VISTA_3D)
    if chave is None or not MOSTRAR_ARESTAS_VISTA_3D:
        return chave
    com_arestas = _ESTILOS_COM_ARESTAS.get(chave)
    if com_arestas in ESTILOS_VISUAIS_VISTA_3D:
        return com_arestas
    return chave


def estilo_visual_configurado():
    """Valor de DisplayStyle a aplicar (ou None quando nao ha nada a aplicar)."""
    return ESTILOS_VISUAIS_VISTA_3D.get(chave_estilo_visual())


def descricao_estilo_visual():
    """Texto do estilo aplicado, para o OUT."""
    chave = chave_estilo_visual()
    if chave is None:
        return None
    pedida = chave_do_estilo_visual(ESTILO_VISUAL_VISTA_3D)
    if pedida is not None and pedida != chave:
        return "{0} (de {1} + MOSTRAR_ARESTAS_VISTA_3D)".format(chave, pedida)
    return chave


def definir_estilo_vista_3d(doc, vista, avisos):
    """
    Aplica o estilo visual (View.DisplayStyle) configurado em
    ESTILO_VISUAL_VISTA_3D. Depois de gravar, confere o que ficou na vista.
    Funciona para qualquer vista (nao so' a 3D): View.DisplayStyle e' propriedade
    comum a todas as View.
    """
    if vista is None:
        return False
    pedido = ESTILO_VISUAL_VISTA_3D
    if pedido is None or (isinstance(pedido, str) and not pedido.strip()):
        return False

    estilo = estilo_visual_configurado()
    if estilo is None:
        avisos.append("Vista (estilo visual): valor desconhecido '{0}' "
                      "(use um de: {1})".format(
                          pedido, ", ".join(sorted(ESTILOS_VISUAIS_VISTA_3D))))
        return False

    try:
        if vista.DisplayStyle == estilo:
            return True
    except Exception:
        pass

    try:
        t = Transaction(doc, "Estilo visual da vista")
        silenciar_avisos(t, avisos)
        t.Start()
        try:
            vista.DisplayStyle = estilo
            t.Commit()
        except Exception as ex:
            try:
                t.RollBack()
            except Exception:
                pass
            avisos.append("Vista (estilo visual): {0}".format(ex))
            return False
    except Exception as ex:
        avisos.append("Vista (estilo visual): {0}".format(ex))
        return False

    try:
        aplicado = vista.DisplayStyle
    except Exception:
        aplicado = None
    if aplicado is not None and not (aplicado == estilo or aplicado is estilo):
        avisos.append("Vista (estilo visual): o arquivo ficou em '{0}' "
                      "(pedido: '{1}')".format(
                          chave_do_estilo_visual(aplicado) or aplicado,
                          chave_estilo_visual() or pedido))
    return True


# -----------------------------------------------------------------------------
#  CATEGORIAS OCULTAS
# -----------------------------------------------------------------------------
def categoria_da_propria_familia(doc):
    try:
        familia = doc.OwnerFamily
        if familia is not None:
            return familia.FamilyCategory
    except Exception:
        pass
    return None


def _categorias_para_ocultar(tipo_vista):
    """
    Devolve a lista de BuiltInCategory a ocultar para o tipo de preview
    escolhido. Se o tipo nao estiver em CATEGORIAS_OCULTAS_POR_TIPO, cai na
    lista PADRAO (CATEGORIAS_OCULTAS_VISTA_3D). 'tipo_vista' e' o tipo EFETIVO
    (VISTA_3D/PLANTA/CORTE/DETALHE/ELEVACAO), nao o IN[1] bruto.
    """
    if tipo_vista in CATEGORIAS_OCULTAS_POR_TIPO:
        return CATEGORIAS_OCULTAS_POR_TIPO[tipo_vista]
    return CATEGORIAS_OCULTAS_VISTA_3D


def ocultar_categorias_vista_3d(doc, vista, avisos, tipo_vista=None):
    """
    Oculta, POR CATEGORIA, anotacoes/cotas e elementos auxiliares na vista de
    preview. A lista de categorias depende do TIPO EFETIVO do preview
    (veja CATEGORIAS_OCULTAS_POR_TIPO); quando 'tipo_vista' e' None ou nao
    esta' no dicionario, vale a lista PADRAO (CATEGORIAS_OCULTAS_VISTA_3D).

    A categoria da propria familia (Family.FamilyCategory) e' sempre
    preservada. Funciona em qualquer View (nao so' 3D).

    Devolve a lista dos nomes EFETIVAMENTE ocultados (na ordem da tabela).
    """
    if vista is None or not OCULTAR_CATEGORIAS_VISTA_3D:
        return []

    categorias = _categorias_para_ocultar(tipo_vista)

    id_propria = None
    propria = categoria_da_propria_familia(doc)
    if propria is not None:
        try:
            id_propria = propria.Id
        except Exception:
            id_propria = None

    ocultadas = []
    ignoradas = []
    t = Transaction(doc, "Ocultar categorias na vista")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        for nome in categorias:
            try:
                categoria_bic = getattr(BuiltInCategory, nome, None)
            except Exception:
                categoria_bic = None
            if categoria_bic is None:
                ignoradas.append(nome)
                continue

            try:
                categoria = Category.GetCategory(doc, categoria_bic)
            except Exception:
                categoria = None
            id_categoria = None
            if categoria is not None:
                try:
                    id_categoria = categoria.Id
                except Exception:
                    id_categoria = None
            if id_categoria is None or id_categoria == ElementId.InvalidElementId:
                ignoradas.append(nome)
                continue

            if id_propria is not None and id_categoria == id_propria:
                avisos.append("Vista: '{0}' e a categoria da propria familia - "
                              "mantida visivel".format(nome))
                continue

            try:
                vista.SetCategoryHidden(id_categoria, True)
                ocultadas.append(nome)
            except Exception as ex:
                # "Category cannot be hidden" e' esperado em algumas categorias de
                # vistas de preview (nao e' falha do script). Registramos so' quando
                # for outro erro, para nao poluir o log.
                if "cannot be hidden" not in str(ex):
                    avisos.append("Vista (ocultar {0}): {1}".format(nome, ex))
        t.Commit()
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Vista (ocultar categorias): {0}".format(ex))
        return []

    if ignoradas:
        avisos.append("Vista: categoria(s) nao encontrada(s) ({0}): {1}".format(
            len(ignoradas), ", ".join(ignoradas)))
    return ocultadas

# -----------------------------------------------------------------------------
#  PREVIEW / SAVE / BACKUP
# -----------------------------------------------------------------------------
def definir_preview_permanente(doc, vista, avisos):
    if vista is None:
        return
    try:
        if not doc.GetDocumentPreviewSettings().IsViewIdValidForPreview(vista.Id):
            avisos.append("Preview: a vista '{0}' nao pode ser usada como preview".format(
                nome_da_vista(vista)))
            return
    except Exception:
        pass
    try:
        t = Transaction(doc, "Preview da vista")
        silenciar_avisos(t, avisos)
        t.Start()
        try:
            doc.GetDocumentPreviewSettings().PreviewViewId = vista.Id
            t.Commit()
        except Exception as ex:
            try:
                t.RollBack()
            except Exception:
                pass
            avisos.append("Preview: {0}".format(ex))
    except Exception as ex:
        avisos.append("Preview: {0}".format(ex))


def fazer_backup(caminho, pasta_raiz):
    try:
        destino_base = os.path.join(pasta_raiz, PASTA_BACKUP)
        relativo = os.path.relpath(caminho, pasta_raiz)
        destino = os.path.join(destino_base, relativo)
        pasta = os.path.dirname(destino)
        if not os.path.isdir(pasta):
            os.makedirs(pasta)
        if not os.path.exists(destino):
            shutil.copy2(caminho, destino)
        return True
    except Exception:
        return False


def salvar_familia(doc, caminho_original, vista):
    preview_valido = False
    if vista is not None:
        try:
            preview_valido = doc.GetDocumentPreviewSettings().IsViewIdValidForPreview(vista.Id)
        except Exception:
            preview_valido = False

    opcoes = SaveOptions()
    opcoes.Compact = True
    if preview_valido:
        opcoes.PreviewViewId = vista.Id

    if SALVAR_NO_MESMO_ARQUIVO:
        doc.Save(opcoes)
        return caminho_original

    destino_pasta = PASTA_DESTINO
    if not destino_pasta:
        destino_pasta = os.path.dirname(caminho_original) + "_2026"
    if not os.path.isdir(destino_pasta):
        os.makedirs(destino_pasta)

    destino = os.path.join(destino_pasta, os.path.basename(caminho_original))
    opcoes_saveas = SaveAsOptions()
    opcoes_saveas.OverwriteExistingFile = True
    opcoes_saveas.Compact = True
    if preview_valido:
        opcoes_saveas.PreviewViewId = vista.Id

    doc.SaveAs(destino, opcoes_saveas)
    return destino


# -----------------------------------------------------------------------------
#  TRADUCAO DE NOMES DE VISTA
# -----------------------------------------------------------------------------
def traduzir_nome_vista(nome):
    chave = chave_nome_vista(nome)
    if not chave:
        return None

    traduzido = NOMES_VISTAS_PT_BR_NORMALIZADOS.get(chave)
    if traduzido:
        return traduzido

    for padrao, modelo in REGRAS_NOMES_VISTAS_PT_BR:
        casamento = padrao.match(chave)
        if casamento:
            return modelo.format(*casamento.groups())
    return None


def renomear_vistas_pt_br(doc, avisos):
    if not RENOMEAR_VISTAS_PT_BR:
        return 0

    renomeadas = 0
    nao_traduzidas = []
    try:
        vistas = list(FilteredElementCollector(doc).OfClass(View))
        for vista in vistas:
            try:
                if vista.IsTemplate:
                    continue
            except Exception:
                continue
            atual = nome_da_vista(vista)
            novo_nome = traduzir_nome_vista(atual)
            if not novo_nome:
                if atual and atual != "nao":
                    nao_traduzidas.append(atual)
                continue
            if novo_nome == atual:
                continue
            if renomear_vista(doc, vista, novo_nome, avisos):
                renomeadas += 1
    except Exception as ex:
        avisos.append("Vistas (consulta): {0}".format(ex))

    if RELATAR_VISTAS_NAO_TRADUZIDAS and nao_traduzidas:
        avisos.append("vistas sem traducao: " + ", ".join(sorted(set(nao_traduzidas))))

    return renomeadas


# -----------------------------------------------------------------------------
#  PROCESSAMENTO DE UMA FAMILIA
# -----------------------------------------------------------------------------
def documentos_abertos():
    abertos = set()
    try:
        for doc in app.Documents:
            try:
                caminho = doc.PathName
                if caminho:
                    abertos.add(os.path.normcase(os.path.abspath(caminho)))
            except Exception:
                pass
    except Exception:
        pass
    return abertos


def ja_salva_na_versao_atual(caminho):
    try:
        return BasicFileInfo.Extract(caminho).IsSavedInCurrentVersion
    except Exception:
        return False


def processar_familia(caminho, pasta_raiz, abertos, tipo_vista, direcao3d, estilo_visual):
    """
    Processa UMA familia .rfa e devolve (status_texto, campos_dict).

      - 'status_texto' e' a linha do OUT/log .txt (comeca com OK/PULADO/FALHA).
      - 'campos_dict' sao os campos estruturados do .csv (mesma informacao).

    Recebe as escolhas do usuario ja resolvidas (tipo_vista/direcao3d/
    estilo_visual) para NAO depender de variaveis globais dentro do loop.

    Ordem dos passos:
      1) Unidades SI
      2) Purge Unused em loop
      3) Vista de preview (tipo escolhido em IN[1]; isometrica em IN[2])
      4) Estilo visual (IN[3]) + categorias ocultas (tabela por tipo)
      5) Preview permanente
      6) Traducao dos nomes de vista
      7) Backup + salvar
    """
    nome = os.path.basename(caminho)
    avisos = []

    # -------------------------------------------------------------------------
    #  PULADOS (antes de abrir o documento)
    # -------------------------------------------------------------------------
    chave = os.path.normcase(os.path.abspath(caminho))
    if chave in abertos:
        status = "PULADO | {0} | arquivo ja aberto no Revit".format(nome)
        return status, {"arquivo": nome, "status": "PULADO",
                        "tipo_escolhido": tipo_vista,
                        "avisos": "arquivo ja aberto no Revit"}

    if IGNORAR_JA_ATUALIZADAS and ja_salva_na_versao_atual(caminho):
        status = "PULADO | {0} | ja salvo no Revit {1}".format(nome, app.VersionNumber)
        return status, {"arquivo": nome, "status": "PULADO",
                        "tipo_escolhido": tipo_vista,
                        "avisos": "ja salvo no Revit {0}".format(app.VersionNumber)}

    # -------------------------------------------------------------------------
    #  ABERTURA + PROCESSAMENTO
    # -------------------------------------------------------------------------
    doc = None
    try:
        doc = app.OpenDocumentFile(caminho)
        if doc is None or not doc.IsFamilyDocument:
            status = "FALHA  | {0} | nao foi possivel abrir como familia (.rfa)".format(nome)
            return status, {"arquivo": nome, "status": "FALHA",
                            "tipo_escolhido": tipo_vista,
                            "avisos": "nao foi possivel abrir como familia (.rfa)"}

        # 1) Unidades do projeto -> Sistema Internacional
        configurar_unidades(doc, avisos)

        # 2) Eliminar Nao Utilizados (em loop)
        purgados = purgar_nao_utilizados(doc, avisos)

        # 3) Vista do preview (tipo escolhido em IN[1], isometrica em IN[2])
        vista_preview, tipo_aplicado = obter_vista_preview(
            doc, tipo_vista, direcao3d, avisos)

        # 4) Estilo visual (IN[3]) + categorias ocultas (tabela por tipo)
        # As funcoes usam ESTILO_VISUAL_VISTA_3D; sobrescrevemos com a escolha.
        global ESTILO_VISUAL_VISTA_3D
        anterior = ESTILO_VISUAL_VISTA_3D
        ESTILO_VISUAL_VISTA_3D = estilo_visual
        try:
            estilo_visual_ok = definir_estilo_vista_3d(doc, vista_preview, avisos)
            estilo_aplicado = descricao_estilo_visual() if estilo_visual_ok else None
        finally:
            ESTILO_VISUAL_VISTA_3D = anterior

        categorias_ocultas = ocultar_categorias_vista_3d(
            doc, vista_preview, avisos, tipo_aplicado)

        # 5) Preview permanente
        definir_preview_permanente(doc, vista_preview, avisos)

        # 6) Nomes das vistas em portugues (Brasil)
        vistas_renomeadas = renomear_vistas_pt_br(doc, avisos)

        # 7) Backup opcional + salvar
        if SALVAR_NO_MESMO_ARQUIVO and FAZER_BACKUP:
            if not fazer_backup(caminho, pasta_raiz):
                avisos.append("Backup: nao foi possivel copiar o original")

        destino = salvar_familia(doc, caminho, vista_preview)

        # ---------------------------------------------------------------------
        #  RESULTADO
        # ---------------------------------------------------------------------
        status = ("OK     | {0} | purgados: {1} | vista preview: {2} ({3}) | "
                  "estilo: {4} | categorias ocultas: {5} | "
                  "vistas renomeadas: {6} | salvo em: {7}").format(
            nome, purgados, nome_da_vista(vista_preview), tipo_aplicado,
            estilo_aplicado or "nao aplicado",
            len(categorias_ocultas), vistas_renomeadas,
            os.path.basename(destino))
        if avisos:
            status += " | avisos: " + "; ".join(avisos)

        campos = {
            "arquivo": nome,
            "status": "OK",
            "purgados": purgados,
            "tipo_escolhido": tipo_vista,          # IN[1] bruto (VISTA_3D, PLANTA...)
            "tipo_preview": tipo_aplicado,         # efetivo (pode diferir no fallback)
            "vista_preview": nome_da_vista(vista_preview),
            "estilo": estilo_aplicado or "nao aplicado",
            "categorias_ocultas": len(categorias_ocultas),
            "vistas_renomeadas": vistas_renomeadas,
            "destino": os.path.basename(destino),
            "avisos": "; ".join(avisos),
        }
        return status, campos

    except Exception as ex:
        status = "FALHA  | {0} | {1}".format(nome, ex)
        return status, {"arquivo": nome, "status": "FALHA",
                        "tipo_escolhido": tipo_vista,
                        "avisos": str(ex)}
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass


# -----------------------------------------------------------------------------
#  ENTRADA: pasta ou lista de arquivos .rfa
# -----------------------------------------------------------------------------
def coletar_arquivos(alvo, arquivos, raizes, raiz_do_arquivo):
    if not isinstance(alvo, str):
        return
    if os.path.isdir(alvo):
        raiz = os.path.abspath(alvo)
        if raiz not in raizes:
            raizes.append(raiz)
        for pasta_atual, pastas, nomes in os.walk(raiz):
            if PASTA_BACKUP in pastas:
                pastas.remove(PASTA_BACKUP)
            for nome in sorted(nomes):
                if nome.lower().endswith(".rfa"):
                    caminho = os.path.join(pasta_atual, nome)
                    arquivos.append(caminho)
                    raiz_do_arquivo[os.path.normcase(caminho)] = raiz
    elif alvo.lower().endswith(".rfa") and os.path.exists(alvo):
        caminho = os.path.abspath(alvo)
        raiz = os.path.dirname(caminho)
        if raiz not in raizes:
            raizes.append(raiz)
        arquivos.append(caminho)
        raiz_do_arquivo[os.path.normcase(caminho)] = raiz


# -----------------------------------------------------------------------------
#  RESOLVE AS ESCOLHAS DO USUARIO (IN[1..3]) E PROCESSAMENTO EM LOTE
# -----------------------------------------------------------------------------
avisos_entradas = []
tipo_vista, direcao3d, estilo_visual, avisos_in = _resolver_entradas_dynamo()
avisos_entradas.extend(avisos_in)

entrada = IN[0]
arquivos = []
raizes = []
raiz_do_arquivo = {}

if isinstance(entrada, list):
    for item in entrada:
        coletar_arquivos(item, arquivos, raizes, raiz_do_arquivo)
else:
    coletar_arquivos(entrada, arquivos, raizes, raiz_do_arquivo)

vistos = set()
lista_final = []
for caminho in arquivos:
    chave = os.path.normcase(os.path.abspath(caminho))
    if chave in vistos:
        continue
    vistos.add(chave)
    raiz = raiz_do_arquivo.get(chave)
    if not raiz:
        raiz = os.path.dirname(os.path.abspath(caminho))
    lista_final.append((caminho, raiz))

pasta_raiz = raizes[0] if raizes else ""

abertos = documentos_abertos()
resultados = []

linhas_csv = []   # campos estruturados (mesma ordem do .txt), para o .csv

ativar_respostas_automaticas()
try:
    for caminho, raiz in lista_final:
        try:
            status, campos = processar_familia(
                caminho, raiz, abertos, tipo_vista, direcao3d, estilo_visual)
            resultados.append(status)
            linhas_csv.append(campos)
        except Exception as ex:
            status = "FALHA  | {0} | {1}".format(os.path.basename(caminho), ex)
            resultados.append(status)
            linhas_csv.append({
                "arquivo": os.path.basename(caminho),
                "status": "FALHA",
                "avisos": str(ex),
                "tipo_escolhido": tipo_vista,
            })
finally:
    desativar_respostas_automaticas()

ok = len([r for r in resultados if r.startswith("OK")])
pulados = len([r for r in resultados if r.startswith("PULADO")])
falhas = len([r for r in resultados if r.startswith("FALHA")])

resumo = ("RESUMO | familias encontradas: {0} | OK: {1} | puladas: {2} | falhas: {3}"
          .format(len(resultados), ok, pulados, falhas))

# Ecoa as escolhas do Dynamo (IN[1..3]) - ajuda a ver no OUT o que foi usado.
resumo += (" | IN[1] tipo de vista: {0} | IN[2] isometrica: {1} | "
           "IN[3] estilo: {2}").format(tipo_vista, direcao3d,
                                       chave_do_estilo_visual(estilo_visual) or estilo_visual)

if _dialogos_respondidos:
    resumo += " | janelas do Revit respondidas: {0}".format(len(_dialogos_respondidos))
    resultados = resultados + _dialogos_respondidos

# Avisos das entradas IN[1..3] entram como linhas proprias (nao contam como
# familia OK/PULADA/FALHA) - assim ficam visiveis no OUT.
for aviso in avisos_entradas:
    resultados.append("AVISO  | " + aviso)

# -----------------------------------------------------------------------------
#  GRAVACAO DOS LOGS (TXT + CSV)
# -----------------------------------------------------------------------------
#  O .txt e' o log "humano" (uma linha por familia, com avisos embutidos).
#  O .csv tem colunas FIXAS, com os MESMOS campos do .txt (e os avisos em uma
#  coluna propria), para abrir no Excel/pandas e filtrar (ex.: "quais familias
#  caíram no fallback da Vista 3D?").
def _linha_csv(campos):
    """
    Monta UMA linha CSV a partir de um dicionario de campos (na ordem fixa).
    Usa o modulo csv embutido (aspas, escape de aspas e quebras de linha
    corretos quando um aviso tem ';' ou aspas).
    """
    import csv
    ordem = ("arquivo", "status", "purgados", "tipo_escolhido",
             "tipo_preview", "vista_preview", "estilo", "categorias_ocultas",
             "vistas_renomeadas", "destino", "avisos")
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=ordem,
                              delimiter=";", quoting=csv.QUOTE_MINIMAL,
                              lineterminator="\n")
    escritor.writeheader()
    escritor.writerow({k: (campos.get(k) if campos.get(k) is not None else "")
                       for k in ordem})
    return buf.getvalue()


def _escrever_logs(caminho_txt, caminho_csv, resumo, resultados, linhas_csv):
    """
    Grava o .txt (legivel) e, se ESCREVER_LOG_CSV, o .csv (estruturado).
    O CSV usa o MESMO escape do _linha_csv (uma so' regra de CSV no script).
    Devolve a lista de avisos de gravacao (vazia quando deu tudo certo).
    """
    avisos = []

    # --- .txt: resumo + uma linha por familia ---------------------------------
    if caminho_txt:
        try:
            with open(caminho_txt, "w", encoding="utf-8") as arquivo_log:
                arquivo_log.write(resumo + "\n")
                arquivo_log.write("\n".join(resultados))
                arquivo_log.write("\n")
        except Exception as ex:
            avisos.append("log .txt: " + str(ex))

    # --- .csv: header fixo + uma linha por familia ----------------------------
    if caminho_csv and ESCREVER_LOG_CSV and linhas_csv:
        try:
            ordem = ("arquivo", "status", "purgados", "tipo_escolhido",
                     "tipo_preview", "vista_preview", "estilo",
                     "categorias_ocultas", "vistas_renomeadas",
                     "destino", "avisos")
            with open(caminho_csv, "w", encoding="utf-8", newline="") as arquivo_csv:
                arquivo_csv.write(";".join(ordem) + "\n")
                for campos in linhas_csv:
                    # _linha_csv devolve "header\nregistro\n"; aproveitamos
                    # SO' o registro (a 2a linha) para nao repetir o header.
                    texto = _linha_csv(campos).split("\n")
                    if len(texto) >= 2:
                        arquivo_csv.write(texto[1] + "\n")
        except Exception as ex:
            avisos.append("log .csv: " + str(ex))

    return avisos


if ESCREVER_LOG and resultados and pasta_raiz:
    caminho_log = os.path.join(pasta_raiz, NOME_LOG)
    caminho_csv = os.path.join(pasta_raiz, NOME_LOG_CSV)
    avisos_log = _escrever_logs(caminho_log, caminho_csv, resumo,
                                resultados, linhas_csv)
    if not avisos_log:
        resumo += " | log: " + caminho_log
        if ESCREVER_LOG_CSV:
            resumo += " | csv: " + caminho_csv
    else:
        resumo += " | " + "; ".join(avisos_log)

OUT = [resumo] + resultados
