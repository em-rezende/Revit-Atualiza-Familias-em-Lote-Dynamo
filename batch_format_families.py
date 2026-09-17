# -*- coding: utf-8 -*-
# =============================================================================
#  ATUALIZA FAMILIAS EM LOTE - REVIT 2026
#  Atualizacao / formatacao em lote de familias (.rfa)
# -----------------------------------------------------------------------------
#  Para CADA familia (.rfa) encontrada na pasta informada em IN[0], o script:
#    1) Abre a familia em segundo plano (abrir + salvar no Revit 2026 atualiza
#       o formato do arquivo para a versao atual)
#    2) Configura as "Unidades do projeto" para o Sistema Internacional (metrico)
#       - Comprimento: mm | Area: m2 | Volume: m3 (constantes ajustaveis abaixo)
#       - Simbolo decimal: virgula (,)  |  Agrupamento de milhar: ponto (.)
#         => numeros exibidos no formato 123.456.789,00
#    3) Executa "Eliminar Nao Utilizados" (Purge Unused) em LOOP ate limpar tudo
#       - usa Document.GetUnusedElements(), a API oficial por tras da janela
#         "Eliminar nao utilizados" do Revit
#    4) Padroniza a VISTA 3D (nome + direcao + estilo visual + categorias
#       ocultas + preview/miniatura do arquivo):
#       - garante que a vista 3D se chame "Vista 1" (renomeia "View 1",
#         "Vista 3D", "{3D}" etc.); se a familia nao tiver vista 3D, cria uma
#       - orienta a vista 3D em "SE Isometric" (camera a sudeste e acima) e
#         GRAVA a orientacao no arquivo (View3D.SaveOrientation)
#       - aplica o ESTILO VISUAL (View.DisplayStyle): "Sombreado"
#         (DisplayStyle.Shading) ou "Sombreado com arestas"
#         (DisplayStyle.ShadingWithEdges) quando MOSTRAR_ARESTAS_VISTA_3D =
#         True - veja ESTILO_VISUAL_VISTA_3D / MOSTRAR_ARESTAS_VISTA_3D
#       - OCULTA, POR CATEGORIA, as anotacoes/cotas (cotas, textos, simbolos de
#         anotacao, niveis, eixos) e os elementos auxiliares (planos/linhas/
#         pontos de referencia, paredes, pisos, forros, telhados) via
#         View.SetCategoryHidden - veja CATEGORIAS_OCULTAS_VISTA_3D. A categoria
#         DA PROPRIA familia nunca e ocultada.
#       - define essa vista 3D como Preview/miniatura do arquivo salvo
#    5) Renomeia as vistas cujo nome ainda esta no padrao do Revit para
#       portugues (Brasil), em qualquer idioma instalado (ingles, frances ou
#       espanhol) - a comparacao ignora acento, caixa alta/baixa e ponto final:
#       Ref. Level -> Nivel de Referencia, Front -> Parte Frontal,
#       Back -> Parte Posterior, Left -> Esquerda, Right -> Direita,
#       Niveau de ref. -> Nivel de Referencia, Vue 1 -> Vista 1,
#       Nivel de referencia -> Nivel de Referencia, Planta baja -> Piso Terreo,
#       Level 1 -> Nivel 1, View 2 -> Vista 2, Seccion 1 -> Corte 1 ...
#    6) SALVA a familia no MESMO caminho usando Document.Save(SaveOptions)
#    7) RESPONDE "OK" sozinho nas janelas de aviso do Revit que exigiriam um
#       clique do usuario (ex.: "As restricoes entre a geometria na familia
#       podem se comportar de forma imprevisivel ao modificar parametros...",
#       com os botoes "Remover restricoes" e "OK"). Sem isso o lote fica parado
#       esperando alguem responder. Veja "JANELAS DE AVISO DO REVIT".
#
#  VISTA 3D: POR QUE O NOME PRECISA SER "Vista 1"
#  A documentacao da API (RevitAPI.xml, View3D.SaveOrientation) diz:
#     "Converts the temporary orientation of the View3D into its saved
#      orientation."
#     "The View3D will be oriented to its saved orientation on file open.
#      To save the orientation of the default View3D, first rename the default
#      View3D."
#  Ou seja: a orientacao da vista 3D PADRAO do documento nao pode ser gravada.
#  Como o script renomeia essa vista para "Vista 1", ela deixa de ser a vista
#  padrao e a orientacao SE Isometric passa a ser salva no .rfa.
#
#  ESTILO VISUAL DA VISTA 3D ("Sombreado" / "Sombreado com arestas")
#  View.DisplayStyle recebe um valor do enum DisplayStyle. ATENCAO: o valor de
#  "Sombreado" e' DisplayStyle.Shading - "DisplayStyle.Shaded" NAO EXISTE na API
#  (verificado na RevitAPI.xml do Revit 2026). Os valores sao Wireframe,
#  HLR ("Linhas ocultas"), Shading ("Sombreado"), ShadingWithEdges ("Sombreado
#  com arestas"), FlatColors ("Cores consistentes"), Realistic ("Realista") e
#  RealisticWithEdges ("Realista com arestas"); "Undefined" nao pode ser
#  atribuido.
#
#  ARESTAS NA VISTA SOMBREADA (MOSTRAR_ARESTAS_VISTA_3D)
#  O checkbox "Mostrar arestas" (Opcoes de exibicao grafica > Modelo) NAO tem
#  propriedade na API: nao existe View.ShowEdges nem View3D.ShowEdges (conferido
#  na RevitAPI.xml do Revit 2026 - View nao tem essa propriedade; o que existe
#  e' ViewDisplayModel, com SmoothEdges/ShowHiddenLines/Transparency). O caminho
#  pela API e' o PROPRIO estilo visual, que tem variantes COM arestas:
#     SOMBREADO + arestas -> "Sombreado com arestas" -> DisplayStyle.ShadingWithEdges
#     REALISTA  + arestas -> "Realista com arestas"  -> DisplayStyle.RealisticWithEdges
#  (rotulos em portugues encontrados em pt-BR\Revit.dll e pt-BR\RevitRes.dll do
#  Revit 2026). Com MOSTRAR_ARESTAS_VISTA_3D = True o script troca o estilo
#  pedido pela variante COM arestas; ESTRUTURA_ARAME e LINHAS_OCULTAS ja mostram
#  as arestas e nao mudam.
#
#  OCULTAR CATEGORIAS NA VISTA 3D (anotacoes, cotas e elementos auxiliares)
#  Em documentos de FAMILIA a API nao oferece View.HideElements (ocultar
#  elementos isolados); o caminho e' ocultar por CATEGORIA:
#     Category.GetCategory(doc, BuiltInCategory.OST_...) + View.SetCategoryHidden
#  O script nunca oculta a categoria que define a propria familia
#  (Family.FamilyCategory): uma familia de parede mantem OST_Walls visivel, uma
#  familia de anotacao mantem OST_GenericAnnotation - o preview nunca fica vazio.
#
#  ORIENTACAO: ViewOrientation3D(eye, up, forward)
#  O vetor "up" precisa ser PERPENDICULAR ao "forward" (exigencia da API).
#  Em SE Isometric: forward = (-1, 1, -1) e up = (-1, 1, 2) normalizados, o que
#  mantem o eixo Z na vertical da tela - a mesma direcao da vista 3D padrao do
#  Revit (up = (-1, 1, 2) normalizado).
#
#  AGRUPAMENTOS DO NAVEGADOR DE PROJETO ("Planta de Piso", "Plantas de Forro",
#  "Elevacoes", "Vistas 3D"...): nao existem como propriedades renomeaveis na
#  API do Revit. Sao textos da INTERFACE do Revit, definidos pelo idioma
#  instalado - no pacote pt-BR eles ja aparecem em portugues (confirmado nos
#  recursos de pt-BR\Revit.dll e pt-BR\RevitRes.dll). O que a API permite
#  renomear sao as VISTAS (View.Name), que e o que este script faz.
#
#  POR QUE NAO USAR SaveAs() NO MESMO CAMINHO?
#  A documentacao da API do Revit 2026 (RevitAPI.xml) diz, para
#  Document.SaveAs(String, SaveAsOptions):
#     InvalidOperationException:
#       "options.overwriteExistingFile is 'false' but there is an existing
#        file at filepath."    <= origem da mensagem "File already exists!"
#  O nome correto da propriedade e OverwriteExistingFile (SINGULAR). O codigo
#  antigo usava o PLURAL (OverwriteExistingFiles), que nao existe na classe
#  SaveAsOptions; a opcao continuou no padrao (false) e o SaveAs falhou.
#  Alem disso, para salvar no proprio caminho o metodo correto e Save():
#  Save(SaveOptions) tambem aceita Compact e PreviewViewId.
#
#  JANELAS DE AVISO DO REVIT ("Remover restricoes" / "OK")
#  O Revit avisa que "as restricoes entre a geometria na familia podem se
#  comportar de forma imprevisivel ao modificar parametros" quando a geometria
#  nao esta restrita aos niveis, planos de referencia ou linhas de referencia.
#  Essa janela e MODAL: enquanto ninguem responde, o Dynamo fica bloqueado - e
#  ela tambem pode aparecer durante o processamento em lote (ao abrir ou salvar
#  a familia e nas operacoes feitas pelas transacoes deste script).
#  O script responde "OK" sozinho, por dois caminhos que se completam:
#    - silenciar_avisos(), instalado em TODAS as transacoes: usa
#      IFailuresPreprocessor; os avisos (warnings) gerados pelas operacoes do
#      script sao descartados e a transacao segue - exatamente o efeito de
#      clicar em "OK";
#    - ativar_respostas_automaticas(): assina o evento
#      UIApplication.DialogBoxShowing e responde a janela com
#      DialogBoxShowingEventArgs.OverrideResult(1) (= TaskDialogResult.Ok /
#      IDOK) antes de ela aparecer; o id e a mensagem da janela vao para o
#      log/OUT (linhas "JANELA | OK: ...").
#  O script NUNCA escolhe "Remover restricoes" (nem qualquer outra resolucao):
#  a familia nao e alterada por causa do aviso. Se algum passo depender da
#  resolucao, ele e desfeito (rollback) e o aviso fica registrado no log/OUT.
#  Para voltar a responder manualmente: RESPONDER_DIALOGOS_COM_OK = False.
#
#  Entrada : IN[0] = caminho de uma pasta (String) ou lista de caminhos .rfa
#  Saida   : OUT = lista de textos com o resultado de cada familia + resumo
# =============================================================================

