"""Recommendations endpoints - list, detail, act on recommendations."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from sqlalchemy import case

from app.extensions import db
from app.models import Recommendation, RecommendationAction
from app.utils.decorators import role_required

recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('/', methods=['GET'])
@jwt_required()
def list_recommendations():
    shift_id = request.args.get('shift_id')
    if not shift_id:
        return jsonify({'error': 'Bad request', 'message': 'shift_id is required'}), 400

    query = Recommendation.query.filter_by(shift_id=shift_id)

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
    if not data or not data.get('response_type'):
        return jsonify({'error': 'Bad request', 'message': 'response_type is required'}), 400

    if data['response_type'] not in ('accepted', 'deferred', 'rejected'):
        return jsonify({'error': 'Bad request', 'message': 'response_type must be accepted, deferred, or rejected'}), 400

    user_id = get_jwt_identity()

    action = RecommendationAction(
        recommendation_id=recommendation_id,
        user_id=user_id,
        response_type=data['response_type'],
        notes=data.get('notes'),
    )

    if data['response_type'] == 'rejected':
        rec.is_active = False

    db.session.add(action)
    db.session.commit()

    return jsonify({'action': action.to_dict()}), 201
