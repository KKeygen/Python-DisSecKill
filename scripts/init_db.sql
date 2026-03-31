-- 分布式秒杀系统数据库初始化脚本（含分库分表）
-- Database: disseckill + 2个订单分片库
-- 编码: UTF-8 / utf8mb4

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ===================== 主库：用户、商品、分类、库存 =====================
CREATE DATABASE IF NOT EXISTS disseckill
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- ===================== 订单分片库 =====================
CREATE DATABASE IF NOT EXISTS disseckill_order_0
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS disseckill_order_1
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE disseckill;

-- ===================== 用户表 =====================
CREATE TABLE IF NOT EXISTS df_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 商品分类表 =====================
CREATE TABLE IF NOT EXISTS df_goods_category (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 商品表 =====================
CREATE TABLE IF NOT EXISTS df_goods (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    `desc` TEXT DEFAULT NULL,
    price DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT '件',
    image VARCHAR(500) DEFAULT NULL,
    is_seckill BOOLEAN NOT NULL DEFAULT FALSE,
    seckill_price DECIMAL(10, 2) DEFAULT NULL,
    seckill_start DATETIME DEFAULT NULL,
    seckill_end DATETIME DEFAULT NULL,
    status SMALLINT NOT NULL DEFAULT 1 COMMENT '0:下架 1:上架',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES df_goods_category(id),
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    INDEX idx_seckill (is_seckill, seckill_start, seckill_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 库存表 =====================
CREATE TABLE IF NOT EXISTS df_inventory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    goods_id BIGINT NOT NULL UNIQUE,
    stock INT NOT NULL DEFAULT 0,
    locked_stock INT NOT NULL DEFAULT 0 COMMENT '已锁定待支付库存',
    version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (goods_id) REFERENCES df_goods(id),
    INDEX idx_goods (goods_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 订单表分片（2库×2表） =====================

-- 订单分片库0：用户ID为偶数
USE disseckill_order_0;

CREATE TABLE IF NOT EXISTS df_order_0 (
    id BIGINT PRIMARY KEY COMMENT '订单ID（雪花算法+基因法）',
    user_id BIGINT NOT NULL,
    goods_id BIGINT NOT NULL,
    count INT NOT NULL DEFAULT 1,
    total_price DECIMAL(10, 2) NOT NULL,
    pay_method SMALLINT NOT NULL DEFAULT 3 COMMENT '1:货到付款 2:微信 3:支付宝 4:银联',
    order_status SMALLINT NOT NULL DEFAULT 1 COMMENT '1:待支付 2:待发货 3:待收货 4:待评价 5:已完成 6:已取消',
    address VARCHAR(256) DEFAULT NULL,
    trade_no VARCHAR(64) DEFAULT NULL,
    is_seckill BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表分片0-0';

CREATE TABLE IF NOT EXISTS df_order_1 (
    id BIGINT PRIMARY KEY COMMENT '订单ID（雪花算法+基因法）',
    user_id BIGINT NOT NULL,
    goods_id BIGINT NOT NULL,
    count INT NOT NULL DEFAULT 1,
    total_price DECIMAL(10, 2) NOT NULL,
    pay_method SMALLINT NOT NULL DEFAULT 3 COMMENT '1:货到付款 2:微信 3:支付宝 4:银联',
    order_status SMALLINT NOT NULL DEFAULT 1 COMMENT '1:待支付 2:待发货 3:待收货 4:待评价 5:已完成 6:已取消',
    address VARCHAR(256) DEFAULT NULL,
    trade_no VARCHAR(64) DEFAULT NULL,
    is_seckill BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表分片0-1';

-- 订单分片库1：用户ID为奇数
USE disseckill_order_1;

CREATE TABLE IF NOT EXISTS df_order_0 (
    id BIGINT PRIMARY KEY COMMENT '订单ID（雪花算法+基因法）',
    user_id BIGINT NOT NULL,
    goods_id BIGINT NOT NULL,
    count INT NOT NULL DEFAULT 1,
    total_price DECIMAL(10, 2) NOT NULL,
    pay_method SMALLINT NOT NULL DEFAULT 3 COMMENT '1:货到付款 2:微信 3:支付宝 4:银联',
    order_status SMALLINT NOT NULL DEFAULT 1 COMMENT '1:待支付 2:待发货 3:待收货 4:待评价 5:已完成 6:已取消',
    address VARCHAR(256) DEFAULT NULL,
    trade_no VARCHAR(64) DEFAULT NULL,
    is_seckill BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表分片1-0';

CREATE TABLE IF NOT EXISTS df_order_1 (
    id BIGINT PRIMARY KEY COMMENT '订单ID（雪花算法+基因法）',
    user_id BIGINT NOT NULL,
    goods_id BIGINT NOT NULL,
    count INT NOT NULL DEFAULT 1,
    total_price DECIMAL(10, 2) NOT NULL,
    pay_method SMALLINT NOT NULL DEFAULT 3 COMMENT '1:货到付款 2:微信 3:支付宝 4:银联',
    order_status SMALLINT NOT NULL DEFAULT 1 COMMENT '1:待支付 2:待发货 3:待收货 4:待评价 5:已完成 6:已取消',
    address VARCHAR(256) DEFAULT NULL,
    trade_no VARCHAR(64) DEFAULT NULL,
    is_seckill BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表分片1-1';

-- 切回主库
USE disseckill;

-- ===================== 初始分类数据 =====================
INSERT INTO df_goods_category (name, description, sort_order) VALUES
    ('数码产品', '手机、电脑、平板等数码产品', 1),
    ('家用电器', '冰箱、洗衣机、空调等家电', 2),
    ('食品饮料', '零食、饮料、生鲜等食品', 3),
    ('服饰鞋包', '男装、女装、鞋靴、箱包', 4),
    ('日用百货', '日常生活用品', 5);

-- ===================== 示例商品数据 =====================

-- 分类1: 数码产品
INSERT INTO df_goods (category_id, name, `desc`, price, unit, image, is_seckill, seckill_price, seckill_start, seckill_end, status) VALUES
(1, '华为 Mate 60 Pro', '麒麟9000S芯片，卫星通信，超感知徕卡影像系统，12GB+512GB', 6999.00, '台', 'https://picsum.photos/seed/huawei-mate60/400/400', FALSE, NULL, NULL, NULL, 1),
(1, '小米14 Ultra 影像旗舰', '骁龙8 Gen3，徕卡光学Summilux镜头，1英寸索尼传感器', 5999.00, '台', 'https://picsum.photos/seed/xiaomi14ultra/400/400', TRUE, 4499.00, NOW(), DATE_ADD(NOW(), INTERVAL 48 HOUR), 1),
(1, 'Apple MacBook Pro 14英寸 M3 Pro', 'M3 Pro芯片，18GB统一内存，512GB SSD，Liquid Retina XDR', 14999.00, '台', 'https://picsum.photos/seed/macbookpro14/400/400', FALSE, NULL, NULL, NULL, 1),
(1, '索尼 WH-1000XM5 头戴降噪耳机', '行业领先降噪，30小时续航，LDAC高解析，多点连接', 2999.00, '副', 'https://picsum.photos/seed/sony-xm5/400/400', TRUE, 1899.00, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR), 1),
(1, 'Apple iPad Air 2024 M2', 'M2芯片，10.9英寸Liquid Retina，Apple Pencil支持', 4799.00, '台', 'https://picsum.photos/seed/ipad-air-m2/400/400', FALSE, NULL, NULL, NULL, 1),
(1, '联想拯救者 Y9000P 2024', '14代酷睿i9-14900HX，RTX4060，16GB DDR5，1TB SSD', 8999.00, '台', 'https://picsum.photos/seed/lenovo-y9000p/400/400', FALSE, NULL, NULL, NULL, 1),
(1, 'DJI Mini 4 Pro 航拍无人机', '4K/60fps HDR，全向避障，34分钟续航，O4图传', 4788.00, '台', 'https://picsum.photos/seed/dji-mini4pro/400/400', TRUE, 3888.00, NOW(), DATE_ADD(NOW(), INTERVAL 36 HOUR), 1),
(1, 'Apple Watch Ultra 2', 'S9芯片，双频精密GPS，100米防水，36小时续航', 5999.00, '块', 'https://picsum.photos/seed/apple-watch-ultra2/400/400', FALSE, NULL, NULL, NULL, 1),

-- 分类2: 家用电器
(2, '戴森 V15 Detect 无线吸尘器', '激光探测微尘，压电传感器实时计数，60分钟续航', 4490.00, '台', 'https://picsum.photos/seed/dyson-v15/400/400', TRUE, 3290.00, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR), 1),
(2, '美的 智能变频空调 1.5匹', '新一级能效，智能WiFi控制，强劲制冷制暖，超静音', 3299.00, '台', 'https://picsum.photos/seed/midea-aircon/400/400', FALSE, NULL, NULL, NULL, 1),
(2, '海尔 505L 十字对开门冰箱', '一级能效变频，干湿分储，智能WIFI操控', 4999.00, '台', 'https://picsum.photos/seed/haier-fridge/400/400', FALSE, NULL, NULL, NULL, 1),
(2, '松下 SD-PM1010 面包机', '自动投料，500g大容量，13小时预约，全自动和面烘烤', 1599.00, '台', 'https://picsum.photos/seed/panasonic-bread/400/400', FALSE, NULL, NULL, NULL, 1),
(2, '小米 净水器 1200G 厨下式', 'RO反渗透，3年长效滤芯，3.2L/min大流量', 2499.00, '台', 'https://picsum.photos/seed/xiaomi-water/400/400', TRUE, 1799.00, NOW(), DATE_ADD(NOW(), INTERVAL 48 HOUR), 1),
(2, '科沃斯 DEEBOT X2 OMNI 扫拖机器人', '方形设计不留死角，8000Pa大吸力，全能基站', 5999.00, '台', 'https://picsum.photos/seed/ecovacs-x2/400/400', FALSE, NULL, NULL, NULL, 1),

-- 分类3: 食品饮料
(3, '三只松鼠 坚果大礼包 1680g', '8袋装混合坚果，含夏威夷果/腰果/碧根果/核桃', 128.00, '箱', 'https://picsum.photos/seed/3squirrels-nuts/400/400', FALSE, NULL, NULL, NULL, 1),
(3, '农夫山泉 东方树叶 茉莉花茶 500ml×15', '0糖0脂0卡，原叶萃取，自然清香', 59.90, '箱', 'https://picsum.photos/seed/nfsq-tea/400/400', FALSE, NULL, NULL, NULL, 1),
(3, '瑞幸咖啡 椰云拿铁速溶 30杯', '真正椰浆，阿拉比卡咖啡豆，冷热双泡', 89.90, '盒', 'https://picsum.photos/seed/luckin-coffee/400/400', TRUE, 59.90, NOW(), DATE_ADD(NOW(), INTERVAL 12 HOUR), 1),
(3, '良品铺子 猪肉脯 500g', '靖江风味，蜜汁猪肉片，高蛋白低脂零食', 49.90, '袋', 'https://picsum.photos/seed/lppz-pork/400/400', FALSE, NULL, NULL, NULL, 1),
(3, '蒙牛特仑苏纯牛奶 250ml×24 整箱', '3.6g优质乳蛋白，源自专属牧场，营养好吸收', 79.90, '箱', 'https://picsum.photos/seed/mengniu-milk/400/400', FALSE, NULL, NULL, NULL, 1),

-- 分类4: 服饰鞋包
(4, 'Nike Air Force 1 经典空军一号', '经典白色AF1，头层牛皮鞋面，Air气垫缓震', 899.00, '双', 'https://picsum.photos/seed/nike-af1/400/400', TRUE, 599.00, NOW(), DATE_ADD(NOW(), INTERVAL 36 HOUR), 1),
(4, '优衣库 轻薄羽绒服 男款', '640蓬松度白鸭绒，轻便保暖，可收纳便携', 499.00, '件', 'https://picsum.photos/seed/uniqlo-down/400/400', FALSE, NULL, NULL, NULL, 1),
(4, '新秀丽 ORFEO 系列拉杆箱 20寸', 'PC材质，TSA海关锁，万向飞机轮，登机箱', 1999.00, '个', 'https://picsum.photos/seed/samsonite-orfeo/400/400', FALSE, NULL, NULL, NULL, 1),
(4, '李宁 䨻科技跑鞋 飞电3 CHALLENGER', '全掌䨻科技中底，碳板支撑，专业竞速跑鞋', 1099.00, '双', 'https://picsum.photos/seed/lining-feidianchallenger/400/400', FALSE, NULL, NULL, NULL, 1),

-- 分类5: 日用百货
(5, '得力 A4 打印纸 70g 500张/包×5', '高白度多功能复印纸，不卡纸，办公必备', 89.00, '箱', 'https://picsum.photos/seed/deli-paper/400/400', FALSE, NULL, NULL, NULL, 1),
(5, '云南白药 牙膏 薄荷清爽 210g×3', '天然活性成分，减轻牙龈问题，持久清新口气', 69.90, '组', 'https://picsum.photos/seed/yunnanbaiyao/400/400', FALSE, NULL, NULL, NULL, 1),
(5, '南极人 全棉四件套 1.8m床', '100%新疆长绒棉，60支高密度，亲肤柔软不起球', 299.00, '套', 'https://picsum.photos/seed/nanjiren-bed/400/400', TRUE, 199.00, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR), 1),
(5, '飞利浦 电动牙刷 HX6856', 'Sonicare声波震动62000次/分，3种模式，14天续航', 599.00, '支', 'https://picsum.photos/seed/philips-tooth/400/400', FALSE, NULL, NULL, NULL, 1);

-- ===================== 库存数据 =====================
-- 为所有商品初始化库存，秒杀商品限量库存较少
INSERT INTO df_inventory (goods_id, stock, locked_stock, version) VALUES
(1, 500, 0, 0),   -- 华为 Mate 60 Pro
(2, 100, 0, 0),   -- 小米14 Ultra (秒杀)
(3, 200, 0, 0),   -- MacBook Pro 14
(4, 150, 0, 0),   -- 索尼 WH-1000XM5 (秒杀)
(5, 300, 0, 0),   -- iPad Air 2024
(6, 120, 0, 0),   -- 联想拯救者 Y9000P
(7, 80, 0, 0),    -- DJI Mini 4 Pro (秒杀)
(8, 60, 0, 0),    -- Apple Watch Ultra 2
(9, 100, 0, 0),   -- 戴森 V15 (秒杀)
(10, 400, 0, 0),  -- 美的空调
(11, 180, 0, 0),  -- 海尔冰箱
(12, 250, 0, 0),  -- 松下面包机
(13, 200, 0, 0),  -- 小米净水器 (秒杀)
(14, 90, 0, 0),   -- 科沃斯扫拖机器人
(15, 1000, 0, 0), -- 三只松鼠坚果
(16, 2000, 0, 0), -- 农夫山泉东方树叶
(17, 500, 0, 0),  -- 瑞幸咖啡 (秒杀)
(18, 800, 0, 0),  -- 良品铺子猪肉脯
(19, 1500, 0, 0), -- 蒙牛特仑苏
(20, 300, 0, 0),  -- Nike AF1 (秒杀)
(21, 600, 0, 0),  -- 优衣库羽绒服
(22, 150, 0, 0),  -- 新秀丽拉杆箱
(23, 400, 0, 0),  -- 李宁跑鞋
(24, 3000, 0, 0), -- 得力打印纸
(25, 1200, 0, 0), -- 云南白药牙膏
(26, 200, 0, 0),  -- 南极人四件套 (秒杀)
(27, 350, 0, 0);  -- 飞利浦电动牙刷

-- ===================== 秒杀幂等去重表（分布式） =====================
-- 幂等表存储在每个订单分片库中
USE disseckill_order_0;
CREATE TABLE IF NOT EXISTS df_seckill_processed (
    request_id VARCHAR(36) PRIMARY KEY COMMENT '幂等键(UUID)',
    order_id BIGINT NOT NULL COMMENT '订单ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 本地消息表（事务消息保障） =====================
-- 用于实现基于本地消息表的分布式事务
CREATE TABLE IF NOT EXISTS df_outbox (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL UNIQUE COMMENT '消息唯一ID',
    topic VARCHAR(100) NOT NULL COMMENT 'Kafka Topic',
    message_key VARCHAR(100) DEFAULT NULL COMMENT '消息Key（分区键）',
    payload TEXT NOT NULL COMMENT '消息体JSON',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待发送 1:已发送 2:发送失败',
    retry_count INT NOT NULL DEFAULT 0 COMMENT '重试次数',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_create (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='本地消息表-事务消息';

-- ===================== 支付记录表 =====================
CREATE TABLE IF NOT EXISTS df_payment_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL COMMENT '订单ID',
    trade_no VARCHAR(64) NOT NULL UNIQUE COMMENT '交易流水号',
    pay_method TINYINT NOT NULL COMMENT '支付方式: 1-支付宝 2-微信 3-余额',
    amount DECIMAL(10,2) NOT NULL COMMENT '支付金额',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待支付 1:支付成功 2:支付失败 3:已退款',
    callback_data TEXT DEFAULT NULL COMMENT '支付回调原始数据',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_trade (trade_no),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';

-- ===================== Saga事务补偿记录表 =====================
CREATE TABLE IF NOT EXISTS df_saga_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    saga_id VARCHAR(36) NOT NULL COMMENT 'Saga事务ID',
    step_name VARCHAR(50) NOT NULL COMMENT '步骤名称',
    step_order INT NOT NULL COMMENT '步骤顺序',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待执行 1:已执行 2:已补偿 3:补偿失败',
    request_data TEXT COMMENT '请求数据',
    response_data TEXT COMMENT '响应数据',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_saga (saga_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Saga事务日志表';

USE disseckill_order_1;
CREATE TABLE IF NOT EXISTS df_seckill_processed (
    request_id VARCHAR(36) PRIMARY KEY COMMENT '幂等键(UUID)',
    order_id BIGINT NOT NULL COMMENT '订单ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 本地消息表（分片库1）
CREATE TABLE IF NOT EXISTS df_outbox (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL UNIQUE COMMENT '消息唯一ID',
    topic VARCHAR(100) NOT NULL COMMENT 'Kafka Topic',
    message_key VARCHAR(100) DEFAULT NULL COMMENT '消息Key（分区键）',
    payload TEXT NOT NULL COMMENT '消息体JSON',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待发送 1:已发送 2:发送失败',
    retry_count INT NOT NULL DEFAULT 0 COMMENT '重试次数',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_create (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='本地消息表-事务消息';

-- 支付记录表（分片库1）
CREATE TABLE IF NOT EXISTS df_payment_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL COMMENT '订单ID',
    trade_no VARCHAR(64) NOT NULL UNIQUE COMMENT '交易流水号',
    pay_method TINYINT NOT NULL COMMENT '支付方式: 1-支付宝 2-微信 3-余额',
    amount DECIMAL(10,2) NOT NULL COMMENT '支付金额',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待支付 1:支付成功 2:支付失败 3:已退款',
    callback_data TEXT DEFAULT NULL COMMENT '支付回调原始数据',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_trade (trade_no),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';

-- Saga事务补偿记录表（分片库1）
CREATE TABLE IF NOT EXISTS df_saga_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    saga_id VARCHAR(36) NOT NULL COMMENT 'Saga事务ID',
    step_name VARCHAR(50) NOT NULL COMMENT '步骤名称',
    step_order INT NOT NULL COMMENT '步骤顺序',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:待执行 1:已执行 2:已补偿 3:补偿失败',
    request_data TEXT COMMENT '请求数据',
    response_data TEXT COMMENT '响应数据',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_saga (saga_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Saga事务日志表';
