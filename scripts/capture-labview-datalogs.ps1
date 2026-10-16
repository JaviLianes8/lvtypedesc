# Capture real type descriptors written by LabVIEW: front-panel datalog files.
#
# Runs each VI listed in -ListFile once through LabVIEW's ActiveX VI Server with
# "log at finish" on, so LabVIEW writes the VI's front panel, type descriptors first, to
# <OutDir>\<name>.dat. Nothing is saved back: the script hashes every VI before and after
# and fails if one changed. A Boolean control named "Stop" is set to true before the run so
# example VIs with a stop button finish after one iteration.
#
#   pwsh scripts/capture-labview-datalogs.ps1 -ListFile vis.txt -OutDir tests/fixtures/labview2026
#
# The script starts its own LabVIEW and closes exactly that process afterwards, so it refuses
# to run while another LabVIEW is open (COM would attach to it, and quitting would close it).
param(
    [Parameter(Mandatory = $true)][string]$ListFile,
    [Parameter(Mandatory = $true)][string]$OutDir
)
$ErrorActionPreference = "Stop"
$BF = [System.Reflection.BindingFlags]
$CO = [System.__ComObject]

function Invoke-Com($obj, [string]$name, [object[]]$argv) {
    return $CO.InvokeMember($name, $BF::InvokeMethod, $null, $obj, $argv)
}
function Get-ComProperty($obj, [string]$name) {
    return $CO.InvokeMember($name, $BF::GetProperty, $null, $obj, $null)
}
function Set-ComProperty($obj, [string]$name, $value) {
    $CO.InvokeMember($name, $BF::SetProperty, $null, $obj, @($value)) | Out-Null
}

$vis = @(Get-Content $ListFile | ForEach-Object { [string]$_.Trim() } | Where-Object { $_ -ne "" })
$before = @{}
foreach ($p in $vis) { $before[$p] = (Get-FileHash -Algorithm SHA256 $p).Hash }
$OutDir = (Resolve-Path $OutDir).Path

if (Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue) {
    throw "LabVIEW is already running; close it first"
}
$app = [Activator]::CreateInstance([Type]::GetTypeFromProgID("LabVIEW.Application"))
$started = @(Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
try {
    "LabVIEW " + (Get-ComProperty $app "Version")
    foreach ($p in $vis) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($p) -replace '[^A-Za-z0-9]+', '_'
        $target = [string](Join-Path $OutDir ($name.Trim('_') + ".dat"))
        $vi = Invoke-Com $app "GetVIReference" @([string]$p, "", $false, 0)
        Set-ComProperty $vi "LogFilePath" ([string]$target)
        Set-ComProperty $vi "LogAtFinish" $true
        try { Invoke-Com $vi "SetControlValue" @("Stop", $true) | Out-Null } catch { }
        Invoke-Com $vi "Run" @($true) | Out-Null
        $deadline = (Get-Date).AddSeconds(30)
        # ExecState 1 is idle: the run has finished.
        while ((Get-ComProperty $vi "ExecState") -ne 1 -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
        }
        if ((Get-ComProperty $vi "ExecState") -ne 1) {
            Invoke-Com $vi "Abort" @() | Out-Null
            throw "$p did not finish in 30 s"
        }
        "wrote $target"
    }
} finally {
    try { Invoke-Com $app "Quit" @() | Out-Null } catch { }
    # Quit does not always end the process; close the LabVIEW this script started, and only it.
    Start-Sleep -Seconds 5
    foreach ($id in $started) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}
foreach ($p in $vis) {
    if ((Get-FileHash -Algorithm SHA256 $p).Hash -ne $before[$p]) { throw "$p changed on disk" }
}
"every VI is unchanged"
