let currentPool = 'char';
let currentCollection = 'chars';

const CACHE_CONFIG = {
    USER_DATA: { key: 'cache_user_data', ttl: 300000 },
    POOL_INFO: { key: 'cache_pool_info', ttl: 86400000 },
    REWARDS: { key: 'cache_rewards', ttl: 300000 },
    HISTORY: { key: 'cache_history', ttl: 300000 },
    CHARS_DETAIL: { key: 'cache_chars_detail', ttl: 300000 }
};

const CacheUtil = {
    set(key, data, ttl = 60000) {
        const cacheData = { data, timestamp: Date.now(), ttl };
        try {
            localStorage.setItem(key, JSON.stringify(cacheData));
        } catch (e) {
            console.warn('LocalStorage 写入失败:', e);
        }
    },

    get(key) {
        try {
            const cacheData = localStorage.getItem(key);
            if (!cacheData) return null;

            const parsed = JSON.parse(cacheData);
            if (Date.now() - parsed.timestamp > parsed.ttl) {
                localStorage.removeItem(key);
                return null;
            }
            return parsed.data;
        } catch (e) {
            console.warn('LocalStorage 读取失败:', e);
            return null;
        }
    },

    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn('LocalStorage 删除失败:', e);
        }
    },

    clear() {
        try {
            Object.values(CACHE_CONFIG).forEach(config => {
                localStorage.removeItem(config.key);
            });
        } catch (e) {
            console.warn('LocalStorage 清空失败:', e);
        }
    },

    clearDataCache() {
        try {
            localStorage.removeItem(CACHE_CONFIG.USER_DATA.key);
            localStorage.removeItem(CACHE_CONFIG.REWARDS.key);
            localStorage.removeItem(CACHE_CONFIG.HISTORY.key);
            localStorage.removeItem(CACHE_CONFIG.CHARS_DETAIL.key);
        } catch (e) {
            console.warn('LocalStorage 数据缓存清空失败:', e);
        }
    }
};

const NAV_BUTTONS = {
    POOL: ['char-pool-btn', 'weapon-pool-btn'],
    COLLECTION: ['chars-tab', 'chars-detail-tab', 'weapons-tab'],
    HISTORY: ['char-history-btn', 'weapon-history-btn'],
    RESOURCE: ['resources-tab']
};

const TEMP_AREAS = ['temp-collection-area', 'temp-resources-area', 'temp-history-area'];

