# Run LabVIEW's own type-descriptor VIs (vi.lib\Utility\GetType.llb) on chosen descriptors.
#
# Each job in -JobFile names a VI of GetType.llb, its inputs and the outputs to read. The
# VIs read or build nested type descriptors as I16 arrays, so their answers are an
# independent reading of the same bytes this library parses. Results go to -OutFile as JSON.
# Jobs are written by scripts/make_gettype_jobs.py.
#
#   pwsh scripts/capture-labview-gettype.ps1 -JobFile jobs.json -OutFile tests/fixtures/labview2026/gettype.json
#
# The VIs are called through the ActiveX VI Server and never saved; the script hashes them
# before and after. It refuses to run while another LabVIEW is open and closes only the
# LabVIEW it started.
param(
    [Parameter(Mandatory = $true)][string]$JobFile,
    [Parameter(Mandatory = $true)][string]$OutFile
)
$ErrorActionPreference = "Stop"
$BF = [System.Reflection.BindingFlags]
$CO = [System.__ComObject]
$LLB = "C:\Program Files\National Instruments\LabVIEW 2026\vi.lib\Utility\GetType.llb\"

function Invoke-Com($obj, [string]$name, [object[]]$argv) {
    return $CO.InvokeMember($name, $BF::InvokeMethod, $null, $obj, $argv)
}
function ConvertTo-LabVIEW($spec) {
    switch ([string]$spec.t) {
        "i16a" { return [int16[]]@($spec.v | ForEach-Object { [int16]$_ }) }
        "i32a" { return [int32[]]@($spec.v | ForEach-Object { [int32]$_ }) }
        "i32" { return [int32]$spec.v }
        "bool" { return [bool]$spec.v }
        "str" { return [string]$spec.v }
    }
    throw "unknown input type $($spec.t)"
}

$jobs = Get-Content $JobFile -Raw | ConvertFrom-Json
$paths = @($jobs | ForEach-Object { $LLB + [string]$_.vi } | Sort-Object -Unique)
$before = @{}
foreach ($p in $paths) { $before[$p] = (Get-FileHash -Algorithm SHA256 $p).Hash }
if (Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue) {
    throw "LabVIEW is already running; close it first"
}
$app = [Activator]::CreateInstance([Type]::GetTypeFromProgID("LabVIEW.Application"))
$started = @(Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$results = New-Object System.Collections.ArrayList
$refs = @{}
try {
    $version = [string]$CO.InvokeMember("Version", $BF::GetProperty, $null, $app, $null)
    foreach ($job in $jobs) {
        $path = $LLB + [string]$job.vi
        if (-not $refs.ContainsKey($path)) {
            $refs[$path] = Invoke-Com $app "GetVIReference" @([string]$path, "", $false, 0)
        }
        $names = New-Object System.Collections.ArrayList
        $values = New-Object System.Collections.ArrayList
        foreach ($p in $job.inputs.PSObject.Properties) {
            $names.Add([string]$p.Name) | Out-Null
            $values.Add((ConvertTo-LabVIEW $p.Value)) | Out-Null
        }
        foreach ($n in $job.outputs) { $names.Add([string]$n) | Out-Null; $values.Add($null) | Out-Null }
        # Call fills the output slots of its second argument in place.
        $argv = [object[]]@([object[]]$names.ToArray(), [object[]]$values.ToArray())
        $byRef = New-Object System.Reflection.ParameterModifier 2
        $byRef[0] = $true
        $byRef[1] = $true
        $CO.InvokeMember("Call", $BF::InvokeMethod, $null, $refs[$path], $argv,
            [System.Reflection.ParameterModifier[]]@($byRef), $null, $null) | Out-Null
        $out = [ordered]@{ "id" = [string]$job.id; "vi" = [string]$job.vi; "hex" = [string]$job.hex }
        $first = $names.Count - $job.outputs.Count
        for ($i = 0; $i -lt $job.outputs.Count; $i++) {
            $out[[string]$job.outputs[$i]] = @(, $argv[1][$first + $i])
        }
        $results.Add($out) | Out-Null
    }
} finally {
    try { Invoke-Com $app "Quit" @() | Out-Null } catch { }
    Start-Sleep -Seconds 5
    foreach ($id in $started) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}
foreach ($p in $paths) {
    if ((Get-FileHash -Algorithm SHA256 $p).Hash -ne $before[$p]) { throw "$p changed on disk" }
}
$doc = [ordered]@{
    "labview" = $version
    "inputs" = "hand-written descriptors from scripts/make_gettype_jobs.py"
    "results" = $results
}
$text = ($doc | ConvertTo-Json -Depth 8) -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($OutFile, $text + "`n", (New-Object System.Text.UTF8Encoding $false))
"wrote $($results.Count) results; every VI is unchanged"
