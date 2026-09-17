# -*- coding: utf-8 -*-
# =============================================================================
#  VALIDADOR (SEM ABRIR O REVIT): ESTILO VISUAL E CATEGORIAS OCULTAS DA VISTA 3D
# -----------------------------------------------------------------------------
#  Testa, fora do Revit, o que o script faz na vista 3D antes de salvar:
#    - definir_estilo_vista_3d(): aplica View.DisplayStyle (padrao
#      DisplayStyle.ShadingWithEdges = "Sombreado com arestas", porque
#      MOSTRAR_ARESTAS_VISTA_3D = True), aceita as chaves de
#      ESTILOS_VISUAIS_VISTA_3D e os apelidos ("SHADING", "Shaded",
#      "SHADING_WITH_EDGES"...), aceita o proprio valor do enum e transforma
#      chave invalida em AVISO (sem mexer na vista); depois de gravar, CONFERE o
#      estilo que ficou na vista e avisa quando o Revit aplicou outro;
#    - chave_estilo_visual()/descricao_estilo_visual()/MOSTRAR_ARESTAS_VISTA_3D:
#      o ajuste de arestas troca "SOMBREADO" por "SOMBREADO_COM_ARESTAS"
#      (DisplayStyle.ShadingWithEdges) e "REALISTA" por "REALISTA_COM_ARESTAS";
#      "ESTRUTURA_ARAME"/"LINHAS_OCULTAS" (que ja mostram as arestas) e
#      "CORES_CONSISTENTES" (sem variante com arestas) nao mudam;
#    - ocultar_categorias_vista_3d(): chama View.SetCategoryHidden para cada
#      categoria de CATEGORIAS_OCULTAS_VISTA_3D, IGNORA nomes de BuiltInCategory
#      que nao existem (erro de digitacao), tolera falha em UMA categoria e -
#      o mais importante - NUNCA oculta a categoria da propria familia
#      (Family.FamilyCategory): uma familia de parede mantem OST_Walls visivel;
#    - ordem dos passos em processar_familia(): orientar -> estilo -> ocultar ->
#      preview, e a linha de resultado com "estilo 3D"/"categorias ocultas"
#      mostrando o estilo que valeu de fato (com o ajuste de arestas).
#
#  Como funciona: as APIs do Revit (clr, Autodesk.Revit.DB, RevitServices) sao
#  substituidas por stubs simples e o proprio batch_format_families.py e' lido e
#  executado no fim deste arquivo. Nada e' gravado em disco.
#
#  Uso (o Python do proprio Dynamo serve):
#      python .\validar_vista_3d.py
#
#  Saida esperada: uma linha "OK   | ..." por verificacao e, no fim,
#  "VERIFICACOES FALHAS: 0" (codigo de saida 0; cada falha aparece listada).
# =============================================================================
"""Valida, fora do Revit, o estilo visual e as categorias ocultas da vista 3D."""

import io
import os
import re
import sys
import builtins
import types

RAIZ = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SCRIPT = os.path.join(RAIZ, "batch_format_families.py")
FONTE = io.open(CAMINHO_SCRIPT, encoding="utf-8").read()

FALHAS = []


def verificar(condicao, descricao):
    print("{0} | {1}".format("OK   " if condicao else "FALHA", descricao))
    if not condicao:
        FALHAS.append(descricao)


class Fake(object):
    """Objeto generico: aceita chamada, indexacao e qualquer atributo."""

    def __init__(self, nome):
        object.__setattr__(self, "_nome", nome)
        object.__setattr__(self, "_filhos", {})

    def __getattr__(self, item):
        filhos = object.__getattribute__(self, "_filhos")
        if item not in filhos:
            filhos[item] = Fake(object.__getattribute__(self, "_nome") + "." + item)
        return filhos[item]

    def __getitem__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return Fake(object.__getattribute__(self, "_nome") + "()")

    def __repr__(self):
        return "<Fake {0}>".format(object.__getattribute__(self, "_nome"))


