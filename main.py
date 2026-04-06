import os, time, httpx, asyncio
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

app = FastAPI(title="Supply Chain MVP v3")

# --- VERSION TRACKING ---
VERSION = "v3.0.0"
SERVICE_TYPE = os.getenv("SERVICE_TYPE", "ats") # default to ats

# --- SRE METRICS ---
REQ_COUNT = Counter("http_requests_total", "Total requests", ["service", "endpoint", "version"])
LATENCY = Histogram("request_latency_seconds", "Latency in seconds", ["service"])
INVENTORY = Gauge("inventory_stock_levels", "Current stock", ["item"])

# --- HEALTH CHECKS (Crucial for Kubernetes) ---
@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "version": VERSION, "service": SERVICE_TYPE}

# --- ATS SERVICE (Inventory) ---
@app.get("/inventory/{item}")
async def get_inventory(item: str):
    REQ_COUNT.labels(service="ats", endpoint="get_inventory", version=VERSION).inc()
    # Mock data logic
    val = 100 if item == "blender" else 25 
    INVENTORY.labels(item=item).set(val)
    return {"item": item, "stock": val, "version": VERSION}

# --- SOURCING SERVICE (Logic) ---
@app.get("/route")
async def get_route(item: str):
    start = time.time()
    REQ_COUNT.labels(service="sourcing", endpoint="get_route", version=VERSION).inc()
    
    # In K8s, we use the Service DNS name
    ats_url = os.getenv("ATS_URL", "http://localhost:8000")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ats_url}/inventory/{item}", timeout=2.0)
            stock = resp.json().get("stock", 0)
            decision = "Warehouse" if stock > 50 else "Store"
    except Exception as e:
        decision = "Error/Fallback-Manual"
    
    LATENCY.labels(service="sourcing").observe(time.time() - start)
    return {"item": item, "source": decision, "version": VERSION}

# --- TRANSPORT SERVICE ---
@app.post("/ship")
async def ship(item: str):
    REQ_COUNT.labels(service="transport", endpoint="ship", version=VERSION).inc()
    return {"status": "In Transit", "item": item, "version": VERSION}

# Prometheus scraping endpoint
app.mount("/metrics", make_asgi_app())
