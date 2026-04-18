from fastapi import APIRouter, HTTPException, Query
from app.services.supabase_client import get_supabase
import pandas as pd
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/sales-summary")
async def sales_summary(period: str = Query("month", enum=["week", "month", "quarter", "year"])):
    try:
        supabase = get_supabase()

        now = datetime.utcnow()
        delta_map = {"week": 7, "month": 30, "quarter": 90, "year": 365}
        cutoff = (now - timedelta(days=delta_map[period])).isoformat()

        orders_res = supabase.table("sales_orders").select("*").gte("created_at", cutoff).eq("status", "paid").execute()
        orders = orders_res.data or []

        if not orders:
            return {"total_revenue": 0, "order_count": 0, "top_products": [], "period": period}

        df = pd.DataFrame(orders)
        total_revenue = float(df["total_amount"].astype(float).sum())
        order_count = len(df)

        order_ids = df["id"].tolist()
        items_res = supabase.table("sales_order_items").select("product_id, quantity, subtotal").in_("sales_order_id", order_ids).execute()
        items = items_res.data or []

        top_products = []
        if items:
            idf = pd.DataFrame(items)
            top = idf.groupby("product_id").agg(
                total_qty=("quantity", "sum"),
                total_revenue=("subtotal", lambda x: float(x.astype(float).sum())),
            ).sort_values("total_revenue", ascending=False).head(5)

            prod_ids = top.index.tolist()
            prods_res = supabase.table("products").select("id, name").in_("id", prod_ids).execute()
            name_map = {p["id"]: p["name"] for p in (prods_res.data or [])}

            for pid, row in top.iterrows():
                top_products.append({
                    "product_id": pid,
                    "name": name_map.get(pid, "Unknown"),
                    "quantity_sold": int(row["total_qty"]),
                    "revenue": row["total_revenue"],
                })

        return {
            "total_revenue": total_revenue,
            "order_count": order_count,
            "top_products": top_products,
            "period": period,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict")
async def predict_sales():
    try:
        supabase = get_supabase()
        orders_res = supabase.table("sales_orders").select("created_at, total_amount").eq("status", "paid").order("created_at").execute()
        orders = orders_res.data or []

        if len(orders) < 2:
            return {"prediction": None, "message": "Not enough data for prediction"}

        df = pd.DataFrame(orders)
        df["total_amount"] = df["total_amount"].astype(float)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["month"] = df["created_at"].dt.to_period("M")

        monthly = df.groupby("month")["total_amount"].sum().reset_index()
        monthly.columns = ["month", "revenue"]

        monthly["idx"] = range(len(monthly))
        if len(monthly) >= 2:
            x = monthly["idx"]
            y = monthly["revenue"]
            slope = (len(x) * (x * y).sum() - x.sum() * y.sum()) / (len(x) * (x ** 2).sum() - x.sum() ** 2)
            intercept = (y.sum() - slope * x.sum()) / len(x)
            next_idx = len(monthly)
            predicted = max(0, intercept + slope * next_idx)
        else:
            predicted = float(monthly["revenue"].iloc[-1])

        return {
            "prediction": round(predicted),
            "trend": "up" if slope > 0 else "down" if slope < 0 else "flat",
            "months_analyzed": len(monthly),
            "message": f"Predicted next month revenue: Rp {round(predicted):,}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