import clr
import os
import re
import shutil

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

# RevitAPIUI traz UIApplication.DialogBoxShowing / DialogBoxShowingEventArgs,
# usados para responder "OK" nas janelas de aviso do Revit (veja
# ativar_respostas_automaticas()).
clr.AddReference('RevitAPIUI')

clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager

from System.Collections.Generic import HashSet, List

# -----------------------------------------------------------------------------
#  CONFIGURACAO
# -----------------------------------------------------------------------------
SALVAR_NO_MESMO_ARQUIVO = True   # True  = sobrescreve o .rfa original (com backup)
PASTA_DESTINO = r""              # Usada somente se SALVAR_NO_MESMO_ARQUIVO = False
                                 # Ex.: r"D:\Familias_2026". Se vazia, cria a pasta
                                 # "<pasta de origem>_2026".

FAZER_BACKUP = True              # Copia o .rfa original antes de sobrescrever
PASTA_BACKUP = "_backup_upgrade" # Subpasta criada na RAIZ DA PESQUISA (a pasta
                                 # informada em IN[0]), com os originais

IGNORAR_JA_ATUALIZADAS = False   # True = pula familias ja salvas no Revit atual

SISTEMA_METRICO_COMPLETO = True  # True  = cria Units(UnitSystem.Metric): todas as
                                 #         especificacoes em metrico (equivalente ao
                                 #         "Sistema Internacional" do Revit)
                                 # False = altera apenas comprimento/area/volume

ACCURACY_COMPRIMENTO = 0.001     # Precisao do comprimento NA UNIDADE DE EXIBICAO
                                 # (0.001 mm = 3 casas decimais). Use 0.1 ou 1.0
                                 # para menos casas decimais.
USAR_AGRUPAMENTO_UNIDADES = True # Aplica agrupamento de milhar tambem nos formatos
                                 # de comprimento/area/volume

MAX_PASSES_PURGE = 30            # Limite de iteracoes do "Eliminar nao utilizados"

ESCREVER_LOG = True              # Grava um log .txt na RAIZ DA PESQUISA (a pasta
                                 # informada em IN[0])
NOME_LOG = "_log_atualiza_familias.txt"

# --- Respostas automaticas nas janelas de aviso do Revit ---------------------
# Sem isso, o lote PARA quando o Revit abre a janela "As restricoes entre a
# geometria na familia podem se comportar de forma imprevisivel..." (botoes
# "Remover restricoes" e "OK") ou qualquer outra janela modal.
RESPONDER_DIALOGOS_COM_OK = True # True  = responde "OK" sozinho nas janelas do
                                 #         Revit (nenhuma resolucao e escolhida:
                                 #         a familia NAO e alterada)
RESULTADO_OK = 1                 # Codigo do botao "OK": TaskDialogResult.Ok (1)
                                 # = IDOK do Windows (1)
IDS_DIALOGOS_IGNORADOS = ()      # Ids (DialogId) que NAO devem ser respondidos,
                                 # para deixar a janela para o usuario. Ex.:
                                 # ("TaskDialog_Save",)
REGISTRAR_DIALOGOS = True        # True  = registra no log/OUT cada janela
                                 #         respondida ("JANELA | OK: ...")

# --- Formato brasileiro/internacional: 123.456.789,00 ------------------------
SYMBOL_DECIMAL = DecimalSymbol.Comma           # virgula como separador decimal
SYMBOL_AGRUPAMENTO = DigitGroupingSymbol.Dot   # ponto como separador de milhar

# --- Unidades metricas aplicadas explicitamente ------------------------------
UNIDADE_COMPRIMENTO = UnitTypeId.Millimeters
UNIDADE_AREA = UnitTypeId.SquareMeters
UNIDADE_VOLUME = UnitTypeId.CubicMeters

# --- VISTA 3D: nome, direcao e preview/miniatura -----------------------------
NOME_VISTA_3D = "Vista 1"        # Nome imposto a vista 3D salva no arquivo.
                                 # IMPORTANTE: a API so permite GRAVAR a
                                 # orientacao de uma vista 3D que NAO seja a
                                 # vista 3D padrao do documento; por isso a
                                 # vista padrao e renomeada (View3D.SaveOrientation).

CRIAR_VISTA_3D_SE_FALTAR = True  # True = cria uma vista 3D isometrica quando a
                                 # familia nao tiver nenhuma vista 3D

DIRECAO_VISTA_3D = "SE_ISOMETRIC"  # Direcao aplicada a vista 3D (veja DIRECOES_VISTA_3D)
FATOR_DISTANCIA_VISTA_3D = 2.0     # Distancia do olho = fator x diagonal do modelo
TAMANHO_MINIMO_VISTA_3D = 3.0      # Diagonal minima considerada (pes internos)

