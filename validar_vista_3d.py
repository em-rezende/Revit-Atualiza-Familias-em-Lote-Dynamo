# -*- coding: utf-8 -*-
# =============================================================================
#  VALIDADOR (SEM ABRIR O REVIT): ESTILO VISUAL, CATEGORIAS OCULTAS E
#  ENTRADAS DO DYNAMO (IN[1]/IN[2]/IN[3])
# -----------------------------------------------------------------------------
#  Testa, fora do Revit, o que o script faz na vista de preview antes de salvar:
#
#    - definir_estilo_vista_3d(): aplica View.DisplayStyle (padrao
#      DisplayStyle.ShadingWithEdges = "Sombreado com arestas", porque
#      MOSTRAR_ARESTAS_VISTA_3D = True), aceita as chaves de
#      ESTILOS_VISUAIS_VISTA_3D e os apelidos ("SHADING", "Shaded",
#      "SHADING_WITH_EDGES"...), aceita o proprio valor do enum e transforma
#      chave invalida em AVISO (sem mexer na vista); depois de gravar, CONFERE o
#      estilo que ficou na vista e avisa quando o Revit aplicou outro;
#
#    - chave_estilo_visual()/descricao_estilo_visual()/MOSTRAR_ARESTAS_VISTA_3D:
#      o ajuste de arestas troca "SOMBREADO" por "SOMBREADO_COM_ARESTAS" e
#      "REALISTA" por "REALISTA_COM_ARESTAS"; "ESTRUTURA_ARAME"/"LINHAS_OCULTAS"
#      (que ja mostram as arestas) e "CORES_CONSISTENTES" (sem variante com
#      arestas) nao mudam;
#
#    - ocultar_categorias_vista_3d(): chama View.SetCategoryHidden para cada
#      categoria da lista do TIPO EFETIVO do preview (CATEGORIAS_OCULTAS_POR_TIPO;
#      fallback na lista padrao CATEGORIAS_OCULTAS_VISTA_3D), IGNORA nomes de
#      BuiltInCategory que nao existem (erro de digitacao), tolera falha em UMA
#      categoria e - o mais importante - NUNCA oculta a categoria da propria
#      familia (Family.FamilyCategory): uma familia de parede mantem OST_Walls
#      visivel;
#
#    - a tabela por tipo: VISTA_3D oculta niveis e eixos (preview limpo);
#      PLANTA e CORTE MANTEM niveis e eixos; ELEVACAO mantem niveis; DETALHE
#      oculta so' as categorias de referencia (vista de desenho);
#
#    - as ENTRADAS DO DYNAMO (IN[1]/IN[2]/IN[3]): _normalizar_escolha()
#      (hifen/underscore/espaco -> mesmo resultado), _resolver_entrada()
#      (rotulo -> chave interna; desconhecido -> padrao + aviso),
#      _resolver_entradas_dynamo() (IN ausente -> padroes sem avisos),
#      as 6 direcoes do cubo (FSD/FSE/TSD/TSE/FID/FIE), os apelidos antigos
#      (SE/SO/NE/NO Isometric), a ortogonalidade forward.up == 0 e as 7 chaves
#      de estilo (Wireframe, Hidden Lines, Shading, Shading With Edges,
#      Flat Colors, Realistic, Realistic With Edges);
#
#    - ordem dos passos em processar_familia(): vista -> estilo -> ocultar ->
#      preview, e a linha de resultado com "estilo:"/"categorias ocultas:"
#      mostrando o estilo que valeu de fato (com o ajuste de arestas);
#
#    - log CSV (_linha_csv): header na ordem fixa e escape correto de aspas e
#      ';' dentro do campo de avisos.
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
"""Valida, fora do Revit, o estilo, as categorias e as entradas IN[1..3]."""

