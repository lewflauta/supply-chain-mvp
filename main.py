import os, time, httpx, asyncio
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

app = FastAPI()
SERVICE_TYPE = os.getenv("SERVICE_TYPE", "ats")

# --- SRE METRICS ---
REQ_COUNT = Counter("http_requests_total", "Total requests", ["service", "endpoint"])
LATENCY = Histogram("request_latency_seconds", "Latency in seconds", ["service"])
INVENTORY = Gauge("inventory_stock_levels", "Current stock", ["item"])

# --- ATS SERVICE ---
@app.get("/inventory/{item}")
async def get_inventory(item: str):
    REQ_COUNT.labels(service="ats", endpoint="get_inventory").inc()
    val = 50 if item == "blender" else 10
    INVENTORY.labels(item=item).set(val)
    return {"item": item, "stock": val}

# --- SOURCING SERVICE ---
@app.get("/route")
async def get_route(item: str):
    start = time.time()
    async with httpx.AsyncClient() as client:
        # Calls the ATS service via Docker DNS
        resp = await client.get("http://0.0.0.0:8000/inventory/" + item)
        stock = resp.json().get("stock", 0)
    
    decision = "Warehouse" if stock > 20 else "Store"
    LATENCY.labels(service="sourcing").observe(time.time() - start)
    return {"item": item, "source": decision, "status": "Optimized"}

# --- TRANSPORT SERVICE ---
@app.post("/ship")
async def ship():
    REQ_COUNT.labels(service="transport", endpoint="ship").inc()
    return {"status": "In Transit", "eta": "2 days"}

# Mount Prometheus metrics endpoint
app.mount("/metrics", make_asgi_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1",port=8000)
