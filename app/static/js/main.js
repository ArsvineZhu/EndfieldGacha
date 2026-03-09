async function initPage() {
    createDOMStructure();

    const singleDrawBtn = document.getElementById('single-draw');
    const tenDrawBtn = document.getElementById('ten-draw');
    const urgentRecruitmentBtn = document.getElementById('urgent-recruitment');

    singleDrawBtn.style.display = 'none';
    tenDrawBtn.style.display = 'none';
    urgentRecruitmentBtn.style.display = 'none';

    await loadUserData();
    setupEventListeners();
    document.querySelector('.gacha-area').style.display = 'block';
    document.querySelector('.stats-area').style.display = 'block';
    updatePoolUI(currentPool);
    await loadUserData();
    showResults([]);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initPage);
