import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from beanie import PydanticObjectId
from beanie.operators import RegEx
from app.models.transaction import Transaction, TransactionType
from app.repositories.base import BaseRepository
from app.schemas.transaction import TransactionFilterParams


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self):
        super().__init__(Transaction)

    async def get_by_id_and_user(
        self, transaction_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[Transaction]:
        return await Transaction.find_one(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )

    async def list_filtered(
        self, user_id: PydanticObjectId, params: TransactionFilterParams
    ) -> Tuple[List[Transaction], int, int]:
        query_dict: Dict[str, Any] = {"user_id": user_id}

        if params.type:
            query_dict["type"] = params.type

        if params.category_id:
            query_dict["category_id"] = PydanticObjectId(params.category_id)

        if params.account_id:
            query_dict["account_id"] = PydanticObjectId(params.account_id)

        if params.credit_card_id:
            query_dict["credit_card_id"] = PydanticObjectId(params.credit_card_id)

        # Date range filtering
        if params.start_date or params.end_date:
            date_query: Dict[str, Any] = {}
            if params.start_date:
                date_query["$gte"] = params.start_date
            if params.end_date:
                date_query["$lte"] = params.end_date
            query_dict["date"] = date_query

        # Amount range filtering
        if params.min_amount is not None or params.max_amount is not None:
            amount_query: Dict[str, Any] = {}
            if params.min_amount is not None:
                amount_query["$gte"] = params.min_amount
            if params.max_amount is not None:
                amount_query["$lte"] = params.max_amount
            query_dict["amount"] = amount_query

        # Search query (case-insensitive regex on title)
        if params.search:
            query_dict["$or"] = [
                {"title": {"$regex": params.search, "$options": "i"}},
                {"notes": {"$regex": params.search, "$options": "i"}},
            ]

        # Sorting
        sort_field = f"-{params.sort_by}" if params.sort_order == "desc" else f"+{params.sort_by}"

        skip = (params.page - 1) * params.limit

        cursor = Transaction.find(query_dict).sort(sort_field)
        total = await cursor.count()
        items = await cursor.skip(skip).limit(params.limit).to_list()
        total_pages = math.ceil(total / params.limit) if total > 0 else 0

        return items, total, total_pages

    async def get_recent(
        self, user_id: PydanticObjectId, limit: int = 10
    ) -> List[Transaction]:
        return (
            await Transaction.find(Transaction.user_id == user_id)
            .sort(-Transaction.date)
            .limit(limit)
            .to_list()
        )

    async def get_summary_totals(
        self,
        user_id: PydanticObjectId,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        match_stage: Dict[str, Any] = {"user_id": user_id}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["date"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$type",
                    "total": {"$sum": "$amount"},
                }
            },
        ]

        result = await Transaction.aggregate(pipeline).to_list()
        totals = {"income": 0.0, "expense": 0.0}
        for item in result:
            if item["_id"] in totals:
                totals[item["_id"]] = float(item["total"])
        return totals

    async def get_income_expense_time_series(
        self,
        user_id: PydanticObjectId,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        match_stage: Dict[str, Any] = {"user_id": user_id}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["date"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": {
                        "period": {
                            "$dateToString": {"format": "%Y-%m", "date": "$date"}
                        },
                        "type": "$type",
                    },
                    "total": {"$sum": "$amount"},
                }
            },
            {"$sort": {"_id.period": 1}},
        ]

        raw_results = await Transaction.aggregate(pipeline).to_list()
        
        # Merge by period
        periods_data: Dict[str, Dict[str, float]] = {}
        for r in raw_results:
            period = r["_id"]["period"]
            trans_type = r["_id"]["type"]
            amount = float(r["total"])
            if period not in periods_data:
                periods_data[period] = {"income": 0.0, "expense": 0.0}
            if trans_type in periods_data[period]:
                periods_data[period][trans_type] = amount

        chart_points = []
        for period in sorted(periods_data.keys()):
            inc = periods_data[period]["income"]
            exp = periods_data[period]["expense"]
            chart_points.append({
                "period": period,
                "income": round(inc, 2),
                "expense": round(exp, 2),
                "net": round(inc - exp, 2),
            })
        return chart_points

    async def get_category_breakdown(
        self,
        user_id: PydanticObjectId,
        trans_type: TransactionType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        match_stage: Dict[str, Any] = {
            "user_id": user_id,
            "type": trans_type.value,
        }
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["date"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$category_id",
                    "total": {"$sum": "$amount"},
                }
            },
            {"$sort": {"total": -1}},
        ]

        return await Transaction.aggregate(pipeline).to_list()


transaction_repo = TransactionRepository()