class IFailuresPreprocessor(object):
    """Precisa ser classe de verdade (usada como classe base)."""
    pass


class HashSet(object):
    def __init__(self, *args):
        self.itens = []

    def __getitem__(self, item):
        return self


class List(object):
    def __init__(self, *args):
        self.itens = []

    def __getitem__(self, item):
        return List

    def Add(self, item):
        self.itens.append(item)


# --- stub de Autodesk.Revit.DB (nomes extraidos do proprio script) -----------
# Os nomes de builtins (Exception, ValueError...) ficam de fora para o star-import
# do script continuar resolvendo "except Exception" para a excecao de verdade.
nomes = sorted(n for n in set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", FONTE))
               if not hasattr(builtins, n))
banco = types.ModuleType("Autodesk.Revit.DB")
for nome in nomes:
    setattr(banco, nome, Fake(nome))
banco.IFailuresPreprocessor = IFailuresPreprocessor
banco.__all__ = nomes

clr = types.ModuleType("clr")
clr.AddReference = lambda *args, **kwargs: None

genericos = types.ModuleType("System.Collections.Generic")
genericos.HashSet = HashSet
genericos.List = List


class Evento(object):
    def __init__(self, dono):
        self.dono = dono

    def __iadd__(self, manipulador):
        self.dono.manipuladores.append(manipulador)
        return self

    def __isub__(self, manipulador):
        if manipulador in self.dono.manipuladores:
            self.dono.manipuladores.remove(manipulador)
        return self


class AplicacaoFalsa(object):
    def __init__(self):
        self.VersionNumber = "2026"
        self.Documents = []


class UIApplicationFalsa(object):
    def __init__(self):
        self.manipuladores = []
        self.DialogBoxShowing = Evento(self)
        self.Application = AplicacaoFalsa()


ui = UIApplicationFalsa()
instancia = Fake("Instance")
instancia.CurrentUIApplication = ui

persistencia = types.ModuleType("RevitServices.Persistence")


class DocumentManager(object):
    Instance = instancia


persistencia.DocumentManager = DocumentManager

for nome, modulo in (
        ("clr", clr),
        ("System", types.ModuleType("System")),
        ("System.Collections", types.ModuleType("System.Collections")),
        ("System.Collections.Generic", genericos),
        ("Autodesk", types.ModuleType("Autodesk")),
        ("Autodesk.Revit", types.ModuleType("Autodesk.Revit")),
        ("Autodesk.Revit.DB", banco),
        ("RevitServices", types.ModuleType("RevitServices")),
        ("RevitServices.Persistence", persistencia),
):
    sys.modules[nome] = modulo

globais = {"__name__": "batch_format_families_teste", "IN": [""]}
exec(compile(FONTE, CAMINHO_SCRIPT, "exec"), globais)

ESTILO_SHADING = banco.DisplayStyle.Shading
ESTILO_WIREFRAME = banco.DisplayStyle.Wireframe
ESTILO_SHADING_COM_ARESTAS = banco.DisplayStyle.ShadingWithEdges
ESTILO_REALISTA_COM_ARESTAS = banco.DisplayStyle.RealisticWithEdges
CONFIG_ORIGINAL = globais["CATEGORIAS_OCULTAS_VISTA_3D"]


# --- stubs das classes usadas pelas funcoes sob teste ------------------------
class IdCategoria(object):
    """ElementId falso: guarda o nome do BuiltInCategory (para comparar)."""

    def __init__(self, nome):
        self.nome = nome

    def __eq__(self, outro):
        return isinstance(outro, IdCategoria) and outro.nome == self.nome

    def __ne__(self, outro):
        return not self.__eq__(outro)

    def __hash__(self):
        return hash(self.nome)

    def __repr__(self):
        return "<Id {0}>".format(self.nome)


