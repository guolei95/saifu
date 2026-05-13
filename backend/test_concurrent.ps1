# ============================================================
# 赛赋 SaiFu 并发排队测试脚本
# 模拟 N 个用户同时发起匹配，验证 Semaphore 排队逻辑
#
# 用法: .\test_concurrent.ps1 -BackendUrl http://localhost:8000
#       .\test_concurrent.ps1 -BackendUrl https://saifu-backend-pk86.onrender.com
# ============================================================
param(
    [string]$BackendUrl = "http://localhost:8000",
    [int]$ConcurrentUsers = 6,
    [int]$TimeoutSeconds = 120
)

$colors = @("Cyan","Yellow","Magenta","Green","Blue","Red","DarkCyan","DarkYellow")

Write-Host @"
╔══════════════════════════════════════════╗
║   赛赋 Saifu 并发排队测试                 ║
║   后端: $BackendUrl
║   用户: $ConcurrentUsers (Semaphore=5 →  ≥1人排队)
╚══════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# ── 模拟用户画像 ──
$allProfiles = @(
    @{ school="清华大学"; major="计算机科学与技术"; grade="大三"; interests="Python,AI,后端开发"; goals=@("保研加分") },
    @{ school="北京大学"; major="金融学"; grade="大二"; interests="数据分析,商业策划"; goals=@("求职简历") },
    @{ school="浙江大学"; major="机械工程"; grade="研一"; interests="智能制造,嵌入式"; goals=@("拿奖率高") },
    @{ school="复旦大学"; major="临床医学"; grade="大四"; interests="医学影像,AI诊断"; goals=@("保研加分") },
    @{ school="上海交大"; major="电子工程"; grade="大三"; interests="FPGA,嵌入式系统"; goals=@("能力锻炼") },
    @{ school="武汉大学"; major="测绘工程"; grade="大二"; interests="GIS,遥感"; goals=@("拿奖率高") },
    @{ school="中山大学"; major="生物科学"; grade="研二"; interests="生物信息,基因测序"; goals=@("保研加分") }
)
$profiles = $allProfiles[0..($ConcurrentUsers - 1)]

# ── 检查连通性 ──
Write-Host "`n🩺 检查后端..."
try {
    $health = Invoke-RestMethod -Uri "$BackendUrl/api/health" -TimeoutSec 10
    Write-Host "   ✅ 后端在线 | LLM: $($health.llm_configured)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 后端不可达: $_" -ForegroundColor Red
    exit 1
}

# ── 核心：并发发起请求 + 轮询 ──
# 为每个用户创建一个后台 Runspace 执行独立轮询
$overallStart = Get-Date
Write-Host "`n🚀 同时发起 $ConcurrentUsers 个匹配请求...`n" -ForegroundColor Cyan

# Step 1: 并发提交所有请求（几乎同时 POST）
$taskIds = [System.Collections.Concurrent.ConcurrentBag[string]]::new()
$submitJobs = @()

for ($i = 0; $i -lt $profiles.Count; $i++) {
    $idx = $i
    $p = $profiles[$i]
    $col = $colors[$i % $colors.Count]

    $job = Start-Job -Name "Submit$i" -ScriptBlock {
        param($profile, $index, $url, $color)
        try {
            $body = ConvertTo-Json $profile -Depth 3
            $resp = Invoke-RestMethod -Uri "$url/api/match" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
            Write-Output "OK|$index|$($resp.task_id)"
        } catch {
            Write-Output "FAIL|$index|$($_.Exception.Message)"
        }
    } -ArgumentList $p, $idx, $BackendUrl, $col

    $submitJobs += $job
}

# 等待所有提交完成
$submitJobs | Wait-Job | Out-Null

$taskList = @()
foreach ($job in $submitJobs) {
    $result = Receive-Job $job
    $parts = $result -split '\|'
    if ($parts[0] -eq "OK") {
        $taskList += @{ Index=[int]$parts[1]; TaskId=$parts[2]; Status="queued" }
        Write-Host "   [用户$($parts[1])] 提交成功 → $($parts[2])" -ForegroundColor Yellow
    } else {
        Write-Host "   [用户$($parts[1])] 提交失败: $($parts[2])" -ForegroundColor Red
        $taskList += @{ Index=[int]$parts[1]; TaskId="FAIL"; Status="error" }
    }
}
$submitJobs | Remove-Job -Force

Write-Host "`n📊 开始轮询（每 3 秒一次）...`n" -ForegroundColor Cyan

# Step 2: 轮询直到全部完成
$doneCount = 0
$totalCount = $taskList.Count
$pollRound = 0

while ($doneCount -lt $totalCount -and $pollRound -lt ($TimeoutSeconds / 3)) {
    $pollRound++
    Start-Sleep -Seconds 3
    $doneCount = 0

    foreach ($t in $taskList) {
        if ($t.Status -eq "done" -or $t.Status -eq "error" -or $t.TaskId -eq "FAIL") {
            $doneCount++
            continue
        }

        try {
            $poll = Invoke-RestMethod -Uri "$BackendUrl/api/match/$($t.TaskId)" -TimeoutSec 10
            $color = $colors[$t.Index % $colors.Count]

            switch ($poll.status) {
                "queued" {
                    $pos = $poll.queue_position
                    Write-Host "   [用户$($t.Index)] 🔵 排队中，前面 $pos 人 (第${pollRound}轮)" -ForegroundColor $color
                }
                "processing" {
                    Write-Host "   [用户$($t.Index)] 🟡 处理中... (第${pollRound}轮)" -ForegroundColor $color
                }
                "done" {
                    $elapsed = [math]::Round(((Get-Date) - $overallStart).TotalSeconds, 1)
                    $matchCount = 0
                    if ($poll.result.open) { $matchCount = $poll.result.open.Count }
                    Write-Host "   [用户$($t.Index)] ✅ 完成！耗时 ${elapsed}s，匹配 ${matchCount} 个竞赛" -ForegroundColor Green
                    $t.Status = "done"
                    $t.Elapsed = $elapsed
                    $t.MatchCount = $matchCount
                    $doneCount++
                }
                "error" {
                    Write-Host "   [用户$($t.Index)] ❌ 错误: $($poll.error)" -ForegroundColor Red
                    $t.Status = "error"
                    $t.Error = $poll.error
                    $doneCount++
                }
            }
        } catch {
            Write-Host "   [用户$($t.Index)] ⚠️ 轮询请求失败" -ForegroundColor DarkGray
        }
    }
}

# ── 汇总报告 ──
$totalElapsed = [math]::Round(((Get-Date) - $overallStart).TotalSeconds, 1)
Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  📊 测试结果汇总" -ForegroundColor White
Write-Host "  ─────────────────────" -ForegroundColor Cyan
Write-Host "  总耗时: ${totalElapsed}s"
Write-Host "  并发数: $ConcurrentUsers | Semaphore: 5"
Write-Host "  完成: $(($taskList | Where-Object { $_.Status -eq 'done' }).Count) / $totalCount"
Write-Host "  失败: $(($taskList | Where-Object { $_.Status -eq 'error' }).Count)"

if ($totalElapsed -gt 30) {
    Write-Host "`n  💡 观察：总耗时 > 30s → 排队的用户确实在等待" -ForegroundColor Yellow
    Write-Host "     前 5 个用户应该几乎同时完成，第 6 个会晚一些" -ForegroundColor Yellow
}

Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "`n💡 提示：如果测试指向云端 Render，首次请求可能需等冷启动（~30s）" -ForegroundColor DarkGray
