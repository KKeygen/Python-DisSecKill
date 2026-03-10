/**
 * DisSecKill 秒杀系统前端脚本
 * 负责加载商品列表和系统状态
 */
(function () {
    'use strict';

    var API_BASE = '/api';

    // 加载商品列表
    function loadGoods() {
        fetch(API_BASE + '/goods/?page=1&size=20')
            .then(function (res) { return res.json(); })
            .then(function (data) {
                var container = document.getElementById('goods-list');
                if (!data.items || data.items.length === 0) {
                    container.innerHTML = '<div class="loading">暂无商品数据</div>';
                    return;
                }
                container.innerHTML = '';
                var seckillContainer = document.getElementById('seckill-list');
                var seckillItems = [];

                data.items.forEach(function (item) {
                    var card = createGoodsCard(item);
                    container.appendChild(card);
                    if (item.is_seckill) {
                        seckillItems.push(item);
                    }
                });

                // 填充秒杀专区
                if (seckillItems.length > 0) {
                    seckillContainer.innerHTML = '';
                    seckillItems.forEach(function (item) {
                        seckillContainer.appendChild(createSeckillCard(item));
                    });
                }

                // 更新统计
                document.getElementById('stat-goods').textContent = data.total || data.items.length;
            })
            .catch(function () {
                document.getElementById('goods-list').innerHTML =
                    '<div class="loading">服务暂不可用，请稍后刷新</div>';
            });
    }

    // 创建商品卡片
    function createGoodsCard(item) {
        var card = document.createElement('div');
        card.className = 'goods-card';
        card.innerHTML =
            '<div class="card-img">📦</div>' +
            '<div class="card-body">' +
            '  <div class="card-title">' + escapeHtml(item.name) + '</div>' +
            '  <div class="card-price">¥' + Number(item.price).toFixed(2) + '</div>' +
            '</div>';
        return card;
    }

    // 创建秒杀卡片
    function createSeckillCard(item) {
        var card = document.createElement('div');
        card.className = 'goods-card';
        card.innerHTML =
            '<div class="card-img">🔥</div>' +
            '<div class="card-body">' +
            '  <div class="card-title">' + escapeHtml(item.name) + '</div>' +
            '  <div class="card-price">¥' + Number(item.seckill_price || item.price).toFixed(2) +
            '    <span class="original">¥' + Number(item.price).toFixed(2) + '</span>' +
            '  </div>' +
            '  <button class="btn-seckill" data-id="' + item.id + '">立即抢购</button>' +
            '</div>';
        return card;
    }

    // HTML转义防XSS
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str || ''));
        return div.innerHTML;
    }

    // 健康检查
    function checkHealth() {
        fetch('/health')
            .then(function (res) { return res.json(); })
            .then(function (data) {
                console.log('网关状态:', data.status);
            })
            .catch(function () {
                console.warn('网关不可达');
            });
    }

    // 初始化
    document.addEventListener('DOMContentLoaded', function () {
        checkHealth();
        loadGoods();
    });
})();
