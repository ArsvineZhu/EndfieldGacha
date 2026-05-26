(() => {
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
                }
            } catch (error) {
                console.error('兑换失败:', error);
                alert('兑换失败，请重试');
            }
        };

        // 充值按钮事件
        document.querySelectorAll('.recharge-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const amount = parseInt(btn.dataset.amount);
                handleRecharge(amount);
            });
        });

        // 兑换按钮事件
        const exchangeOroberylBtn = document.getElementById('exchange-origeometry-oroberyl');
        const exchangeAllOroberylBtn = document.getElementById('exchange-all-oroberyl');
        const exchangeArsenalBtn = document.getElementById('exchange-origeometry-arsenal');
        const exchangeAllArsenalBtn = document.getElementById('exchange-all-arsenal');
        const exchangeAmountInput = document.getElementById('exchange-amount');
        const exchangeAmountArsenalInput = document.getElementById('exchange-amount-arsenal');

        if (exchangeOroberylBtn) {
            exchangeOroberylBtn.addEventListener('click', () => {
                const amount = parseInt(exchangeAmountInput.value) || 1;
                handleExchange('origeometry', 'oroberyl', amount);
            });
        }

        if (exchangeAllOroberylBtn) {
            exchangeAllOroberylBtn.addEventListener('click', async () => {
                try {
                    const response = await fetch('/api/user_data');
                    const data = await response.json();
                    const amount = data.resources.origeometry || 0;
                    if (amount > 0) {
                        handleExchange('origeometry', 'oroberyl', amount);
                    } else {
                        alert('没有可兑换的衍质源石');
                    }
                } catch (error) {
                    console.error('获取用户数据失败:', error);
                }
            });
        }

        if (exchangeArsenalBtn) {
            exchangeArsenalBtn.addEventListener('click', () => {
                const amount = parseInt(exchangeAmountArsenalInput.value) || 1;
                handleExchange('origeometry', 'arsenal_tickets', amount);
            });
        }

        if (exchangeAllArsenalBtn) {
            exchangeAllArsenalBtn.addEventListener('click', async () => {
                try {
                    const response = await fetch('/api/user_data');
                    const data = await response.json();
                    const amount = data.resources.origeometry || 0;
                    if (amount > 0) {
                        handleExchange('origeometry', 'arsenal_tickets', amount);
                    } else {
                        alert('没有可兑换的衍质源石');
                    }
                } catch (error) {
                    console.error('获取用户数据失败:', error);
                }
            });
        }
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
            // 清空内容区域并添加卡池相关元素
            contentArea.innerHTML = '';
            contentArea.appendChild(gachaArea);
            contentArea.appendChild(statsArea);
            gachaArea.style.display = 'block';
            statsArea.style.display = 'block';
            updatePoolUI('char');
            await loadUserData();
            await updateRewards();
        });

        document.getElementById('weapon-pool-btn').addEventListener('click', async () => {
            currentPool = 'weapon';
            resetAllButtons();
            document.getElementById('weapon-pool-btn').classList.add('active');
            // 清空内容区域并添加卡池相关元素
            contentArea.innerHTML = '';
            contentArea.appendChild(gachaArea);
            contentArea.appendChild(statsArea);
            gachaArea.style.display = 'block';
            statsArea.style.display = 'block';
            updatePoolUI('weapon');
            await loadUserData();
            await updateRewards();
        });

        document.getElementById('single-draw').addEventListener('click', () => performGacha(1));
        document.getElementById('ten-draw').addEventListener('click', () => performGacha(10));
        document.getElementById('urgent-recruitment').addEventListener('click', () => performUrgentRecruitment());

        document.getElementById('chars-tab').addEventListener('click', async () => {
            currentCollection = 'chars';
            resetAllButtons();
            document.getElementById('chars-tab').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

            const collectionArea = document.createElement('div');
            collectionArea.className = 'collection-area';
            collectionArea.id = 'temp-collection-area';
            collectionArea.innerHTML = '<h2>干员获取统计</h2><div id="collection-container" class="collection-container"></div>';
            contentArea.appendChild(collectionArea);
            await loadUserData();
        });

        document.getElementById('chars-detail-tab').addEventListener('click', async () => {
            resetAllButtons();
            document.getElementById('chars-detail-tab').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

            const charsDetailArea = document.createElement('div');
            charsDetailArea.className = 'collection-area';
            charsDetailArea.id = 'temp-collection-area';
            charsDetailArea.innerHTML = '<h2>干员详情</h2><div id="chars-detail-container" class="chars-detail-container"></div>';
            contentArea.appendChild(charsDetailArea);
            await loadUserData();
            updateCharsDetail();
        });

        document.getElementById('weapons-tab').addEventListener('click', async () => {
            currentCollection = 'weapons';
            resetAllButtons();
            document.getElementById('weapons-tab').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

            const collectionArea = document.createElement('div');
            collectionArea.className = 'collection-area';
            collectionArea.id = 'temp-collection-area';
            collectionArea.innerHTML = `
                <h2>贵重品库/武器</h2>
                <div class="filter-container" style="margin-bottom:20px;padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="display:flex;flex-wrap:wrap;gap:25px;align-items:center;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <label style="color:#e0e0e0;font-weight:500;min-width:60px;">稀有度:</label>
                            <select id="star-filter" style="padding:10px 16px;background:linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));color:#fff;border:2px solid rgba(255,255,255,0.2);border-radius:8px;cursor:pointer;transition:all 0.3s ease;font-size:14px;font-weight:500;min-width:100px;appearance:none;background-image:url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 12 12%22><path fill=%22%23fff%22 d=%22M6 8L1 3h10z%22/></svg>');background-repeat:no-repeat;background-position:right 12px center;padding-right:36px;">
                                <option value="" style="background:#333;color:#fff;">全部</option>
                                <option value="6" style="background:#333;color:#ff4444;">6星</option>
                                <option value="5" style="background:#333;color:#f39c12;">5星</option>
                                <option value="4" style="background:#333;color:#9b59b6;">4星</option>
                            </select>
                        </div>
                        <div style="display:flex;align-items:center;gap:12px;">
                            <label style="color:#e0e0e0;font-weight:500;min-width:60px;">类型:</label>
                            <select id="type-filter" style="padding:10px 16px;background:linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));color:#fff;border:2px solid rgba(255,255,255,0.2);border-radius:8px;cursor:pointer;transition:all 0.3s ease;font-size:14px;font-weight:500;min-width:120px;appearance:none;background-image:url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 12 12%22><path fill=%22%23fff%22 d=%22M6 8L1 3h10z%22/></svg>');background-repeat:no-repeat;background-position:right 12px center;padding-right:36px;">
                                <option value="" style="background:#333;color:#fff;">全部</option>
                                <option value="单手剑" style="background:#333;color:#fff;">单手剑</option>
                                <option value="施术单元" style="background:#333;color:#fff;">施术单元</option>
                                <option value="铳械" style="background:#333;color:#fff;">铳械</option>
                                <option value="双手剑" style="background:#333;color:#fff;">双手剑</option>
                                <option value="长柄武器" style="background:#333;color:#fff;">长柄武器</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div id="collection-container" class="collection-container"></div>
            `;
            contentArea.appendChild(collectionArea);
            
            // 添加筛选器事件监听
            const starFilter = document.getElementById('star-filter');
            const typeFilter = document.getElementById('type-filter');
            if (starFilter && typeFilter) {
                starFilter.addEventListener('change', () => loadUserData());
                typeFilter.addEventListener('change', () => loadUserData());
            }
            
            await loadUserData();
        });

        document.getElementById('resources-tab').addEventListener('click', async () => {
            resetAllButtons();
            document.getElementById('resources-tab').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

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
            contentArea.appendChild(resourcesArea);
            setupResourceManagementListeners();
            await loadUserData();
        });

        document.getElementById('clear-data-btn').addEventListener('click', async () => {
            if (confirm('确定要清空所有抽卡数据吗？此操作不可恢复。')) {
                await clearUserData();
            }
        });

        document.getElementById('char-history-btn').addEventListener('click', async () => {
            resetAllButtons();
            document.getElementById('char-history-btn').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

            const historyArea = document.createElement('div');
            historyArea.className = 'history-area';
            historyArea.id = 'temp-history-area';
            historyArea.innerHTML = '<h2>寻访记录</h2><div id="char-history-container" class="history-container"></div>';
            contentArea.appendChild(historyArea);
            await loadHistory('char');
        });

        document.getElementById('weapon-history-btn').addEventListener('click', async () => {
            resetAllButtons();
            document.getElementById('weapon-history-btn').classList.add('active');
            // 清空内容区域
            contentArea.innerHTML = '';

            const historyArea = document.createElement('div');
            historyArea.className = 'history-area';
            historyArea.id = 'temp-history-area';
            historyArea.innerHTML = '<h2>申领记录</h2><div id="weapon-history-container" class="history-container"></div>';
            contentArea.appendChild(historyArea);
            await loadHistory('weapon');
        });
    }

    // 暴露到全局
    window.setupEventListeners = setupEventListeners;
})();
