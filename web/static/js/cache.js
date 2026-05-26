(() => {
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

    // 暴露到全局
    window.CACHE_CONFIG = CACHE_CONFIG;
    window.CacheUtil = CacheUtil;
})();