/**
 * Antigravity Token Monitor (CLI)
 * 智能增强版：自动扫描本地标准路径以寻找真实的 telemetry.log 文件，并支持实时监听模式
 */
const fs = require('fs');
const path = require('path');

// 自动检测的潜在路径列表
const userProfile = process.env.USERPROFILE || 'C:\\Users\\rriww';
const possiblePaths = [
    path.join(userProfile, 'AppData', 'Roaming', 'Antigravity', 'logs', 'telemetry.log'),
    path.join(userProfile, 'AppData', 'Local', 'antigravity', 'logs', 'telemetry.log'),
    path.join(userProfile, '.gemini', 'antigravity', 'logs', 'telemetry.log'),
    path.join(userProfile, 'AppData', 'Roaming', 'Cursor', 'User', 'globalStorage', 'antigravity', 'telemetry.log'),
    path.join(userProfile, 'AppData', 'Roaming', 'Code', 'User', 'globalStorage', 'antigravity', 'telemetry.log')
];

function findLogFile() {
    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            return p;
        }
    }
    return null;
}

function checkBalance(isWatchMode = false) {
    const logPath = findLogFile();

    if (isWatchMode) {
        console.clear();
        console.log(`\x1b[35m[●] Antigravity 实时配额监视器正在运行... (按 Ctrl+C 退出)\x1b[0m`);
        console.log(`\x1b[90m正在监听日志: ${logPath || '等待日志生成...'}\x1b[0m\n`);
    } else {
        console.log("🔍 正在扫描系统中的 Antigravity 遥测日志...");
    }

    if (!logPath) {
        console.error("\n❌ 未能找到 telemetry.log！");
        console.log("💡 提示：这通常是因为您刚刚启动，本地尚未产生握手数据日志。");
        console.log("💡 建议：请确保您本地的 IDE 中已启用 Antigravity，并在运行一次代码扫描/对话后重试。");
        if (!isWatchMode) {
            console.log("\n已扫描的潜在路径包括:");
            possiblePaths.forEach(p => console.log(` - ${p}`));
        }
        return;
    }

    if (!isWatchMode) {
        console.log(`\n✨ 成功定位日志文件: ${logPath}`);
    }

    try {
        const logs = fs.readFileSync(logPath, 'utf-8').split('\n');
        let totalWeeklyUsed = 0;
        let currentSprintUsed = 0;
        let lastUpdateTime = "未知";

        logs.forEach(line => {
            if (line.includes('QuotaUpdate_Premium')) {
                const match = line.match(/"weekly_units_consumed":\s*(\d+).*?"sprint_units_consumed":\s*(\d+)/);
                if (match) {
                    totalWeeklyUsed = parseInt(match[1]);
                    currentSprintUsed = parseInt(match[2]);
                }
            }
        });

        // 获取文件最后修改时间以实现实时更新感知
        const stats = fs.statSync(logPath);
        lastUpdateTime = stats.mtime.toLocaleTimeString('zh-CN');

        const weeklyLimit = 2800; 
        const sprintLimit = 250;

        console.log(`\x1b[36m📊 [Antigravity 真实配额报告] (最后更新: ${lastUpdateTime})\x1b[0m`);
        console.log("----------------------------------------");
        console.log(`⏱️  5小时冲刺剩余: \x1b[1m${sprintLimit - currentSprintUsed}\x1b[0m / ${sprintLimit} units`);
        console.log(`🏃‍♂️ 7天马拉松剩余: \x1b[1m${weeklyLimit - totalWeeklyUsed}\x1b[0m / ${weeklyLimit} units`);
        console.log("----------------------------------------");

        if (totalWeeklyUsed >= (weeklyLimit * 0.9)) {
            console.log("⚠️  \x1b[31m警告：您已严重逼近 2800 units 的隐形周上限！随时可能触发7天锁定。\x1b[0m");
            console.log("💡 建议：立即在 Settings -> Models 中将主模型切换为 Claude，或使用 Flash 模型处理简单的任务。");
        } else {
            console.log("✅ \x1b[32m额度健康，可以继续分配大规模的 RTL / CDC 分析及回测优化任务。\x1b[0m");
        }

    } catch (err) {
        console.error("解析日志时发生错误:", err.message);
    }
}

// 主入口逻辑
const args = process.argv.slice(2);
const isWatch = args.includes('watch') || args.includes('--watch');

if (isWatch) {
    const logPath = findLogFile();
    checkBalance(true);
    
    if (logPath) {
        // 使用 fs.watchFile 确保跨平台及 Windows 的鲁棒性
        fs.watchFile(logPath, { interval: 1000 }, (curr, prev) => {
            if (curr.mtime !== prev.mtime) {
                checkBalance(true);
            }
        });
    } else {
        // 如果文件一开始不存在，则每秒轮询检测一次，直到文件生成
        const initInterval = setInterval(() => {
            const pathCheck = findLogFile();
            if (pathCheck) {
                clearInterval(initInterval);
                checkBalance(true);
                fs.watchFile(pathCheck, { interval: 1000 }, (curr, prev) => {
                    checkBalance(true);
                });
            }
        }, 1000);
    }
} else {
    checkBalance(false);
}
