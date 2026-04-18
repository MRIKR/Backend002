from pydantic import BaseModel
from typing import Optional


class SalesSummary(BaseModel):
    total_revenue: float
    order_count: int
    top_products: list
    period: str


class PredictionResponse(BaseModel):
    prediction: Optional[float]
    trend: Optional[str]
    months_analyzed: Optional[int]
    message: str