class ElementIdFalsa(object):
    InvalidElementId = IdCategoria("#INVALIDO")


class BicFalsa(object):
    def __init__(self, nome):
        self.nome = nome

    def __repr__(self):
        return "BuiltInCategory." + self.nome


class BuiltInCategoryFalsa(object):
    """Enum BuiltInCategory falso: so' tem os nomes informados."""

    def __init__(self, nomes_bic):
        for nome in nomes_bic:
            setattr(self, nome, BicFalsa(nome))


class CategoriaFalsa(object):
    def __init__(self, nome):
        self.Id = IdCategoria(nome)

    def __repr__(self):
        return "<Categoria {0}>".format(self.Id.nome)


class CategoriasFalsas(object):
    """Category falso: GetCategory(doc, bic) -> Id = nome do BuiltInCategory."""

    @staticmethod
    def GetCategory(documento, categoria_bic):
        return CategoriaFalsa(categoria_bic.nome)


class CategoriasQueDevolvemNone(object):
    @staticmethod
    def GetCategory(documento, categoria_bic):
        return None


class CategoriasQueFalham(object):
    @staticmethod
    def GetCategory(documento, categoria_bic):
        raise RuntimeError("categoria indisponivel: " + categoria_bic.nome)


class VistaFalsa(object):
    """View falso: guarda o estilo visual e as categorias ocultadas."""

    def __init__(self, estilo_inicial=None, falhas=()):
        self.DisplayStyle = estilo_inicial
        self.ocultadas = []
        self.falhas = tuple(falhas)

    def SetCategoryHidden(self, id_categoria, ocultar):
        nome = getattr(id_categoria, "nome", id_categoria)
        if nome in self.falhas:
            raise RuntimeError("categoria nao pode ser ocultada: {0}".format(nome))
        if ocultar:
            self.ocultadas.append(nome)


class VistaQueFalhaNoEstilo(object):
    """Vista cujo DisplayStyle sempre lanca (para testar o rollback)."""

    def __init__(self):
        object.__setattr__(self, "_estilo", None)
        self.ocultadas = []

    @property
    def DisplayStyle(self):
        return object.__getattribute__(self, "_estilo")

    @DisplayStyle.setter
    def DisplayStyle(self, valor):
        raise RuntimeError("DisplayStyle nao pode ser alterado nesta vista")

    def SetCategoryHidden(self, id_categoria, ocultar):
        if ocultar:
            self.ocultadas.append(getattr(id_categoria, "nome", id_categoria))


class VistaQueIgnoraOEstilo(VistaFalsa):
    """
    Vista que ACEITA a atribuicao de DisplayStyle mas continua em outro estilo -
    o mesmo que uma vista do Revit que recusa o estilo pedido. O script deve
    perceber (conferencia feita depois de gravar) e registrar o aviso.
    """

    def __init__(self, estilo_final):
        object.__setattr__(self, "estilo_final", estilo_final)
        VistaFalsa.__init__(self)

    @property
    def DisplayStyle(self):
        return object.__getattribute__(self, "estilo_final")

    @DisplayStyle.setter
    def DisplayStyle(self, valor):
        pass          # aceita a atribuicao e mantem o estilo antigo


class FamiliaFalsa(object):
    def __init__(self, nome_categoria):
        self.FamilyCategory = None if nome_categoria is None else CategoriaFalsa(nome_categoria)


class DocumentoFalso(object):
    def __init__(self, familia=None):
        self.OwnerFamily = familia


class DocumentoSemFamilia(object):
    """Documento sem OwnerFamily (organizar()/doc de projeto)."""

    @property
    def OwnerFamily(self):
        raise RuntimeError("documento nao tem OwnerFamily")


class OpcoesFalsas(object):
    def __init__(self):
        self.preprocessador = None
        self.clear_after_rollback = None

    def SetFailuresPreprocessor(self, preprocessador):
        self.preprocessador = preprocessador

    def SetClearAfterRollback(self, valor):
        self.clear_after_rollback = valor