GRAVAR_ORIENTACAO_VISTA_3D = True  # True  = converte a orientacao temporaria na
                                   #         orientacao SALVA do arquivo
                                   #         (View3D.SaveOrientation): o .rfa
                                   #         reabre ja em SE Isometric
                                   # False = so ajusta a vista na sessao atual
                                   #         (o preview muda, mas a direcao
                                   #         gravada no arquivo nao)

# Nomes tipicos da vista 3D criada automaticamente pelo Revit. Servem apenas
# para escolher qual vista 3D renomear quando a familia tiver mais de uma.

NOMES_PADRAO_VISTA_3D = (
    # comparados com chave_nome_vista() (minusculo, sem acento)
    "view 1", "vista 1", "vista 3d", "vista 3d {3d}", "3d view", "{3d}",
    "vue 1", "vue 3d", "vue 3d {3d}",   # frances
)

# Direcoes disponiveis: (forward, up) - vetores de ViewOrientation3D.
# "SE Isometric" = camera a SUDESTE e acima, olhando para noroeste e para baixo.
# O vetor "up" precisa ser PERPENDICULAR ao "forward" e mantem o eixo Z na
# vertical da tela (mesma direcao da vista 3D padrao do Revit):
#   SE: forward (-1,  1, -1) | up (-1,  1, 2)  ->  (-1*-1) + ( 1*1) + (-1*2) = 0
#   SO: forward ( 1,  1, -1) | up ( 1,  1, 2)  ->  ( 1*1)  + ( 1*1) + (-1*2) = 0
#   NE: forward (-1, -1, -1) | up (-1, -1, 2)  ->  (-1*-1) + (-1*-1) + (-1*2) = 0
#   NO: forward ( 1, -1, -1) | up ( 1, -1, 2)  ->  ( 1*1)  + (-1*-1) + (-1*2) = 0
DIRECOES_VISTA_3D = {
    "SE_ISOMETRIC": ((-1.0, 1.0, -1.0), (-1.0, 1.0, 2.0)),    # Sudeste (padrao)
    "SO_ISOMETRIC": ((1.0, 1.0, -1.0), (1.0, 1.0, 2.0)),      # Sudoeste
    "NE_ISOMETRIC": ((-1.0, -1.0, -1.0), (-1.0, -1.0, 2.0)),  # Nordeste
    "NO_ISOMETRIC": ((1.0, -1.0, -1.0), (1.0, -1.0, 2.0)),    # Noroeste
}

# --- VISTA 3D: estilo visual (View.DisplayStyle) ------------------------------
# Estilo visual aplicado a vista 3D antes de salvar (o mesmo estilo aparece no
# preview/miniatura do arquivo). Chaves aceitas (a comparacao ignora caixa,
# espacos e o nome do valor do enum tambem funciona):
#   ESTRUTURA_ARAME        -> DisplayStyle.Wireframe         ("Estrutura de arame")
#   LINHAS_OCULTAS         -> DisplayStyle.HLR               ("Linhas ocultas")
#   SOMBREADO              -> DisplayStyle.Shading           ("Sombreado") <= padrao
#   SOMBREADO_COM_ARESTAS  -> DisplayStyle.ShadingWithEdges  ("Sombreado com arestas")
#   CORES_CONSISTENTES     -> DisplayStyle.FlatColors        ("Cores consistentes")
#   REALISTA               -> DisplayStyle.Realistic         ("Realista")
#   REALISTA_COM_ARESTAS   -> DisplayStyle.RealisticWithEdges ("Realista com arestas")
# CUIDADO: o valor de "Sombreado" NAO e DisplayStyle.Shaded (esse valor nao
# existe na API). Para nao mexer no estilo, use "" (string vazia).
ESTILO_VISUAL_VISTA_3D = "SOMBREADO"

ESTILOS_VISUAIS_VISTA_3D = {
    "ESTRUTURA_ARAME": DisplayStyle.Wireframe,
    "LINHAS_OCULTAS": DisplayStyle.HLR,
    "SOMBREADO": DisplayStyle.Shading,
    "CORES_CONSISTENTES": DisplayStyle.FlatColors,
    "REALISTA": DisplayStyle.Realistic,
}

# Valores do enum que so existem em versoes mais novas da API (ShadingWithEdges
# e RealisticWithEdges, presentes no Revit 2026): entram na tabela SOMENTE se
# existirem nesta versao do Revit, para o script continuar carregando (em vez de
# falhar no import) em uma instalacao mais antiga.
for _chave, _nome_do_valor in (("SOMBREADO_COM_ARESTAS", "ShadingWithEdges"),
                               ("REALISTA_COM_ARESTAS", "RealisticWithEdges")):
    _valor = getattr(DisplayStyle, _nome_do_valor, None)
    if _valor is not None:
        ESTILOS_VISUAIS_VISTA_3D[_chave] = _valor
del _chave, _nome_do_valor, _valor

# Apelidos aceitos em ESTILO_VISUAL_VISTA_3D -> chave de ESTILOS_VISUAIS_VISTA_3D
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

# --- VISTA 3D: arestas visiveis ("Sombreado com arestas") ---------------------
# Mostra as arestas da geometria no preview. A API do Revit NAO tem
# View.ShowEdges / View3D.ShowEdges (o checkbox "Mostrar arestas" das opcoes de
# exibicao grafica nao existe como propriedade - conferido na RevitAPI.xml do
# Revit 2026). O que a API oferece sao os estilos visuais COM arestas:
#     SOMBREADO + arestas -> DisplayStyle.ShadingWithEdges  ("Sombreado com arestas")
#     REALISTA  + arestas -> DisplayStyle.RealisticWithEdges ("Realista com arestas")
# Com True, o estilo pedido em ESTILO_VISUAL_VISTA_3D e' trocado pela variante
# COM arestas (inclusive quando o estilo e' dado pelo valor do enum):
#     "SOMBREADO" / "SHADING"   -> SOMBREADO_COM_ARESTAS
#     "REALISTA" / "REALISTIC"  -> REALISTA_COM_ARESTAS
# "ESTRUTURA_ARAME" e "LINHAS_OCULTAS" ja mostram as arestas: nao mudam (e
# "CORES_CONSISTENTES" nao tem variante com arestas na API).
# Com False, vale exatamente o que estiver em ESTILO_VISUAL_VISTA_3D.
# Em uma versao do Revit sem ShadingWithEdges/RealisticWithEdges o ajuste e'
# ignorado em silencio: o estilo simples continua sendo aplicado.
MOSTRAR_ARESTAS_VISTA_3D = True

# Estilo COM arestas correspondente a cada estilo pedido (o que nao estiver
# aqui ja mostra as arestas - ou nao tem variante com arestas).
_ESTILOS_COM_ARESTAS = {
    "SOMBREADO": "SOMBREADO_COM_ARESTAS",
    "REALISTA": "REALISTA_COM_ARESTAS",
}

# --- VISTA 3D: categorias ocultas (anotacoes, cotas, elementos auxiliares) ----
# Antes de salvar, a vista 3D (a mesma gravada como preview) recebe "Ocultar em
# vista" para cada categoria da lista abaixo - o equivalente a desmarcar a
# categoria em "Visibilidade/Substituicoes da vista" (V/G):
#   View.SetCategoryHidden(Category.GetCategory(doc, BuiltInCategory).Id, True)
# Em documento de FAMILIA a API nao permite ocultar ELEMENTOS isolados (nao ha
# View.HideElements); ocultar por categoria e' o caminho possivel.
#
# Os nomes sao de valores do enum BuiltInCategory (nao sao os rotulos do
# idioma). Nomes que nao existirem sao ignorados com aviso no log/OUT, e a
# categoria DA PROPRIA familia (Family.FamilyCategory) NUNCA e ocultada - assim
# uma familia de parede continua mostrando a propria parede, uma de anotacao
# continua mostrando o proprio simbolo, e o preview nunca fica vazio.
OCULTAR_CATEGORIAS_VISTA_3D = True

