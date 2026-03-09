(() => {
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

    // 移除抽卡后自动滚动效果
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

    // 暴露到全局
    window.showResults = showResults;
    window.performGacha = performGacha;
    window.performUrgentRecruitment = performUrgentRecruitment;
})();