function createDOMStructure() {
    const app = document.getElementById('app');
    app.innerHTML = `
        <div class="app-container">
            <div class="nav-overlay" id="nav-overlay"></div>
            
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
                
                <div class="content-area">
                    <div class="gacha-area">
                        <div class="pool-info">
                            <div class="pool-info-content">
                                <div class="pool-name" id="pool-name">特许寻访</div>
                                <div class="boosted-items" id="boosted-items"></div>
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

async function loadUserData(forceRefresh = false) {
    try {
        if (!forceRefresh) {
            const cachedData = CacheUtil.get(CACHE_CONFIG.USER_DATA.key);
            if (cachedData) {
                updateStats(cachedData);
                updateCollection(cachedData.collection);
                updateResources(cachedData.resources);

                const gachaData = currentPool === 'char' ? cachedData.char_gacha : cachedData.weapon_gacha;
                const totalCount = currentPool === 'char' ? gachaData.total_draws : gachaData.total_apply;
                if (shouldUpdateRewards(totalCount)) {
                    await updateRewards();
                }
                return;
            }
        }

        const response = await fetch('/api/user_data');
        const data = await response.json();

        CacheUtil.set(CACHE_CONFIG.USER_DATA.key, data, CACHE_CONFIG.USER_DATA.ttl);

        updateStats(data);
        updateCollection(data.collection);
        updateResources(data.resources);

        const gachaData = currentPool === 'char' ? data.char_gacha : data.weapon_gacha;
        const totalCount = currentPool === 'char' ? gachaData.total_draws : gachaData.total_apply;
        if (shouldUpdateRewards(totalCount)) {
            await updateRewards(true);
        }
    } catch (error) {
        console.error('加载用户数据失败:', error);
        const cachedData = CacheUtil.get(CACHE_CONFIG.USER_DATA.key);
        if (cachedData) {
            updateStats(cachedData);
            updateCollection(cachedData.collection);
            updateResources(cachedData.resources);
        }
    }
}

async function updateRewards(forceRefresh = false) {
    const cacheKey = `${CACHE_CONFIG.REWARDS.key}_${currentPool}`;

    if (!forceRefresh) {
        const cachedData = CacheUtil.get(cacheKey);
        if (cachedData) {
            displayRewards(cachedData);
            return;
        }
    }

    try {
        const response = await fetch(`/api/rewards?pool_type=${currentPool}`);
        const data = await response.json();
        const rewards = data.rewards || [];

        CacheUtil.set(cacheKey, rewards, CACHE_CONFIG.REWARDS.ttl);
        displayRewards(rewards);
    } catch (error) {
        console.error('加载累计奖励失败:', error);
        const rewardsContainer = document.getElementById('rewards-container');
        if (rewardsContainer) {
            rewardsContainer.innerHTML = '';
            const errorMessage = document.createElement('div');
            errorMessage.style.cssText = 'color:#aaa;text-align:center;padding:10px';
            errorMessage.textContent = '暂无累计奖励';
            rewardsContainer.appendChild(errorMessage);
        }
    }
}

function displayRewards(rewards) {
    const rewardsContainer = document.getElementById('rewards-container');
    if (!rewardsContainer) return;

    rewardsContainer.innerHTML = '';

    if (rewards.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.style.cssText = 'color:#aaa;text-align:center;padding:10px';
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

function updateResources(resources) {
    const resourceIds = ['chartered-permits', 'oroberyl', 'arsenal-tickets', 'origeometry', 'total-recharge'];
    const resourceKeys = ['chartered_permits', 'oroberyl', 'arsenal_tickets', 'origeometry', 'total_recharge'];
    const prefix = ['￥', '', '', '', '￥'];

    resourceIds.forEach((id, index) => {
        const el = document.getElementById(id);
        if (el) {
            const value = index === 4 ? '￥' : '';
            el.textContent = value + formatNumber(resources[resourceKeys[index]] || 0);
            el.style.transition = 'all 0.5s ease';
            el.style.transform = 'scale(1.1)';
            setTimeout(() => { el.style.transform = 'scale(1)'; }, 300);
        }
    });

    const urgentCount = resources.urgent_recruitment || 0;
    const singleDrawBtn = document.getElementById('single-draw');
    const tenDrawBtn = document.getElementById('ten-draw');
    const urgentRecruitmentBtn = document.getElementById('urgent-recruitment');

    if (currentPool === 'weapon') {
        singleDrawBtn.style.display = 'inline-block';
        tenDrawBtn.style.display = 'none';
        tenDrawBtn.style.visibility = 'hidden';
        tenDrawBtn.style.width = '0';
        tenDrawBtn.style.margin = '0';
        urgentRecruitmentBtn.style.display = 'none';
    } else if (currentPool === 'char') {
        if (urgentCount > 0) {
            singleDrawBtn.style.display = 'none';
            tenDrawBtn.style.display = 'none';
            urgentRecruitmentBtn.style.display = 'inline-block';
        } else {
            singleDrawBtn.style.display = 'inline-block';
            tenDrawBtn.style.display = 'inline-block';
            urgentRecruitmentBtn.style.display = 'none';
        }
    } else {
        singleDrawBtn.style.display = 'inline-block';
        tenDrawBtn.style.display = 'inline-block';
        urgentRecruitmentBtn.style.display = 'none';
    }
}

function formatNumber(num) {
    return typeof num === 'number' ? num.toLocaleString() : num;
}

function updateStats(data) {
    const gachaData = currentPool === 'char' ? data.char_gacha : data.weapon_gacha;

    const statIds = ['total-draws', 'no-6star', 'no-5star', 'no-up'];
    const statKeys = currentPool === 'char'
        ? ['total', 'no_6star', 'no_5star_plus', 'no_up']
        : ['total', 'no_6star', null, 'no_up'];

    statIds.forEach((id, index) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = statKeys[index] ? formatNumber(gachaData[statKeys[index]]) : 'N/A';
            if (el.textContent !== 'N/A') {
                el.style.transition = 'all 0.5s ease';
                el.style.transform = 'scale(1.1)';
                setTimeout(() => { el.style.transform = 'scale(1)'; }, 300);
            }
        }
    });
}

function updateCollection(collection) {
    const container = document.getElementById('collection-container');
    if (!container) return;

    container.innerHTML = '';
    const items = currentCollection === 'chars' ? collection.chars : collection.weapons;

    if (Object.keys(items).length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.style.cssText = 'color:#aaa;text-align:center;padding:20px';
        emptyMessage.textContent = '暂无数据';
        container.appendChild(emptyMessage);
    } else {
        Object.entries(items).forEach(([name, info]) => {
            const item = document.createElement('div');
            item.className = `collection-item star-${info.star}`;
            item.innerHTML = `${name}<span class="count">${info.count}</span>`;
            container.appendChild(item);

            const countEl = item.querySelector('.count');
            if (countEl) {
                countEl.style.cssText = 'font-weight:bold;font-size:16px;padding:2px 8px;border-radius:10px;background-color:rgba(0,0,0,0.3);box-shadow:0 2px 4px rgba(0,0,0,0.3);transition:all 0.5s ease;transform:scale(1.2)';
                setTimeout(() => { countEl.style.transform = 'scale(1)'; }, 300);
            }
        });
    }
}

async function performGacha(count) {
    try {
        const actualCount = currentPool === 'weapon' ? 1 : count;

        if (currentPool === 'char') {
            const userDataResponse = await fetch('/api/user_data');
            const userData = await userDataResponse.json();
            const urgentCount = userData.resources.urgent_recruitment || 0;

            if (urgentCount > 0) {
                const urgentResponse = await fetch('/api/urgent_recruitment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const urgentResult = await urgentResponse.json();
                if (urgentResult.error) {
                    alert('加急招募失败：' + urgentResult.error);
                    return;
                }

                CacheUtil.clearDataCache();
                await loadUserData(true);
                await updateRewards(true);
                await loadHistory(currentPool, true);
                await updateCharsDetail(true);
                showResults(urgentResult.results);
                return;
            }
        }

        const response = await fetch('/api/gacha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pool_type: currentPool, count: actualCount })
        });

        const result = await response.json();
        if (result.error) {
            alert('抽卡失败：' + result.error);
            return;
        }

        CacheUtil.clearDataCache();
        await loadUserData(true);
        await updateRewards(true);
        await loadHistory(currentPool, true);
        await updateCharsDetail(true);
        showResults(result.results);
    } catch (error) {
        console.error('抽卡失败:', error);
        alert('抽卡失败，请重试');
    }
}

async function performUrgentRecruitment() {
    try {
        const response = await fetch('/api/urgent_recruitment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.error) {
            alert('加急招募失败：' + result.error);
            return;
        }

        CacheUtil.clearDataCache();
        await loadUserData(true);
        await updateRewards(true);
        await loadHistory(currentPool, true);
        await updateCharsDetail(true);
        showResults(result.results);
    } catch (error) {
        console.error('加急招募失败:', error);
        alert('加急招募失败，请重试');
    }
}

function createEmojiFall() {
    const emojis = ['🎉', '✨', '🌟', '💫', '🎊', '🌸', '💐', '🎈'];
    const congratulationTexts = ['恭喜', '欧气满满', '好运连连'];

    // 创建 50 个飘落的 emoji
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const emoji = document.createElement('div');
            emoji.className = 'emoji-fall';

            // 随机选择 emoji 或恭喜文字
            if (Math.random() > 0.7) {
                emoji.textContent = congratulationTexts[Math.floor(Math.random() * congratulationTexts.length)];
                emoji.style.fontSize = `${10 + Math.random() * 16}px`;
            } else {
                emoji.textContent = emojis[Math.floor(Math.random() * emojis.length)];
                emoji.style.fontSize = `${14 + Math.random() * 20}px`;
            }

            // 随机位置
            emoji.style.left = `${Math.random() * 100}vw`;

            // 随机动画时长（2-5 秒）
            const duration = 2 + Math.random() * 3;
            emoji.style.animationDuration = `${duration}s`;

            // 随机延迟（0-2 秒）
            emoji.style.animationDelay = `${Math.random() * 2}s`;

            document.body.appendChild(emoji);

            // 动画结束后移除元素
            setTimeout(() => {
                emoji.remove();
            }, (duration + 2) * 1000);
        }, i * 50);
    }
}

function showResults(results) {
    const container = document.getElementById('results-container');
    container.innerHTML = '';

    let maxStar = 0;
    let hasBoostedItem = false;

    // 获取当前卡池的 UP 列表（boosted items）
    const boostedItemsEl = document.getElementById('boosted-items');
    const boostedItemNames = [];
    if (boostedItemsEl) {
        const boostedItemSpans = boostedItemsEl.querySelectorAll('.boosted-item');
        boostedItemSpans.forEach(span => {
            // 提取名称（去掉可能的类型后缀）
            const text = span.textContent;
            const name = text.includes('(') ? text.split('(')[0].trim() : text.trim();
            boostedItemNames.push(name);
        });
    }

    results.forEach(result => {
        maxStar = Math.max(maxStar, result.star);
        // 检查是否是概率提升的项目（UP 角色/武器）
        if (boostedItemNames.includes(result.name)) {
            hasBoostedItem = true;
        }
    });

    // 如果抽到概率提升的项目，触发 emoji 飘落效果
    if (hasBoostedItem) {
        createEmojiFall();
    }

    const cards = [];
    for (let i = 0; i < 10; i++) {
        if (i < results.length) {
            const result = results[i];
            const card = document.createElement('div');
            const animationClass = results.length === 1 ? 'slide-in-left' : 'slide-in';
            card.className = `result-card star-${result.star} gray ${animationClass}`;
            card.style.animationDelay = `${i * 0.1}s`;

            // 为 6 星卡片添加拉伸效果元素
            if (result.star === 6) {
                const stretchEffect = document.createElement('div');
                stretchEffect.className = 'stretch-effect';
                card.appendChild(stretchEffect);
            }

            const cardContent = document.createElement('div');
            cardContent.className = 'card-content';
            cardContent.style.opacity = '0';
            cardContent.innerHTML = result.name + (result.is_up_g || result.is_6_g || result.is_5_g ? '<br>*' : '');

            card.appendChild(cardContent);
            container.appendChild(card);
            cards.push({ card, result, cardContent });
        } else {
            const card = document.createElement('div');
            card.className = 'result-card empty';
            container.appendChild(card);
        }
    }

    // 添加 3D 倾斜效果（容器级别监听）
    if (!('ontouchstart' in window)) {
        container.addEventListener('mousemove', (e) => {
            const containerRect = container.getBoundingClientRect();
            const containerCenterX = containerRect.left + containerRect.width / 2;
            const containerCenterY = containerRect.top + containerRect.height / 2;

            const mouseX = e.clientX;
            const mouseY = e.clientY;

            // 计算容器整体的倾斜角度
            const maxRotation = 10;
            const rotateContainerX = ((mouseY - containerCenterY) / (containerRect.height / 2)) * -maxRotation;
            const rotateContainerY = ((mouseX - containerCenterX) / (containerRect.width / 2)) * maxRotation;

            // 为每个卡片应用倾斜效果
            cards.forEach(({ card, result }) => {
                if (result) {
                    const cardRect = card.getBoundingClientRect();
                    const cardCenterX = cardRect.left + cardRect.width / 2;
                    const cardCenterY = cardRect.top + cardRect.height / 2;

                    // 计算卡片相对于容器的位置偏移
                    const offsetX = (cardCenterX - containerCenterX) / (containerRect.width / 2);
                    const offsetY = (cardCenterY - containerCenterY) / (containerRect.height / 2);

                    // 根据卡片位置调整倾斜角度，产生视差效果
                    const cardRotateX = rotateContainerX + (offsetY * 5);
                    const cardRotateY = rotateContainerY + (offsetX * 5);

                    // 计算卡片到鼠标的距离，用于缩放
                    const distanceX = Math.abs(mouseX - cardCenterX);
                    const distanceY = Math.abs(mouseY - cardCenterY);
                    const maxDistance = Math.sqrt(Math.pow(containerRect.width, 2) + Math.pow(containerRect.height, 2));
                    const distance = Math.sqrt(Math.pow(distanceX, 2) + Math.pow(distanceY, 2));
                    const scale = 1 + (1 - distance / maxDistance) * 0.1;

                    // 对于 5、6 星卡片，添加额外的上下拉伸效果
                    if (result.star >= 5) {
                        // 计算鼠标是否在卡片上方
                        const isInCard = (
                            e.clientX >= cardRect.left &&
                            e.clientX <= cardRect.right &&
                            e.clientY >= cardRect.top &&
                            e.clientY <= cardRect.bottom
                        );

                        // 根据鼠标位置切换拉伸类
                        if (isInCard) {
                            if (!card.classList.contains('extended')) {
                                card.classList.add('extended');
                            }
                        } else {
                            if (card.classList.contains('extended')) {
                                card.classList.remove('extended');
                            }
                        }
                    } else {
                        // 移除非 5、6 星卡片的拉伸类
                        if (card.classList.contains('extended')) {
                            card.classList.remove('extended');
                        }
                    }

                    card.style.transform = `perspective(1000px) rotateX(${cardRotateX}deg) rotateY(${cardRotateY}deg) scale3d(${scale}, ${scale}, 1)`;
                    card.style.boxShadow = `${-cardRotateY / 2}px ${cardRotateX / 2}px 20px rgba(0, 0, 0, 0.4)`;
                    card.style.zIndex = Math.floor(scale * 100) + (result.star >= 5 ? 10 : 0);
                }
            });
        });

        container.addEventListener('mouseleave', () => {
            cards.forEach(({ card, result }) => {
                if (result) {
                    card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
                    card.style.boxShadow = 'none';
                    card.style.zIndex = '';
                }
            });
        });
    }

    if (results.length > 0) {
        setTimeout(() => {
            if (results.length === 1) {
                const cardInfo = cards[0];
                if (cardInfo) {
                    cardInfo.card.classList.remove('gray');
                    cardInfo.card.classList.add(`animate-star-${cardInfo.result.star}`);
                    setTimeout(() => {
                        cardInfo.cardContent.style.opacity = '1';
                        cardInfo.cardContent.style.transition = 'opacity 0.5s ease-in-out';
                    }, 300);
                }
            } else {
                const highestStarCards = cards.filter(c => c.result.star === maxStar);
                highestStarCards.forEach((c, i) => {
                    setTimeout(() => {
                        c.card.classList.remove('gray');
                        c.card.classList.add(`animate-star-${c.result.star}`);
                    }, i * 100);
                });

                cards.filter(c => c.result.star !== maxStar).forEach((c, i) => {
                    setTimeout(() => {
                        c.card.classList.remove('gray');
                        c.card.classList.add(`animate-star-${c.result.star}`);
                    }, highestStarCards.length * 100 + i * 100);
                });

                const cardsByRarity = {};
                cards.forEach((c, i) => {
                    const star = c.result.star;
                    if (!cardsByRarity[star]) cardsByRarity[star] = [];
                    cardsByRarity[star].push({ ...c, originalIndex: i });
                });

                const sortedCards = [];
                Object.keys(cardsByRarity).sort((a, b) => parseInt(a) - parseInt(b)).forEach(rarity => {
                    cardsByRarity[rarity].sort((a, b) => a.originalIndex - b.originalIndex);
                    sortedCards.push(...cardsByRarity[rarity]);
                });

                sortedCards.forEach((c, i) => {
                    setTimeout(() => {
                        c.cardContent.style.opacity = '1';
                        c.cardContent.style.transition = 'opacity 0.5s ease-in-out';
                    }, 500 + i * 100);
                });
            }
        }, 500);
    }

    if (window.innerWidth <= 768) {
        setTimeout(() => {
            const resultArea = document.querySelector('.result-area');
            if (resultArea) resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 1000);
    }
}

function clearResults() {
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    for (let i = 0; i < 10; i++) {
        const card = document.createElement('div');
        card.className = 'result-card empty';
        container.appendChild(card);
    }
}

async function updateCharsDetail(forceRefresh = false) {
    const container = document.getElementById('chars-detail-container');
    if (!container) return;

    if (!forceRefresh) {
        const cachedData = CacheUtil.get(CACHE_CONFIG.CHARS_DETAIL.key);
        if (cachedData) {
            renderCharsDetail(cachedData, container);
            return;
        }
    }

    try {
        const response = await fetch('/api/user_data');
        const data = await response.json();
        const chars = data.collection.chars;

        CacheUtil.set(CACHE_CONFIG.CHARS_DETAIL.key, chars, CACHE_CONFIG.CHARS_DETAIL.ttl);
        renderCharsDetail(chars, container);
    } catch (error) {
        console.error('加载干员详情失败:', error);
        container.innerHTML = '<div style="color:#aaa;text-align:center;padding:20px">加载失败</div>';
    }
}

function renderCharsDetail(chars, container) {
    if (Object.keys(chars).length === 0) {
        container.innerHTML = '<div style="color:#aaa;text-align:center;padding:20px">暂无干员数据</div>';
        return;
    }

    const charsByStar = {};
    Object.entries(chars).forEach(([name, info]) => {
        const star = info.star;
        if (!charsByStar[star]) charsByStar[star] = [];
        charsByStar[star].push({ name, info });
    });

    container.innerHTML = '';
    Object.keys(charsByStar).sort((a, b) => parseInt(b) - parseInt(a)).forEach(star => {
        const starSection = document.createElement('div');
        starSection.className = `star-section star-${star}`;
        starSection.innerHTML = `<h3>${star}星干员</h3>`;

        const charGrid = document.createElement('div');
        charGrid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:15px;padding:10px;margin-bottom:20px';

        charsByStar[star].sort((a, b) => a.name.localeCompare(b.name)).forEach(({ name, info }) => {
            const charCard = document.createElement('div');
            charCard.className = `char-card star-${info.star}`;
            charCard.innerHTML = `<div class="char-name">${name}</div><div class="char-potential">${Math.min(info.count, 5)}</div>`;
            charGrid.appendChild(charCard);
        });

        starSection.appendChild(charGrid);
        container.appendChild(starSection);
    });
}

async function updatePoolUI(poolType, forceRefresh = false) {
    clearResults();

    const uiConfig = {
        char: {
            single: 'Headhunt×1',
            ten: 'Headhunt×10',
            resultTitle: '寻访结果',
            statsTitle: '寻访统计',
            labels: ['累计寻访次数', '6 星保底计数', '5 星保底计数', 'UP 保底计数']
        },
        weapon: {
            single: 'Arsenal Issue×1',
            ten: null,
            resultTitle: '申领结果',
            statsTitle: '申领统计',
            labels: ['累计申领次数', '6 星保底计数', 'N/A', 'UP 保底计数']
        }
    };

    const config = uiConfig[poolType];

    document.getElementById('single-draw').textContent = config.single;
    document.getElementById('ten-draw').style.display = config.ten ? 'inline-block' : 'none';
    document.getElementById('ten-draw').style.visibility = config.ten ? 'visible' : 'hidden';
    document.getElementById('ten-draw').style.width = config.ten ? 'auto' : '0';
    document.getElementById('ten-draw').style.margin = config.ten ? '0 10px' : '0';
    document.getElementById('result-title').textContent = config.resultTitle;
    document.getElementById('stats-title').textContent = config.statsTitle;

    ['total-label', 'six-star-label', 'five-star-label', 'up-label'].forEach((id, i) => {
        document.getElementById(id).textContent = config.labels[i];
    });

    document.getElementById('single-draw').className = `draw-btn ${poolType === 'char' ? 'single-draw' : 'weapon-draw'}`;
    document.getElementById('ten-draw').className = 'draw-btn ten-draw';

    const cacheKey = `${CACHE_CONFIG.POOL_INFO.key}_${poolType}`;

    if (!forceRefresh) {
        const cachedData = CacheUtil.get(cacheKey);
        if (cachedData) {
            updatePoolInfoUI(cachedData, poolType);
            return;
        }
    }

    try {
        const response = await fetch(`/api/pool_info?pool_type=${poolType}`);
        const data = await response.json();

        if (data.error) {
            console.error('获取卡池信息失败:', data.error);
            return;
        }

        CacheUtil.set(cacheKey, data, CACHE_CONFIG.POOL_INFO.ttl);
        updatePoolInfoUI(data, poolType);
    } catch (error) {
        console.error('获取卡池信息失败:', error);
        const cachedData = CacheUtil.get(cacheKey);
        if (cachedData) updatePoolInfoUI(cachedData, poolType);
    }
}

function updatePoolInfoUI(data, poolType) {
    const prefix = poolType === 'char' ? '特许寻访 ' : '武库申领 ';
    document.getElementById('pool-name').textContent = prefix + data.pool_name;

    const boostedItems = document.getElementById('boosted-items');
    boostedItems.innerHTML = '';

    data.boosted_items.forEach(item => {
        const itemElement = document.createElement('span');
        itemElement.className = 'boosted-item';
        itemElement.textContent = item.type ? `${item.name} (${item.type})` : item.name;
        boostedItems.appendChild(itemElement);
    });
}

function removeAllTempAreas() {
    TEMP_AREAS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.remove();
    });
}

function resetAllButtons() {
    [...NAV_BUTTONS.POOL, ...NAV_BUTTONS.COLLECTION, ...NAV_BUTTONS.HISTORY, ...NAV_BUTTONS.RESOURCE].forEach(id => {
        document.getElementById(id)?.classList.remove('active');
    });
}

function setupEventListeners() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const navOverlay = document.getElementById('nav-overlay');
    const leftNav = document.querySelector('.left-nav');

    if (mobileMenuBtn && navOverlay && leftNav) {
        const toggleNav = (show) => {
            mobileMenuBtn.classList.toggle('active', show);
            leftNav.classList.toggle('active', show);
            navOverlay.classList.toggle('active', show);
            document.body.style.overflow = show ? 'hidden' : '';
        };

        mobileMenuBtn.addEventListener('click', () => {
            toggleNav(!leftNav.classList.contains('active'));
        });

        navOverlay.addEventListener('click', () => toggleNav(false));

        leftNav.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    setTimeout(() => toggleNav(false), 300);
                }
            });
        });
    }

    document.getElementById('char-pool-btn').addEventListener('click', async () => {
        currentPool = 'char';
        resetAllButtons();
        document.getElementById('char-pool-btn').classList.add('active');
        updatePoolUI('char');
        document.querySelector('.gacha-area').style.display = 'block';
        document.querySelector('.stats-area').style.display = 'block';
        removeAllTempAreas();
        await loadUserData();
        await updateRewards();
    });

    document.getElementById('weapon-pool-btn').addEventListener('click', async () => {
        currentPool = 'weapon';
        resetAllButtons();
        document.getElementById('weapon-pool-btn').classList.add('active');
        updatePoolUI('weapon');
        document.querySelector('.gacha-area').style.display = 'block';
        document.querySelector('.stats-area').style.display = 'block';
        removeAllTempAreas();
        await loadUserData();
        await updateRewards();
    });

    document.getElementById('single-draw').addEventListener('click', () => performGacha(1));
    document.getElementById('ten-draw').addEventListener('click', () => performGacha(10));
    document.getElementById('urgent-recruitment').addEventListener('click', () => performUrgentRecruitment());

    document.getElementById('chars-tab').addEventListener('click', async () => {
        clearResults();
        currentCollection = 'chars';
        resetAllButtons();
        document.getElementById('chars-tab').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const collectionArea = document.createElement('div');
        collectionArea.className = 'collection-area';
        collectionArea.id = 'temp-collection-area';
        collectionArea.innerHTML = '<h2>干员获取统计</h2><div id="collection-container" class="collection-container"></div>';
        document.querySelector('.content-area').appendChild(collectionArea);
        await loadUserData();
    });

    document.getElementById('chars-detail-tab').addEventListener('click', async () => {
        clearResults();
        resetAllButtons();
        document.getElementById('chars-detail-tab').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const charsDetailArea = document.createElement('div');
        charsDetailArea.className = 'collection-area';
        charsDetailArea.id = 'temp-collection-area';
        charsDetailArea.innerHTML = '<h2>干员详情</h2><div id="chars-detail-container" class="chars-detail-container"></div>';
        document.querySelector('.content-area').appendChild(charsDetailArea);
        await loadUserData();
        updateCharsDetail();
    });

    document.getElementById('weapons-tab').addEventListener('click', async () => {
        clearResults();
        currentCollection = 'weapons';
        resetAllButtons();
        document.getElementById('weapons-tab').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const collectionArea = document.createElement('div');
        collectionArea.className = 'collection-area';
        collectionArea.id = 'temp-collection-area';
        collectionArea.innerHTML = '<h2>贵重品库/武器</h2><div id="collection-container" class="collection-container"></div>';
        document.querySelector('.content-area').appendChild(collectionArea);
        await loadUserData();
    });

    document.getElementById('resources-tab').addEventListener('click', async () => {
        clearResults();
        resetAllButtons();
        document.getElementById('resources-tab').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const userData = await (await fetch('/api/user_data')).json();
        const firstRecharge = userData.resources.first_recharge || {};

        const rechargeTiers = [
            { amount: 6, first: '首充特惠：获得 6 个衍质源石', normal: '获得 3 个衍质源石' },
            { amount: 30, first: '首充双倍：获得 24 个衍质源石', normal: '获得 15 个衍质源石' },
            { amount: 98, first: '首充双倍：获得 84 个衍质源石', normal: '获得 50 个衍质源石' },
            { amount: 198, first: '首充双倍：获得 170 个衍质源石', normal: '获得 102 个衍质源石' },
            { amount: 328, first: '首充双倍：获得 282 个衍质源石', normal: '获得 171 个衍质源石' },
            { amount: 648, first: '首充双倍：获得 560 个衍质源石', normal: '获得 350 个衍质源石' }
        ];

        let rechargeButtons = '';
        rechargeTiers.forEach(tier => {
            const isFirst = firstRecharge[tier.amount.toString()] !== false;
            const text = isFirst ? tier.first : tier.normal;
            const rewardText = isFirst && text && text.includes(':') ? `首充${text.split(':')[1]}` : (text || '');
            const oroberylCount = text ? text.match(/(\d+) 个衍质源石/)?.[1] || text.match(/(\d+) 个嵌晶玉/)?.[1] || '' : '';
            rechargeButtons += `<button class="recharge-btn first-recharge" data-amount="${tier.amount}" data-reward="${rewardText}"><div class="button-content"><div class="oroberyl-count">${oroberylCount}</div><div class="first-reward">${rewardText}</div></div><div class="price-bar">¥${tier.amount}</div></button>`;
        });

        const resourcesArea = document.createElement('div');
        resourcesArea.className = 'resources-area';
        resourcesArea.id = 'temp-resources-area';
        resourcesArea.innerHTML = `
            <h2>资源管理</h2>
            <div class="resources-management">
                <div class="resource-card">
                    <h3>充值模拟 (不会产生消费)</h3>
                    <div class="recharge-options">${rechargeButtons}</div>
                </div>
                <div class="resource-card">
                    <h3>资源兑换</h3>
                    <div class="exchange-options">
                        <div class="exchange-item">
                            <input type="number" id="exchange-amount" min="1" value="1" style="width:60px;padding:5px;margin-right:10px;background:#333;color:white;border:1px solid #555;border-radius:4px">
                            <button id="exchange-origeometry-oroberyl" class="exchange-btn">衍质源石 → 嵌晶玉 (1:75)</button>
                            <button id="exchange-all-oroberyl" class="exchange-btn all-btn">ALL</button>
                        </div>
                        <div class="exchange-item">
                            <input type="number" id="exchange-amount-arsenal" min="1" value="1" style="width:60px;padding:5px;margin-right:10px;background:#333;color:white;border:1px solid #555;border-radius:4px">
                            <button id="exchange-origeometry-arsenal" class="exchange-btn">衍质源石 → 武库配额 (1:25)</button>
                            <button id="exchange-all-arsenal" class="exchange-btn all-btn">ALL</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.querySelector('.content-area').appendChild(resourcesArea);
        setupResourceManagementListeners();
        await loadUserData();
    });

    document.getElementById('clear-data-btn').addEventListener('click', async () => {
        if (confirm('确定要清空所有抽卡数据吗？此操作不可恢复。')) {
            await clearUserData();
        }
    });

    document.getElementById('char-history-btn').addEventListener('click', async () => {
        clearResults();
        resetAllButtons();
        document.getElementById('char-history-btn').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const historyArea = document.createElement('div');
        historyArea.className = 'history-area';
        historyArea.id = 'temp-history-area';
        historyArea.innerHTML = '<h2>寻访记录</h2><div id="char-history-container" class="history-container"></div>';
        document.querySelector('.content-area').appendChild(historyArea);
        await loadHistory('char');
    });

    document.getElementById('weapon-history-btn').addEventListener('click', async () => {
        clearResults();
        resetAllButtons();
        document.getElementById('weapon-history-btn').classList.add('active');
        document.querySelector('.gacha-area').style.display = 'none';
        document.querySelector('.stats-area').style.display = 'none';
        removeAllTempAreas();

        const historyArea = document.createElement('div');
        historyArea.className = 'history-area';
        historyArea.id = 'temp-history-area';
        historyArea.innerHTML = '<h2>申领记录</h2><div id="weapon-history-container" class="history-container"></div>';
        document.querySelector('.content-area').appendChild(historyArea);
        await loadHistory('weapon');
    });
}

