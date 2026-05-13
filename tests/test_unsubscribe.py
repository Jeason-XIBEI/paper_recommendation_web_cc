"""
邮件退订流程测试
覆盖：创建订阅 → 管理页 → 暂停/恢复 → 退订 → 验证
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from app import create_app
from app.models import db, Subscription


class TestUnsubscribeFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.app.config['TESTING'] = True
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

        # 预先创建一个测试订阅
        sub = Subscription(
            email='test_unsub@example.com',
            keywords='traffic flow prediction',
            username='Test User',
            days_back=30,
            frequency='weekly'
        )
        db.session.add(sub)
        db.session.commit()
        cls.token = sub.unsubscribe_token
        cls.sub_id = sub.id
        print(f"\n  测试订阅创建完成，token: {cls.token}")

    @classmethod
    def tearDownClass(cls):
        db.session.rollback()
        db.drop_all()
        cls.ctx.pop()

    # ---- 页面加载 ----

    def test_manage_page_loads(self):
        """GET /manage/<token> 应返回 200 并显示订阅信息"""
        resp = self.client.get(f'/manage/{self.token}')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('traffic flow prediction', html)
        self.assertIn('test_unsub@example.com', html)

    def test_manage_page_invalid_token(self):
        """无效 token 应显示'无效链接'"""
        resp = self.client.get('/manage/00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('无效链接', resp.get_data(as_text=True))

    def test_unsubscribe_page_loads(self):
        """GET /unsubscribe/<token> 应返回 200"""
        resp = self.client.get(f'/unsubscribe/{self.token}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('traffic flow prediction', resp.get_data(as_text=True))

    def test_unsubscribe_page_invalid_token(self):
        """无效 token 应显示'无效链接'"""
        resp = self.client.get('/unsubscribe/00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('无效链接', resp.get_data(as_text=True))

    # ---- API ----

    def test_subscribe_api_returns_urls(self):
        """订阅 API 返回 manage_url 和 unsubscribe_url"""
        resp = self.client.post('/api/subscribe', json={
            'email': 'another@example.com',
            'keywords': 'GNN graph neural network',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('/manage/', data['manage_url'])
        self.assertIn('/unsubscribe/', data['unsubscribe_url'])

    def test_manage_api_returns_detail(self):
        """GET /api/manage/<token> 返回订阅详情"""
        resp = self.client.get(f'/api/manage/{self.token}')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['keywords'], 'traffic flow prediction')
        self.assertTrue(data['is_active'])

    def test_manage_api_invalid_token(self):
        """无效 token 的 API 返回 404"""
        resp = self.client.get('/api/manage/00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, 404)

    def test_toggle_pause_and_resume(self):
        """暂停后 is_active=False，恢复后 is_active=True"""
        # 确保当前是活跃状态
        sub = db.session.get(Subscription, self.sub_id)
        sub.is_active = True
        db.session.commit()

        # 暂停
        resp = self.client.post(f'/api/manage/{self.token}/toggle')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['is_active'])
        self.assertIn('暂停', data['message'])

        # 恢复
        resp = self.client.post(f'/api/manage/{self.token}/toggle')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['is_active'])
        self.assertIn('恢复', data['message'])

    def test_unsubscribe_deactivates(self):
        """POST /api/unsubscribe/<token> 将 is_active 设为 False"""
        # 确保订阅是活跃的
        sub = db.session.get(Subscription, self.sub_id)
        sub.is_active = True
        db.session.commit()

        resp = self.client.post(f'/api/unsubscribe/{self.token}')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('退订成功', data['message'])

        # 数据库验证
        sub = db.session.get(Subscription, self.sub_id)
        self.assertFalse(sub.is_active)

    def test_repeat_unsubscribe_is_idempotent(self):
        """重复退订不报错"""
        resp = self.client.post(f'/api/unsubscribe/{self.token}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('退订成功', resp.get_json()['message'])

    def test_unsubscribe_api_invalid_token(self):
        """无效 token 退订返回 404"""
        resp = self.client.post('/api/unsubscribe/00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, 404)

    def test_subscriptions_api_requires_email(self):
        """无 email 参数返回 400，有 email 返回 200"""
        resp = self.client.get('/api/subscriptions')
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get('/api/subscriptions?email=test_unsub@example.com')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(s['email'] == 'test_unsub@example.com' for s in data))


if __name__ == '__main__':
    unittest.main(verbosity=2)
