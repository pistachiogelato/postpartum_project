let currentProgress = 0;

function updateProgress(weight) {
    currentProgress += weight;
    if (currentProgress > 100) currentProgress = 100;
    
    // 更新用户的进度条
    document.getElementById("mood-bar").style.width = currentProgress + "%";
}

// 假设每个家庭成员都有独立的进度条
function updateMemberProgress(memberId, weight) {
    const progressBar = document.getElementById("progress-" + memberId);
    let currentProgress = parseInt(progressBar.style.width) || 0;
    currentProgress += weight;
    if (currentProgress > 100) currentProgress = 100;
    progressBar.style.width = currentProgress + "%";
}