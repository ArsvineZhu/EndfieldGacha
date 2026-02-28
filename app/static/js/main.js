let currentPool = 'char';
let currentCollection = 'chars';

// 创建 DOM 结构
function createDOMStructure() {
    const app = document.getElementById('app');
    app.innerHTML = `
        <div class="app-container">
            <!-- 移动端导航遮罩层 -->
            <div class="nav-overlay" id="nav-overlay"></div>
            
            <!-- 顶部导航栏 -->
            <header class="top-nav">
                <button class="mobile-menu-btn" id="mobile-menu-btn" aria-label="菜单">
                    <i class="fas fa-bars"></i>
                </button>
                <h1 class="app-title">终末地抽卡模拟器</h1>
                <div class="top-resources">
                    <div class="resource-item">
                        <span class="resource-label">特许寻访凭证</span>
                        <span id="chartered-permits" class="resource-value">10</span>
                    </div>
                    <div class="resource-item">
                        <span class="resource-label">嵌晶玉</span>
                        <span id="oroberyl" class="resource-value">5000</span>
                    </div>
                    <div class="resource-item">
                        <span class="resource-label">武库配额</span>
                        <span id="arsenal-tickets" class="resource-value">2000</span>
                    </div>
                    <div class="resource-item">
                        <span class="resource-label">衍质源石</span>
                        <span id="origeometry" class="resource-value">0</span>
                    </div>
                    <div class="resource-item">
                        <span class="resource-label">累计充值</span>
                        <span id="total-recharge" class="resource-value">￥0</span>
                    </div>
                </div>
            </header>
            
            <div class="main-content">
                <!-- 左侧导航栏 -->
                <nav class="left-nav">
                    <div class="nav-section">
                        <h3>卡池</h3>
                        <button id="char-pool-btn" class="nav-btn active">特许寻访</button>
                        <button id="weapon-pool-btn" class="nav-btn">武库申领</button>
                    </div>
                    <div class="nav-section">
                        <h3>历史记录</h3>
                        <button id="char-history-btn" class="nav-btn">寻访记录</button>
                        <button id="weapon-history-btn" class="nav-btn">申领记录</button>
                    </div>
                    <div class="nav-section">
                        <h3>数据信息</h3>
                        <button id="chars-tab" class="nav-btn">干员获取统计</button>
                        <button id="chars-detail-tab" class="nav-btn">干员详情</button>
                        <button id="weapons-tab" class="nav-btn">贵重品库/武器</button>
                    </div>
                    <div class="nav-section">
                        <h3>资源管理</h3>
                        <button id="resources-tab" class="nav-btn">资源管理</button>
                        <button id="clear-data-btn" class="nav-btn danger">清空数据</button>
                    </div>
                </nav>
                
                <!-- 主内容区域 -->
                <div class="content-area">
                    <!-- 抽卡控制区 -->
                    <div class="gacha-area">
                        <!-- 卡池信息区域 -->
                        <div class="pool-info">
                            <div class="pool-info-content">
                                <div class="pool-name" id="pool-name">特许寻访</div>
                                <div class="boosted-items" id="boosted-items">
                                </div>
                            </div>
                            <div class="gacha-controls">
                                <button id="single-draw" class="draw-btn single-draw">Headhunt×1</button>
                                <button id="ten-draw" class="draw-btn ten-draw">Headhunt×10</button>
                                <button id="urgent-recruitment" class="draw-btn urgent-draw" style="display: none;">加急招募</button>
                            </div>
                        </div>
                        
                        <div class="result-area">
                            <h2 id="result-title">寻访结果</h2>
                            <div id="results-container" class="results-container"></div>
                        </div>
                        
                        <div class="rewards-area">
                            <h3 id="rewards-title">累计奖励</h3>
                            <div id="rewards-container" class="rewards-container"></div>
                        </div>
                    </div>
                    
                    <!-- 统计区域 -->
                    <div class="stats-area">
                        <h2 id="stats-title">寻访统计</h2>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-label" id="total-label">累计寻访次数</span>
                                <span id="total-draws" class="stat-value">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label" id="six-star-label">6 星保底计数</span>
                                <span id="no-6star" class="stat-value">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label" id="five-star-label">5 星保底计数</span>
                                <span id="no-5star" class="stat-value">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label" id="up-label">UP 保底计数</span>
                                <span id="no-up" class="stat-value">0</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 初始化页面
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

// 加载用户数据
async function loadUserData() {
    try {
        const response = await fetch('/api/user_data');
        const data = await response.json();
        updateStats(data);
        updateCollection(data.collection);
        updateResources(data.resources);
        await updateRewards();
    } catch (error) {
        console.error('加载用户数据失败:', error);
    }
}

// 更新累计奖励
async function updateRewards() {
    try {
        const response = await fetch(`/api/rewards?pool_type=${currentPool}`);
        const data = await response.json();
        const rewards = data.rewards || [];
        
        const rewardsContainer = document.getElementById('rewards-container');
        if (rewardsContainer) {
            rewardsContainer.innerHTML = '';
            
            if (rewards.length === 0) {
                const emptyMessage = document.createElement('div');
                emptyMessage.style.color = '#aaa';
                emptyMessage.style.textAlign = 'center';
                emptyMessage.style.padding = '10px';
                emptyMessage.textContent = '暂无累计奖励';
                rewardsContainer.appendChild(emptyMessage);
            } else {
                rewards.forEach(reward => {
                    const rewardItem = document.createElement('div');
                    rewardItem.className = 'reward-item';
                    rewardItem.textContent = reward;
                    rewardsContainer.appendChild(rewardItem);
                });
            }
        }
    } catch (error) {
        console.error('加载累计奖励失败:', error);
        const rewardsContainer = document.getElementById('rewards-container');
        if (rewardsContainer) {
            rewardsContainer.innerHTML = '';
            const errorMessage = document.createElement('div');
            errorMessage.style.color = '#aaa';
            errorMessage.style.textAlign = 'center';
            errorMessage.style.padding = '10px';
            errorMessage.textContent = '暂无累计奖励';
            rewardsContainer.appendChild(errorMessage);
        }
    }
}

// 更新资源信息和按钮显示
function updateResources(resources) {
    // 更新顶部导航栏中的资源显示
    const charteredPermitsEl = document.getElementById('chartered-permits');
    const oroberylEl = document.getElementById('oroberyl');
    const arsenalTicketsEl = document.getElementById('arsenal-tickets');
    const origeometryEl = document.getElementById('origeometry');
    const totalRechargeEl = document.getElementById('total-recharge');
    
    charteredPermitsEl.textContent = formatNumber(resources.chartered_permits || 0);
    oroberylEl.textContent = formatNumber(resources.oroberyl || 0);
    arsenalTicketsEl.textContent = formatNumber(resources.arsenal_tickets || 0);
    origeometryEl.textContent = formatNumber(resources.origeometry || 0);
    totalRechargeEl.textContent = '￥' + formatNumber(resources.total_recharge || 0);
    
    // 添加数字更新动画
    [charteredPermitsEl, oroberylEl, arsenalTicketsEl, origeometryEl, totalRechargeEl].forEach(el => {
        el.style.transition = 'all 0.5s ease';
        el.style.transform = 'scale(1.1)';
        setTimeout(() => {
            el.style.transform = 'scale(1)';
        }, 300);
    });
    
    const urgentCount = resources.urgent_recruitment || 0;
    
    // 控制按钮显示
    const singleDrawBtn = document.getElementById('single-draw');
    const tenDrawBtn = document.getElementById('ten-draw');
    const urgentRecruitmentBtn = document.getElementById('urgent-recruitment');
    
    console.log('updateResources called with currentPool:', currentPool, 'urgentCount:', urgentCount);
    
    // 武器池：只显示单抽按钮，隐藏十连和加急招募按钮
    if (currentPool === 'weapon') {
        console.log('Weapon pool: showing single draw button, hiding others');
        singleDrawBtn.style.display = 'inline-block';
        tenDrawBtn.style.display = 'none';
        tenDrawBtn.style.visibility = 'hidden';
        tenDrawBtn.style.width = '0';
        tenDrawBtn.style.margin = '0';
        urgentRecruitmentBtn.style.display = 'none';
    } 
    // 角色池：根据加急招募次数决定显示哪个按钮
    else if (currentPool === 'char') {
        if (urgentCount > 0) {
            console.log('Char pool with urgent recruitment: showing urgent button, hiding others');
            // 加急招募可用时，显示加急招募按钮，隐藏单抽和十连按钮
            singleDrawBtn.style.display = 'none';
            tenDrawBtn.style.display = 'none';
            urgentRecruitmentBtn.style.display = 'inline-block';
        } else {
            console.log('Char pool without urgent recruitment: showing single and ten draw buttons');
            // 否则，显示单抽和十连按钮，隐藏加急招募按钮
            singleDrawBtn.style.display = 'inline-block';
            tenDrawBtn.style.display = 'inline-block';
            urgentRecruitmentBtn.style.display = 'none';
        }
    } else {
        console.log('Default case: showing single and ten draw buttons');
        // 默认情况：显示单抽和十连按钮，隐藏加急招募按钮
        singleDrawBtn.style.display = 'inline-block';
        tenDrawBtn.style.display = 'inline-block';
        urgentRecruitmentBtn.style.display = 'none';
    }
}

// 添加千位分隔符
function formatNumber(num) {
    if (typeof num === 'number') {
        return num.toLocaleString();
    }
    return num;
}

// 更新统计数据
function updateStats(data) {
    const gachaData = currentPool === 'char' ? data.char_gacha : data.weapon_gacha;
    
    const totalDrawsEl = document.getElementById('total-draws');
    const no6starEl = document.getElementById('no-6star');
    const no5starEl = document.getElementById('no-5star');
    const noUpEl = document.getElementById('no-up');
    
    if (totalDrawsEl && no6starEl && no5starEl && noUpEl) {
        if (currentPool === 'char') {
            totalDrawsEl.textContent = formatNumber(gachaData.total_draws);
            no6starEl.textContent = formatNumber(gachaData.no_6star_draw);
            no5starEl.textContent = formatNumber(gachaData.no_5star_plus_draw);
            noUpEl.textContent = formatNumber(gachaData.no_up_draw);
        } else {
            totalDrawsEl.textContent = formatNumber(gachaData.total_apply);
            no6starEl.textContent = formatNumber(gachaData.no_6star_apply);
            no5starEl.textContent = 'N/A';
            noUpEl.textContent = formatNumber(gachaData.no_up_apply);
        }
        
        // 添加数字更新动画
        [totalDrawsEl, no6starEl, no5starEl, noUpEl].forEach(el => {
            if (el.textContent !== 'N/A') {
                el.style.transition = 'all 0.5s ease';
                el.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    el.style.transform = 'scale(1)';
                }, 300);
            }
        });
    }
}

// 更新收藏展示
function updateCollection(collection) {
    const container = document.getElementById('collection-container');
    if (container) {
        container.innerHTML = '';
        
        const items = currentCollection === 'chars' ? collection.chars : collection.weapons;
        
        if (Object.keys(items).length === 0) {
            // 显示暂无数据提示
            const emptyMessage = document.createElement('div');
            emptyMessage.style.color = '#aaa';
            emptyMessage.style.textAlign = 'center';
            emptyMessage.style.padding = '20px';
            emptyMessage.textContent = '暂无数据';
            container.appendChild(emptyMessage);
        } else {
            Object.entries(items).forEach(([name, info]) => {
                const item = document.createElement('div');
                item.className = `collection-item star-${info.star}`;
                item.innerHTML = `
                    ${name}
                    <span class="count">${info.count}</span>
                `;
                container.appendChild(item);
                
                // 优化计数显示效果
                const countEl = item.querySelector('.count');
                if (countEl) {
                    // 添加更好的视觉效果
                    countEl.style.fontWeight = 'bold';
                    countEl.style.fontSize = '16px';
                    countEl.style.padding = '2px 8px';
                    countEl.style.borderRadius = '10px';
                    countEl.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
                    countEl.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.3)';
                    
                    // 添加计数动画
                    countEl.style.transition = 'all 0.5s ease';
                    countEl.style.transform = 'scale(1.2)';
                    setTimeout(() => {
                        countEl.style.transform = 'scale(1)';
                    }, 300);
                }
            });
        }
    }
}

// 执行抽卡
async function performGacha(count) {
    try {
        // 武器池只能进行单次申领
        const actualCount = currentPool === 'weapon' ? 1 : count;
        
        // 检查是否为角色池且有加急招募次数
        if (currentPool === 'char') {
            // 先获取用户数据，检查是否有加急招募次数
            const userDataResponse = await fetch('/api/user_data');
            const userData = await userDataResponse.json();
            const urgentCount = userData.resources.urgent_recruitment || 0;
            
            if (urgentCount > 0) {
                // 有加急招募次数，先消耗加急招募
                const urgentResponse = await fetch('/api/urgent_recruitment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const urgentResult = await urgentResponse.json();
                if (urgentResult.error) {
                    alert('加急招募失败: ' + urgentResult.error);
                    return;
                }
                
                await loadUserData();
                await updateRewards();
                showResults(urgentResult.results);
                return;
            }
        }
        
        // 没有加急招募次数或不是角色池，执行普通抽卡
        const response = await fetch('/api/gacha', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pool_type: currentPool,
                count: actualCount
            })
        });
        
        const result = await response.json();
        if (result.error) {
            alert('抽卡失败: ' + result.error);
            return;
        }
        
        await loadUserData();
        await updateRewards();
        showResults(result.results);
    } catch (error) {
        console.error('抽卡失败:', error);
        alert('抽卡失败，请重试');
    }
}

// 执行加急招募
async function performUrgentRecruitment() {
    try {
        const response = await fetch('/api/urgent_recruitment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.error) {
            alert('加急招募失败: ' + result.error);
            return;
        }
        
        await loadUserData();
        await updateRewards();
        showResults(result.results);
    } catch (error) {
        console.error('加急招募失败:', error);
        alert('加急招募失败，请重试');
    }
}

// 展示抽卡结果
function showResults(results) {
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    
    // 计算最高稀有度
    let maxStar = 0;
    results.forEach(result => {
        if (result.star > maxStar) {
            maxStar = result.star;
        }
    });
    
    // 总是显示10个卡片
    const cards = [];
    for (let i = 0; i < 10; i++) {
        if (i < results.length) {
            // 显示实际抽卡结果
            const result = results[i];
            const card = document.createElement('div');
            // 单抽时使用从左向右的动画，十连抽时使用从右向左的动画
            const animationClass = results.length === 1 ? 'slide-in-left' : 'slide-in';
            card.className = `result-card star-${result.star} gray ${animationClass}`;
            card.style.animationDelay = `${i * 0.1}s`;
            
            // 创建卡片内容容器
            const cardContent = document.createElement('div');
            cardContent.className = 'card-content';
            // 初始隐藏内容
            cardContent.style.opacity = '0';
            cardContent.innerHTML = result.name;
            
            // 添加保底标记
            if (result.is_up_g || result.is_6_g || result.is_5_g) {
                cardContent.innerHTML += '<br>*';
            }
            
            card.appendChild(cardContent);
            container.appendChild(card);
            cards.push({ card, result, cardContent });
        } else {
            // 显示空白卡片
            const card = document.createElement('div');
            card.className = 'result-card empty';
            card.textContent = '';
            container.appendChild(card);
        }
    }
    
    // 执行动画
    if (results.length > 0) {
        // 延迟显示实际内容和发光动画，保留悬念
        setTimeout(() => {
            if (results.length === 1) {
                // 单结果动画
                const cardInfo = cards[0];
                if (cardInfo) {
                    // 移除灰色样式
                    cardInfo.card.classList.remove('gray');
                    // 添加对应星级的动画
                    cardInfo.card.classList.add(`animate-star-${cardInfo.result.star}`);
                    // 延迟显示内容，确保颜色已经确定
                    setTimeout(() => {
                        cardInfo.cardContent.style.opacity = '1';
                        cardInfo.cardContent.style.transition = 'opacity 0.5s ease-in-out';
                    }, 300);
                }
            } else {
                // 多结果动画
                // 1. 先显示最高稀有度的卡片颜色
                const highestStarCards = cards.filter(cardInfo => cardInfo.result.star === maxStar);
                highestStarCards.forEach((cardInfo, index) => {
                    setTimeout(() => {
                        cardInfo.card.classList.remove('gray');
                        cardInfo.card.classList.add(`animate-star-${cardInfo.result.star}`);
                    }, index * 100);
                });
                
                // 2. 然后显示其他卡片的颜色
                const otherCards = cards.filter(cardInfo => cardInfo.result.star !== maxStar);
                otherCards.forEach((cardInfo, index) => {
                    setTimeout(() => {
                        cardInfo.card.classList.remove('gray');
                        cardInfo.card.classList.add(`animate-star-${cardInfo.result.star}`);
                    }, highestStarCards.length * 100 + index * 100);
                });
                
                // 3. 最后按稀有度从低到高、从左到右显示名称
                // 先按稀有度分组，再按原始顺序排列
                const cardsByRarity = {};
                cards.forEach((cardInfo, index) => {
                    const star = cardInfo.result.star;
                    if (!cardsByRarity[star]) {
                        cardsByRarity[star] = [];
                    }
                    cardsByRarity[star].push({ ...cardInfo, originalIndex: index });
                });
                
                // 按稀有度从低到高排序
                const sortedRarities = Object.keys(cardsByRarity).sort((a, b) => parseInt(a) - parseInt(b));
                
                // 收集所有卡片，按稀有度从低到高，同一稀有度按原始顺序
                const sortedCards = [];
                sortedRarities.forEach(rarity => {
                    // 同一稀有度按原始顺序排列（从左到右）
                    cardsByRarity[rarity].sort((a, b) => a.originalIndex - b.originalIndex);
                    sortedCards.push(...cardsByRarity[rarity]);
                });
                
                // 按顺序显示名称
                sortedCards.forEach((cardInfo, index) => {
                    setTimeout(() => {
                        cardInfo.cardContent.style.opacity = '1';
                        cardInfo.cardContent.style.transition = 'opacity 0.5s ease-in-out';
                    }, 500 + index * 100);
                });
            }
        }, 500); // 0.5 秒后显示实际内容
    }
    
    // 移动端优化：滚动到结果区域
    if (window.innerWidth <= 768) {
        setTimeout(() => {
            const resultArea = document.querySelector('.result-area');
            if (resultArea) {
                resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 1000);
    }
}

// 清空抽卡结果
function clearResults() {
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    
    // 显示10个空白卡片
    for (let i = 0; i < 10; i++) {
        const card = document.createElement('div');
        card.className = 'result-card empty';
        card.textContent = '';
        container.appendChild(card);
    }
}

// 更新干员详情
function updateCharsDetail() {
    const container = document.getElementById('chars-detail-container');
    if (container) {
        container.innerHTML = '';
        
        // 获取用户数据
        const userDataResponse = fetch('/api/user_data');
        userDataResponse.then(response => response.json()).then(data => {
            const chars = data.collection.chars;
            
            if (Object.keys(chars).length === 0) {
                // 显示暂无数据提示
                const emptyMessage = document.createElement('div');
                emptyMessage.style.color = '#aaa';
                emptyMessage.style.textAlign = 'center';
                emptyMessage.style.padding = '20px';
                emptyMessage.textContent = '暂无干员数据';
                container.appendChild(emptyMessage);
            } else {
                // 按稀有度分类干员
                const charsByStar = {};
                Object.entries(chars).forEach(([name, info]) => {
                    const star = info.star;
                    if (!charsByStar[star]) {
                        charsByStar[star] = [];
                    }
                    charsByStar[star].push({ name, info });
                });
                
                // 按稀有度从高到低排序
                const sortedStars = Object.keys(charsByStar).sort((a, b) => parseInt(b) - parseInt(a));
                
                // 显示分类后的干员
                sortedStars.forEach(star => {
                    const starSection = document.createElement('div');
                    starSection.className = `star-section star-${star}`;
                    starSection.innerHTML = `<h3>${star}星干员</h3>`;
                    
                    const charGrid = document.createElement('div');
                    charGrid.style.display = 'grid';
                    charGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(150px, 1fr))';
                    charGrid.style.gap = '15px';
                    charGrid.style.padding = '10px';
                    charGrid.style.marginBottom = '20px';
                    
                    // 按名称排序
                    charsByStar[star].sort((a, b) => a.name.localeCompare(b.name));
                    
                    charsByStar[star].forEach(({ name, info }) => {
                        // 计算潜能等级（最多5级）
                        const potential = Math.min(info.count, 5);
                        
                        const charCard = document.createElement('div');
                        charCard.className = `char-card star-${info.star}`;
                        charCard.innerHTML = `
                            <div class="char-name">${name}</div>
                            <div class="char-potential">${potential}</div>
                        `;
                        charGrid.appendChild(charCard);
                    });
                    
                    starSection.appendChild(charGrid);
                    container.appendChild(starSection);
                });
            }
        }).catch(error => {
            console.error('加载干员详情失败:', error);
            container.innerHTML = '<div style="color: #aaa; text-align: center; padding: 20px;">加载失败</div>';
        });
    }
}

// 更新卡池UI用词
async function updatePoolUI(poolType) {
    console.log('updatePoolUI called with poolType:', poolType);
    
    // 清空抽卡结果
    clearResults();
    
    if (poolType === 'char') {
        // 角色卡池用词
        console.log('Setting char pool UI');
        document.getElementById('single-draw').textContent = 'Headhunt×1';
        document.getElementById('ten-draw').textContent = 'Headhunt×10';
        // 重置十连抽按钮的样式，确保它可以正常显示
        document.getElementById('ten-draw').style.display = 'inline-block';
        document.getElementById('ten-draw').style.visibility = 'visible';
        document.getElementById('ten-draw').style.width = 'auto';
        document.getElementById('ten-draw').style.margin = '0 10px';
        // 最终显示状态由updateResources函数决定
        document.getElementById('result-title').textContent = '寻访结果';
        document.getElementById('stats-title').textContent = '寻访统计';
        document.getElementById('total-label').textContent = '累计寻访次数';
        document.getElementById('six-star-label').textContent = '6星保底计数';
        document.getElementById('five-star-label').textContent = '5星保底计数';
        document.getElementById('up-label').textContent = 'UP保底计数';
        
        // 更新按钮类
        document.getElementById('single-draw').className = 'draw-btn single-draw';
        document.getElementById('ten-draw').className = 'draw-btn ten-draw';
    } else {
        // 武器卡池用词
        console.log('Setting weapon pool UI');
        document.getElementById('single-draw').textContent = 'Arsenal Issue×1';
        document.getElementById('ten-draw').style.display = 'none'; // 隐藏十连抽按钮
        document.getElementById('ten-draw').style.visibility = 'hidden'; // 额外设置visibility
        document.getElementById('ten-draw').style.width = '0'; // 额外设置宽度
        document.getElementById('ten-draw').style.margin = '0'; // 额外设置 margin
        document.getElementById('result-title').textContent = '申领结果';
        document.getElementById('stats-title').textContent = '申领统计';
        document.getElementById('total-label').textContent = '累计申领次数';
        document.getElementById('six-star-label').textContent = '6星保底计数';
        document.getElementById('five-star-label').textContent = 'N/A';
        document.getElementById('up-label').textContent = 'UP保底计数';
        
        // 更新按钮类
        document.getElementById('single-draw').className = 'draw-btn weapon-draw';
    }
    
    // 从后端API获取卡池信息
    try {
        const response = await fetch(`/api/pool_info?pool_type=${poolType}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('获取卡池信息失败:', data.error);
            return;
        }
        
        // 更新卡池名称，添加卡池类型前缀
        let poolTypePrefix = '';
        if (poolType === 'char') {
            poolTypePrefix = '特许寻访 ';
        } else {
            poolTypePrefix = '武库申领 ';
        }
        document.getElementById('pool-name').textContent = poolTypePrefix + data.pool_name;
        
        // 更新概率提升的物品
        const boostedItems = document.getElementById('boosted-items');
        boostedItems.innerHTML = '';
        
        data.boosted_items.forEach(item => {
            const itemElement = document.createElement('span');
            itemElement.className = 'boosted-item';
            if (item.type) {
                itemElement.textContent = `${item.name} (${item.type})`;
            } else {
                itemElement.textContent = item.name;
            }
            boostedItems.appendChild(itemElement);
        });
    } catch (error) {
        console.error('获取卡池信息失败:', error);
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 移动端菜单按钮
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const navOverlay = document.getElementById('nav-overlay');
    const leftNav = document.querySelector('.left-nav');
    
    if (mobileMenuBtn && navOverlay && leftNav) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenuBtn.classList.toggle('active');
            leftNav.classList.toggle('active');
            navOverlay.classList.toggle('active');
            document.body.style.overflow = leftNav.classList.contains('active') ? 'hidden' : '';
        });
        
        navOverlay.addEventListener('click', () => {
            mobileMenuBtn.classList.remove('active');
            leftNav.classList.remove('active');
            navOverlay.classList.remove('active');
            document.body.style.overflow = '';
        });
        
        // 导航按钮点击后关闭导航栏
        const navBtns = leftNav.querySelectorAll('.nav-btn');
        navBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    setTimeout(() => {
                        mobileMenuBtn.classList.remove('active');
                        leftNav.classList.remove('active');
                        navOverlay.classList.remove('active');
                        document.body.style.overflow = '';
                    }, 300);
                }
            });
        });
    }
    
    // 卡池选择
    document.getElementById('char-pool-btn').addEventListener('click', async () => {
        currentPool = 'char';
        // 更新卡池按钮状态
        document.getElementById('char-pool-btn').classList.add('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置收藏按钮状态
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 更新卡池 UI
        updatePoolUI('char');
        // 显示抽卡和统计区域，隐藏收藏区域
        document.querySelector('.gacha-area').style.display = 'block';
        document.querySelector('.stats-area').style.display = 'block';
        // 移除收藏区域
        const collectionArea = document.getElementById('temp-collection-area');
        if (collectionArea) {
            collectionArea.remove();
        }
        // 移除资源管理区域
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 加载并更新数据
        await loadUserData();
    });
    
    document.getElementById('weapon-pool-btn').addEventListener('click', async () => {
        currentPool = 'weapon';
        // 更新卡池按钮状态
        document.getElementById('weapon-pool-btn').classList.add('active');
        document.getElementById('char-pool-btn').classList.remove('active');
        // 重置收藏按钮状态
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 更新卡池 UI
        updatePoolUI('weapon');
        // 显示抽卡和统计区域，隐藏收藏区域
        document.querySelector('.gacha-area').style.display = 'block';
        document.querySelector('.stats-area').style.display = 'block';
        // 移除收藏区域
        const collectionArea = document.getElementById('temp-collection-area');
        if (collectionArea) {
            collectionArea.remove();
        }
        // 移除资源管理区域
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 加载并更新数据
        await loadUserData();
    });
    
    // 抽卡按钮
    document.getElementById('single-draw').addEventListener('click', () => {
        performGacha(1);
    });
    
    document.getElementById('ten-draw').addEventListener('click', () => {
        performGacha(10);
    });
    
    // 加急招募按钮
    document.getElementById('urgent-recruitment').addEventListener('click', () => {
        performUrgentRecruitment();
    });
    
    // 收藏标签切换
    document.getElementById('chars-tab').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        currentCollection = 'chars';
        // 更新收藏按钮状态
        document.getElementById('chars-tab').classList.add('active');
        document.getElementById('chars-detail-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 隐藏抽卡和统计区域，显示收藏区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除资源管理区域
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 显示收藏区域
        const collectionArea = document.createElement('div');
        collectionArea.className = 'collection-area';
        collectionArea.id = 'temp-collection-area';
        collectionArea.innerHTML = `
            <h2>干员获取统计</h2>
            <div id="collection-container" class="collection-container"></div>
        `;
        // 移除旧的收藏区域（如果存在）
        const oldCollectionArea = document.getElementById('temp-collection-area');
        if (oldCollectionArea) {
            oldCollectionArea.remove();
        }
        // 添加新的收藏区域
        document.querySelector('.content-area').appendChild(collectionArea);
        // 加载并更新数据
        await loadUserData();
    });
    
    // 干员详情标签切换
    document.getElementById('chars-detail-tab').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        // 更新按钮状态
        document.getElementById('chars-detail-tab').classList.add('active');
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 隐藏抽卡和统计区域，显示干员详情区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除资源管理区域
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 显示干员详情区域
        const charsDetailArea = document.createElement('div');
        charsDetailArea.className = 'collection-area';
        charsDetailArea.id = 'temp-collection-area';
        charsDetailArea.innerHTML = `
            <h2>干员详情</h2>
            <div id="chars-detail-container" class="chars-detail-container"></div>
        `;
        // 移除旧的收藏区域（如果存在）
        const oldCollectionArea = document.getElementById('temp-collection-area');
        if (oldCollectionArea) {
            oldCollectionArea.remove();
        }
        // 添加新的干员详情区域
        document.querySelector('.content-area').appendChild(charsDetailArea);
        // 加载并更新干员详情数据
        await loadUserData();
        updateCharsDetail();
    });
    
    document.getElementById('weapons-tab').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        currentCollection = 'weapons';
        // 更新收藏按钮状态
        document.getElementById('weapons-tab').classList.add('active');
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('chars-detail-tab').classList.remove('active');
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 隐藏抽卡和统计区域，显示收藏区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除资源管理区域
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 显示收藏区域
        const collectionArea = document.createElement('div');
        collectionArea.className = 'collection-area';
        collectionArea.id = 'temp-collection-area';
        collectionArea.innerHTML = `
            <h2>贵重品库/武器</h2>
            <div id="collection-container" class="collection-container"></div>
        `;
        // 移除旧的收藏区域（如果存在）
        const oldCollectionArea = document.getElementById('temp-collection-area');
        if (oldCollectionArea) {
            oldCollectionArea.remove();
        }
        // 添加新的收藏区域
        document.querySelector('.content-area').appendChild(collectionArea);
        // 加载并更新数据
        await loadUserData();
    });
    
    // 资源管理按钮
    document.getElementById('resources-tab').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置收藏按钮状态
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 隐藏抽卡和统计区域，显示资源管理区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除收藏区域（干员、贵重品库）
        const collectionArea = document.getElementById('temp-collection-area');
        if (collectionArea) {
            collectionArea.remove();
        }
        // 移除历史记录区域
        const historyArea = document.getElementById('temp-history-area');
        if (historyArea) {
            historyArea.remove();
        }
        // 移除旧的资源管理区域（如果存在）
        const oldResourcesArea = document.getElementById('temp-resources-area');
        if (oldResourcesArea) {
            oldResourcesArea.remove();
        }
        // 获取用户数据，根据首充状态更新充值按钮
        const userDataResponse = await fetch('/api/user_data');
        const userData = await userDataResponse.json();
        const firstRecharge = userData.resources.first_recharge || {};
        
        // 显示资源管理区域
        const resourcesArea = document.createElement('div');
        resourcesArea.className = 'resources-area';
        resourcesArea.id = 'temp-resources-area';
        
        // 构建充值按钮HTML
        let rechargeButtons = '';
        const rechargeTiers = [
            { amount: 6, firstRechargeText: '首充特惠：获得 6 个衍质源石', normalText: '获得 3 个衍质源石' },
            { amount: 30, firstRechargeText: '首充双倍：获得 24 个衍质源石', normalText: '获得 15 个衍质源石' },
            { amount: 98, firstRechargeText: '首充双倍：获得 84 个衍质源石', normalText: '获得 50 个衍质源石' },
            { amount: 198, firstRechargeText: '首充双倍：获得 170 个衍质源石', normalText: '获得 102 个衍质源石' },
            { amount: 328, firstRechargeText: '首充双倍：获得 282 个衍质源石', normalText: '获得 171 个衍质源石' },
            { amount: 648, firstRechargeText: '首充双倍：获得 560 个衍质源石', normalText: '获得 350 个衍质源石' }
        ];
        
        rechargeTiers.forEach(tier => {
            const isFirstRecharge = firstRecharge[tier.amount.toString()] || false;
            const buttonClass = 'recharge-btn first-recharge'; // 始终使用首充按钮样式，保持黄色和金色配色
            const buttonText = isFirstRecharge ? tier.firstRechargeText : tier.normalText;
            const rewardText = isFirstRecharge ? `首充${buttonText.split('：')[1]}` : buttonText;
            rechargeButtons += `<button class="${buttonClass}" data-amount="${tier.amount}" data-reward="${rewardText}"><div class="button-content"><div class="amount">¥${tier.amount}</div></div></button>`;
        });
        
        resourcesArea.innerHTML = `
            <h2>资源管理</h2>
            <div class="resources-management">
                <div class="resource-card">
                    <h3>充值模拟（不会产生消费）</h3>
                    <div class="recharge-options">
                        ${rechargeButtons}
                    </div>
                </div>
                <div class="resource-card">
                    <h3>资源兑换</h3>
                    <div class="exchange-options">
                        <div class="exchange-item">
                            <input type="number" id="exchange-amount" min="1" value="1" style="width: 60px; padding: 5px; margin-right: 10px; background: #333; color: white; border: 1px solid #555; border-radius: 4px;">
                            <button id="exchange-origeometry-oroberyl" class="exchange-btn">衍质源石 → 嵌晶玉 (1:75)</button>
                            <button id="exchange-all-oroberyl" class="exchange-btn all-btn">ALL</button>
                        </div>
                        <div class="exchange-item">
                            <input type="number" id="exchange-amount-arsenal" min="1" value="1" style="width: 60px; padding: 5px; margin-right: 10px; background: #333; color: white; border: 1px solid #555; border-radius: 4px;">
                            <button id="exchange-origeometry-arsenal" class="exchange-btn">衍质源石 → 武库配额 (1:25)</button>
                            <button id="exchange-all-arsenal" class="exchange-btn all-btn">ALL</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        // 添加新的资源管理区域
        document.querySelector('.content-area').appendChild(resourcesArea);
        // 添加充值和兑换按钮的事件监听器
        setupResourceManagementListeners();
        // 加载并更新数据
        await loadUserData();
    });
    
    // 清空数据按钮
    document.getElementById('clear-data-btn').addEventListener('click', async () => {
        if (confirm('确定要清空所有抽卡数据吗？此操作不可恢复。')) {
            await clearUserData();
        }
    });
    
    // 寻访记录按钮
    document.getElementById('char-history-btn').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置收藏按钮状态
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('chars-detail-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.add('active');
        document.getElementById('weapon-history-btn').classList.remove('active');
        // 隐藏抽卡和统计区域，显示历史记录区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除其他区域
        const collectionArea = document.getElementById('temp-collection-area');
        if (collectionArea) {
            collectionArea.remove();
        }
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除旧的历史记录区域（如果存在）
        const oldHistoryArea = document.getElementById('temp-history-area');
        if (oldHistoryArea) {
            oldHistoryArea.remove();
        }
        // 显示寻访记录区域
        const historyArea = document.createElement('div');
        historyArea.className = 'history-area';
        historyArea.id = 'temp-history-area';
        historyArea.innerHTML = `
            <h2>寻访记录</h2>
            <div id="char-history-container" class="history-container"></div>
        `;
        // 添加新的历史记录区域
        document.querySelector('.content-area').appendChild(historyArea);
        // 加载并显示寻访记录
        await loadHistory('char');
    });
    
    // 申领记录按钮
    document.getElementById('weapon-history-btn').addEventListener('click', async () => {
        // 清空抽卡结果
        clearResults();
        
        // 重置卡池按钮状态
        document.getElementById('char-pool-btn').classList.remove('active');
        document.getElementById('weapon-pool-btn').classList.remove('active');
        // 重置收藏按钮状态
        document.getElementById('chars-tab').classList.remove('active');
        document.getElementById('chars-detail-tab').classList.remove('active');
        document.getElementById('weapons-tab').classList.remove('active');
        // 重置资源管理按钮状态
        document.getElementById('resources-tab').classList.remove('active');
        // 重置历史记录按钮状态
        document.getElementById('char-history-btn').classList.remove('active');
        document.getElementById('weapon-history-btn').classList.add('active');
        // 隐藏抽卡和统计区域，显示历史记录区域
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        // 移除其他区域
        const collectionArea = document.getElementById('temp-collection-area');
        if (collectionArea) {
            collectionArea.remove();
        }
        const resourcesArea = document.getElementById('temp-resources-area');
        if (resourcesArea) {
            resourcesArea.remove();
        }
        // 移除旧的历史记录区域（如果存在）
        const oldHistoryArea = document.getElementById('temp-history-area');
        if (oldHistoryArea) {
            oldHistoryArea.remove();
        }
        // 显示申领记录区域
        const historyArea = document.createElement('div');
        historyArea.className = 'history-area';
        historyArea.id = 'temp-history-area';
        historyArea.innerHTML = `
            <h2>申领记录</h2>
            <div id="weapon-history-container" class="history-container"></div>
        `;
        // 添加新的历史记录区域
        document.querySelector('.content-area').appendChild(historyArea);
        // 加载并显示申领记录
        await loadHistory('weapon');
    });
}

// 清空用户数据
async function clearUserData() {
    try {
        const response = await fetch('/api/clear_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.message) {
            alert(result.message);
            await loadUserData();
            await updateRewards();
        }
    } catch (error) {
        console.error('清空数据失败:', error);
        alert('清空数据失败，请重试');
    }
}

// 加载历史记录
async function loadHistory(poolType) {
    try {
        const response = await fetch(`/api/history?pool_type=${poolType}`);
        const data = await response.json();
        const history = data.history || [];
        
        const containerId = poolType === 'char' ? 'char-history-container' : 'weapon-history-container';
        const container = document.getElementById(containerId);
        
        if (container) {
            container.innerHTML = '';
            
            if (history.length === 0) {
                const emptyMessage = document.createElement('div');
                emptyMessage.style.color = '#aaa';
                emptyMessage.style.textAlign = 'center';
                emptyMessage.style.padding = '20px';
                emptyMessage.style.fontSize = '16px';
                emptyMessage.textContent = poolType === 'char' ? '暂无寻访记录' : '暂无申领记录';
                container.appendChild(emptyMessage);
            } else {
                // 倒序显示，最新的在前面
                const reversedHistory = [...history].reverse();
                
                // 分组显示，每 10 次为一组
                const groups = [];
                for (let i = 0; i < reversedHistory.length; i += 10) {
                    groups.push(reversedHistory.slice(i, i + 10));
                }
                
                groups.forEach((group, groupIndex) => {
                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'history-group';
                    groupDiv.style.marginBottom = '20px';
                    groupDiv.style.padding = '15px';
                    groupDiv.style.background = 'rgba(255, 255, 255, 0.05)';
                    groupDiv.style.borderRadius = '8px';
                    groupDiv.style.border = '1px solid rgba(255, 255, 255, 0.1)';
                    
                    // 组标题
                    const groupTitle = document.createElement('div');
                    groupTitle.className = 'history-group-title';
                    groupTitle.style.color = '#aaa';
                    groupTitle.style.fontSize = '14px';
                    groupTitle.style.marginBottom = '10px';
                    const startNumber = reversedHistory.length - groupIndex * 10;
                    const endNumber = Math.max(0, reversedHistory.length - (groupIndex + 1) * 10);
                    if (endNumber === startNumber - 1) {
                        groupTitle.textContent = `第 ${startNumber} 次`;
                    } else {
                        groupTitle.textContent = `第 ${startNumber} ~ ${endNumber + 1} 次`;
                    }
                    groupDiv.appendChild(groupTitle);
                    
                    // 结果卡片容器
                    const resultsDiv = document.createElement('div');
                    resultsDiv.style.display = 'flex';
                    resultsDiv.style.flexWrap = 'wrap';
                    resultsDiv.style.gap = '10px';
                    
                    group.forEach((item, index) => {
                        const resultCard = document.createElement('div');
                        resultCard.className = `history-result-card star-${item.star}`;
                        resultCard.style.padding = '10px 15px';
                        resultCard.style.background = getStarBackground(item.star);
                        resultCard.style.borderRadius = '4px';
                        resultCard.style.color = getStarColor(item.star);
                        resultCard.style.fontWeight = 'bold';
                        resultCard.style.minWidth = '120px';
                        resultCard.style.textAlign = 'center';
                        resultCard.style.border = `2px solid ${getStarColor(item.star)}`;
                        
                        let cardContent = item.name;
                        if (item.is_up_g || item.is_6_g || item.is_5_g) {
                            cardContent += ' *';
                        }
                        resultCard.textContent = cardContent;
                        resultsDiv.appendChild(resultCard);
                    });
                    
                    groupDiv.appendChild(resultsDiv);
                    container.appendChild(groupDiv);
                });
            }
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
        const containerId = poolType === 'char' ? 'char-history-container' : 'weapon-history-container';
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div style="color: #aaa; text-align: center; padding: 20px;">加载失败</div>';
        }
    }
}

// 获取星级背景色
function getStarBackground(star) {
    switch(star) {
        case 6: return 'rgba(231, 76, 60, 0.2)';
        case 5: return 'rgba(243, 156, 18, 0.2)';
        case 4: return 'rgba(155, 89, 182, 0.2)';
        case 3: return 'rgba(52, 152, 219, 0.2)';
        default: return 'rgba(100, 100, 100, 0.2)';
    }
}

// 获取星级颜色
function getStarColor(star) {
    switch(star) {
        case 6: return '#ff4444';
        case 5: return '#f39c12';
        case 4: return '#9b59b6';
        case 3: return '#3498db';
        default: return '#999';
    }
}

// 设置资源管理监听器
function setupResourceManagementListeners() {
    // 充值按钮事件
    const rechargeBtns = document.querySelectorAll('.recharge-btn');
    rechargeBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const amount = parseInt(btn.dataset.amount);
            
            try {
                const response = await fetch('/api/recharge', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        amount: amount
                    })
                });
                
                const result = await response.json();
                if (result.message) {
                    alert(result.message);
                    await loadUserData();
                    // 充值后重新进入资源管理页面，刷新按钮样式
                    document.getElementById('resources-tab').click();
                } else if (result.error) {
                    alert('充值失败: ' + result.error);
                }
            } catch (error) {
                console.error('充值失败:', error);
                alert('充值失败，请重试');
            }
        });
    });
    
    // 兑换按钮事件
    const exchangeOroberylBtn = document.getElementById('exchange-origeometry-oroberyl');
    if (exchangeOroberylBtn) {
        exchangeOroberylBtn.addEventListener('click', async () => {
            const amount = parseInt(document.getElementById('exchange-amount').value) || 1;
            
            try {
                const response = await fetch('/api/exchange', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        from: 'origeometry',
                        to: 'oroberyl',
                        amount: amount
                    })
                });
                
                const result = await response.json();
                if (result.message) {
                    alert(result.message);
                    await loadUserData();
                } else if (result.error) {
                    alert('兑换失败: ' + result.error);
                }
            } catch (error) {
                console.error('兑换失败:', error);
                alert('兑换失败，请重试');
            }
        });
    }
    
    const exchangeArsenalBtn = document.getElementById('exchange-origeometry-arsenal');
    if (exchangeArsenalBtn) {
        exchangeArsenalBtn.addEventListener('click', async () => {
            const amount = parseInt(document.getElementById('exchange-amount-arsenal').value) || 1;
            
            try {
                const response = await fetch('/api/exchange', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        from: 'origeometry',
                        to: 'arsenal_tickets',
                        amount: amount
                    })
                });
                
                const result = await response.json();
                if (result.message) {
                    alert(result.message);
                    await loadUserData();
                } else if (result.error) {
                    alert('兑换失败: ' + result.error);
                }
            } catch (error) {
                console.error('兑换失败:', error);
                alert('兑换失败，请重试');
            }
        });
    }
    
    // ALL按钮事件
    const exchangeAllOroberylBtn = document.getElementById('exchange-all-oroberyl');
    if (exchangeAllOroberylBtn) {
        exchangeAllOroberylBtn.addEventListener('click', async () => {
            try {
                // 获取用户数据，获取源石数量
                const userDataResponse = await fetch('/api/user_data');
                const userData = await userDataResponse.json();
                const origeometryAmount = userData.resources.origeometry || 0;
                
                if (origeometryAmount <= 0) {
                    alert('没有可兑换的衍质源石');
                    return;
                }
                
                const response = await fetch('/api/exchange', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        from: 'origeometry',
                        to: 'oroberyl',
                        amount: origeometryAmount
                    })
                });
                
                const result = await response.json();
                if (result.message) {
                    alert(result.message);
                    await loadUserData();
                } else if (result.error) {
                    alert('兑换失败: ' + result.error);
                }
            } catch (error) {
                console.error('兑换失败:', error);
                alert('兑换失败，请重试');
            }
        });
    }
    
    const exchangeAllArsenalBtn = document.getElementById('exchange-all-arsenal');
    if (exchangeAllArsenalBtn) {
        exchangeAllArsenalBtn.addEventListener('click', async () => {
            try {
                // 获取用户数据，获取源石数量
                const userDataResponse = await fetch('/api/user_data');
                const userData = await userDataResponse.json();
                const origeometryAmount = userData.resources.origeometry || 0;
                
                if (origeometryAmount <= 0) {
                    alert('没有可兑换的衍质源石');
                    return;
                }
                
                const response = await fetch('/api/exchange', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        from: 'origeometry',
                        to: 'arsenal_tickets',
                        amount: origeometryAmount
                    })
                });
                
                const result = await response.json();
                if (result.message) {
                    alert(result.message);
                    await loadUserData();
                } else if (result.error) {
                    alert('兑换失败: ' + result.error);
                }
            } catch (error) {
                console.error('兑换失败:', error);
                alert('兑换失败，请重试');
            }
        });
    }
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', initPage);
