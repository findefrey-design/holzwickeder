# ============================================================
# Der Holzwickeder - Daten-Fetcher (Windows/Firmennetz)
# Liest quellen.json (gemeinsame Liste mit fetch.py) und holt
# alles nach data/ + data/fetch-report.json (Selbst-Diagnose).
# Invoke-WebRequest nutzt den Windows-Zertifikatspeicher und
# funktioniert damit hinter der Firmen-TLS-Interception.
# ============================================================

$ErrorActionPreference = 'Continue'
$OutDir = Join-Path $PSScriptRoot 'data'
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force $OutDir | Out-Null }
$Cfg = Get-Content (Join-Path $PSScriptRoot 'quellen.json') -Raw | ConvertFrom-Json

$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DerHolzwickeder/1.0 (private Leseansicht)'
$report = [System.Collections.Generic.List[object]]::new()

function Get-Quelle {
    param([string]$Name, [string]$Url, [string]$Ext)
    $entry = @{ name = $Name; url = $Url; ok = $false; status = $null; bytes = 0; error = $null }
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 25 -Headers @{ 'User-Agent' = $UA; 'Accept' = '*/*' }
        [System.IO.File]::WriteAllText((Join-Path $OutDir "$Name.$Ext"), $r.Content, [System.Text.UTF8Encoding]::new($false))
        $entry.ok = $true; $entry.status = [int]$r.StatusCode; $entry.bytes = $r.Content.Length
    } catch {
        $entry.error = $_.Exception.Message
        if ($_.Exception.Response) { $entry.status = [int]$_.Exception.Response.StatusCode }
    }
    $script:report.Add([pscustomobject]$entry)
    Write-Host "[$(if($entry.ok){'OK  '}else{'FAIL'})] $Name ($($entry.bytes) B) $(if($entry.error){' - ' + $entry.error})"
}

function Add-Sonderfall {
    param([string]$Name, [string]$UrlLabel, [scriptblock]$Block)
    try {
        $n = & $Block
        $script:report.Add([pscustomobject]@{ name = $Name; url = $UrlLabel; ok = $true; status = 200; bytes = $n; error = $null })
        Write-Host "[OK  ] $Name ($n B)"
    } catch {
        $script:report.Add([pscustomobject]@{ name = $Name; url = $UrlLabel; ok = $false; status = $null; bytes = 0; error = $_.Exception.Message })
        Write-Host "[FAIL] $Name - $($_.Exception.Message)"
    }
}

# ---------- Standardquellen aus quellen.json ----------
Get-Quelle 'wetter' $Cfg.wetter_url 'json'
foreach ($q in $Cfg.quellen) { Get-Quelle $q.name $q.url $q.ext }

# ---------- Boerse (Yahoo-Chart, nur meta-Bloecke) ----------
Add-Sonderfall 'boerse' 'query1.finance.yahoo.com (aggregiert)' {
    $metas = foreach ($sym in $Cfg.boerse_symbole) {
        try {
            $enc = [uri]::EscapeDataString($sym)
            (Invoke-RestMethod -Uri "https://query1.finance.yahoo.com/v8/finance/chart/${enc}?range=5d&interval=1d" -TimeoutSec 15 -Headers @{ 'User-Agent' = $UA }).chart.result[0].meta
        } catch { Write-Host "  boerse: $sym fehlgeschlagen - $($_.Exception.Message)" }
    }
    $json = $metas | Where-Object { $_ } | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $OutDir 'boerse.json'), $json, [System.Text.UTF8Encoding]::new($false))
    $json.Length
}

# ---------- Hacker News Top-Items ----------
Add-Sonderfall 'tech_hn' 'hacker-news.firebaseio.com (aggregiert)' {
    $ids = Invoke-RestMethod -Uri 'https://hacker-news.firebaseio.com/v0/topstories.json' -TimeoutSec 25 -Headers @{ 'User-Agent' = $UA }
    $items = foreach ($id in ($ids | Select-Object -First $Cfg.hn_top)) {
        try { Invoke-RestMethod -Uri "https://hacker-news.firebaseio.com/v0/item/$id.json" -TimeoutSec 15 -Headers @{ 'User-Agent' = $UA } } catch {}
    }
    $json = $items | Where-Object { $_ } | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $OutDir 'tech_hn.json'), $json, [System.Text.UTF8Encoding]::new($false))
    $json.Length
}

# ---------- Volltexte (tagesschau details je Ressort) ----------
Add-Sonderfall 'volltexte' 'tagesschau.de details (aggregiert)' {
    $texte = [ordered]@{}
    foreach ($prop in $Cfg.volltexte.PSObject.Properties) {
        $pfad = Join-Path $OutDir "$($prop.Name).json"
        if (-not (Test-Path $pfad)) { continue }
        $news = (Get-Content $pfad -Raw -Encoding utf8 | ConvertFrom-Json).news
        $zaehler = 0
        foreach ($n in $news) {
            if (($n.type -and $n.type -ne 'story') -or (-not $n.details)) { continue }
            try {
                $d = Invoke-RestMethod -Uri $n.details -TimeoutSec 20 -Headers @{ 'User-Agent' = $UA }
                $inhalt = @($d.content | Where-Object { $_.type -in @('text', 'headline') } |
                    ForEach-Object { @{ type = $_.type; value = [string]$_.value } })
                if ($inhalt.Count -gt 0) { $texte[$n.details] = $inhalt }
            } catch { Write-Host "  volltext: $($n.externalId) fehlgeschlagen - $($_.Exception.Message)" }
            $zaehler++
            if ($zaehler -ge $prop.Value) { break }
        }
    }
    $json = $texte | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText((Join-Path $OutDir 'volltexte.json'), $json, [System.Text.UTF8Encoding]::new($false))
    $json.Length
}

# ---------- Selbst-Report ----------
$summary = [pscustomobject]@{
    generated = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
    ok        = @($report | Where-Object ok).Count
    failed    = @($report | Where-Object { -not $_.ok }).Count
    sources   = $report
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $OutDir 'fetch-report.json') -Encoding utf8
Write-Host ("`n{0} OK, {1} FAIL -> fetch-report.json" -f $summary.ok, $summary.failed)
