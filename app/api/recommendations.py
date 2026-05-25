"""Recommendations endpoints - list, detail, act on recommendations."""
import json

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from sqlalchemy import case

from app.extensions import db
from app.models import Recommendation, RecommendationAction, Shift
from app.models.audit_log import AuditLog
from app.utils.decorators import role_required

recommendations_bp = Blueprint('recommendations', __name__)
recommendations_bp.strict_slashes = False


@recommendations_bp.route('/', methods=['GET'])
@jwt_required()
def list_recommendations():
    claims = get_jwt()
    shift_id = request.args.get('shift_id')

    # Auto-detect shift_id from JWT restaurant_id if not provided
    if not shift_id:
        restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))
        if not restaurant_id:
            return jsonify({'error': 'Bad request', 'message': 'shift_id or restaurant_id is required'}), 400
        shift = Shift.query.filter_by(
            restaurant_id=restaurant_id, status='active'
        ).first()
        if not shift:
            return jsonify({'recommendations': []}), 200
        shift_id = shift.shift_id

    query = Recommendation.query.filter_by(shift_id=shift_id)

    # Support 'status' param: pending, accepted, dismissed, expired
    status = request.args.get('status')
    if status:
        if status == 'pending':
            query = query.filter_by(is_active=True)
        elif status == 'accepted':
            # Active recommendations that have an 'accepted' action
            query = query.filter(
                Recommendation.is_active == True,  # noqa: E712
                Recommendation.actions.any(
                    RecommendationAction.response_type == 'accepted'
                )
            )
        elif status == 'deferred':
            # Recommendations that were deferred
            query = query.filter(
                Recommendation.is_active == False,  # noqa: E712
                Recommendation.actions.any(
                    RecommendationAction.response_type == 'deferred'
                )
            )
        elif status == 'dismissed':
            # Recommendations that were rejected
            query = query.filter(
                Recommendation.is_active == False,  # noqa: E712
                Recommendation.actions.any(
                    RecommendationAction.response_type == 'rejected'
                )
            )
        elif status == 'expired':
            query = query.filter(
                Recommendation.is_active == False,  # noqa: E712
            )
    else:
        # Legacy support: active_only param
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        if active_only:
            query = query.filter_by(is_active=True)

    rec_type = request.args.get('rec_type')
    if rec_type:
        query = query.filter_by(rec_type=rec_type)

    priority = request.args.get('priority')
    if priority:
        query = query.filter_by(priority=priority)

    priority_order = case(
        (Recommendation.priority == 'high', 1),
        (Recommendation.priority == 'medium', 2),
        (Recommendation.priority == 'low', 3),
        else_=4,
    )
    recs = query.order_by(priority_order, Recommendation.created_at.desc()).all()

    return jsonify({'recommendations': [r.to_dict() for r in recs]}), 200


@recommendations_bp.route('/<recommendation_id>', methods=['GET'])
@jwt_required()
def get_recommendation(recommendation_id):
    rec = db.session.get(Recommendation, recommendation_id)
    if not rec:
        return jsonify({'error': 'Not found', 'message': 'Recommendation not found'}), 404

    rec_dict = rec.to_dict()
    rec_dict['actions'] = [a.to_dict() for a in rec.actions.all()]

    return jsonify({'recommendation': rec_dict}), 200


@recommendations_bp.route('/<recommendation_id>/action', methods=['POST'])
@role_required('admin', 'manager')
def act_on_recommendation(recommendation_id):
    rec = db.session.get(Recommendation, recommendation_id)
    if not rec:
        return jsonify({'error': 'Not found', 'message': 'Recommendation not found'}), 404

    if not rec.is_active:
        return jsonify({'error': 'Bad request', 'message': 'Recommendation is no longer active'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    # Accept both 'response_type' and 'action_type' from frontend
    response_type = data.get('response_type') or data.get('action_type')
    if not response_type:
        return jsonify({'error': 'Bad request', 'message': 'response_type or action_type is required'}), 400

    # Accept 'dismissed' as alias for 'rejected'
    if response_type == 'dismissed':
        response_type = 'rejected'

    if response_type not in ('accepted', 'deferred', 'rejected'):
        return jsonify({'error': 'Bad request', 'message': 'response_type must be accepted, deferred, rejected, or dismissed'}), 400

    user_id = get_jwt_identity()

    action = RecommendationAction(
        recommendation_id=recommendation_id,
        user_id=user_id,
        response_type=response_type,
        notes=data.get('notes'),
    )

    if response_type in ('rejected', 'deferred'):
        rec.is_active = False
    elif response_type == 'accepted':
        rec.is_active = False

    db.session.add(action)
    db.session.commit()

    # Audit log: recommendation action
    audit_entry = AuditLog(
        user_id=user_id,
        action=f'recommendation_{response_type}',
        object_type='recommendation',
        object_id=recommendation_id,
        details=json.dumps({
            'title': rec.title,
            'response_type': response_type,
            'notes': data.get('notes'),
        }),
    )
    db.session.add(audit_entry)
    db.session.commit()

    return jsonify({
        'action': action.to_dict(),
        'recommendation': rec.to_dict(),
    }), 201
