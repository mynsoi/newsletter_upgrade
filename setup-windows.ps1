# mentor-lab 칼럼 작업실 — Windows 처음 설치
#
# 실행: setup-windows.cmd 를 더블클릭 (또는 PowerShell에서 .\setup-windows.cmd)
# 여러 번 돌려도 된다 — 이미 있는 것은 건너뛴다.
#
# 설치하는 것: Git · Python · Node.js (winget) / Claude Code / codex (npm) /
#             Pillow (pip) / 작업실 화면 패키지·빌드 (app/)
# 로그인·연결은 계정이 필요해 자동으로 하지 않는다 — 끝에 남은 일을 보여 준다.

# 실패 판정은 종료 코드로 한다 — Windows PowerShell 5.1은 Stop일 때 npm 경고(표준 오류)까지 실패로 멈춘다
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = $PSScriptRoot
Set-Location $Root
$Todo = New-Object System.Collections.Generic.List[string]

function Step($m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  [!] $m" -ForegroundColor Yellow }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

function Refresh-Path {
    # winget·설치 프로그램이 바꾼 PATH를 지금 창에도 반영한다
    $parts = @([Environment]::GetEnvironmentVariable("Path", "Machine"), [Environment]::GetEnvironmentVariable("Path", "User"),
               "$env:USERPROFILE\.local\bin", "$env:APPDATA\npm")
    $env:Path = ($parts | Where-Object { $_ }) -join ";"
}

function Winget-Install($id, $name, $extra = @()) {
    if (-not (Has "winget")) {
        throw "winget이 없습니다. Microsoft Store에서 '앱 설치 관리자(App Installer)'를 설치한 뒤 다시 실행하세요."
    }
    Write-Host "  $name 설치 중 (winget $id)..."
    winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements --silent @extra
    # -1978335189: 이미 설치됨(업데이트 없음)
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { throw "$name 설치 실패 (winget 종료 코드 $LASTEXITCODE)" }
    Refresh-Path
}

function Find-Python {
    # 스토어 바로가기(WindowsApps\python.exe)는 Python이 없어도 '있는 것처럼' 보인다 — 실제로 돌려 버전을 확인한다.
    # start-windows.cmd와 같은 순서(py -3 → python)로 찾아야 Pillow를 깐 파이썬으로 작업실이 뜬다.
    foreach ($c in @(@("py", "-3"), @("python"))) {
        if (-not (Has $c[0])) { continue }
        $args_ = @($c | Select-Object -Skip 1) + @("-c", "import sys; print(sys.executable); print(sys.version_info >= (3, 10))")
        try { $out = & $c[0] @args_ 2>$null } catch { continue }
        if ($LASTEXITCODE -eq 0 -and $out.Count -ge 2 -and $out[1] -eq "True" -and (Test-Path $out[0])) { return $out[0] }
    }
    return $null
}

function Node-Ok {
    if (-not (Has "node")) { return $false }
    $v = (node -v) -replace "^v", ""
    $p = $v.Split(".") | ForEach-Object { [int]$_ }
    # vite 8 요구: ^20.19.0 || >=22.12.0
    return (($p[0] -eq 20 -and $p[1] -ge 19) -or ($p[0] -eq 22 -and $p[1] -ge 12) -or $p[0] -ge 23)
}

Refresh-Path

# ---------- 1. 기본 도구 ----------
Step "Git"
if (Has "git") { Ok (git --version) } else { Winget-Install "Git.Git" "Git"; Ok (git --version) }

Step "Python"
$Py = Find-Python
if (-not $Py) { Winget-Install "Python.Python.3.13" "Python 3.13" @("--scope", "user"); $Py = Find-Python }
if (-not $Py) { throw "Python을 찾지 못했습니다. 새 PowerShell 창에서 setup-windows.cmd를 다시 실행해 보세요." }
Ok "$Py ($(& $Py --version))"

Step "Node.js"
if (-not (Has "node")) { Winget-Install "OpenJS.NodeJS.LTS" "Node.js LTS" }
if (Node-Ok) { Ok "node $(node -v)" } else { throw "Node.js $(node -v)는 너무 낮습니다 — 20.19 이상 또는 22.12 이상이 필요합니다 (winget upgrade OpenJS.NodeJS.LTS)." }

# ---------- 2. AI 도구 ----------
Step "Claude Code (과정 1 초안 · 진행자)"
if (-not (Has "claude")) {
    Write-Host "  Claude Code 설치 중 (claude.ai/install.ps1)..."
    Invoke-RestMethod https://claude.ai/install.ps1 -ErrorAction Stop | Invoke-Expression
    Refresh-Path
}
if (Has "claude") { Ok "claude $(claude --version)" } else { throw "Claude Code 설치를 확인하지 못했습니다. 새 창에서 다시 실행하세요." }

Step "codex (astra · 그림)"
# npm.cmd로 부른다 — npm.ps1은 실행 정책에 막힐 수 있다
if (-not (Has "codex")) { & npm.cmd install -g "@openai/codex"; if ($LASTEXITCODE) { throw "codex 설치 실패" }; Refresh-Path }
Ok "$(codex --version)"

# ---------- 3. 작업실 ----------
Step "Pillow (그림 축소본)"
& $Py -m pip install --disable-pip-version-check -q --upgrade Pillow
if ($LASTEXITCODE) { throw "Pillow 설치 실패" }
# 작업실은 -I(격리)로 뜬다 — 그 상태에서 보여야 한다(사용자 폴더에 깔리면 -I에서 안 보임)
& $Py -X utf8 -I -c "import PIL" 2>&1 | Out-Null
if ($LASTEXITCODE) { throw "Pillow가 작업실 실행 방식(-I)에서 보이지 않습니다. Python을 '모든 사용자'가 아닌 '현재 사용자'로 설치했는지 확인하세요." }
Ok "Pillow $(& $Py -X utf8 -I -c 'import PIL; print(PIL.__version__)')"

Step "작업실 화면 (app/)"
Push-Location "$Root\app"
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "  패키지 받는 중 (npm ci, 몇 분 걸립니다)..."
        & npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE) { throw "npm ci 실패 — 위 오류를 확인하세요" }
    } else { Ok "node_modules 있음 (다시 받으려면 app\node_modules를 지우고 실행)" }
    & npm.cmd run build
    if ($LASTEXITCODE) { throw "화면 빌드 실패 — 위 오류를 확인하세요" }
    Ok "app\dist 빌드됨"
} finally { Pop-Location }

