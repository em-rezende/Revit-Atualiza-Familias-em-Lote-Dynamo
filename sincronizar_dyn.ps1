<#
    sincronizar_dyn.ps1
    ---------------------------------------------------------------------------
    Mantem o codigo Python do grafo Dynamo (.dyn) identico ao arquivo .py.

    O arquivo "Atualiza Familias em Lote.dyn" guarda todo o script Python dentro do
    campo JSON "Code" do no PythonScriptNode. Sempre que batch_format_families.py
    for alterado, rode este script para copiar o conteudo para o .dyn:

        powershell -ExecutionPolicy Bypass -File ".\sincronizar_dyn.ps1"

    O script tambem CONFERE o resultado: le o .dyn de volta como JSON e compara
    o campo Code com o arquivo .py (avisa se algo nao bater).
#>
[CmdletBinding()]
param(
    [string]$Py  = '',
    [string]$Dyn = ''
)

# Caminhos: por padrao, os dois arquivos ficam na mesma pasta deste script
$raiz = $PSScriptRoot
if (-not $raiz) { $raiz = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $raiz) { $raiz = (Get-Location).Path }
if (-not $Py)  { $Py  = Join-Path $raiz 'batch_format_families.py' }
if (-not $Dyn) { $Dyn = Join-Path $raiz 'Atualiza Familias em Lote.dyn' }

$utf8 = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $Py))  { throw "Arquivo Python nao encontrado: $Py" }
if (-not (Test-Path $Dyn)) { throw "Grafo Dynamo nao encontrado: $Dyn" }

# 1) Codigo Python (quebras de linha LF dentro do JSON)
$code = $utf8.GetString([System.IO.File]::ReadAllBytes($Py))
$code = $code.TrimStart([char]0xFEFF).Replace("`r`n", "`n").Replace("`r", "`n")
if (-not $code.EndsWith("`n")) { $code += "`n" }

# 2) Escapa para JSON (aspas, barras e caracteres de controle). Acentos ficam
#    como caracteres normais, igual ao restante do .dyn (UTF-8 sem BOM).
$sb = New-Object System.Text.StringBuilder
foreach ($ch in $code.ToCharArray()) {
    switch ($ch) {
        '"'  { [void]$sb.Append('\"');  continue }
        '\'  { [void]$sb.Append('\\');  continue }
        "`n" { [void]$sb.Append('\n');  continue }
        "`r" { [void]$sb.Append('\r');  continue }
        "`t" { [void]$sb.Append('\t');  continue }
        default {
            if ([int]$ch -lt 32) { [void]$sb.Append('\u{0:x4}' -f [int]$ch) }
            else { [void]$sb.Append($ch) }
        }
    }
}
$escapado = $sb.ToString()

# 3) Substitui SOMENTE o valor do campo "Code" (preserva o resto do arquivo)
$linhas = [System.IO.File]::ReadAllLines($Dyn)
$indice = -1
for ($i = 0; $i -lt $linhas.Count; $i++) {
    if ($linhas[$i].Contains('"Code": "')) { $indice = $i; break }
}
if ($indice -lt 0) { throw 'Campo "Code" nao encontrado no .dyn' }

$rotulo = '"Code": "'
$linha  = $linhas[$indice]
$inicio = $linha.IndexOf($rotulo) + $rotulo.Length
$fim    = $linha.LastIndexOf('"')
if (-not ($linha.Substring($fim) -match '^",?$')) {
    throw "Formato inesperado no fim da linha do campo Code: $($linha.Substring($fim))"
}

$linhas[$indice] = $linha.Substring(0, $inicio) + $escapado + $linha.Substring($fim)
[System.IO.File]::WriteAllText($Dyn, ($linhas -join "`r`n") + "`r`n", $utf8)

# 4) Confere: le o .dyn de volta como JSON e compara com o .py
$json = [System.IO.File]::ReadAllText($Dyn, $utf8) | ConvertFrom-Json
$no = $json.Nodes | Where-Object {
    $_.NodeType -eq 'PythonScriptNode' -and
    ($_.PSObject.Properties.Name -contains 'Code')
} | Select-Object -First 1

if ($null -eq $no) { throw 'PythonScriptNode nao encontrado apos a gravacao' }

$codeDyn = $no.Code.Replace("`r`n", "`n").Replace("`r", "`n")
if ($codeDyn -ne $code) {
    throw 'FALHA: o codigo gravado no .dyn nao e igual ao do .py'
}

Write-Output ("OK | .dyn sincronizado com {0} | {1} caracteres | Engine: {2}" -f `
    (Split-Path $Py -Leaf), $code.Length, $no.Engine)
