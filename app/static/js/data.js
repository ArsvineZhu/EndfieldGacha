(() => {
    function shouldUpdateRewards(totalCount) {
        // 累计奖励每10抽更新一次
        return totalCount % 10 === 0;
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

    // 暴露到全局
    window.loadUserData = loadUserData;
    window.updateRewards = updateRewards;
    window.updateCharsDetail = updateCharsDetail;
    window.loadHistory = loadHistory;
    window.clearUserData = clearUserData;
})();
