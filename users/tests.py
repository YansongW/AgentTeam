from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .utils import generate_token, verify_token
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache

User = get_user_model()

class UserRegistrationTests(TestCase):
    """用户注册API测试"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('users:register')
        self.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'password2': 'testpassword123',
        }
    
    def test_valid_registration(self):
        """测试有效的用户注册请求"""
        response = self.client.post(
            self.register_url, 
            self.valid_user_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')
        self.assertEqual(User.objects.get().email, 'test@example.com')
        self.assertFalse(User.objects.get().is_active)  # 用户应该处于未激活状态
    
    def test_invalid_registration_existing_username(self):
        """测试使用已存在的用户名注册"""
        User.objects.create_user(username='testuser', email='existing@example.com', password='password123')
        
        response = self.client.post(
            self.register_url, 
            self.valid_user_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data['error'])
    
    def test_invalid_registration_existing_email(self):
        """测试使用已存在的邮箱注册"""
        User.objects.create_user(username='existing', email='test@example.com', password='password123')
        
        response = self.client.post(
            self.register_url, 
            self.valid_user_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['error'])
    
    def test_invalid_registration_password_mismatch(self):
        """测试两次密码输入不匹配"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password2'] = 'differentpassword123'
        
        response = self.client.post(
            self.register_url, 
            invalid_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data['error'])
    
    def test_invalid_registration_weak_password(self):
        """测试弱密码注册"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = '123'
        invalid_data['password2'] = '123'
        
        response = self.client.post(
            self.register_url, 
            invalid_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error'])

class EmailVerificationTests(TestCase):
    """邮箱验证相关测试"""
    
    def setUp(self):
        # 创建一个未激活的测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            is_active=False
        )
        
        # 生成验证令牌并保存
        from users.utils import generate_token
        self.token = generate_token(self.user.email)
        
        # 验证URL
        self.verification_url = reverse('users:verify-email', args=[self.token])
        
        # 创建测试客户端
        self.client = APIClient()
    
    def test_valid_verification(self):
        """测试有效的邮箱验证"""
        # 保存token和email的对应关系到缓存，以便验证能通过
        cache_key = f'email_verification:{self.token}'
        cache.set(cache_key, self.user.email, 86400)
        
        response = self.client.get(self.verification_url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # 重新获取用户并检查是否已激活
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
    
    def test_invalid_token_verification(self):
        """测试无效令牌"""
        # 使用一个不存在的令牌
        invalid_url = reverse('users:verify-email', args=['invalid-token'])
        response = self.client.get(invalid_url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # 确保用户未被激活
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_already_verified(self):
        """测试已验证用户的再次验证"""
        # 先激活用户
        self.user.is_active = True
        self.user.save()
        
        # 保存token和email的对应关系到缓存，以便验证能通过
        cache_key = f'email_verification:{self.token}'
        cache.set(cache_key, self.user.email, 86400)
        
        # 尝试再次验证
        response = self.client.get(self.verification_url)
        
        # 验证返回"已激活"的消息
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('已经激活', response.data['message'])

class UserLoginTests(TestCase):
    """用户登录API测试"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('users:login')
        self.token_refresh_url = reverse('users:token_refresh')
        
        # 创建测试用户
        self.user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='password123',
            is_active=True
        )
        
        # 未激活用户
        self.inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='password123',
            is_active=False
        )
        
        # 重置缓存，清除任何锁定状态
        cache.clear()
    
    def test_valid_login_with_username(self):
        """测试使用用户名正确登录"""
        data = {
            'username': 'loginuser',
            'password': 'password123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_valid_login_with_email(self):
        """测试使用邮箱正确登录"""
        data = {
            'email': 'login@example.com',  # 使用邮箱
            'password': 'password123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        # 验证响应状态码
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证返回的令牌
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_invalid_login_wrong_password(self):
        """测试密码错误的登录请求"""
        data = {
            'username': 'loginuser',
            'password': 'wrongpassword123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_invalid_login_inactive_user(self):
        """测试未激活用户的登录请求"""
        # 尝试登录
        data = {
            'username': 'inactiveuser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # 修改匹配的错误消息
        self.assertIn('尚未激活', response.data['error'])
    
    def test_token_refresh(self):
        """测试令牌刷新功能"""
        # 先进行登录获取刷新令牌
        login_data = {
            'username': 'loginuser',
            'password': 'password123'
        }
        
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # 使用刷新令牌获取新的访问令牌
        refresh_data = {
            'refresh': refresh_token
        }
        
        response = self.client.post(self.token_refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_attempt_limit(self):
        """测试登录失败次数限制"""
        # 首先重置尝试次数
        self._reset_login_attempts()
        
        # 连续尝试错误登录5次
        for i in range(5):
            data = {
                'username': 'loginuser',
                'password': 'wrongpassword'
            }
            response = self.client.post(self.login_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # 第6次尝试应该被锁定 (现在期望429状态码)
        data = {
            'username': 'loginuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('尝试次数过多', response.data['error'])

    def _reset_login_attempts(self):
        # 重置登录尝试次数（清除缓存）
        cache.clear()

class PermissionsTests(TestCase):
    """权限控制功能测试"""
    
    def setUp(self):
        self.client = APIClient()
        
        # 创建普通用户
        self.user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            password='normalpassword123',
            is_active=True,
            role='user'
        )
        
        # 创建管理员用户
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword123',
            is_active=True,
            role='admin'
        )
        
        # 登录URL
        self.login_url = reverse('users:login')
        
        # 管理员功能URL
        self.user_management_url = reverse('users:user_management')
        self.login_attempts_url = reverse('users:login_attempts')
    
    def test_user_cannot_access_admin_features(self):
        """测试普通用户无法访问管理员功能"""
        # 普通用户登录
        login_data = {
            'username': 'normaluser',
            'password': 'normalpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 尝试访问用户管理功能
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 尝试访问登录尝试管理功能
        response = self.client.get(self.login_attempts_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_access_admin_features(self):
        """测试管理员用户可以访问管理员功能"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 访问用户管理功能
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 访问登录尝试管理功能
        response = self.client.get(self.login_attempts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_can_access_own_profile(self):
        """测试普通用户可以访问自己的个人资料"""
        # 普通用户登录
        login_data = {
            'username': 'normaluser',
            'password': 'normalpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 访问自己的个人资料
        profile_url = reverse('users:user_profile', args=[self.user.id])
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'normaluser')
    
    def test_user_cannot_access_others_profile(self):
        """测试普通用户不能访问其他用户的个人资料"""
        # 普通用户登录
        login_data = {
            'username': 'normaluser',
            'password': 'normalpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 尝试访问管理员的个人资料
        profile_url = reverse('users:user_profile', args=[self.admin.id])
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_access_any_profile(self):
        """测试管理员可以访问任何用户的个人资料"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 访问自己的个人资料
        own_profile_url = reverse('users:user_profile', args=[self.admin.id])
        response = self.client.get(own_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'adminuser')
        
        # 访问普通用户的个人资料
        other_profile_url = reverse('users:user_profile', args=[self.user.id])
        response = self.client.get(other_profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'normaluser')

class UserProfileTests(TestCase):
    """用户资料功能测试"""
    
    def setUp(self):
        self.client = APIClient()
        
        # 创建测试用户
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='profilepassword123',
            is_active=True
        )
        
        # 登录URL和资料URL
        self.login_url = reverse('users:login')
        self.profile_url = reverse('users:user_profile', args=[self.user.id])
        self.password_change_url = reverse('users:password_change')
        
        # 重置缓存
        cache.clear()
    
    def test_update_profile(self):
        """测试更新个人资料"""
        # 用户登录
        login_data = {
            'username': 'profileuser',
            'password': 'profilepassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 更新个人资料
        update_data = {
            'bio': '这是一段个人简介',
            'avatar': 'https://example.com/avatar.jpg'
        }
        response = self.client.patch(self.profile_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证资料已更新
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, '这是一段个人简介')
        self.assertEqual(self.user.avatar, 'https://example.com/avatar.jpg')
    
    def test_change_password(self):
        """测试修改密码"""
        # 用户登录
        login_data = {
            'username': 'profileuser',
            'password': 'profilepassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 修改密码
        password_data = {
            'current_password': 'profilepassword123',
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        }
        response = self.client.post(self.password_change_url, password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证密码已修改
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))
        
        # 使用新密码登录
        new_login_data = {
            'username': 'profileuser',
            'password': 'newpassword456'
        }
        new_login_response = self.client.post(self.login_url, new_login_data, format='json')
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)
        
    def test_change_password_with_wrong_current(self):
        """测试使用错误的当前密码修改密码"""
        # 用户登录
        login_data = {
            'username': 'profileuser',
            'password': 'profilepassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 使用错误的当前密码
        password_data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        }
        response = self.client.post(self.password_change_url, password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # 验证密码未修改
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('profilepassword123'))

    def tearDown(self):
        """清理测试环境"""
        cache.clear()
        super().tearDown()

class UserManagementTests(TestCase):
    """用户管理功能测试"""
    
    def setUp(self):
        self.client = APIClient()
        
        # 创建管理员用户
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword123',
            is_active=True,
            role='admin'
        )
        
        # 创建普通用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            is_active=True,
            role='user'
        )
        
        # URL
        self.login_url = reverse('users:login')
        self.user_management_url = reverse('users:user_management')
        
        # 重置缓存
        cache.clear()
    
    def test_list_users(self):
        """测试获取用户列表"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 获取用户列表
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # 管理员和测试用户
        
        # 验证返回的用户信息
        usernames = [user['username'] for user in response.data['results']]
        self.assertIn('adminuser', usernames)
        self.assertIn('testuser', usernames)
    
    def test_update_user_status(self):
        """测试更新用户状态"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 禁用用户
        update_data = {
            'user_id': self.user.id,
            'is_active': False
        }
        response = self.client.post(self.user_management_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证用户状态已更新
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        
        # 重新激活用户
        update_data = {
            'user_id': self.user.id,
            'is_active': True
        }
        response = self.client.post(self.user_management_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证用户状态已更新
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
    
    def test_update_user_role(self):
        """测试更新用户角色"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 将普通用户升级为管理员
        update_data = {
            'user_id': self.user.id,
            'role': 'admin'
        }
        response = self.client.put(self.user_management_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证用户角色已更新
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'admin')
        
        # 将用户恢复为普通用户
        update_data = {
            'user_id': self.user.id,
            'role': 'user'
        }
        response = self.client.put(self.user_management_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证用户角色已更新
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'user')
    
    def test_admin_cannot_deactivate_self(self):
        """测试管理员不能禁用自己的账户"""
        # 管理员登录
        login_data = {
            'username': 'adminuser',
            'password': 'adminpassword123'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # 获取访问令牌
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 尝试禁用自己的账户
        update_data = {
            'user_id': self.admin.id,
            'is_active': False
        }
        response = self.client.post(self.user_management_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # 验证账户状态未变
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def tearDown(self):
        """清理测试环境"""
        cache.clear()
        super().tearDown()

class TokenRefreshTests(TestCase):
    """Token刷新测试"""
    
    def setUp(self):
        # 创建一个测试用户
        self.user = User.objects.create_user(
            username='tokenuser',
            email='token@example.com',
            password='password123',
            is_active=True
        )
        
        # 登录并获取访问令牌和刷新令牌
        login_data = {
            'username': 'tokenuser',
            'password': 'password123'
        }
        login_response = self.client.post(reverse('users:login'), login_data, format='json')
        self.access_token = login_response.data['access']
        self.refresh_token = login_response.data['refresh']
        
        # Token刷新URL
        self.refresh_url = reverse('users:token_refresh')
        
    def test_token_refresh(self):
        """测试使用刷新令牌获取新的访问令牌"""
        refresh_data = {
            'refresh': self.refresh_token
        }
        
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # 验证新令牌与原令牌不同
        self.assertNotEqual(response.data['access'], self.access_token)
        
    def test_invalid_refresh_token(self):
        """测试使用无效的刷新令牌"""
        refresh_data = {
            'refresh': 'invalid-refresh-token'
        }
        
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        # 验证响应 - 应该是认证错误
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