class TransacaoFalsa(object):
    """Transaction falsa: registra inicio/commit/rollback de cada transacao."""

    criadas = []

    def __init__(self, *args, **kwargs):
        self.opcoes = OpcoesFalsas()
        self.iniciada = 0
        self.commits = 0
        self.rollbacks = 0
        TransacaoFalsa.criadas.append(self)

    def GetFailureHandlingOptions(self):
        return self.opcoes

    def SetFailureHandlingOptions(self, opcoes):
        self.opcoes = opcoes

    def Start(self):
        self.iniciada += 1

    def Commit(self):
        self.commits += 1

    def RollBack(self):
        self.rollbacks += 1


def ambiente(nomes_bic=None, categoria_familia="OST_GenericModel", provedor=None,
             vista=None, doc=None, estilo="SOMBREADO", ocultar=True):
    """
    Instala os stubs usados pelas funcoes sob teste e devolve (doc, vista).
    'nomes_bic' limita os nomes existentes em BuiltInCategory (um nome fora
    dessa lista representa um erro de digitacao em CATEGORIAS_OCULTAS_VISTA_3D).
    """
    globais["BuiltInCategory"] = BuiltInCategoryFalsa(
        CONFIG_ORIGINAL if nomes_bic is None else nomes_bic)
    globais["Category"] = CategoriasFalsas if provedor is None else provedor
    globais["ElementId"] = ElementIdFalsa
    globais["Transaction"] = TransacaoFalsa
    globais["ESTILO_VISUAL_VISTA_3D"] = estilo
    globais["OCULTAR_CATEGORIAS_VISTA_3D"] = ocultar
    TransacaoFalsa.criadas = []
    if doc is None:
        doc = DocumentoFalso(None if categoria_familia is None
                             else FamiliaFalsa(categoria_familia))
    if vista is None:
        vista = VistaFalsa()
    return doc, vista


definir_estilo = globais["definir_estilo_vista_3d"]
ocultar_categorias = globais["ocultar_categorias_vista_3d"]
estilo_configurado = globais["estilo_visual_configurado"]
categoria_da_familia = globais["categoria_da_propria_familia"]
chave_estilo = globais["chave_estilo_visual"]
chave_do_estilo = globais["chave_do_estilo_visual"]
descricao_estilo = globais["descricao_estilo_visual"]

ESTILO_CONFIGURADO = globais["ESTILO_VISUAL_VISTA_3D"]
ESTILOS = globais["ESTILOS_VISUAIS_VISTA_3D"]
APELIDOS = globais["_APELIDOS_ESTILO_VISUAL"]
COM_ARESTAS = globais["_ESTILOS_COM_ARESTAS"]
MOSTRAR_ARESTAS = globais["MOSTRAR_ARESTAS_VISTA_3D"]

print("--- configuracao ---")
verificar(globais["OUT"][0].startswith("RESUMO | familias encontradas: 0"),
          "bloco em lote executado: " + globais["OUT"][0])
verificar(ESTILO_CONFIGURADO == "SOMBREADO" and MOSTRAR_ARESTAS is True,
          "padrao: ESTILO_VISUAL_VISTA_3D = {0!r} + MOSTRAR_ARESTAS_VISTA_3D = {1!r}".format(
              ESTILO_CONFIGURADO, MOSTRAR_ARESTAS))
verificar(estilo_configurado() is ESTILO_SHADING_COM_ARESTAS,
          "padrao -> DisplayStyle.ShadingWithEdges ('Sombreado com arestas')")
verificar(sorted(ESTILOS) == ["CORES_CONSISTENTES", "ESTRUTURA_ARAME", "LINHAS_OCULTAS",
                              "REALISTA", "REALISTA_COM_ARESTAS", "SOMBREADO",
                              "SOMBREADO_COM_ARESTAS"],
          "ESTILOS_VISUAIS_VISTA_3D: " + ", ".join(sorted(ESTILOS)))
