"""Daily reports routes: GET /api/reports/daily and GET /api/reports/daily/export."""

from flask import Blueprint, Response, jsonify, request
from backend.app.services.report_service import (
    export_daily_appointments_csv,
    generate_daily_report,
)
from backend.app.utils.auth import roles_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports/daily", methods=["GET"])
@roles_required("ADMIN")
def get_daily_report():
    """Admin-only daily reports summary endpoint."""
    date_str = request.args.get("date")
    report = generate_daily_report(date_str)
    return jsonify(report), 200


@reports_bp.route("/reports/daily/export", methods=["GET"])
@roles_required("ADMIN")
def get_daily_export():
    """Admin-only CSV export of daily appointments."""
    date_str = request.args.get("date")
    csv_data = export_daily_appointments_csv(date_str)
    filename = f"daily_appointments_{date_str or 'today'}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
