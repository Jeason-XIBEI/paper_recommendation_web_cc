"""页面路由"""

from flask import Blueprint, render_template
from app.models import Subscription

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/tasks')
def tasks():
    return render_template('tasks.html')


@main_bp.route('/subscribe')
def subscribe():
    return render_template('subscribe.html')


@main_bp.route('/unsubscribe/<token>')
def unsubscribe_page(token):
    sub = Subscription.query.filter_by(unsubscribe_token=token).first()
    return render_template('unsubscribe.html', sub=sub, token=token)


@main_bp.route('/manage/<token>')
def manage_page(token):
    sub = Subscription.query.filter_by(unsubscribe_token=token).first()
    return render_template('manage.html', sub=sub, token=token)
