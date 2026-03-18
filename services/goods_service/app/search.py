from elasticsearch import AsyncElasticsearch
from app.config import get_settings
from app.schemas import GoodsResponse

settings = get_settings()

es_client_pool = None

async def get_es() -> AsyncElasticsearch:
    global es_client_pool
    if es_client_pool is None:
        es_client_pool = AsyncElasticsearch(settings.elasticsearch_url)
    return es_client_pool

async def init_es_index():
    es = await get_es()
    if not await es.indices.exists(index="goods"):
        await es.indices.create(
            index="goods",
            body={
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "text", "analyzer": "standard", "search_analyzer": "standard"},
                        "desc": {"type": "text", "analyzer": "standard", "search_analyzer": "standard"},
                        "price": {"type": "double"},
                        "image": {"type": "keyword"}
                    }
                }
            }
        )

async def sync_goods_to_es(goods: GoodsResponse):
    es = await get_es()
    await es.index(
        index="goods",
        id=str(goods.id),
        document={
            "id": goods.id,
            "name": goods.name,
            "desc": goods.desc,
            "price": float(goods.price),
            "image": goods.image or ""
        }
    )

async def search_goods_from_es(keyword: str, page: int = 1, size: int = 20):
    es = await get_es()
    body = {
        "query": {
            "multi_match": {
                "query": keyword,
                "fields": ["name", "desc"]
            }
        },
        "from": (page - 1) * size,
        "size": size
    }
    # ignore 404 for when index doesn't exist
    has_index = await es.indices.exists(index="goods")
    if not has_index: return [], 0
    
    res = await es.search(index="goods", body=body)
    hits = res["hits"]["hits"]
    total = res["hits"]["total"]["value"]
    
    docs = [hit["_source"] for hit in hits]
    return docs, total