async function clearUserData() {
    try {
        const response = await fetch('/api/clear_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.message) {
            alert(result.message);
            CacheUtil.clearDataCache();
            await loadUserData(true);
            await updateRewards(true);
            await loadHistory(currentPool, true);
            await updateCharsDetail(true);
        }
    } catch (error) {
        console.error('清空数据失败:', error);
        alert('清空数据失败，请重试');
    }
}

async function loadHistory(poolType, forceRefresh = false) {
    const cacheKey = `${CACHE_CONFIG.HISTORY.key}_${poolType}`;

    if (!forceRefresh) {
        const cachedData = CacheUtil.get(cacheKey);
        if (cachedData) {
            displayHistory(cachedData, poolType);
            return;
        }
    }

    try {
        const response = await fetch(`/api/history?pool_type=${poolType}`);
        const data = await response.json();
        const history = data.history || [];

        CacheUtil.set(cacheKey, history, CACHE_CONFIG.HISTORY.ttl);
        displayHistory(history, poolType);
    } catch (error) {
        console.error('加载历史记录失败:', error);
        const container = document.getElementById(
            poolType === 'char' ? 'char-history-container' : 'weapon-history-container'
        );
        if (container) {
            container.innerHTML = '<div style="color:#aaa;text-align:center;padding:20px">加载失败</div>';
        }
    }
}

