# Lesende Freigabeprüfung. Fügt keinerlei Zertifikate oder Windows-Ausnahmen hinzu.
param(
    [Parameter(Mandatory=$true)][string[]]$Roots,
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Report,
    [switch]$AuditOnly
)
$ErrorActionPreference = 'Stop'
$files = @((Get-Item -LiteralPath $Installer))
foreach ($root in $Roots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "Fehlender Prüfordner: $root" }
    $files += @(Get-ChildItem -LiteralPath $root -File -Recurse | Where-Object { $_.Extension -in '.exe','.dll','.pyd' })
}
$rows = @($files | Sort-Object FullName -Unique | ForEach-Object {
    $signature = Get-AuthenticodeSignature -LiteralPath $_.FullName
    [ordered]@{
        path=$_.FullName
        sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        status=[string]$signature.Status
        signer=if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
    }
})
$invalid = @($rows | Where-Object { $_.status -ne 'Valid' })
[ordered]@{
    ok=($invalid.Count -eq 0)
    checked_files=$rows.Count
    invalid_files=$invalid.Count
    smart_app_control_device_test=$false
    note='Gültige Authenticode-Signaturen sind erforderlich; diese Prüfung garantiert keine SAC-Zulassung. Keine Änderungen am Windows-Vertrauensspeicher.'
    files=$rows
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding utf8
if ($invalid.Count -gt 0 -and -not $AuditOnly) {
    throw "Release blocked: $($invalid.Count) Dateien ohne gültige vertrauenswürdige Authenticode-Signatur."
}
