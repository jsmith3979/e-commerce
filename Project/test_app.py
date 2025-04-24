import unittest
import bcrypt
from app import app
from unittest.mock import patch, MagicMock


class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        # simulates the app for testing
        self.app = app.test_client()
        self.app.testing = True

    def test_home_redirects_when_not_logged_in(self):
        # If not logged in and accessing home, should still load HTML or potentially redirect later
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'html', response.data)

    def test_login_page_get(self):
        # Accessing the login page via GET should work
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_post_invalid_user(self):
        # Invalid login credentials should not log the user in
        response = self.app.post('/login', data={
            'email': 'fake@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Incorrect email or password', response.data)

    def test_create_listing_redirects_if_not_logged_in(self):
        #  If not logged in, trying to access /Create_listing should redirect
        response = self.app.get('/Create_listing', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    @patch('app.session', {'user_id': 1})
    def test_create_listing_page_renders_logged_in(self):
        # Logged in user should see the create listing page
        response = self.app.get('/Create_listing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create Listing', response.data)

    @patch('app.session', {'user_id': 1})
    def test_create_listing_post_missing_fields(self):
        # Submitting the form with no data test
        response = self.app.post('/Create_listing', data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 400)

    @patch('app.session', {'user_id': 1})
    def test_create_listing_invalid_quantity(self):
        # Stock quantity must be a number, this test submits text instead
        data = {
            'item_name': 'Test',
            'item_description': 'Test Desc',
            'item_price': '10',
            'item_category': 'Books',
            'item_stock_quantity': 'notanumber'
        }
        response = self.app.post('/Create_listing', data=data)
        self.assertEqual(response.status_code, 302)

    @patch('app.connect_to_mysql')
    def test_login_with_mocked_db(self, mock_connect):
        # test a successful login using a mocked DB connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Create a hashed password for comparison
        hashed_pw = bcrypt.hashpw(b'correctpassword', bcrypt.gensalt()).decode('utf-8')

        # Set up mock DB response
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'is_admin': 0,
            'password': hashed_pw,
            'is_banned': False
        }

        # test login form submission
        response = self.app.post('/login', data={
            'email': 'test@example.com',
            'password': 'correctpassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'testuser', response.data)

class SendMessageTestCase(unittest.TestCase):
        def setUp(self):
            self.app = app.test_client()
            self.app.testing = True
        # test sending messages.
        @patch('app.connect_to_mysql')
        @patch('app.session', {'user_id': 1})
        def test_send_message_success(self, mock_connect):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            # Setup mock behavior
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock fetch results for username and item name
            mock_cursor.fetchone.side_effect = [
                ('TestSender',),
                ('TestItem',)
            ]

            # Make POST request to send a message
            response = self.app.post('/send_message', data={
                'receiver_id': '2',
                'item_id': '10',
                'message': 'Hello!'
            }, follow_redirects=False)

            # Assert the route redirects (to /chat)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/chat/2/10', response.location)

            # Check that insert queries were attempted
            self.assertTrue(mock_cursor.execute.called)
            self.assertGreaterEqual(mock_cursor.execute.call_count, 3)

        @patch('app.connect_to_mysql')
        @patch('app.session', {'user_id': 1})
        def test_send_message_db_error(self, mock_connect):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Simulate error during DB operation
            mock_cursor.execute.side_effect = Exception("DB Fail")

            response = self.app.post('/send_message', data={
                'receiver_id': '2',
                'item_id': '10',
                'message': 'Hello!'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error sending message', response.data)


if __name__ == '__main__':
    unittest.main()
