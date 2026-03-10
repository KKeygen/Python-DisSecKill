-- 分布式秒杀系统数据库初始化脚本
-- Database: disseckill

CREATE DATABASE IF NOT EXISTS disseckill
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

-- ===================== 订单表 =====================
CREATE TABLE IF NOT EXISTS df_order (
    id VARCHAR(32) PRIMARY KEY COMMENT '订单号',
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
    -- 微服务架构下不使用跨服务FK，通过应用层保证引用完整性
    INDEX idx_user (user_id),
    INDEX idx_status (order_status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================== 初始分类数据 =====================
INSERT INTO df_goods_category (name, description, sort_order) VALUES
    ('数码产品', '手机、电脑、平板等数码产品', 1),
    ('家用电器', '冰箱、洗衣机、空调等家电', 2),
    ('食品饮料', '零食、饮料、生鲜等食品', 3),
    ('服饰鞋包', '男装、女装、鞋靴、箱包', 4),
    ('日用百货', '日常生活用品', 5);

-- ===================== 秒杀幂等去重表 =====================
CREATE TABLE IF NOT EXISTS df_seckill_processed (
    request_id VARCHAR(36) PRIMARY KEY COMMENT '幂等键(UUID)',
    order_id VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
