(() => {
    // 全局共享变量，直接挂载到window，确保跨模块同步
    window.currentPool = 'char';
    window.currentCollection = 'chars';

    function formatNumber(num) {
        return typeof num === 'number' ? num.toLocaleString() : num;
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

        // 只有当按钮元素存在时才修改样式（非卡池页面这些元素会被移除）
        if (singleDrawBtn && tenDrawBtn && urgentRecruitmentBtn) {
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

        // 获取筛选条件
        let filteredItems = items;
        if (currentCollection === 'weapons') {
            const starFilter = document.getElementById('star-filter');
            const typeFilter = document.getElementById('type-filter');
            
            const selectedStar = starFilter ? starFilter.value : '';
            const selectedType = typeFilter ? typeFilter.value : '';
            
            filteredItems = {};
            Object.entries(items).forEach(([name, info]) => {
                const matchesStar = !selectedStar || info.star.toString() === selectedStar;
                const matchesType = !selectedType || info.type === selectedType;
                if (matchesStar && matchesType) {
                    filteredItems[name] = info;
                }
            });
        }

        if (Object.keys(filteredItems).length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.style.cssText = 'color:#aaa;text-align:center;padding:20px';
            emptyMessage.textContent = '暂无数据';
            container.appendChild(emptyMessage);
        } else {
            // 按星级分组
            const itemsByStar = {};
            Object.entries(filteredItems).forEach(([name, info]) => {
                const star = info.star;
                if (!itemsByStar[star]) itemsByStar[star] = [];
                itemsByStar[star].push({ name, info });
            });

            // 按星级降序排序并渲染
            Object.keys(itemsByStar)
                .sort((a, b) => parseInt(b) - parseInt(a))
                .forEach(star => {
                    // 创建星级section
                    const starSection = document.createElement('div');
                    starSection.className = `star-section star-${star}`;
                    
                    // 确定标题文本
                    const titleText = currentCollection === 'chars' 
                        ? `${star}星干员` 
                        : `${star}星武器`;
                    
                    starSection.innerHTML = `<h3>${titleText}</h3>`;

                    // 创建item容器
                    const itemContainer = document.createElement('div');
                    itemContainer.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;';

                    // 按名称升序排序并渲染item
                    itemsByStar[star]
                        .sort((a, b) => a.name.localeCompare(b.name))
                        .forEach(({ name, info }) => {
                            const item = document.createElement('div');
                            item.className = `collection-item star-${info.star}`;
                            // 显示武器类型（如果有）
                            const displayName = currentCollection === 'weapons' && info.type 
                                ? `${name} (${info.type})` 
                                : name;
                            item.innerHTML = `${displayName}<span class="count">${info.count}</span>`;
                            itemContainer.appendChild(item);

                            const countEl = item.querySelector('.count');
                            if (countEl) {
                                countEl.style.cssText = 'font-weight:bold;font-size:16px;padding:2px 8px;border-radius:10px;background-color:rgba(0,0,0,0.3);box-shadow:0 2px 4px rgba(0,0,0,0.3);transition:all 0.5s ease;transform:scale(1.2)';
                                setTimeout(() => { countEl.style.transform = 'scale(1)'; }, 300);
                            }
                        });

                    starSection.appendChild(itemContainer);
                    container.appendChild(starSection);
                });
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
            charGrid.className = 'char-grid';
            charGrid.style.cssText = 'display:grid;gap:25px;padding:10px;margin-bottom:20px';

            charsByStar[star].sort((a, b) => a.name.localeCompare(b.name)).forEach(({ name, info }) => {
                const charCard = document.createElement('div');
                charCard.className = `char-card star-${info.star}`;
                
                // 生成潜能显示的五个小长方形
                let potentialIndicators = '';
                const potential = Math.min(info.count, 5);
                for (let i = 0; i < 5; i++) {
                    const isActive = i < potential;
                    potentialIndicators += `<div class="potential-indicator ${isActive ? 'active' : ''}"></div>`;
                }
                
                charCard.innerHTML = `
                    <div class="char-name">${name}</div>
                    <div class="potential-bar">${potentialIndicators}</div>
                `;
                charGrid.appendChild(charCard);
            });

            starSection.appendChild(charGrid);
            container.appendChild(starSection);
        });
    }

    function updatePoolInfoUI(data, poolType) {
        const poolTypeLabel = poolType === 'char' ? '特许寻访' : '武库申领';
        document.getElementById('pool-name').textContent = `${poolTypeLabel} · ${data.pool_name}`;

        const boostedItems = document.getElementById('boosted-items');
        boostedItems.innerHTML = '';

        data.boosted_items.forEach(item => {
            const itemElement = document.createElement('span');
            itemElement.className = 'boosted-item';
            itemElement.textContent = item.type ? `${item.name} (${item.type})` : item.name;
            boostedItems.appendChild(itemElement);
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

    function displayHistory(history, poolType, operations = []) {
        const container = document.getElementById(
            poolType === 'char' ? 'char-history-container' : 'weapon-history-container'
        );
        if (!container) return;

        container.innerHTML = '';

        // 操作类型映射
        const operationTypeMap = {
            'GET_ONE': '单抽',
            'GET_TEN': '十连',
            'URGENT': '加急寻访',
            'ISSUE': '申领'
        };

        if (operations && operations.length > 0) {
            const reversedOperations = [...operations].reverse();
            
            // 将连续的单抽分组
            const groupedOperations = [];
            let currentSingleDrawGroup = null;
            
            reversedOperations.forEach((operation) => {
                if (operation.type === 'GET_ONE') {
                    // 如果是单抽
                    if (!currentSingleDrawGroup) {
                        currentSingleDrawGroup = {
                            type: 'SINGLE_GROUP',
                            operations: []
                        };
                        groupedOperations.push(currentSingleDrawGroup);
                    }
                    currentSingleDrawGroup.operations.push(operation);
                } else {
                    // 不是单抽，结束当前的单抽分组
                    currentSingleDrawGroup = null;
                    groupedOperations.push(operation);
                }
            });

            groupedOperations.forEach((groupOrOp, index) => {
                if (groupOrOp.type === 'SINGLE_GROUP') {
                    // 处理单抽分组
                    const singleDrawsContainer = document.createElement('div');
                    singleDrawsContainer.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;';
                    
                    groupOrOp.operations.forEach((operation) => {
                        const groupDiv = document.createElement('div');
                        groupDiv.className = 'history-group';
                        groupDiv.style.cssText = 'padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;border:1px solid rgba(255,255,255,0.1);flex:1;min-width:200px;max-width:300px;';

                        // 解析时间
                        const time = new Date(operation.time);
                        const timeStr = time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

                        // 构建标题
                        const operationName = operationTypeMap[operation.type] || operation.type;
                        const groupTitle = document.createElement('div');
                        groupTitle.className = 'history-group-title';
                        groupTitle.style.cssText = 'color:#aaa;font-size:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;';
                        groupTitle.innerHTML = `
                            <span>${operationName}</span>
                            <span>${timeStr}</span>
                        `;
                        groupDiv.appendChild(groupTitle);

                        const resultsDiv = document.createElement('div');
                        resultsDiv.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px';

                        operation.results.forEach(item => {
                            const resultCard = document.createElement('div');
                            resultCard.className = `history-result-card star-${item.star}`;
                            resultCard.style.cssText = `padding:6px 10px;background:${getStarBackground(item.star)};border-radius:4px;color:${getStarColor(item.star)};font-weight:bold;min-width:80px;text-align:center;border:2px solid ${getStarColor(item.star)};font-size:12px;`;
                            resultCard.textContent = item.name + (item.is_up_g || item.is_6_g || item.is_5_g ? ' *' : '');
                            resultsDiv.appendChild(resultCard);
                        });

                        groupDiv.appendChild(resultsDiv);
                        singleDrawsContainer.appendChild(groupDiv);
                    });
                    
                    container.appendChild(singleDrawsContainer);
                } else {
                    // 处理普通操作（非单抽）
                    const groupDiv = document.createElement('div');
                    groupDiv.className = `history-group ${groupOrOp.type === 'URGENT' ? 'urgent' : ''}`;
                    
                    // 加急寻访添加特殊边框效果
                    let borderStyle = '1px solid rgba(255,255,255,0.1)';
                    if (groupOrOp.type === 'URGENT') {
                        borderStyle = '2px solid #27ae60';
                    }
                    
                    groupDiv.style.cssText = `margin-bottom:20px;padding:15px;background:rgba(255,255,255,0.05);border-radius:8px;border:${borderStyle}`;

                    // 解析时间
                    const time = new Date(groupOrOp.time);
                    const timeStr = time.toLocaleString('zh-CN');

                    // 构建标题
                    const operationName = operationTypeMap[groupOrOp.type] || groupOrOp.type;
                    const groupTitle = document.createElement('div');
                    groupTitle.className = 'history-group-title';
                    groupTitle.style.cssText = 'color:#aaa;font-size:14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;';
                    
                    let titleContent = operationName;
                    if (groupOrOp.type === 'URGENT') {
                        titleContent = `<span style="color:#27ae60;font-weight:bold;">${operationName}</span>`;
                    }
                    
                    groupTitle.innerHTML = `
                        <span>${titleContent}</span>
                        <span style="font-size:12px;">${timeStr}</span>
                    `;
                    groupDiv.appendChild(groupTitle);

                    const resultsDiv = document.createElement('div');
                    resultsDiv.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px';

                    groupOrOp.results.forEach(item => {
                        const resultCard = document.createElement('div');
                        resultCard.className = `history-result-card star-${item.star}`;
                        resultCard.style.cssText = `padding:10px 15px;background:${getStarBackground(item.star)};border-radius:4px;color:${getStarColor(item.star)};font-weight:bold;min-width:120px;text-align:center;border:2px solid ${getStarColor(item.star)}`;
                        resultCard.textContent = item.name + (item.is_up_g || item.is_6_g || item.is_5_g ? ' *' : '');
                        resultsDiv.appendChild(resultCard);
                    });

                    groupDiv.appendChild(resultsDiv);
                    container.appendChild(groupDiv);
                }
            });
        } else {
            // 没有操作记录
            const emptyMessage = document.createElement('div');
            emptyMessage.style.cssText = 'color:#aaa;text-align:center;padding:20px;font-size:16px';
            emptyMessage.textContent = poolType === 'char' ? '暂无寻访记录' : '暂无申领记录';
            container.appendChild(emptyMessage);
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

    // 暴露到全局
    window.currentPool = currentPool;
    window.currentCollection = currentCollection;
    window.updateResources = updateResources;
    window.updateStats = updateStats;
    window.updateCollection = updateCollection;
    window.displayRewards = displayRewards;
    window.renderCharsDetail = renderCharsDetail;
    window.updatePoolInfoUI = updatePoolInfoUI;
    window.updatePoolUI = updatePoolUI;
    window.getStarBackground = getStarBackground;
    window.getStarColor = getStarColor;
    window.displayHistory = displayHistory;
    window.clearResults = clearResults;
})();
