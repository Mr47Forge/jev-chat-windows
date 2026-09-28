$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoZip = "https://github.com/Mr47Forge/jev-chat-windows/archive/refs/heads/dev-external-source.zip"
$Temp = Join-Path $env:TEMP ("jev-chat-dev-update-" + [Guid]::NewGuid().ToString("N"))
$Zip = Join-Path $Temp "src.zip"
$Extract = Join-Path $Temp "src"
$Stage = Join-Path $Temp "stage"
$Backup = Join-Path $Temp "backup"

function Write-Step([string]$Text) {
    Write-Host ("[进行中] " + $Text) -ForegroundColor Cyan
}

function Read-Plan([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "新源码缺少 dev/runtime-sync.txt，拒绝继续按旧结构覆盖"
    }

    $plan = [ordered]@{
        Generation = ""
        Dirs = @()
        Files = @()
        Required = @()
    }

    foreach ($raw in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line -eq "JEV_RUNTIME_SYNC_V2") {
            continue
        }
        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) { continue }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Replace("/", "\")
        if ([IO.Path]::IsPathRooted($value) -or $value -match '(^|\\)\.\.(\\|$)') {
            throw "非法同步路径：$value"
        }

        switch ($key) {
            "generation" { $plan.Generation = $value }
            "dir" { $plan.Dirs += $value }
            "file" { $plan.Files += $value }
            "required" { $plan.Required += $value }
        }
    }

    if (-not $plan.Generation) { throw "同步清单缺少 generation" }
    if (($plan.Dirs.Count + $plan.Files.Count) -eq 0) { throw "同步清单为空" }
    return $plan
}

function Copy-Dir([string]$Source, [string]$Destination) {
    if (Test-Path $Destination) {
        Remove-Item $Destination -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item $Source $Destination -Recurse -Force
}

function Backup-Target([string]$Relative) {
    $src = Join-Path $Root $Relative
    $dst = Join-Path $Backup $Relative
    if (Test-Path $src -PathType Container) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item $src $dst -Recurse -Force
        return $true
    }
    if (Test-Path $src -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item $src $dst -Force
        return $true
    }
    return $false
}

try {
    Write-Host "V2 同步器：按 dev/runtime-sync.txt 更新，不再写死 app/core。" -ForegroundColor Gray
    Write-Host "会同步 vendor；不会覆盖用户配置、聊天资料或长期记忆数据库。" -ForegroundColor Gray
    Write-Host ""

    New-Item -ItemType Directory -Force -Path $Temp | Out-Null

    Write-Step "下载 dev-external-source 最新源码"
    try {
        Invoke-WebRequest -Uri $RepoZip -OutFile $Zip -UseBasicParsing -TimeoutSec 90
    }
    catch {
        throw "下载源码失败：$($_.Exception.Message)"
    }

    if (-not (Test-Path $Zip) -or (Get-Item $Zip).Length -lt 1024) {
        throw "下载到的源码压缩包无效或为空"
    }

    Write-Step "解压源码"
    Expand-Archive -Path $Zip -DestinationPath $Extract -Force
    $Source = Get-ChildItem $Extract -Directory | Select-Object -First 1
    if (-not $Source) { throw "下载包结构异常：没有找到源码目录" }

    $Plan = Read-Plan (Join-Path $Source.FullName "dev\runtime-sync.txt")

    $LocalGenerationFile = Join-Path $Root "runtime-generation.txt"
    if (-not (Test-Path $LocalGenerationFile)) {
        throw "当前开发运行时太旧，缺少 runtime-generation.txt。请重新下载一次完整 JevChat-Windows-Dev。"
    }
    $LocalGeneration = (Get-Content $LocalGenerationFile -Raw).Trim()
    if ($LocalGeneration -ne $Plan.Generation) {
        throw "运行时代际已变化（本地 $LocalGeneration，源码 $($Plan.Generation)），请重新下载完整开发环境。"
    }

    $LocalRequirements = Join-Path $Root "requirements.txt"
    $SourceRequirements = Join-Path $Source.FullName "requirements.txt"
    if ((Test-Path $LocalRequirements) -and (Test-Path $SourceRequirements)) {
        $a = (Get-FileHash $LocalRequirements -Algorithm SHA256).Hash
        $b = (Get-FileHash $SourceRequirements -Algorithm SHA256).Hash
        if ($a -ne $b) {
            throw "requirements.txt 已变化，冻结运行时可能缺依赖。请重新下载完整开发环境。"
        }
    }

    Write-Step "准备新版业务源码"
    New-Item -ItemType Directory -Force -Path $Stage | Out-Null
    foreach ($name in $Plan.Dirs) {
        $src = Join-Path $Source.FullName $name
        $dst = Join-Path $Stage $name
        if (-not (Test-Path $src -PathType Container)) { throw "同步清单目录不存在：$name" }
        Copy-Dir $src $dst
    }
    foreach ($name in $Plan.Files) {
        $src = Join-Path $Source.FullName $name
        $dst = Join-Path $Stage $name
        if (-not (Test-Path $src -PathType Leaf)) { throw "同步清单文件不存在：$name" }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item $src $dst -Force
    }

    foreach ($name in $Plan.Required) {
        if (-not (Test-Path (Join-Path $Stage $name))) {
            throw "新版结构校验失败，缺少：$name"
        }
    }

    Write-Step "备份当前业务源码"
    New-Item -ItemType Directory -Force -Path $Backup | Out-Null
    $Existed = @{}
    foreach ($name in @($Plan.Dirs) + @($Plan.Files)) {
        $Existed[$name] = Backup-Target $name
    }

    try {
        Write-Step "按 V2 清单替换业务源码"
        $RootCache = Join-Path $Root "__pycache__"
        if (Test-Path $RootCache) { Remove-Item $RootCache -Recurse -Force }

        foreach ($name in $Plan.Dirs) {
            $src = Join-Path $Stage $name
            $dst = Join-Path $Root $name
            Copy-Dir $src $dst
        }
        foreach ($name in $Plan.Files) {
            $src = Join-Path $Stage $name
            $dst = Join-Path $Root $name
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
            Copy-Item $src $dst -Force
        }

        foreach ($name in $Plan.Required) {
            if (-not (Test-Path (Join-Path $Root $name))) {
                throw "更新后校验失败，缺少：$name"
            }
        }
    }
    catch {
        Write-Step "更新失败，正在回滚"
        foreach ($name in @($Plan.Dirs) + @($Plan.Files)) {
            $target = Join-Path $Root $name
            if (Test-Path $target) { Remove-Item $target -Recurse -Force }
            if ($Existed[$name]) {
                $saved = Join-Path $Backup $name
                if (Test-Path $saved -PathType Container) {
                    Copy-Dir $saved $target
                }
                elseif (Test-Path $saved -PathType Leaf) {
                    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
                    Copy-Item $saved $target -Force
                }
            }
        }
        throw
    }

    Write-Host ""
    Write-Host "[成功] V2 源码与 vendor 同步完成。" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host ""
    Write-Host ("[失败] " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
finally {
    if (Test-Path $Temp) {
        Remove-Item $Temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
