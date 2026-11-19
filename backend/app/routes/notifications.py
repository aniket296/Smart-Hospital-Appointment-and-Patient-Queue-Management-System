"""Notification logs routes: GET /api/notifications."""

from flask import Blueprint, g, jsonify, request
from backend.app.models import NotificationLog
from backend.app.utils.auth import auth_required

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
@auth_required
def get_notifications():
    """
    Paginated notification logs.
    Admin sees all notifications.
    Patients see only notifications tied to their user_id or patient_id.
    Doctors see only notifications tied to their user_id or their patient queue.
    """
    user = g.current_user
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    query = NotificationLog.query

    if user.role == "PATIENT":
        patient_id = user.patient_profile.id if user.patient_profile else -1
        query = query.filter(
            (NotificationLog.user_id == user.id) | (NotificationLog.patient_id == patient_id)
        )
    elif user.role == "DOCTOR":
        query = query.filter(NotificationLog.user_id == user.id)

    pagination = query.order_by(NotificationLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "notifications": [n.to_dict() for n in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        }
    ), 200
