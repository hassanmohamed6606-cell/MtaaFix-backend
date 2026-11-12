from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_
from app.extensions import db
from app.models import Report, User
from app.services.email_service import send_report_notification
from app.services.image_service import ImageServiceError, upload_image
from app.utils.validators import STATUSES, validate_report

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def request_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


@reports_bp.get("")
def list_reports():
    query = Report.query
    category = request.args.get("category")
    status = request.args.get("status")
    search = request.args.get("search", "").strip()
    if category and category != "All":
        query = query.filter_by(category=category)
    if status and status != "All":
        query = query.filter_by(status=status)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Report.title.ilike(term), Report.description.ilike(term), Report.location_name.ilike(term)))
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 50)
    result = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(reports=[item.to_dict() for item in result.items], pagination={
        "page": page, "per_page": per_page, "total": result.total, "pages": result.pages,
    })


@reports_bp.get("/<int:report_id>")
def get_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify(error="Report not found."), 404
    return jsonify(report=report.to_dict())


@reports_bp.post("")
@jwt_required()
def create_report():
    data = request_data()
    error = validate_report(data)
    if error:
        return jsonify(error=error), 400
    image_url = data.get("image_url") or None
    if request.files.get("image"):
        try:
            image_url = upload_image(request.files["image"])
        except ImageServiceError as exc:
            return jsonify(error=str(exc)), 503
    user = current_user()
    report = Report(
        title=data["title"].strip(), description=data["description"].strip(),
        category=data["category"], location_name=data["location_name"].strip(),
        latitude=float(data["latitude"]) if data.get("latitude") not in (None, "") else None,
        longitude=float(data["longitude"]) if data.get("longitude") not in (None, "") else None,
        image_url=image_url, user_id=user.id,
    )
    db.session.add(report)
    db.session.commit()
    send_report_notification(report, "created")
    return jsonify(report=report.to_dict()), 201


@reports_bp.put("/<int:report_id>")
@jwt_required()
def update_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify(error="Report not found."), 404
    user = current_user()
    if report.user_id != user.id and user.role != "admin":
        return jsonify(error="You can only edit your own reports."), 403
    data = request_data()
    error = validate_report(data, partial=True)
    if error:
        return jsonify(error=error), 400
    for field in ("title", "description", "category", "location_name"):
        if field in data:
            setattr(report, field, data[field].strip())
    for field in ("latitude", "longitude"):
        if field in data:
            setattr(report, field, float(data[field]) if data[field] not in (None, "") else None)
    if "image_url" in data:
        report.image_url = data["image_url"] or None
    if request.files.get("image"):
        try:
            report.image_url = upload_image(request.files["image"])
        except ImageServiceError as exc:
            return jsonify(error=str(exc)), 503
    db.session.commit()
    send_report_notification(report, "updated")
    return jsonify(report=report.to_dict())


@reports_bp.delete("/<int:report_id>")
@jwt_required()
def delete_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify(error="Report not found."), 404
    user = current_user()
    if report.user_id != user.id and user.role != "admin":
        return jsonify(error="You can only delete your own reports."), 403
    db.session.delete(report)
    db.session.commit()
    return jsonify(message="Report deleted.")


@reports_bp.patch("/<int:report_id>/status")
@jwt_required()
def update_status(report_id):
    user = current_user()
    if user.role != "admin":
        return jsonify(error="Administrator access is required."), 403
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify(error="Report not found."), 404
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUSES:
        return jsonify(error="Invalid status."), 400
    report.status = status
    db.session.commit()
    send_report_notification(report, "status updated")
    return jsonify(report=report.to_dict())


@reports_bp.get("/mine")
@jwt_required()
def my_reports():
    user = current_user()
    reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    return jsonify(reports=[item.to_dict() for item in reports])