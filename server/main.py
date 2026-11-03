from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float
    stock_on_hand: int
    lead_time_days: int

class RestockItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float
    line_cost: float

class RestockRecommendations(BaseModel):
    budget: float
    items: List[RestockItem]
    total_cost: float
    remaining_budget: float

class RestockOrderItemRequest(BaseModel):
    sku: str
    quantity: int

class RestockOrderRequest(BaseModel):
    items: List[RestockOrderItemRequest]

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockItem]
    total_cost: float
    lead_time_days: int
    order_date: str
    expected_delivery: str
    status: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False
    purchase_order_id: Optional[str] = None

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    priority: str
    dueDate: str
    status: str

class CreateTaskRequest(BaseModel):
    title: str
    priority: str = "medium"
    dueDate: str

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

# Kept apart from `orders` (sales orders): restock orders are purchases and must not skew dashboard/report revenue.
restock_orders: List[dict] = []

# Higher weight = restocked first when the budget cannot cover everything
TREND_WEIGHT = {"increasing": 3, "stable": 2, "decreasing": 1}

def build_restock_item(forecast: dict, quantity: int) -> dict:
    return {
        "sku": forecast["item_sku"],
        "name": forecast["item_name"],
        "quantity": quantity,
        "unit_cost": forecast["unit_cost"],
        "line_cost": round(quantity * forecast["unit_cost"], 2),
    }

@app.get("/api/restock/recommendations", response_model=RestockRecommendations)
def get_restock_recommendations(budget: float):
    """Recommend items to restock within budget, ranked by shortfall x trend weight"""
    if budget < 0:
        raise HTTPException(status_code=400, detail="Budget must not be negative")

    short = [(f, f["forecasted_demand"] - f["stock_on_hand"]) for f in demand_forecasts]
    short = [(f, gap) for f, gap in short if gap > 0]
    short.sort(key=lambda fg: fg[1] * TREND_WEIGHT.get(fg[0]["trend"], 1), reverse=True)

    remaining = budget
    items = []
    for forecast, gap in short:
        # Greedy: buy the full shortfall if affordable, else a partial quantity, else skip.
        # shortcut: greedy fill is not an optimal fit, upgrade to knapsack if budgets get tight.
        # Integer cents: float floor division drops a unit on exact fits (64 // 6.4 == 9.0)
        quantity = min(gap, round(remaining * 100) // round(forecast["unit_cost"] * 100))
        if quantity <= 0:
            continue
        item = build_restock_item(forecast, quantity)
        items.append(item)
        remaining -= item["line_cost"]

    total = round(budget - remaining, 2)
    return {"budget": budget, "items": items, "total_cost": total, "remaining_budget": round(remaining, 2)}

@app.post("/api/restock-orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: RestockOrderRequest):
    """Submit a restocking order. Lead time is the longest item lead time."""
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    by_sku = {f["item_sku"]: f for f in demand_forecasts}
    items = []
    lead_time = 0
    for line in request.items:
        forecast = by_sku.get(line.sku)
        if forecast is None:
            raise HTTPException(status_code=400, detail=f"Unknown SKU {line.sku}")
        if line.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity for {line.sku} must be positive")
        items.append(build_restock_item(forecast, line.quantity))
        lead_time = max(lead_time, forecast["lead_time_days"])

    today = date.today()
    number = len(restock_orders) + 1
    order = {
        "id": f"R{number}",
        "order_number": f"RST-{today.year}-{number:04d}",
        "items": items,
        "total_cost": round(sum(i["line_cost"] for i in items), 2),
        "lead_time_days": lead_time,
        "order_date": today.isoformat(),
        "expected_delivery": (today + timedelta(days=lead_time)).isoformat(),
        "status": "Submitted",
    }
    restock_orders.append(order)
    return order

@app.get("/api/restock-orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get submitted restocking orders, newest first"""
    return list(reversed(restock_orders))

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        # The dashboard keys its "View PO" button on purchase_order_id, so it survives a page reload
        item_dict["purchase_order_id"] = next(
            (po["id"] for po in purchase_orders if po["backlog_item_id"] == item["id"]), None
        )
        result.append(item_dict)
    return result

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create a purchase order for a backlog item (one PO per item)"""
    if not any(b["id"] == request.backlog_item_id for b in backlog_items):
        raise HTTPException(status_code=404, detail="Backlog item not found")
    if any(po["backlog_item_id"] == request.backlog_item_id for po in purchase_orders):
        raise HTTPException(status_code=409, detail="Backlog item already has a purchase order")
    if request.quantity <= 0 or request.unit_cost <= 0:
        raise HTTPException(status_code=400, detail="Quantity and unit cost must be positive")
    try:
        date.fromisoformat(request.expected_delivery_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="expected_delivery_date must be YYYY-MM-DD")

    po = {
        "id": f"PO-{len(purchase_orders) + 1:04d}",
        **request.model_dump(),
        "status": "Submitted",
        "created_date": date.today().isoformat(),
    }
    purchase_orders.append(po)
    return po

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order(backlog_item_id: str):
    """Get the purchase order for a backlog item"""
    for po in purchase_orders:
        if po["backlog_item_id"] == backlog_item_id:
            return po
    raise HTTPException(status_code=404, detail="Purchase order not found")

# User tasks, in memory. Ids start at 1000 so they never collide with the client-side mock task ids,
# which App.vue tells apart from API tasks by id alone.
tasks: List[dict] = []
next_task_id = 1000

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get user tasks, newest first"""
    return list(reversed(tasks))

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(request: CreateTaskRequest):
    global next_task_id
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    task = {"id": next_task_id, **request.model_dump(), "status": "pending"}
    next_task_id += 1
    tasks.append(task)
    return task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            del tasks[i]
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: int):
    """Flip a task between pending and completed"""
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "completed" if task["status"] == "pending" else "pending"
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
