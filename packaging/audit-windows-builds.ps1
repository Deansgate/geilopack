# Prüft ausschließlich die bereits veröffentlichten, hashgeprüften Builds.
# Keine SAC-/Defender-Ausnahmen, keine Änderung von Schutzrichtlinien.
$ErrorActionPreference = 'Stop'
$root = Join-Path $PWD 'security-audit'
New-Item -ItemType Directory -Force $root | Out-Null
$releases = @(
    @{ Name='old'; Tag='v0.2.0-dev.2.1'; Hash='f606e4a0320bff0933cbf0753c19fe88b5bcede8159e8a7db72b933237fb2f32' },
    @{ Name='new'; Tag='v0.2.1-dev.4.1'; Hash='aa62191e8b5b72cf50e078502f7ed994b3f570d01d00b3ee833b9e7d94c72a64' }
)
function Signature-Row($file, $relative) {
    $signature = Get-AuthenticodeSignature -LiteralPath $file
    $version = (Get-Item -LiteralPath $file).VersionInfo
    [ordered]@{
        path=$relative; sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        size=(Get-Item -LiteralPath $file).Length
        signature_status=[string]$signature.Status
        signature_message=$signature.StatusMessage
        signer_subject=if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
        signer_thumbprint=if ($signature.SignerCertificate) { $signature.SignerCertificate.Thumbprint } else { $null }
        timestamp_subject=if ($signature.TimeStamperCertificate) { $signature.TimeStamperCertificate.Subject } else { $null }
        company=$version.CompanyName; description=$version.FileDescription
        file_version=$version.FileVersion; product_version=$version.ProductVersion
    }
}
foreach ($release in $releases) {
    $directory = Join-Path $root $release.Name
    New-Item -ItemType Directory -Force $directory | Out-Null
    $setup = Join-Path $directory 'Setup.exe'
    Invoke-WebRequest "https://github.com/Deansgate/geilopack/releases/download/$($release.Tag)/Setup.exe" -OutFile $setup
    $hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $release.Hash) { throw "Unerwarteter Installer-Hash: $($release.Name)" }
    Signature-Row $setup 'Setup.exe' | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $directory 'installer-signature.json')
    $install = Join-Path $directory 'installed'
    $log = Join-Path $directory 'installation.log'
    $process = Start-Process -FilePath $setup -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=$install","/LOG=$log") -PassThru
    if (-not $process.WaitForExit(180000)) { $process.Kill(); throw 'Installations-Timeout' }
    if ($process.ExitCode -ne 0) { throw "Installation fehlgeschlagen: $($process.ExitCode)" }
    $rows = @(Get-ChildItem $install -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.pyd' } | ForEach-Object {
        Signature-Row $_.FullName ([IO.Path]::GetRelativePath($install, $_.FullName).Replace('\','/'))
    })
    $rows | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $directory 'pe-signatures.json')
    python packaging/inspect-pe.py $install (Join-Path $directory 'pe-imports.json')
    if ($LASTEXITCODE -ne 0) { throw 'PE-Inspektion fehlgeschlagen.' }
}
python packaging/compare-build-audit.py $root
if ($LASTEXITCODE -ne 0) { throw 'Vergleich fehlgeschlagen.' }
$defender = [ordered]@{ completed=$false; detections=@(); limitations='Kein Smart-App-Control-Test auf dem Benutzergerät.' }
try {
    $status = Get-MpComputerStatus
    $defender.engine_version = $status.AMEngineVersion
    $defender.signature_version = $status.AntivirusSignatureVersion
    $defender.antivirus_enabled = $status.AntivirusEnabled
    $defender.started = (Get-Date).ToUniversalTime().ToString('o')
    $started = Get-Date
    Start-MpScan -ScanType CustomScan -ScanPath $root
    $defender.detections = @(Get-MpThreatDetection -ErrorAction SilentlyContinue | Where-Object { $_.InitialDetectionTime -ge $started } | Select-Object ThreatID,InitialDetectionTime,ActionSuccess,Resources)
    $defender.completed = $true
} catch { $defender.error = $_.Exception.Message }
$defender | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $root 'defender.json')
Get-Content (Join-Path $root 'comparison-summary.json')
Get-Content (Join-Path $root 'defender.json')
