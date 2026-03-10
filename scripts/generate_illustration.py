"""
使用 NanoBanana 生成秒杀系统架构插图
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from misc.edit import generate_image

# 生成系统架构插图
generate_image(
    prompt='''A professional, clean technical infographic illustration for a distributed flash-sale (seckill) e-commerce system architecture.

The illustration shows a layered architecture with:

TOP LAYER: Multiple user devices (phones, laptops) sending requests
SECOND LAYER: An Nginx gateway shield icon with "Rate Limiting" and "Load Balancing" labels, showing traffic being distributed
THIRD LAYER: Four microservice boxes arranged horizontally:
  - User Service (blue, person icon)
  - Goods Service (green, shopping bag icon)  
  - Order Service (orange, receipt icon)
  - Inventory Service (red, warehouse icon)
Each service box shows "x2 instances" label
BOTTOM LAYER: Three infrastructure components:
  - MySQL database cylinder (purple)
  - Redis cache (red lightning bolt icon)
  - RabbitMQ message queue (orange rabbit icon)

Arrows flow downward showing the request flow. A special highlighted path shows the "Flash Sale Flow": User → Nginx → Inventory Service → Redis (Lua atomic) → RabbitMQ → Order Consumer → MySQL

Style: Modern flat design, minimal, white background, soft shadows, consistent color palette (blues, greens, oranges), no text except labels, suitable for technical documentation. Professional enterprise architecture diagram aesthetic.''',
    out_file='docs/diagrams/system_overview.png'
)