function displayHistory(history, poolType) {
    const container = document.getElementById(
        poolType === 'char' ? 'char-history-container' : 'weapon-history-container'
    );
    if (!container) return;

    container.innerHTML = '';

    if (history.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.style.cssText = 'color:#aaa;text-align:center;padding:20px;font-size:16px';
        emptyMessage.textContent = poolType === 'char' ? '暂无寻访记录' : '暂无申领记录';
        container.appendChild(emptyMessage);
    } else {
        const reversedHistory = [...history].reverse();
        const groups = [];
        for (let i = 0; i < reversedHistory.length; i += 10) {
            groups.push(reversedHistory.slice(i, i + 10));
        }

        groups.forEach((group, groupIndex) => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'history-group';
            groupDiv.style.cssText = 'margin-bottom:20px;padding:15px;background:rgba(255,255,255,0.05);border-radius:8px;border:1px solid rgba(255,255,255,0.1)';

            const startNumber = reversedHistory.length - groupIndex * 10;
            const endNumber = Math.max(0, reversedHistory.length - (groupIndex + 1) * 10);

            const groupTitle = document.createElement('div');
            groupTitle.className = 'history-group-title';
            groupTitle.style.cssText = 'color:#aaa;font-size:14px;margin-bottom:10px';
            groupTitle.textContent = endNumber === startNumber - 1 ? `第 ${startNumber} 次` : `第 ${startNumber} ~ ${endNumber + 1} 次`;
            groupDiv.appendChild(groupTitle);

            const resultsDiv = document.createElement('div');
            resultsDiv.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px';

            group.forEach(item => {
                const resultCard = document.createElement('div');
                resultCard.className = `history-result-card star-${item.star}`;
                resultCard.style.cssText = `padding:10px 15px;background:${getStarBackground(item.star)};border-radius:4px;color:${getStarColor(item.star)};font-weight:bold;min-width:120px;text-align:center;border:2px solid ${getStarColor(item.star)}`;
                resultCard.textContent = item.name + (item.is_up_g || item.is_6_g || item.is_5_g ? ' *' : '');
                resultsDiv.appendChild(resultCard);
            });

            groupDiv.appendChild(resultsDiv);
            container.appendChild(groupDiv);
        });
    }
}

