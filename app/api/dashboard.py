"""Dashboard endpoints - current state, metrics, trends, evaluation trigger."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.services.dashboard_service import DashboardService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_state():
    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))

    result = DashboardService.get_current_dashboard(restaurant_id)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 200


@dashboard_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_metrics():
    shift_id = request.args.get('shift_id')
    if not shift_id:
        return jsonify({'error': 'Bad request', 'message': 'shift_id is required'}), 400

    minutes = request.args.get('minutes', 60, type=int)
    result = DashboardService.get_shift_metrics(shift_id, minutes)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 200


@dashboard_bp.route('/trends', methods=['GET'])
@jwt_required()
def get_trends():
    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))
    days = request.args.get('days', 7, type=int)

    result = DashboardService.get_trends(restaurant_id, days)
    return jsonify(result), 200


@dashboard_bp.route('/evaluate', methods=['POST'])
@jwt_required()
def evaluate():
    from app.models.shift import Shift
    from app.models.operational_snapshot import OperationalSnapshot
    from app.services.forecast_service import ForecastService
    from app.services.recommendation_engine import RecommendationEngine
    from app.services.alert_service import AlertService

    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))

    shift = (
        Shift.query
        .filter_by(restaurant_id=restaurant_id, status='active')
        .first()
    )
    if not shift:
        return jsonify({'error': 'Not found', 'message': 'No active shift for this restaurant'}), 404

    snapshot = (
        OperationalSnapshot.query
        .filter_by(shift_id=shift.shift_id)
        .order_by(OperationalSnapshot.captured_at.desc())
        .first()
    )
    if not snapshot:
        return jsonify({'error': 'Not found', 'message': 'No snapshots for this shift'}), 404

    forecast_result = ForecastService.forecast_demand(shift.shift_id)
    new_recs = RecommendationEngine.evaluate(shift.shift_id, snapshot.snapshot_id)
    new_alerts = AlertService.evaluate(shift.shift_id, snapshot.snapshot_id)

    return jsonify({
        'forecast': forecast_result,
        'new_recommendations': [r.to_dict() for r in new_recs],
        'new_alerts': [a.to_dict() for a in new_alerts],
    }), 200
