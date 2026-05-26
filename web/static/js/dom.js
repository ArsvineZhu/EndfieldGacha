(() => {
    const NAV_BUTTONS = {
        POOL: ['char-pool-btn', 'weapon-pool-btn'],
        COLLECTION: ['chars-tab', 'chars-detail-tab', 'weapons-tab'],
        HISTORY: ['char-history-btn', 'weapon-history-btn'],
        RESOURCE: ['resources-tab']
    };

    const TEMP_AREAS = ['temp-collection-area', 'temp-resources-area', 'temp-history-area'];

    function createDOMStructure() {
        const root = document.getElementById('root');
        root.innerHTML = `
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
        // 直接挂载到全局window对象，确保其他模块可以访问
        window.gachaArea = document.querySelector('.gacha-area');
        window.statsArea = document.querySelector('.stats-area');
        window.contentArea = document.querySelector('.content-area');
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

    // 暴露到全局
    window.createDOMStructure = createDOMStructure;
    window.removeAllTempAreas = removeAllTempAreas;
    window.resetAllButtons = resetAllButtons;
})();