# ---------- 4. 남은 일 (계정·연결) ----------
Step "확인"
if (-not (Test-Path "$env:USERPROFILE\.claude.json")) { $Todo.Add("Claude 로그인: 새 창에서 claude 실행 → 브라우저 로그인") }  # 로그인 흔적이 없을 때만
if (-not (Test-Path "$env:USERPROFILE\.codex\auth.json")) { $Todo.Add("Codex 로그인(astra·그림이 씀): codex login → ChatGPT 계정") }
if (-not (Has "aside")) { $Todo.Add("Aside(원문 수집): https://aside.com/download 에서 설치 → 로그인 (aside 명령이 잡히는지 새 창에서 확인)") }
if (-not (git config --global user.name) -or -not (git config --global user.email)) {
    $Todo.Add("git 이름·메일(위키 자동 커밋): git config --global user.name ""이름"" / git config --global user.email ""메일""")
}
if (-not (Has "tailscale")) { $Todo.Add("(선택) 다른 PC에서 작업실 열기: winget install Tailscale.Tailscale → 로그인") }

Write-Host ""
Write-Host "설치 끝. 작업실 실행: start-windows.cmd  →  http://localhost:8771" -ForegroundColor Green
if ($Todo.Count) {
    Write-Host ""
    Write-Host "남은 일:" -ForegroundColor Yellow
    $i = 1
    foreach ($t in $Todo) { Write-Host "  $i. $t"; $i++ }
}
