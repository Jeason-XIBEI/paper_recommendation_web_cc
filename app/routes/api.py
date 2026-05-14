"""API 路由"""

import json
import os
import logging
from flask import Blueprint, request, jsonify, send_file, Response

from app.models import db, SearchTask, Subscription
from app.sse import create_sse_endpoint
from app.tasks import executor, run_search_task

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


# ============ 搜索任务 ============
@api_bp.route('/api/search', methods=['POST'])
def api_search():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        keywords = data.get('keywords')
        if not keywords:
            return jsonify({'error': '请输入关键词'}), 400

        days_back = int(data.get('days_back', 30))
        email = data.get('email', '')
        task_name = data.get('task_name', f"搜索_{keywords[:20]}")
        temperature = float(data.get('temperature', 0.3))
        temperature = max(0.1, min(0.3, temperature))
        selected_journals = data.get('journals', [])

        task = SearchTask(
            task_name=task_name, keywords=keywords, days_back=days_back,
            email=email, temperature=temperature,
            selected_journals=','.join(selected_journals), status='pending'
        )
        db.session.add(task)
        db.session.commit()

        from flask import current_app
        executor.submit(run_search_task, current_app._get_current_object(), task.id, selected_journals)

        return jsonify({'task_id': task.id, 'status': 'pending'})
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/tasks')
def api_get_tasks():
    tasks = SearchTask.query.order_by(SearchTask.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': t.id, 'task_name': t.task_name,
        'keywords': t.keywords[:100] if t.keywords else '',
        'status': t.status, 'progress': t.progress, 'paper_count': t.paper_count,
        'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S') if t.created_at else '',
        'result_file': t.result_file,
        'selected_journals': t.selected_journals.split(',') if t.selected_journals else []
    } for t in tasks])


@api_bp.route('/api/task/<int:task_id>')
def api_task_status(task_id):
    task = db.session.get(SearchTask, task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify({
        'id': task.id, 'status': task.status,
        'progress': task.progress, 'paper_count': task.paper_count,
        'result_file': task.result_file
    })


@api_bp.route('/api/task/<int:task_id>/stream')
def api_task_stream(task_id):
    return create_sse_endpoint(task_id)


@api_bp.route('/api/result/<int:task_id>')
def api_get_result(task_id):
    task = db.session.get(SearchTask, task_id)
    if not task or not task.result_file or not os.path.exists(task.result_file):
        return jsonify([])
    with open(task.result_file, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))


@api_bp.route('/api/download/<int:task_id>')
def api_download(task_id):
    task = db.session.get(SearchTask, task_id)
    if not task or not task.result_file:
        return jsonify({'error': '文件不存在'}), 404
    return send_file(task.result_file, as_attachment=True, download_name=f'papers_task_{task_id}.json')


@api_bp.route('/api/export/<int:task_id>/<format>')
def api_export(task_id, format):
    from src.export_service import export_bibtex, export_csv, export_json

    task = db.session.get(SearchTask, task_id)
    if not task or not task.result_file:
        return jsonify({'error': '结果文件不存在'}), 404
    with open(task.result_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    if format == 'bibtex':
        content = export_bibtex(papers)
        filename = f'papers_task_{task_id}.bib'
        mime = 'text/plain; charset=utf-8'
    elif format == 'csv':
        content = export_csv(papers)
        filename = f'papers_task_{task_id}.csv'
        mime = 'text/csv; charset=utf-8-sig'
    else:
        content = export_json(papers)
        filename = f'papers_task_{task_id}.json'
        mime = 'application/json; charset=utf-8'

    return Response(content, mimetype=mime,
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


# ============ 订阅 ============
@api_bp.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    try:
        data = request.get_json()
        existing = Subscription.query.filter_by(
            email=data.get('email'), keywords=data.get('keywords'), is_active=True
        ).first()
        if existing:
            return jsonify({'message': '您已订阅过相同关键词'})

        sub = Subscription(
            username=data.get('username', '匿名'), email=data.get('email'),
            keywords=data.get('keywords'), days_back=int(data.get('days_back', 30)),
            frequency=data.get('frequency', 'weekly')
        )
        db.session.add(sub)
        db.session.commit()
        return jsonify({
            'message': '订阅成功！',
            'manage_url': f'/manage/{sub.unsubscribe_token}',
            'unsubscribe_url': f'/unsubscribe/{sub.unsubscribe_token}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/subscriptions')
def api_get_subscriptions():
    email = request.args.get('email', '')
    if not email:
        return jsonify({'error': '请提供邮箱地址'}), 400
    subs = Subscription.query.filter_by(email=email).all()
    return jsonify([{
        'id': s.id, 'username': s.username, 'email': s.email,
        'keywords': s.keywords[:100], 'frequency': s.frequency,
        'is_active': s.is_active,
        'last_run': s.last_run.strftime('%Y-%m-%d %H:%M:%S') if s.last_run else None,
        'created_at': s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'unsubscribe_url': f'/unsubscribe/{s.unsubscribe_token}',
        'manage_url': f'/manage/{s.unsubscribe_token}'
    } for s in subs])


@api_bp.route('/api/manage/<token>')
def api_manage_subscription(token):
    sub = Subscription.query.filter_by(unsubscribe_token=token).first()
    if not sub:
        return jsonify({'error': '订阅不存在'}), 404
    return jsonify({
        'id': sub.id, 'username': sub.username, 'email': sub.email,
        'keywords': sub.keywords, 'days_back': sub.days_back,
        'frequency': sub.frequency, 'is_active': sub.is_active,
        'last_run': sub.last_run.strftime('%Y-%m-%d %H:%M:%S') if sub.last_run else None,
        'created_at': sub.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    })


@api_bp.route('/api/manage/<token>/toggle', methods=['POST'])
def api_toggle_subscription(token):
    sub = Subscription.query.filter_by(unsubscribe_token=token).first()
    if not sub:
        return jsonify({'error': '订阅不存在'}), 404
    sub.is_active = not sub.is_active
    db.session.commit()
    return jsonify({
        'message': f'订阅已{"恢复" if sub.is_active else "暂停"}',
        'is_active': sub.is_active
    })


@api_bp.route('/api/unsubscribe/<token>', methods=['POST'])
def api_unsubscribe(token):
    sub = Subscription.query.filter_by(unsubscribe_token=token).first()
    if not sub:
        return jsonify({'error': '订阅不存在'}), 404
    sub.is_active = False
    db.session.commit()
    return jsonify({'message': '退订成功！您将不再收到此订阅的邮件推送。'})


# ============ 数据源 ============
@api_bp.route('/api/journals')
def api_get_journals():
    from config.settings import JOURNALS, ARXIV_CATEGORIES, CONFERENCES
    return jsonify({
        'journals': JOURNALS,
        'arxiv': ARXIV_CATEGORIES,
        'conferences': list(CONFERENCES.keys()),
    })