function getStarBackground(star) {
    return {
        6: 'rgba(231,76,60,0.2)',
        5: 'rgba(243,156,18,0.2)',
        4: 'rgba(155,89,182,0.2)',
        3: 'rgba(52,152,219,0.2)'
    }[star] || 'rgba(100,100,100,0.2)';
}

function getStarColor(star) {
    return {
        6: '#ff4444',
        5: '#f39c12',
        4: '#9b59b6',
        3: '#3498db'
    }[star] || '#999';
}

function setupResourceManagementListeners() {
    const handleRecharge = async (amount) => {
        try {
            const response = await fetch('/api/recharge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount })
            });

            const result = await response.json();
            if (result.message) {
                alert(result.message);
                CacheUtil.clearDataCache();
                await loadUserData(true);
                await updateRewards(true);
                await loadHistory(currentPool, true);
                await updateCharsDetail(true);
                document.getElementById('resources-tab').click();
            } else if (result.error) {
                alert('充值失败：' + result.error);
            }
        } catch (error) {
            console.error('充值失败:', error);
            alert('充值失败，请重试');
        }
    };

    const handleExchange = async (from, to, amount) => {
        try {
            const response = await fetch('/api/exchange', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ from, to, amount })
            });

            const result = await response.json();
            if (result.message) {
                alert(result.message);
                CacheUtil.clearDataCache();
                await loadUserData(true);
                await updateRewards(true);
                await loadHistory(currentPool, true);
                await updateCharsDetail(true);
            } else if (result.error) {
                alert('兑换失败：' + result.error);
            }
        } catch (error) {
            console.error('兑换失败:', error);
            alert('兑换失败，请重试');
        }
    };

    document.querySelectorAll('.recharge-btn').forEach(btn => {
        btn.addEventListener('click', () => handleRecharge(parseInt(btn.dataset.amount)));
    });

    const exchangeOroberylBtn = document.getElementById('exchange-origeometry-oroberyl');
    if (exchangeOroberylBtn) {
        exchangeOroberylBtn.addEventListener('click', () => {
            const amount = parseInt(document.getElementById('exchange-amount').value) || 1;
            handleExchange('origeometry', 'oroberyl', amount);
        });
    }

    const exchangeArsenalBtn = document.getElementById('exchange-origeometry-arsenal');
    if (exchangeArsenalBtn) {
        exchangeArsenalBtn.addEventListener('click', () => {
            const amount = parseInt(document.getElementById('exchange-amount-arsenal').value) || 1;
            handleExchange('origeometry', 'arsenal_tickets', amount);
        });
    }

    const exchangeAllOroberylBtn = document.getElementById('exchange-all-oroberyl');
    if (exchangeAllOroberylBtn) {
        exchangeAllOroberylBtn.addEventListener('click', async () => {
            const userData = await (await fetch('/api/user_data')).json();
            const amount = userData.resources.origeometry || 0;
            if (amount <= 0) {
                alert('没有可兑换的衍质源石');
                return;
            }
            handleExchange('origeometry', 'oroberyl', amount);
        });
    }

    const exchangeAllArsenalBtn = document.getElementById('exchange-all-arsenal');
    if (exchangeAllArsenalBtn) {
        exchangeAllArsenalBtn.addEventListener('click', async () => {
            const userData = await (await fetch('/api/user_data')).json();
            const amount = userData.resources.origeometry || 0;
            if (amount <= 0) {
                alert('没有可兑换的衍质源石');
                return;
            }
            handleExchange('origeometry', 'arsenal_tickets', amount);
        });
    }
}

function shouldUpdateRewards(totalCount) {
    return [30, 60].includes(totalCount) || (totalCount > 239 && (totalCount - 240) % 240 === 0);
}

window.addEventListener('DOMContentLoaded', initPage);