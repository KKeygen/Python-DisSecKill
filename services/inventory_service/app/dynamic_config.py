from app.nacos_support import InventoryDynamicConfig


_config = InventoryDynamicConfig()


def get_dynamic_config() -> InventoryDynamicConfig:
    return _config


def set_dynamic_config(new_config: InventoryDynamicConfig):
    global _config
    _config = new_config