verificar(ESTILOS["SOMBREADO"] is ESTILO_SHADING and
          ESTILOS["LINHAS_OCULTAS"] is banco.DisplayStyle.HLR and
          ESTILOS["ESTRUTURA_ARAME"] is ESTILO_WIREFRAME and
          ESTILOS["CORES_CONSISTENTES"] is banco.DisplayStyle.FlatColors and
          ESTILOS["REALISTA"] is banco.DisplayStyle.Realistic and
          ESTILOS["SOMBREADO_COM_ARESTAS"] is ESTILO_SHADING_COM_ARESTAS and
          ESTILOS["REALISTA_COM_ARESTAS"] is ESTILO_REALISTA_COM_ARESTAS,
          "chaves -> Wireframe/HLR/Shading/ShadingWithEdges/FlatColors/Realistic/RealisticWithEdges")
verificar(COM_ARESTAS == {"SOMBREADO": "SOMBREADO_COM_ARESTAS",
                          "REALISTA": "REALISTA_COM_ARESTAS"},
          "estilos COM arestas mapeados: " + repr(COM_ARESTAS))
verificar(all(destino in ESTILOS for destino in APELIDOS.values()),
          "todos os apelidos apontam para uma chave existente: " + repr(APELIDOS))
verificar(globais["OCULTAR_CATEGORIAS_VISTA_3D"] is True,
          "OCULTAR_CATEGORIAS_VISTA_3D ligado por padrao")
verificar(len(set(CONFIG_ORIGINAL)) == len(CONFIG_ORIGINAL) and
          all(nome.startswith("OST_") for nome in CONFIG_ORIGINAL),
          "CATEGORIAS_OCULTAS_VISTA_3D sem repeticao e com nomes de BuiltInCategory")
verificar(all(nome in CONFIG_ORIGINAL for nome in
              ("OST_Dimensions", "OST_TextNotes", "OST_GenericAnnotation", "OST_Levels",
               "OST_Grids", "OST_CLines", "OST_ReferenceLines", "OST_ReferencePoints",
               "OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs")),
          "anotacoes/cotas e elementos auxiliares previstos na lista: {0}".format(
              len(CONFIG_ORIGINAL)))

print("--- estilo visual da vista 3D (definir_estilo_vista_3d) ---")
doc, vista = ambiente()
vista.DisplayStyle = ESTILO_WIREFRAME
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and vista.DisplayStyle is ESTILO_SHADING_COM_ARESTAS,
          "padrao aplica 'Sombreado com arestas' (DisplayStyle.ShadingWithEdges)")
verificar(avisos == [], "sem avisos ao aplicar o estilo: " + repr(avisos))
verificar(len(TransacaoFalsa.criadas) == 1 and TransacaoFalsa.criadas[0].iniciada == 1
          and TransacaoFalsa.criadas[0].commits == 1,
          "estilo gravado em transacao (1 Start + 1 Commit)")

doc, vista = ambiente()
vista.DisplayStyle = ESTILO_SHADING_COM_ARESTAS
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and TransacaoFalsa.criadas == [],
          "vista ja no estilo pedido: nada e' gravado (nenhuma transacao)")

doc, vista = ambiente(estilo="  shading ")
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and vista.DisplayStyle is ESTILO_SHADING_COM_ARESTAS and avisos == [],
          "apelido/espacos/caixa ('  shading ') resolvem para Sombreado (+ arestas)")

doc, vista = ambiente(estilo=ESTILO_SHADING)
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and vista.DisplayStyle is ESTILO_SHADING_COM_ARESTAS,
          "aceita o proprio valor do enum (ESTILO_VISUAL_VISTA_3D = DisplayStyle.Shading)")