import io
import os
import re
import sys
import math
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
    o mesmo que uma vista do Revit que recusa o estilo pedido.
    """

    def __init__(self, estilo_final):
        object.__setattr__(self, "estilo_final", estilo_final)
        VistaFalsa.__init__(self)

    @property
    def DisplayStyle(self):
        return object.__getattribute__(self, "estilo_final")

    @DisplayStyle.setter
    def DisplayStyle(self, valor):
        pass


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

print("--- categorias ocultas na vista (ocultar_categorias_vista_3d) ---")
doc, vista = ambiente()
avisos = []
ocultadas = ocultar_categorias(doc, vista, avisos)
verificar(ocultadas == list(CONFIG_ORIGINAL),
          "familia generica: as {0} categorias da lista padrao ocultadas".format(
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
# Vista do preview (IN[1]/IN[2]) -> estilo (IN[3]) -> categorias ocultas -> preview.
padrao = re.compile(
    r"vista_preview, tipo_aplicado = obter_vista_preview\(\s*\n"
    r"\s*doc, tipo_vista, direcao3d, avisos\)\s*\n"
    r".*?"
    r"estilo_visual_ok = definir_estilo_vista_3d\(doc, vista_preview, avisos\)\s*\n"
    r".*?"
    r"categorias_ocultas = ocultar_categorias_vista_3d\(\s*\n"
    r"\s*doc, vista_preview, avisos, tipo_aplicado\)\s*\n"
    r".*?"
    r"definir_preview_permanente\(doc, vista_preview, avisos\)",
    re.DOTALL)
verificar(padrao.search(FONTE) is not None,
          "vista do preview preparada na ordem: vista -> estilo -> categorias -> preview")

# Na vista 3D (IN[1] = "Vista 3D"), obter_vista_preview() padroniza o NOME e so'
# depois ORIENTA a vista (nome -> direcao).
padrao_3d = re.compile(
    r'vista = obter_vista_3d\(doc, avisos\)\s*\n'
    r'\s*padronizar_nome_vista_3d\(doc, vista, avisos\)\s*\n'
    r'\s*orientar_vista_3d\(doc, vista, avisos, direcao3d\)\s*\n'
    r'\s*return vista, "VISTA_3D"')
verificar(padrao_3d.search(FONTE) is not None,
          "vista 3D preparada na ordem: nome -> direcao")

# O rotulo "estilo 3D:" antigo foi trocado por "estilo:" (que vale para qualquer
# tipo de preview). E o "categorias ocultas:" continua. O tipo efetivo do
# preview (VISTA_3D/PLANTA/...) e' acrescentado entre parenteses.
verificar("estilo: {4} | categorias ocultas: {5} | " in FONTE and
          "estilo_aplicado = descricao_estilo_visual()" in FONTE,
          "linha de resultado do lote mostra 'estilo' (com o ajuste de arestas) "
          "e 'categorias ocultas'")

print("--- IN[1]/IN[2]/IN[3] (escolhas do Dynamo) ---")
_normalizar_escolha = globais["_normalizar_escolha"]
_resolver_entrada = globais["_resolver_entrada"]
_resolver_entradas_dynamo = globais["_resolver_entradas_dynamo"]
TIPOS_VISTA_PREVIEW = globais["TIPOS_VISTA_PREVIEW"]
DIRECOES_VISTA_3D_APELIDOS = globais["DIRECOES_VISTA_3D_APELIDOS"]
ESTILOS_VISUAIS_APELIDOS = globais["ESTILOS_VISUAIS_APELIDOS"]
DIRECOES_VISTA_3D = globais["DIRECOES_VISTA_3D"]

# 1) Normalizacao de rotulos: hifens, underscores e espacos caem na mesma chave
verificar(_normalizar_escolha("Frente-Superior-Direita").upper() ==
          _normalizar_escolha("Frente Superior Direita").upper() ==
          _normalizar_escolha("FRENTE_SUPERIOR_DIREITA").upper(),
          "_normalizar_escolha: hifen, espaco e underscore sao equivalentes")
verificar(_normalizar_escolha("  shading ") == "shading",
          "_normalizar_escolha: strip e caixa preservada (normalizacao no resolver)")
verificar(_normalizar_escolha("") is None and _normalizar_escolha(None) is None,
          "_normalizar_escolha: vazio/None -> None")

# 2) _resolver_entrada: rotulo valido, apelido e valor desconhecido
def _resolver_com_avisos(valor, padrao, mapa):
    avisos = []
    resultado = _resolver_entrada(valor, padrao, mapa, "teste", avisos)
    return resultado, avisos

r, av = _resolver_com_avisos("Vista 3D", "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "VISTA_3D" and av == [], "IN[1] 'Vista 3D' -> VISTA_3D")
r, av = _resolver_com_avisos("Planta", "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "PLANTA" and av == [], "IN[1] 'Planta' -> PLANTA")
r, av = _resolver_com_avisos("Elevação", "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "ELEVACAO" and av == [], "IN[1] 'Elevação' -> ELEVACAO")
r, av = _resolver_com_avisos("VISTA_3D", "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "VISTA_3D" and av == [], "IN[1] chave interna -> mesmo valor")
r, av = _resolver_com_avisos("xyz", "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "VISTA_3D" and len(av) == 1 and "xyz" in av[0],
          "IN[1] desconhecido -> padrao + aviso: " + repr(av))
r, av = _resolver_com_avisos(None, "VISTA_3D", TIPOS_VISTA_PREVIEW)
verificar(r == "VISTA_3D" and av == [], "IN[1] ausente -> padrao sem aviso")

# 3) IN[2]: as 6 direcoes do cubo + apelidos antigos
for entrada, esperado in (
        ("Topo", "TOPO"), ("Frontal", "FRONTAL"),
        ("Esquerda", "ESQUERDA"), ("Direita", "DIREITA"),
        ("Posterior", "POSTERIOR"), ("Inferior", "INFERIOR"),
        ("Top", "TOPO"), ("Front", "FRONTAL"),
        ("Left", "ESQUERDA"), ("Right", "DIREITA"),
        ("Back", "POSTERIOR"), ("Bottom", "INFERIOR"),
#
        ("Frente-Superior-Direita", "FSD"),
        ("Frente-Superior-Esquerda", "FSE"),
        ("Tras-Superior-Direita", "TSD"),
        ("Tras-Superior-Esquerda", "TSE"),
        ("Frente-Inferior-Direita", "FID"),
        ("Frente-Inferior-Esquerda", "FIE"),
        ("FSD", "FSD"), ("fid", "FID"),
        ("SE Isometric", "FSD"),
        ("SO Isometric", "FSE"),
        ("NE Isometric", "TSD"),
        ("NO Isometric", "TSE"),
):
    r, av = _resolver_com_avisos(entrada, "FSD", DIRECOES_VISTA_3D_APELIDOS)
    verificar(r == esperado and av == [],
              "IN[2] {0!r} -> {1}".format(entrada, esperado))
r, av = _resolver_com_avisos("xyz", "FSD", DIRECOES_VISTA_3D_APELIDOS)
verificar(r == "FSD" and len(av) == 1,
          "IN[2] desconhecido -> padrao + aviso")

# 4) Ortogonalidade das 6 direcoes (forward . up == 0) e sinal do Z no up
for chave_dir, (fwd, up) in DIRECOES_VISTA_3D.items():
    dot = fwd[0] * up[0] + fwd[1] * up[1] + fwd[2] * up[2]
    verificar(abs(dot) < 1e-9,
              "DIRECOES_VISTA_3D[{0}]: forward . up = {1}".format(chave_dir, dot))
verificar(DIRECOES_VISTA_3D["FID"][1][2] < 0 and DIRECOES_VISTA_3D["FIE"][1][2] < 0,
          "FID/FIE: up tem componente Z negativo (camera abaixo do modelo)")
verificar(DIRECOES_VISTA_3D["FSD"][1][2] > 0 and DIRECOES_VISTA_3D["FSE"][1][2] > 0
          and DIRECOES_VISTA_3D["TSD"][1][2] > 0 and DIRECOES_VISTA_3D["TSE"][1][2] > 0,
          "FSD/FSE/TSD/TSE: up tem componente Z positivo (camera acima)")

# 5) IN[3]: rotulos, apelidos e desconhecido
for entrada, esperado in (
        ("Wireframe", "ESTRUTURA_ARAME"),
        ("Hidden Lines", "LINHAS_OCULTAS"),
        ("Shading", "SOMBREADO"),
        ("Shading With Edges", "SOMBREADO_COM_ARESTAS"),
        ("Flat Colors", "CORES_CONSISTENTES"),
        ("Realistic", "REALISTA"),
        ("Realistic With Edges", "REALISTA_COM_ARESTAS"),
        ("SHADING_WITH_EDGES", "SOMBREADO_COM_ARESTAS"),
        ("HIDDEN_LINES", "LINHAS_OCULTAS"),
):
    chave = ESTILOS_VISUAIS_APELIDOS.get(entrada.upper(), entrada.upper())
    verificar(chave_do_estilo(chave) == esperado,
              "IN[3] {0!r} -> {1}".format(entrada, esperado))

# 6) _resolver_entradas_dynamo: com IN = [""] (sem entradas), cai tudo no padrao
def _resolver_com_in(lista_in):
    globais["IN"] = lista_in
    return _resolver_entradas_dynamo()

tipo, direcao, estilo, avisos = _resolver_com_in([""])
verificar(tipo == "VISTA_3D" and direcao == "FSD" and
          chave_do_estilo(estilo) == "SOMBREADO" and avisos == [],
          "IN=[] -> padroes sem avisos")
tipo, direcao, estilo, avisos = _resolver_com_in(
    ["", "Planta", "Frente-Inferior-Direita", "Realistic With Edges"])
verificar(tipo == "PLANTA" and direcao == "FID" and
          chave_do_estilo(estilo) == "REALISTA_COM_ARESTAS" and avisos == [],
          "IN completo -> escolhas resolvidas")
tipo, direcao, estilo, avisos = _resolver_com_in(["", "xyz", "xyz", "xyz"])
verificar(tipo == "VISTA_3D" and direcao == "FSD" and
          chave_do_estilo(estilo) == "SOMBREADO" and len(avisos) == 3,
          "IN invalido -> 3 avisos, tudo no padrao: " + repr(avisos))

# Restaura IN para o estado inicial (nao interfere em mais nada)
globais["IN"] = [""]

print("--- categorias ocultas por tipo de vista (CATEGORIAS_OCULTAS_POR_TIPO) ---")
_categorias_para_ocultar = globais["_categorias_para_ocultar"]
CATEGORIAS_POR_TIPO = globais["CATEGORIAS_OCULTAS_POR_TIPO"]
CATEGORIAS_PADRAO = globais["CATEGORIAS_OCULTAS_VISTA_3D"]

# 1) Toda chave esperada esta presente
for tipo in ("VISTA_3D", "PLANTA", "CORTE", "DETALHE", "ELEVACAO"):
    verificar(tipo in CATEGORIAS_POR_TIPO,
              "CATEGORIAS_OCULTAS_POR_TIPO tem {0}".format(tipo))

# 2) Diferenca conceitual: VISTA_3D oculta OST_Levels/OST_Grids; PLANTA/CORTE nao
verificar("OST_Levels" in CATEGORIAS_POR_TIPO["VISTA_3D"] and
          "OST_Grids" in CATEGORIAS_POR_TIPO["VISTA_3D"],
          "VISTA_3D oculta niveis e eixos (preview limpo)")
verificar("OST_Levels" not in CATEGORIAS_POR_TIPO["PLANTA"] and
          "OST_Grids" not in CATEGORIAS_POR_TIPO["PLANTA"],
          "PLANTA mantem niveis e eixos")
verificar("OST_Levels" not in CATEGORIAS_POR_TIPO["CORTE"] and
          "OST_Grids" not in CATEGORIAS_POR_TIPO["CORTE"],
          "CORTE mantem niveis e eixos")
verificar("OST_Levels" in CATEGORIAS_POR_TIPO["ELEVACAO"] and
          "OST_Grids" not in CATEGORIAS_POR_TIPO["ELEVACAO"],
          "ELEVACAO: mantem niveis (uteis de frente), sem eixos")
verificar("OST_Levels" not in CATEGORIAS_POR_TIPO["DETALHE"] and
          "OST_Dimensions" not in CATEGORIAS_POR_TIPO["DETALHE"],
          "DETALHE: nao oculta niveis nem cotas (vista de desenho)")

# 3) Fallback: tipo desconhecido/None -> lista PADRAO
verificar(_categorias_para_ocultar("QUALQUER") == CATEGORIAS_PADRAO and
          _categorias_para_ocultar(None) == CATEGORIAS_PADRAO,
          "tipo desconhecido/None -> lista padrao")

# 4) Toda categoria da tabela e' nome valido de BuiltInCategory
todos = set()
for lista in CATEGORIAS_POR_TIPO.values():
    todos.update(lista)
todos.update(CATEGORIAS_PADRAO)
for nome in sorted(todos):
    verificar(nome.startswith("OST_"),
              "categoria '{0}' tem prefixo OST_".format(nome))

# 5) ocultar_categorias_vista_3d aceita tipo_vista e usa a tabela certa
globais["CATEGORIAS_OCULTAS_VISTA_3D"] = CATEGORIAS_PADRAO
doc, vista = ambiente()
ocultadas_3d = ocultar_categorias(doc, vista, [], "VISTA_3D")
verificar(ocultadas_3d == list(CATEGORIAS_POR_TIPO["VISTA_3D"]),
          "ocultar_categorias_vista_3d(tipo='VISTA_3D') usa a tabela de VISTA_3D")

doc, vista = ambiente()
ocultadas_planta = ocultar_categorias(doc, vista, [], "PLANTA")
verificar(ocultadas_planta == list(CATEGORIAS_POR_TIPO["PLANTA"]),
          "ocultar_categorias_vista_3d(tipo='PLANTA') usa a tabela de PLANTA")
verificar("OST_Levels" not in ocultadas_planta and "OST_Grids" not in ocultadas_planta,
          "PLANTA: niveis e eixos efetivamente preservados")

doc, vista = ambiente()
ocultadas_padrao = ocultar_categorias(doc, vista, [], None)
verificar(ocultadas_padrao == list(CATEGORIAS_PADRAO),
          "ocultar_categorias_vista_3d(tipo=None) usa a lista padrao")

# 6) A categoria da propria familia continua preservada em qualquer tipo
doc, vista = ambiente(categoria_familia="OST_Walls")
ocultadas = ocultar_categorias(doc, vista, [], "VISTA_3D")
verificar("OST_Walls" not in ocultadas,
          "categoria da propria familia preservada tambem com tabela por tipo")

print("--- log CSV (campos e escape) ---")
_linha_csv = globais["_linha_csv"]

campos_teste = {
    "arquivo": "Porta.rfa",
    "status": "OK",
    "purgados": 4,
    "tipo_escolhido": "VISTA_3D",
    "tipo_preview": "VISTA_3D",
    "vista_preview": "Vista 1",
    "estilo": "SOMBREADO_COM_ARESTAS",
    "categorias_ocultas": 12,
    "vistas_renomeadas": 0,
    "destino": "Porta.rfa",
    "avisos": "",
}
texto = _linha_csv(campos_teste)
verificar(texto.startswith("arquivo;status;purgados;"),
          "CSV: header comeca com 'arquivo;status;purgados;'")
verificar("Porta.rfa" in texto and "SOMBREADO_COM_ARESTAS" in texto,
          "CSV: valores do registro presentes")
verificar(texto.count("\n") == 2,
          "CSV: header + 1 registro (2 quebras de linha)")

campos_aviso = dict(campos_teste)
campos_aviso["avisos"] = 'erro "grave"; outro'
texto = _linha_csv(campos_aviso)
verificar('""grave""' in texto and '; outro' in texto,
          "CSV: aspas duplicadas e ';' preservados no campo de avisos")

print("--- resumo ---")
if FALHAS:
    print("VERIFICACOES FALHAS: {0}".format(len(FALHAS)))
    for falha in FALHAS:
        print("  - " + falha)
    sys.exit(1)
print("VERIFICACOES FALHAS: 0")