CATEGORIAS_OCULTAS_VISTA_3D = (
    # Anotacoes / cotas / textos
    "OST_Dimensions",         # Cotas
    "OST_TextNotes",          # Notas de texto
    "OST_GenericAnnotation",  # Simbolos de anotacao (anotacao genetica)
    "OST_Levels",             # Niveis (inclui o Nivel de Referencia)
    "OST_Grids",              # Eixos
    # Planos / linhas / pontos de referencia (construcao)
    "OST_CLines",             # Planos de referencia (nome interno do BIC)
    "OST_ReferenceLines",     # Linhas de referencia
    "OST_ReferencePoints",    # Pontos de referencia
    # Elementos auxiliares (hospedeiros / contexto do modelo)
    "OST_Walls",              # Paredes
    "OST_Floors",             # Pisos
    "OST_Ceilings",           # Forros
    "OST_Roofs",              # Telhados
)

# --- Comparacao dos nomes de vista -------------------------------------------
# O Revit grava os nomes padrao no IDIOMA instalado, com acentos e, as vezes,
# ponto final ("Niveau de réf.", "Élévation", "Sección", "Detrás"). Para que a
# traducao funcione em qualquer idioma suportado, o nome da vista e convertido
# em uma CHAVE NORMALIZADA antes de ser comparado:
#   - minusculas;
#   - sem acentos (é -> e, ñ -> n, ç -> c, á -> a ...);
#   - aspas tipograficas normalizadas (’ ´ ` -> ');
#   - tracos tipograficos normalizados (– — − -> -);
#   - espacos repetidos / espaco inquebravel reduzidos a um espaco simples;
#   - espacos e pontos no inicio/fim descartados.
# Resultado: "Niveau de Référence", "niveau de référence", "NIVEAU DE RÉF." e
# "niveau de ref" caem todos na mesma chave -> funciona sem depender de como o
# nome foi digitado/acentuado.
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
    """
    Chave normalizada de um nome de vista (veja o comentario acima). Serve tanto
    para o dicionario NOMES_VISTAS_PT_BR quanto para as REGRAS_NOMES_VISTAS_PT_BR,
    de modo que acento, caixa alta/baixa e espacos extras nunca impedem a traducao.
    """
    chave = (nome or "").strip().lower()
    chave = chave.translate(_TABELA_ACENTOS)
    chave = re.sub(r"[\s\u00a0\u202f]+", " ", chave)
    return chave.strip(" .")


# --- Nomes de vistas em portugues (Brasil) -----------------------------------
RENOMEAR_VISTAS_PT_BR = True     # True = renomeia as vistas que ainda usam os
                                 # nomes padrao do Revit (ingles, frances ou
                                 # espanhol) para portugues (Brasil)
                                 # (Ref. Level, Front, Back, Left, Right,
                                 #  Level 1, View 2, Section 1, Niveau de réf.,
                                 #  Nivel de referencia, Alzado ...)

RELATAR_VISTAS_NAO_TRADUZIDAS = False  # True = acrescenta ao log/OUT a lista dos
                                 # nomes de vista que NAO foram traduzidos.
                                 # Use True para descobrir os nomes padrao de um
                                 # idioma ainda nao mapeado (veja o README) e
                                 # volte a False depois.