doc, vista = ambiente(estilo="Sombreado com arestas")
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and vista.DisplayStyle is ESTILO_SHADING_COM_ARESTAS and avisos == [],
          "'Sombreado com arestas' (rotulo do Revit) -> SOMBREADO_COM_ARESTAS")

doc, vista = ambiente(estilo="SHADING_WITH_EDGES")
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and vista.DisplayStyle is ESTILO_SHADING_COM_ARESTAS and avisos == [],
          "apelido SHADING_WITH_EDGES -> SOMBREADO_COM_ARESTAS")

doc, vista = ambiente(estilo="")
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is False and vista.DisplayStyle is None and avisos == []
          and TransacaoFalsa.criadas == [],
          "estilo \"\" = nao mexer na vista (sem aviso e sem transacao)")

doc, vista = ambiente(estilo="ZZZ")
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is False and vista.DisplayStyle is None and len(avisos) == 1
          and "valor desconhecido" in avisos[0] and "SOMBREADO" in avisos[0],
          "estilo invalido vira aviso: " + repr(avisos))

doc, vista = ambiente()
avisos = []
resultado = definir_estilo(doc, None, avisos)
verificar(resultado is False and avisos == [] and TransacaoFalsa.criadas == [],
          "vista3d = None: nada e' feito (familia sem vista 3D)")

doc, vista = ambiente(vista=VistaQueFalhaNoEstilo())
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is False and len(avisos) == 1 and "estilo visual" in avisos[0],
          "falha ao alterar o estilo vira aviso: " + repr(avisos))
verificar(TransacaoFalsa.criadas[0].rollbacks == 1 and TransacaoFalsa.criadas[0].commits == 0,
          "falha no estilo: transacao desfeita (rollback), sem interromper o lote")

doc, vista = ambiente(vista=VistaQueIgnoraOEstilo(ESTILO_WIREFRAME))
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and len(avisos) == 1
          and "ficou em 'ESTRUTURA_ARAME'" in avisos[0]
          and "SOMBREADO_COM_ARESTAS" in avisos[0],
          "conferencia pos-gravacao: vista que recusa o estilo vira aviso: " + repr(avisos))

doc, vista = ambiente(estilo="Estrutura de arame")
verificar(estilo_configurado() is ESTILO_WIREFRAME,
          "'Estrutura de arame' (rotulo do Revit, com espacos) -> DisplayStyle.Wireframe")

print("--- arestas na vista sombreada (MOSTRAR_ARESTAS_VISTA_3D) ---")
doc, vista = ambiente()
verificar(chave_estilo() == "SOMBREADO_COM_ARESTAS",
          "padrao: chave_estilo_visual() -> SOMBREADO_COM_ARESTAS")
verificar(descricao_estilo() == "SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D)",
          "descricao_estilo_visual(): " + repr(descricao_estilo()))

globais["ESTILO_VISUAL_VISTA_3D"] = "REALISTA"
verificar(chave_estilo() == "REALISTA_COM_ARESTAS" and
          estilo_configurado() is ESTILO_REALISTA_COM_ARESTAS,
          "REALISTA + arestas -> DisplayStyle.RealisticWithEdges")

globais["ESTILO_VISUAL_VISTA_3D"] = "CORES_CONSISTENTES"
verificar(chave_estilo() == "CORES_CONSISTENTES" and
          estilo_configurado() is banco.DisplayStyle.FlatColors and
          descricao_estilo() == "CORES_CONSISTENTES",
          "CORES_CONSISTENTES nao tem variante com arestas: nada muda")

globais["ESTILO_VISUAL_VISTA_3D"] = "LINHAS_OCULTAS"
verificar(estilo_configurado() is banco.DisplayStyle.HLR and
          descricao_estilo() == "LINHAS_OCULTAS",
          "LINHAS_OCULTAS ja mostra as arestas: continua HLR")