# Nomes exatos (comparados pela chave normalizada: sem diferenciar
# maiusculas/minusculas, acentos, aspas tipograficas nem ponto final).
# Inclui os padroes do Revit em INGLES, FRANCES e ESPANHOL -> portugues (Brasil).
NOMES_VISTAS_PT_BR = {
    # --- Ingles (EN) ---
    # Vista 3D
    "{3d}": "Vista 3D",
    "3d view": "Vista 3D",
    "default 3d view": "Vista 3D",
    # Nivel de referencia
    "ref. level": "Nível de Referência",
    "ref level": "Nível de Referência",
    "reference level": "Nível de Referência",
    "ref. plane": "Nível de Referência",
    "ref plane": "Nível de Referência",
    # Piso terreo
    "ground floor": "Piso Térreo",
    "ground level": "Piso Térreo",
    # Elevacoes / vistas ortogonais
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
    # Comuns ao ingles, frances e espanhol (mesma grafia nos tres idiomas)
    "exterior": "Exterior",
    "interior": "Interior",
    # Planos / forro / legenda / passeio
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

    # --- Frances (FR) ---
    # Vista 3D
    "vue 3d": "Vista 3D",
    "vue 3d {3d}": "Vista 3D",
    "vue 1": "Vista 1",
    # Nivel de referencia ("Niveau de référence" / "Niveau de réf.")
    "niveau de référence": "Nível de Referência",
    "niveau de réf.": "Nível de Referência",
    "niveau ref.": "Nível de Referência",
    "ref. niveau": "Nível de Referência",

    # Elevacoes / vistas ortogonais
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

    # Planos / forro / legenda / passeio
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
    # "élévation" e "détail" nao precisam constar aqui: a comparacao ignora
    # acentos, portanto "elevation" e "detail" (secao em ingles) ja os cobrem

    # --- Espanhol (ES) ---
    # Vista 3D
    "vista 3d": "Vista 3D",
    "vista 3d {3d}": "Vista 3D",
    "vista 1": "Vista 1",
    # Nivel de referencia
    "nivel de referencia": "Nível de Referência",
    "nivel de ref.": "Nível de Referência",
    "nivel ref.": "Nível de Referência",
    "ref. nivel": "Nível de Referência",
    # Elevacoes / vistas ortogonais
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
    # Planos / forro / leyenda / recorrido
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

# Dicionario de consulta com as chaves JA NORMALIZADAS (minusculo, sem acento,
# sem ponto/espaco nas pontas). E montado uma unica vez, na carga do script, e e
# ele que traduzir_nome_vista() usa - assim a busca e sempre feita pelo mesmo
# criterio com que as chaves foram cadastradas (veja chave_nome_vista).
NOMES_VISTAS_PT_BR_NORMALIZADOS = {
    chave_nome_vista(nome): traducao for nome, traducao in NOMES_VISTAS_PT_BR.items()
}

# Nomes numerados do Revit ("View 2", "Level 1", "Section 3", "Niveau 1",
# "Sección 2", "Alzado 1"...): INGLES / FRANCES / ESPANHOL -> portugues (Brasil)
# IMPORTANTE: as regras sao aplicadas sobre a CHAVE NORMALIZADA do nome
# (minusculo, sem acento - veja chave_nome_vista), por isso os padroes abaixo
# sao escritos SEM acento: "detail" cobre "Détail", "elevation" cobre
# "Élévation", "seccion" cobre "Sección".
REGRAS_NOMES_VISTAS_PT_BR = (
    # --- Ingles ---
    (re.compile(r"^view\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^level\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^section\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^detail\s+(\d+)$"), "Detalhe {0}"),
    (re.compile(r"^elevation\s+(\d+)$"), "Elevação {0}"),
    (re.compile(r"^plan\s+(\d+)$"), "Planta {0}"),

    # --- Frances ---
    (re.compile(r"^vue\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^niveau\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^coupe\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^vue en plan\s+(\d+)$"), "Planta {0}"),

    # --- Espanhol ---
    (re.compile(r"^vista\s+(\d+)$"), "Vista {0}"),
    (re.compile(r"^nivel\s+(-?\d+)$"), "Nível {0}"),
    (re.compile(r"^seccion\s+(\d+)$"), "Corte {0}"),
    (re.compile(r"^detalle\s+(\d+)$"), "Detalhe {0}"),
    (re.compile(r"^alzado\s+(\d+)$"), "Elevação {0}"),

    # --- Vista 3D numerada: "Vue 3D 1", "Vista 3D 2" ---
    (re.compile(r"^(?:vue|vista)\s+3d\s+(\d+)$"), "Vista 3D {0}"),
)

app = DocumentManager.Instance.CurrentUIApplication.Application


# -----------------------------------------------------------------------------
#  FUNCOES AUXILIARES
# -----------------------------------------------------------------------------
def silenciar_avisos(transacao, avisos=None):
    """
    Instala um IFailuresPreprocessor na transacao para que os avisos do Revit
    (por exemplo, os gerados ao eliminar elementos ou ao trocar as unidades)
    nao abram caixas de dialogo e nao interrompam o lote. Deve ser chamado em
    TODAS as transacoes do script.

    A resposta automatica e sempre "OK": os avisos (warnings) sao descartados e
    a transacao segue - o script NUNCA escolhe uma RESOLUCAO ("Remover
    restricoes", "Excluir elementos"...), ou seja, nada e alterado na familia
    para "resolver" o aviso.

    Se ainda sobrar uma FALHA de erro (FailureSeverity.Error), que nao pode ser
    descartada, o preprocessador pede o ROLLBACK da transacao: o passo e
    desfeito (e fica registrado em 'avisos') em vez de abrir uma janela modal do
    Revit e travar o processamento ate alguem clicar.
    Se algo falhar aqui, o script continua normalmente.
    """
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
            # FailuresAccessor.DeleteAllWarnings() remove apenas avisos (warnings)
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
# O Revit pode abrir uma janela MODAL no meio do lote e parar tudo ate alguem
# responder - por exemplo o aviso "As restricoes entre a geometria na familia
# podem se comportar de forma imprevisivel ao modificar parametros...", com os
# botoes "Remover restricoes" e "OK".
# Os avisos das transacoes do script ficam com silenciar_avisos(); as janelas
# que o proprio Revit abre (ao abrir/salvar a familia, por exemplo) sao
# respondidas pelo evento UIApplication.DialogBoxShowing.
# A resposta e sempre o botao "OK" - nenhuma resolucao e escolhida.
_handler_dialogos = None     # referencia do handler (o .NET nao pode perde-la)
_dialogos_respondidos = []   # textos das janelas respondidas (vai para o OUT/log)


def _atributo_janela(argumentos, atributo):
    """
    Valor de texto de um atributo do evento de janela ('' quando nao existe:
    o DialogBoxShowingEventArgs simples nao tem a propriedade Message - so o
    TaskDialogShowingEventArgs tem).
    """
    try:
        return str(getattr(argumentos, atributo) or "")
    except Exception:
        return ""


def _ao_mostrar_dialogo(remetente, argumentos):
    """
    Handler do evento DialogBoxShowing: responde "OK" na janela que o Revit
    estiver mostrando e registra o que foi respondido.

    DialogBoxShowingEventArgs.OverrideResult(valor) fecha a janela SEM mostra-la,
    devolvendo 'valor' como se fosse o botao clicado:
      - caixa de mensagem do Windows -> IDOK = 1;
      - TaskDialog -> TaskDialogResult.Ok = 1 (CommandLink1 seria 1001);
      - caixa de dialogo comum -> qualquer valor diferente de zero fecha a janela.
    Como a janela nao chega a aparecer, o Dynamo segue executando sem parar.
    """
    identificador = _atributo_janela(argumentos, "DialogId")
    if identificador in IDS_DIALOGOS_IGNORADOS:
        return   # desta janela o usuario deve responder pessoalmente

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
    """
    Passa a responder "OK" (RESULTADO_OK) em qualquer janela modal que o Revit
    mostrar durante o lote - assina o evento UIApplication.DialogBoxShowing.
    Retorna True quando o evento foi assinado.
    """
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
    """Remove o handler do evento (nao deixa o script interferindo no Revit)."""
    global _handler_dialogos
    if _handler_dialogos is None:
        return
    try:
        DocumentManager.Instance.CurrentUIApplication.DialogBoxShowing -= _handler_dialogos
    except Exception:
        pass
    _handler_dialogos = None




def aplicar_formato(units, spec, tipo_unidade, accuracy, avisos):
    """
    Aplica um tipo de unidade (e, opcionalmente, a precisao) a uma especificacao
    do objeto Units. Falhas sao registradas em 'avisos' em vez de abortar o lote.
    """
    try:
        if not units.IsModifiableSpec(spec):
            return
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
    """
    Configura as Unidades do projeto da familia para o sistema metrico e define
    o formato numerico 123.456.789,00 (virgula decimal / ponto de agrupamento).
    """
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
    """
    Tamanho de uma colecao, seja ela uma lista Python ou uma colecao .NET.
    IMPORTANTE (CPython3): as colecoes devolvidas pela API do Revit
    (GetUnusedElements, Delete, etc.) chegam ao Python como LISTAS, que NAO
    possuem a propriedade .Count usada pelo IronPython. Por isso o script usa
    len() primeiro e .Count apenas como alternativa.
    """
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


def purgar_nao_utilizados(doc, avisos):
    """
    Executa o "Eliminar Nao Utilizados" (Purge Unused) em loop, ate que nao
    existam mais elementos nao utilizados.
    GetUnusedElements devolve os mesmos elementos da janela Purge Unused e
    somente os que podem ser excluidos; um conjunto de categorias vazio
    significa "todas as categorias".
    """
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
            # O preprocessador de falhas pediu ROLLBACK (falha de erro do Revit):
            # nao insiste, senao a mesma exclusao se repetiria ate MAX_PASSES_PURGE.
            avisos.append("Purge: exclusao desfeita pelo Revit ({0})".format(estado))
            break

        quantidade = contar(removidos)
        total += quantidade
        if quantidade == 0:
            break

    return total


def nome_da_vista(vista):
    """Nome atual da vista ('nao' se a vista nao existir ou estiver invalidada)."""
    if vista is None:
        return "nao"
    try:
        return vista.Name
    except Exception:
        return "nao"


def nome_vista_em_uso(doc, nome):
    """True se ja existe alguma vista (de qualquer tipo) com esse nome."""
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
    """
    Renomeia uma vista. A API exige uma transacao para alterar View.Name.
    Devolve True se o nome ficou como solicitado.
    """
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


def obter_vista_3d(doc, avisos=None):
    """
    Retorna a vista 3D que sera salva como vista padrao do arquivo e usada como
    preview/miniatura. Ordem de preferencia:
      1) uma vista 3D que ja se chame NOME_VISTA_3D ("Vista 1");
      2) uma vista 3D valida para gerar preview (exigencia da API ao usar
         SaveOptions.PreviewViewId), preferindo os nomes tipicos do Revit
         ("View 1", "Vista 3D", "{3D}"...);
      3) uma vista 3D isometrica nova, criada pelo script
         (se CRIAR_VISTA_3D_SE_FALTAR = True).
    """
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

    # 1) a vista 3D ja tem o nome padrao
    for vista in vistas:
        if nome_da_vista(vista) == NOME_VISTA_3D:
            return vista

    # 2) vista 3D valida para ser preview
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

    # 3) a familia nao tem vista 3D: cria uma isometrica
    if CRIAR_VISTA_3D_SE_FALTAR:
        return criar_vista_3d(doc, avisos)

    return None


def tipo_vista_3d(doc):
    """ViewFamilyType de vista 3D (ViewFamily.ThreeDimensional) da familia."""
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
    """
    Cria uma vista 3D isometrica (View3D.CreateIsometric) na familia, usada
    quando a familia nao tem nenhuma vista 3D. Devolve a vista criada ou None.
    """
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
    """
    Garante que a vista 3D se chame NOME_VISTA_3D ("Vista 1").
    Renomear tambem e um requisito da API: a orientacao da vista 3D PADRAO do
    documento nao pode ser gravada; ao renomear, a vista passa a ser uma vista 3D
    normal e View3D.SaveOrientation passa a funcionar.
    Devolve True se a vista ja tinha (ou recebeu) o nome padrao.
    """
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
    """
    Centro e diagonal (em pes - unidades internas do Revit) da caixa que envolve
    a geometria da familia. Sao usados para posicionar a camera da vista 3D.
    Se nenhuma geometria for encontrada, devolve a origem e o tamanho minimo
    configurado, para a vista nunca ficar sem enquadramento.
    """
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


def orientar_vista_3d(doc, vista, avisos):
    """
    Orienta a vista 3D na direcao de DIRECAO_VISTA_3D ("SE Isometric": camera a
    sudeste e acima, olhando para noroeste e para baixo, com o eixo Z na vertical
    da tela - a mesma direcao da vista 3D padrao do Revit).
    Passos:
      1) View3D.SetOrientation(ViewOrientation3D) -> orientacao TEMPORARIA.
         O vetor "up" precisa ser PERPENDICULAR ao "forward" (garantido pela
         tabela DIRECOES_VISTA_3D);
      2) View3D.SaveOrientation() -> converte a orientacao temporaria na
         orientacao SALVA do arquivo (o .rfa reabre nessa direcao). So funciona
         porque a vista 3D foi renomeada antes (nao e mais a vista 3D padrao).
    Devolve True se a orientacao foi aplicada.
    """
    direcao = DIRECOES_VISTA_3D.get(DIRECAO_VISTA_3D)
    if vista is None or direcao is None:
        return False

    try:
        if vista.IsLocked:            # travada por outro script/usuario
            vista.Unlock()
    except Exception:
        pass

    centro, tamanho = centro_e_tamanho_do_modelo(doc, vista)
    frente = XYZ(direcao[0][0], direcao[0][1], direcao[0][2]).Normalize()
    cima = XYZ(direcao[1][0], direcao[1][1], direcao[1][2]).Normalize()
    olho = centro.Subtract(frente.Multiply(tamanho * FATOR_DISTANCIA_VISTA_3D))

    t = Transaction(doc, "Orientar vista 3D ({0})".format(DIRECAO_VISTA_3D))
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        vista.SetOrientation(ViewOrientation3D(olho, cima, frente))
        if GRAVAR_ORIENTACAO_VISTA_3D:
            try:
                if vista.CanSaveOrientation():
                    vista.SaveOrientation()   # direcao gravada no arquivo
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


def chave_do_estilo_visual(valor):
    """
    Chave de ESTILOS_VISUAIS_VISTA_3D correspondente a 'valor', ou None quando o
    valor nao for reconhecido. 'valor' pode ser a propria chave ("SOMBREADO"),
    um apelido ("SHADING", "Shaded", "SHADING_WITH_EDGES"...), o rotulo do Revit
    ("Sombreado com arestas", que vira "SOMBREADO_COM_ARESTAS") ou o valor do
    enum (DisplayStyle.Shading).
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        chave = "_".join(valor.split()).upper()   # ignora caixa e espacos repetidos
        if not chave:
            return None
        return _APELIDOS_ESTILO_VISUAL.get(chave, chave)
    for chave, candidato in ESTILOS_VISUAIS_VISTA_3D.items():
        if candidato is valor or candidato == valor:
            return chave
    return None


def chave_estilo_visual():
    """
    Chave do estilo que sera REALMENTE aplicado na vista 3D: o estilo pedido em
    ESTILO_VISUAL_VISTA_3D ja ajustado por MOSTRAR_ARESTAS_VISTA_3D, que troca
    "SOMBREADO" por "SOMBREADO_COM_ARESTAS" e "REALISTA" por
    "REALISTA_COM_ARESTAS" (as variantes COM arestas do estilo). None quando nao
    ha nada a aplicar (""/None) ou quando o valor nao e' reconhecido.
    """
    chave = chave_do_estilo_visual(ESTILO_VISUAL_VISTA_3D)
    if chave is None or not MOSTRAR_ARESTAS_VISTA_3D:
        return chave
    com_arestas = _ESTILOS_COM_ARESTAS.get(chave)
    if com_arestas in ESTILOS_VISUAIS_VISTA_3D:   # variante existe nesta versao
        return com_arestas
    return chave


def estilo_visual_configurado():
    """
    Valor de DisplayStyle que sera aplicado na vista 3D, ou None quando nao ha
    nada a aplicar. Aceita a chave de ESTILOS_VISUAIS_VISTA_3D ("SOMBREADO"), um
    apelido ("SHADING", "Shaded", "Realistic", "Estrutura de arame"...) ou o
    proprio valor do enum (ESTILO_VISUAL_VISTA_3D = DisplayStyle.Shading).
    Leva em conta MOSTRAR_ARESTAS_VISTA_3D, que troca o estilo pedido pela
    variante COM arestas ("SOMBREADO" -> DisplayStyle.ShadingWithEdges).
    "" ou None = nao mexer no estilo.
    """
    return ESTILOS_VISUAIS_VISTA_3D.get(chave_estilo_visual())


def descricao_estilo_visual():
    """
    Texto do estilo visual que sera aplicado, para o log/OUT:
      - a propria chave configurada, quando nada foi ajustado;
      - "SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D)",
        quando MOSTRAR_ARESTAS_VISTA_3D trocou o estilo pela variante com arestas.
    None quando nao ha estilo a aplicar.
    """
    chave = chave_estilo_visual()
    if chave is None:
        return None
    pedida = chave_do_estilo_visual(ESTILO_VISUAL_VISTA_3D)
    if pedida is not None and pedida != chave:
        return "{0} (de {1} + MOSTRAR_ARESTAS_VISTA_3D)".format(chave, pedida)
    return chave


def definir_estilo_vista_3d(doc, vista, avisos):
    """
    Aplica o ESTILO VISUAL da vista 3D (View.DisplayStyle) configurado em
    ESTILO_VISUAL_VISTA_3D - por padrao "Sombreado" (DisplayStyle.Shading); com
    MOSTRAR_ARESTAS_VISTA_3D = True o padrao passa a ser "Sombreado com arestas"
    (DisplayStyle.ShadingWithEdges).
    O estilo fica GRAVADO no arquivo e vale tambem para o preview/miniatura.
    Depois de gravar, CONFERE o estilo que ficou na vista: se o Revit nao aceitar
    o valor pedido (a API recusa alguns estilos em algumas vistas), o aviso
    aparece no log/OUT - em vez de o preview sair diferente do esperado sem
    ninguem perceber.
    Devolve True quando a vista esta (ou ficou) no estilo pedido.
    """
    if vista is None:
        return False
    pedido = ESTILO_VISUAL_VISTA_3D
    if pedido is None or (isinstance(pedido, str) and not pedido.strip()):
        return False                       # configurado para nao mexer no estilo

    estilo = estilo_visual_configurado()
    if estilo is None:
        avisos.append("Vista 3D (estilo visual): valor desconhecido '{0}' "
                      "(use um de: {1})".format(
                          pedido, ", ".join(sorted(ESTILOS_VISUAIS_VISTA_3D))))
        return False

    try:
        if vista.DisplayStyle == estilo:
            return True                    # ja esta no estilo pedido
    except Exception:
        pass

    try:
        t = Transaction(doc, "Estilo visual da vista 3D")
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
            avisos.append("Vista 3D (estilo visual): {0}".format(ex))
            return False
    except Exception as ex:
        avisos.append("Vista 3D (estilo visual): {0}".format(ex))
        return False

    # Conferencia: o arquivo ficou no estilo pedido?
    try:
        aplicado = vista.DisplayStyle
    except Exception:
        aplicado = None
    if aplicado is not None and not (aplicado == estilo or aplicado is estilo):
        avisos.append("Vista 3D (estilo visual): o arquivo ficou em '{0}' "
                      "(pedido: '{1}')".format(
                          chave_do_estilo_visual(aplicado) or aplicado,
                          chave_estilo_visual() or pedido))
    return True


def categoria_da_propria_familia(doc):
    """
    Categoria que DEFINE a familia (Family.FamilyCategory) ou None.
    Serve para o script nunca ocultar a categoria da propria familia: a
    geometria de uma familia de parede esta em OST_Walls, a de uma familia de
    anotacao em OST_GenericAnnotation - ocultar essas categorias deixaria a
    vista 3D (e o preview) vazios.
    """
    try:
        familia = doc.OwnerFamily
        if familia is not None:
            return familia.FamilyCategory
    except Exception:
        pass
    return None


def ocultar_categorias_vista_3d(doc, vista, avisos):
    """
    Oculta, POR CATEGORIA, as anotacoes/cotas e os elementos auxiliares na vista
    3D (CATEGORIAS_OCULTAS_VISTA_3D) - o mesmo efeito de desmarcar a categoria
    em "Visibilidade/Substituicoes da vista" (V/G):

        View.SetCategoryHidden(Category.GetCategory(doc, BuiltInCategory).Id, True)

    Documento de familia nao aceita ocultar ELEMENTOS isolados (nao ha
    View.HideElements), por isso o caminho e' ocultar a categoria inteira.
    A categoria da propria familia (Family.FamilyCategory) e sempre preservada.

    Devolve a lista dos nomes de BuiltInCategory EFETIVAMENTE ocultados (na
    ordem de CATEGORIAS_OCULTAS_VISTA_3D).
    """
    if vista is None or not OCULTAR_CATEGORIAS_VISTA_3D:
        return []

    id_propria = None
    propria = categoria_da_propria_familia(doc)
    if propria is not None:
        try:
            id_propria = propria.Id
        except Exception:
            id_propria = None

    ocultadas = []
    ignoradas = []
    t = Transaction(doc, "Ocultar categorias na vista 3D")
    silenciar_avisos(t, avisos)
    t.Start()
    try:
        for nome in CATEGORIAS_OCULTAS_VISTA_3D:
            # 1) O nome existe nesta versao do Revit? (erro de digitacao)
            try:
                categoria_bic = getattr(BuiltInCategory, nome, None)
            except Exception:
                categoria_bic = None
            if categoria_bic is None:
                ignoradas.append(nome)
                continue

            # 2) A familia tem essa categoria?
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

            # 3) Nunca ocultar a categoria da propria familia
            if id_propria is not None and id_categoria == id_propria:
                avisos.append("Vista 3D: '{0}' e a categoria da propria familia - "
                              "mantida visivel".format(nome))
                continue

            try:
                vista.SetCategoryHidden(id_categoria, True)
                ocultadas.append(nome)
            except Exception as ex:
                avisos.append("Vista 3D (ocultar {0}): {1}".format(nome, ex))
        t.Commit()
    except Exception as ex:
        try:
            t.RollBack()
        except Exception:
            pass
        avisos.append("Vista 3D (ocultar categorias): {0}".format(ex))
        return []

    if ignoradas:
        avisos.append("Vista 3D: categoria(s) nao encontrada(s) ({0}): {1}".format(
            len(ignoradas), ", ".join(ignoradas)))
    return ocultadas


def definir_preview_permanente(doc, vista, avisos):
    """
    Grava na familia a vista 3D como preview permanente (a mesma opcao que
    aparece em "Salvar como > Opcoes"). A miniatura do arquivo salvo tambem
    recebe essa vista por meio de SaveOptions.PreviewViewId.
    """
    if vista is None:
        return
    # A API aceita como preview somente uma vista valida (exigencia de
    # DocumentPreviewSettings.PreviewViewId e de SaveOptions.PreviewViewId).
    try:
        if not doc.GetDocumentPreviewSettings().IsViewIdValidForPreview(vista.Id):
            avisos.append("Preview: a vista 3D nao pode ser usada como preview")
            return
    except Exception:
        pass
    try:
        t = Transaction(doc, "Preview da Vista 3D")
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


def traduzir_nome_vista(nome):
    """
    Nome da vista em portugues (Brasil) ou None se o nome nao corresponder a
    nenhum padrao conhecido do Revit (ingles, frances ou espanhol).
    A busca e feita sobre a CHAVE NORMALIZADA do nome (minusculo, sem acento,
    sem espacos repetidos e sem ponto final), de modo que "Niveau de Référence",
    "niveau de reference" e "NIVEAU DE RÉF." caem na mesma chave.
    """
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
    """
    Renomeia as vistas que ainda usam o nome padrao do Revit em INGLES, FRANCES
    ou ESPANHOL (Ref. Level, Front, Back, Left, Right, Level 1, View 2,
    Niveau de réf., Face avant, Nivel de referencia, Alzado 1...) para os nomes
    em portugues do Brasil. Somente NOMES DE VISTAS sao alterados: niveis, tipos
    de vista e os agrupamentos do Navegador de Projeto nao sao tocados - esses
    ultimos sao textos da interface do Revit, definidos pelo idioma instalado
    (nao existem na API como propriedades renomeaveis).
    Devolve quantas vistas foram renomeadas.
    """
    if not RENOMEAR_VISTAS_PT_BR:
        return 0

    renomeadas = 0
    nao_traduzidas = []
    try:
        # list() antes de alterar: evita iterar o coletor enquanto o
        # documento muda
        vistas = list(FilteredElementCollector(doc).OfClass(View))
        for vista in vistas:
            try:
                if vista.IsTemplate:      # modelo de vista: nome nao muda
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

    # Diagnostico opcional: ajuda a descobrir os nomes padrao de um idioma que
    # ainda nao esteja mapeado (ligue RELATAR_VISTAS_NAO_TRADUZIDAS = True).
    if RELATAR_VISTAS_NAO_TRADUZIDAS and nao_traduzidas:
        avisos.append("vistas sem traducao: " + ", ".join(sorted(set(nao_traduzidas))))

    return renomeadas


def fazer_backup(caminho, pasta_raiz):
    """
    Copia o arquivo original para a subpasta de backup, preservando a arvore.

    pasta_raiz e' a RAIZ DA PESQUISA (a pasta informada em IN[0]), nunca a pasta
    do primeiro .rfa encontrado: o backup nasce em
        "<raiz da pesquisa>/_backup_upgrade/<subpastas ate o .rfa>"
    """
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
    """
    Salva a familia.
      - Modo padrao: Document.Save(SaveOptions) -> sobrescreve o MESMO arquivo
        (upgrade para o Revit atual), sem o erro "File already exists!".
      - Modo alternativo: Document.SaveAs(SaveAsOptions) para outra pasta,
        sempre com OverwriteExistingFile = True (nome correto, SINGULAR).
    """
    # A API valida a vista somente no momento de usar as opcoes: se ela nao
    # servir como preview, Save/SaveAs lanca ArgumentException. Por isso o
    # PreviewViewId so e definido quando a vista e comprovadamente valida.
    preview_valido = False
    if vista is not None:
        try:
            preview_valido = doc.GetDocumentPreviewSettings().IsViewIdValidForPreview(vista.Id)
        except Exception:
            preview_valido = False

    opcoes = SaveOptions()
    opcoes.Compact = True                 # compacta/reduz o arquivo salvo
    if preview_valido:
        opcoes.PreviewViewId = vista.Id   # miniatura = Vista 3D

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
    opcoes_saveas.OverwriteExistingFile = True   # <<< SINGULAR (nao "Files")
    opcoes_saveas.Compact = True
    if preview_valido:
        opcoes_saveas.PreviewViewId = vista.Id

    doc.SaveAs(destino, opcoes_saveas)
    return destino


def documentos_abertos():
    """Caminhos (normalizados) dos documentos abertos na sessao do Revit."""
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
    """True se o arquivo .rfa ja esta salvo na versao atual do Revit."""
    try:
        return BasicFileInfo.Extract(caminho).IsSavedInCurrentVersion
    except Exception:
        return False


def processar_familia(caminho, pasta_raiz, abertos):
    """Processa UMA familia .rfa e devolve um texto de status."""
    nome = os.path.basename(caminho)
    avisos = []

    chave = os.path.normcase(os.path.abspath(caminho))
    if chave in abertos:
        return "PULADO | {0} | arquivo ja aberto no Revit".format(nome)

    if IGNORAR_JA_ATUALIZADAS and ja_salva_na_versao_atual(caminho):
        return "PULADO | {0} | ja salvo no Revit {1}".format(nome, app.VersionNumber)

    doc = None
    try:
        doc = app.OpenDocumentFile(caminho)
        if doc is None or not doc.IsFamilyDocument:
            return "FALHA  | {0} | nao foi possivel abrir como familia (.rfa)".format(nome)

        # 1) Unidades do projeto -> Sistema Internacional
        configurar_unidades(doc, avisos)

        # 2) Eliminar Nao Utilizados (em loop)
        purgados = purgar_nao_utilizados(doc, avisos)

        # 3) Vista 3D: nome padrao ("Vista 1"), direcao SE Isometric, estilo
        #    visual ("Sombreado" / "Sombreado com arestas"), categorias ocultas
        #    (anotacoes/cotas e elementos auxiliares) e preview/miniatura
        vista3d = obter_vista_3d(doc, avisos)
        padronizar_nome_vista_3d(doc, vista3d, avisos)
        orientar_vista_3d(doc, vista3d, avisos)
        estilo_visual_ok = definir_estilo_vista_3d(doc, vista3d, avisos)
        categorias_ocultas = ocultar_categorias_vista_3d(doc, vista3d, avisos)
        definir_preview_permanente(doc, vista3d, avisos)

        # 4) Nomes das vistas em portugues (Brasil)
        vistas_renomeadas = renomear_vistas_pt_br(doc, avisos)

        # 5) Backup opcional do original (antes de sobrescrever), na RAIZ DA
        #    PESQUISA (a pasta informada em IN[0]), preservando as subpastas
        if SALVAR_NO_MESMO_ARQUIVO and FAZER_BACKUP:
            if not fazer_backup(caminho, pasta_raiz):
                avisos.append("Backup: nao foi possivel copiar o original")

        # 6) Salvar (upgrade para o Revit atual)
        destino = salvar_familia(doc, caminho, vista3d)

        # "estilo 3D" mostra a chave que valeu de fato - ex.:
        # "SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D)"
        # quando MOSTRAR_ARESTAS_VISTA_3D trocou o estilo pedido.
        estilo_aplicado = descricao_estilo_visual() if estilo_visual_ok else None
        status = ("OK     | {0} | purgados: {1} | vista 3D: {2} | "
                  "estilo 3D: {3} | categorias ocultas: {4} | "
                  "vistas renomeadas: {5} | salvo em: {6}").format(
            nome, purgados, nome_da_vista(vista3d),
            estilo_aplicado or "nao aplicado",
            len(categorias_ocultas), vistas_renomeadas,
            os.path.basename(destino))
        if avisos:
            status += " | avisos: " + "; ".join(avisos)
        return status

    except Exception as ex:
        return "FALHA  | {0} | {1}".format(nome, ex)
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
    """
    Coleta os .rfa de UM item de IN[0] e anota a RAIZ DA PESQUISA de cada um.

    A raiz da pesquisa e' a PASTA informada em IN[0] (ou a pasta do arquivo,
    quando o item e' um .rfa) - NUNCA a pasta do primeiro .rfa encontrado.
    E' nessa raiz que nascem o PASTA_BACKUP e o NOME_LOG.
    """
    if not isinstance(alvo, str):
        return
    if os.path.isdir(alvo):
        raiz = os.path.abspath(alvo)
        if raiz not in raizes:
            raizes.append(raiz)
        for pasta_atual, pastas, nomes in os.walk(raiz):
            if PASTA_BACKUP in pastas:            # nunca reprocessar o backup
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


entrada = IN[0]
arquivos = []         # caminhos .rfa, na ordem da varredura
raizes = []           # raizes da pesquisa, na ordem de IN[0]
raiz_do_arquivo = {}  # caminho normalizado -> raiz da pesquisa

if isinstance(entrada, list):
    for item in entrada:
        coletar_arquivos(item, arquivos, raizes, raiz_do_arquivo)
else:
    coletar_arquivos(entrada, arquivos, raizes, raiz_do_arquivo)

# Remove duplicados mantendo a ordem. Cada familia leva junto a SUA raiz da
# pesquisa: o backup (_backup_upgrade) e o log nascem nessa raiz, e nao dentro
# da primeira subpasta que tiver uma familia.
vistos = set()
lista_final = []      # [(caminho, raiz da pesquisa), ...]
for caminho in arquivos:
    chave = os.path.normcase(os.path.abspath(caminho))
    if chave in vistos:
        continue
    vistos.add(chave)
    raiz = raiz_do_arquivo.get(chave)
    if not raiz:
        raiz = os.path.dirname(os.path.abspath(caminho))
    lista_final.append((caminho, raiz))

# Raiz usada para gravar o LOG: a primeira pasta informada em IN[0].
pasta_raiz = raizes[0] if raizes else ""

# -----------------------------------------------------------------------------
#  PROCESSAMENTO EM LOTE
# -----------------------------------------------------------------------------
abertos = documentos_abertos()
resultados = []

# Responde "OK" sozinho nas janelas de aviso do Revit que interromperiam o lote
# (ex.: "Remover restricoes" / "OK" sobre as restricoes da geometria da familia:
# sem isso o Dynamo fica parado esperando alguem clicar em uma delas).
ativar_respostas_automaticas()
try:
    for caminho, raiz in lista_final:
        try:
            resultados.append(processar_familia(caminho, raiz, abertos))
        except Exception as ex:   # rede de seguranca: continua com a proxima familia
            resultados.append("FALHA  | {0} | {1}".format(os.path.basename(caminho), ex))
finally:
    desativar_respostas_automaticas()   # nao deixa o handler preso no Revit

ok = len([r for r in resultados if r.startswith("OK")])
pulados = len([r for r in resultados if r.startswith("PULADO")])
falhas = len([r for r in resultados if r.startswith("FALHA")])

resumo = ("RESUMO | familias encontradas: {0} | OK: {1} | puladas: {2} | falhas: {3}"
          .format(len(resultados), ok, pulados, falhas))

# Janelas do Revit respondidas automaticamente (APOS a contagem das familias,
# para nao entrar nos totais de OK/puladas/falhas).
if _dialogos_respondidos:
    resumo += " | janelas do Revit respondidas: {0}".format(len(_dialogos_respondidos))
    resultados = resultados + _dialogos_respondidos

if ESCREVER_LOG and resultados and pasta_raiz:
    caminho_log = os.path.join(pasta_raiz, NOME_LOG)
    try:
        with open(caminho_log, "w", encoding="utf-8") as arquivo_log:
            arquivo_log.write(resumo + "\n")
            arquivo_log.write("\n".join(resultados))
            arquivo_log.write("\n")
        resumo += " | log: " + caminho_log
    except Exception as ex:
        resumo += " | aviso ao gravar log: " + str(ex)

OUT = [resumo] + resultados