globais["MOSTRAR_ARESTAS_VISTA_3D"] = False
globais["ESTILO_VISUAL_VISTA_3D"] = "SOMBREADO"
verificar(chave_estilo() == "SOMBREADO" and estilo_configurado() is ESTILO_SHADING and
          descricao_estilo() == "SOMBREADO",
          "MOSTRAR_ARESTAS_VISTA_3D = False: vale o estilo simples (DisplayStyle.Shading)")

doc, vista = ambiente(estilo=ESTILO_SHADING)
vista.DisplayStyle = ESTILO_SHADING
avisos = []
resultado = definir_estilo(doc, vista, avisos)
verificar(resultado is True and TransacaoFalsa.criadas == [],
          "ajuste desligado + vista ja em Shading: nada e' gravado")

globais["ESTILO_VISUAL_VISTA_3D"] = "SOMBREADO_COM_ARESTAS"
verificar(estilo_configurado() is ESTILO_SHADING_COM_ARESTAS and
          descricao_estilo() == "SOMBREADO_COM_ARESTAS",
          "chave explicita SOMBREADO_COM_ARESTAS vale mesmo com o ajuste desligado")

globais["ESTILO_VISUAL_VISTA_3D"] = "SOMBREADO"
globais["MOSTRAR_ARESTAS_VISTA_3D"] = True
verificar(estilo_configurado() is ESTILO_SHADING_COM_ARESTAS and
          descricao_estilo().startswith("SOMBREADO_COM_ARESTAS"),
          "ajuste de arestas ligado de novo (padrao restaurado)")

print("--- categorias ocultas na vista 3D (ocultar_categorias_vista_3d) ---")
doc, vista = ambiente()
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == list(CONFIG_ORIGINAL),
          "familia generica: as {0} categorias configuradas ocultadas na ordem".format(
              len(ocultadas)))
verificar(vista.ocultadas == list(CONFIG_ORIGINAL),
          "View.SetCategoryHidden(Id, True) chamado para cada categoria")
verificar(avisos == [], "sem avisos: " + repr(avisos))
verificar(len(TransacaoFalsa.criadas) == 1 and TransacaoFalsa.criadas[0].iniciada == 1
          and TransacaoFalsa.criadas[0].commits == 1,
          "tudo em uma unica transacao comitada")

doc, vista = ambiente(categoria_familia="OST_Walls")
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar("OST_Walls" not in ocultadas and "OST_Walls" not in vista.ocultadas,
          "familia de PAREDE (FamilyCategory = OST_Walls): a propria parede segue visivel")
verificar(ocultadas == [n for n in CONFIG_ORIGINAL if n != "OST_Walls"],
          "as demais {0} categorias foram ocultadas normalmente".format(len(ocultadas)))
verificar(len(avisos) == 1 and "OST_Walls" in avisos[0] and "propria familia" in avisos[0],
          "aviso registrado para a categoria preservada: " + repr(avisos))

doc, vista = ambiente(categoria_familia="OST_GenericAnnotation")
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar("OST_GenericAnnotation" not in ocultadas and len(ocultadas) == len(CONFIG_ORIGINAL) - 1,
          "familia de ANOTACAO: o proprio simbolo nao e' ocultado (preview nao fica vazio)")

doc, vista = ambiente()
ocultadas = ocultar_categorias(doc, vista, [])
verificar("OST_Dimensions" in ocultadas and "OST_GenericAnnotation" in ocultadas,
          "cotas (OST_Dimensions) e anotacoes (OST_GenericAnnotation) ocultadas por categoria")

globais["CATEGORIAS_OCULTAS_VISTA_3D"] = ("OST_Dimensions", "OST_NaoExiste", "OST_Walls")
doc, vista = ambiente(nomes_bic=("OST_Dimensions", "OST_Walls"))
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == ["OST_Dimensions", "OST_Walls"],
          "nome inexistente em CATEGORIAS_OCULTAS_VISTA_3D e' ignorado: " + repr(ocultadas))
verificar(len(avisos) == 1 and "nao encontrada" in avisos[0] and "OST_NaoExiste" in avisos[0],
          "erro de digitacao na lista vira aviso: " + repr(avisos))

globais["CATEGORIAS_OCULTAS_VISTA_3D"] = ("OST_Dimensions",)
doc, vista = ambiente(provedor=CategoriasQueDevolvemNone)
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == [] and vista.ocultadas == [] and len(avisos) == 1
          and "nao encontrada" in avisos[0],
          "Category.GetCategory -> None (categoria fora da familia): ignorada com aviso")

doc, vista = ambiente(provedor=CategoriasQueFalham)
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == [] and len(avisos) == 1 and "OST_Dimensions" in avisos[0],
          "Category.GetCategory que lanca nao interrompe o lote: " + repr(avisos))

globais["CATEGORIAS_OCULTAS_VISTA_3D"] = CONFIG_ORIGINAL

doc, vista = ambiente(vista=VistaFalsa(falhas=("OST_Dimensions",)))
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == [n for n in CONFIG_ORIGINAL if n != "OST_Dimensions"],
          "falha em UMA categoria nao impede as outras de serem ocultadas")
verificar(len(avisos) == 1 and "OST_Dimensions" in avisos[0] and "ocultar" in avisos[0],
          "falha ao ocultar vira aviso: " + repr(avisos))
verificar(TransacaoFalsa.criadas[0].commits == 1 and TransacaoFalsa.criadas[0].rollbacks == 0,
          "o que deu certo continua ocultado (transacao comitada, sem rollback)")

doc, vista = ambiente(doc=DocumentoSemFamilia())
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == list(CONFIG_ORIGINAL) and avisos == [],
          "doc sem OwnerFamily: oculta a lista inteira, sem avisos")

doc, vista = ambiente(categoria_familia=None)
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == list(CONFIG_ORIGINAL) and avisos == [],
          "familia sem FamilyCategory: oculta a lista inteira, sem avisos")

doc, vista = ambiente(ocultar=False)
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == [] and vista.ocultadas == [] and TransacaoFalsa.criadas == [],
          "OCULTAR_CATEGORIAS_VISTA_3D = False: nada e' ocultado (botao de desligar)")

doc, vista = ambiente()
ocultadas = ocultar_categorias(doc, None, [])
verificar(ocultadas == [] and TransacaoFalsa.criadas == [],
          "vista3d = None: nada e' feito (familia sem vista 3D)")

print("--- ordem dos passos no lote (processar_familia) ---")
padrao = re.compile(
    r"vista3d = obter_vista_3d\(doc, avisos\)\s*\n"
    r"\s*padronizar_nome_vista_3d\(doc, vista3d, avisos\)\s*\n"
    r"\s*orientar_vista_3d\(doc, vista3d, avisos\)\s*\n"
    r"\s*estilo_visual_ok = definir_estilo_vista_3d\(doc, vista3d, avisos\)\s*\n"
    r"\s*categorias_ocultas = ocultar_categorias_vista_3d\(doc, vista3d, avisos\)\s*\n"
    r"\s*definir_preview_permanente\(doc, vista3d, avisos\)")
verificar(padrao.search(FONTE) is not None,
          "vista 3D preparada na ordem: nome -> direcao -> estilo -> categorias -> preview")
verificar("estilo 3D: {3} | categorias ocultas: {4} | " in FONTE and
          "estilo_aplicado = descricao_estilo_visual()" in FONTE,
          "linha de resultado do lote mostra 'estilo 3D' (com o ajuste de arestas) "
          "e 'categorias ocultas'")

print("--- resumo ---")
if FALHAS:
    print("VERIFICACOES FALHAS: {0}".format(len(FALHAS)))
    for falha in FALHAS:
        print("  - " + falha)
    sys.exit(1)
print("VERIFICACOES FALHAS: 0")



