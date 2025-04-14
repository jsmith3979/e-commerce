from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
import bcrypt
from flask import send_file
import io


app = Flask(__name__)
app.secret_key = 'your_secret_key'

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='Digitalsystems',
            user='root',
            password='darkknight3979'
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None


@app.route('/')
def Unlogged_home():
    # Fetch the items from the database
    category = request.args.get('category', '')  # Get selected category
    price_min = request.args.get('price_min', '')
    price_max = request.args.get('price_max', '')

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Base query
            query = """
                 SELECT items.*, users.username 
                 FROM items 
                 JOIN users ON items.user_id = users.user_id
                 WHERE 1=1
             """
            params = []

            # Apply filters if selected
            if category:
                query += " AND items.category = %s"
                params.append(category)

            if price_min:
                query += " AND items.price >= %s"
                params.append(price_min)

            if price_max:
                query += " AND items.price <= %s"
                params.append(price_max)

            cursor.execute(query, params)
            items = cursor.fetchall()

            # Fetch distinct categories for the filter dropdown
            cursor.execute("SELECT DISTINCT category FROM items")
            categories = [row['category'] for row in cursor.fetchall()]

            if 'user_id' in session:
                return redirect(url_for('logged_home'))
            else:
                return render_template('unlogged_home.html', items=items, categories=categories)

        except Error as e:
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('Unlogged_home'))
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('Unlogged_home'))




@app.route('/login')
def loginhtml():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('logged_home'))  # Prevent logged-in user from visiting the login page again

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = connect_to_mysql()
        if connection is not None:
            try:
                cursor = connection.cursor(dictionary=True)

                # Check if user exists
                query = "SELECT * FROM users WHERE email = %s"
                cursor.execute(query, (email,))
                user = cursor.fetchone()

                if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    # Login successful, store user info in session
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['is_admin'] = user['is_admin']  # Store admin status

                    flash('Login successful!', 'success')

                    # Check if there's a next URL (page the user was trying to access before login)
                    next_url = request.args.get('next')
                    if next_url:
                        return redirect(next_url)  # Redirect to the originally requested page
                    else:
                        # Redirect to the logged-in homepage (or dashboard)
                        return redirect(url_for('logged_home'))
                else:
                    flash('Invalid email or password', 'danger')
                    return redirect(url_for('login'))

            except Error as e:
                return f"Database Error: {e}"
            finally:
                cursor.close()
                connection.close()
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')



@app.route('/dashboard')
def logged_home():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))

    # category = request.args.get('category', '')  # Get selected category
    # price_min = request.args.get('price_min', '')
    # price_max = request.args.get('price_max', '')

    # if session.get('is_admin') == 1:  # Assuming 'is_admin' is stored in the session
    #     return redirect(url_for('admin_dashboard'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                  SELECT items.*, users.username 
                  FROM items 
                  JOIN users ON items.user_id = users.user_id
                  WHERE 1=1
              """
            # params = []
            #
            # if category:
            #     query += " AND items.category = %s"
            #     params.append(category)
            #
            # if price_min:
            #     query += " AND items.price >= %s"
            #     params.append(price_min)
            #
            # if price_max:
            #     query += " AND items.price <= %s"
            #     params.append(price_max)

            cursor.execute(query)
            items = cursor.fetchall()

            # Fetch distinct categories for filter dropdown
            cursor.execute("SELECT DISTINCT category FROM items")
            categories = [row['category'] for row in cursor.fetchall()]

            return render_template('home.html', items=items, categories=categories)
        except Error as e:
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('Unlogged_home'))
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return render_template('unlogged_home.html', username=session.get('username'))



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('Unlogged_home'))

@app.route('/register', methods=['GET'])
def show_form():
    return render_template('register.html')
@app.route('/register', methods=['POST'])
def register():

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    # Hash the password before storing it in the database
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert the data into MySQL
    connection = connect_to_mysql()
    if connection is not None:
        try:
            cursor = connection.cursor()

            # SQL query to insert data into users table
            query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
            values = (name, email, hashed_password)

            cursor.execute(query, values)
            connection.commit()

            return redirect(url_for('login'))

        except Error as e:
            return f"Error: {e}"
        finally:
            cursor.close()
            connection.close()
    return "Failed to connect to the database."


@app.route('/Create_listing', methods=['GET', 'POST'])
def create_listing():
    if request.method == 'POST':

        # Check if user is logged in
        if 'user_id' not in session:
            flash('You must be logged in to create a listing!', 'warning')
            return redirect(url_for('login'))  # Redirect to login if not logged in

        # Get form data
        item_name = request.form['item_name']
        item_description = request.form['item_description']
        item_price = request.form['item_price']
        item_category = request.form['item_category']
        item_stock_quantity = request.form['item_stock_quantity']

        # Handle the image file upload
        image_file = request.files.get('image')
        image_data = None
        if image_file:
            image_data = image_file.read()  # <-- Error might happen here


        # Get the current logged-in user's ID from session
        user_id = session['user_id']

        try:
            item_stock_quantity = int(item_stock_quantity)
            if item_stock_quantity < 0:
                flash('Stock quantity must be a positive number!', 'danger')
                return redirect(url_for('create_listing'))
        except ValueError:
            flash('Invalid stock quantity. Please enter a number.', 'danger')
            return redirect(url_for('create_listing'))


        # Connect to MySQL and insert data into the database
        connection = connect_to_mysql()
        if connection:
            try:
                cursor = connection.cursor()

                # SQL query to insert data into the items table, including the user_id
                query = """
                    INSERT INTO items (user_id, name, description, price, category, image, stock_quantity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (user_id, item_name, item_description, item_price, item_category, image_data, item_stock_quantity)

                cursor.execute(query, values)
                connection.commit()
                notification_query = """
                    INSERT INTO notifications (user_id, message)
                    VALUES (%s, %s)
                """
                # Create a message for the notification
                notification_message = f"Your listing '{item_name}' was successfully created!"
                cursor.execute(notification_query, (user_id, notification_message))
                connection.commit()

                return redirect(url_for('logged_home'))

            except Error as e:
                print(f"Database Error: {e}")
                flash(f"Database Error: {e}", 'danger')
                return redirect(url_for('create_listing'))
            finally:
                cursor.close()
                connection.close()

        flash("Failed to connect to the database.", 'danger')
        return redirect(url_for('create_listing'))

    return render_template('create_listing.html')




@app.route('/item_image/<int:item_id>')
def item_image(item_id):
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Fetch image binary data for the given item_id
            query = "SELECT image FROM items WHERE item_id = %s"
            cursor.execute(query, (item_id,))
            result = cursor.fetchone()
            if result and result['image']:
                image_data = result['image']
                return send_file(io.BytesIO(image_data), mimetype='image/jpeg')
            else:
                return "Image not found", 404
        except Error as e:
            return f"Error: {e}", 500
        finally:
            cursor.close()
            connection.close()
    return "Failed to connect to the database.", 500


# @app.route('/item/<int:item_id>', methods=['GET', 'POST'])
# def item_detail(item_id):
#     connection = connect_to_mysql()  # Establish database connection
#     if connection:
#         try:
#             cursor = connection.cursor(dictionary=True)
#
#             # Fetch the specific item by its ID
#             query = "SELECT * FROM items WHERE item_id = %s"
#             cursor.execute(query, (item_id,))
#             item = cursor.fetchone()
#
#             if request.method == 'POST':  # If form is submitted (Add to Basket or Favorite)
#                 if 'user_id' not in session:
#                     flash("You need to log in to add items to your basket or favorite.", 'warning')
#                     return redirect(url_for('login'))
#
#                 if 'favorite' in request.form:
#                     # Toggle favorite status
#                     favorite_action = request.form['favorite']
#                     if favorite_action == 'favorite':
#                         # Insert into adminfavorites (favorite the item)
#                         cursor.execute("INSERT INTO adminfavorites (user_id, item_id) VALUES (%s, %s)",
#                                        (session['user_id'], item_id))
#                         connection.commit()
#                         flash('Item favorited successfully!', 'success')
#                     elif favorite_action == 'unfavorite':
#                         # Remove from adminfavorites (unfavorite the item)
#                         cursor.execute("DELETE FROM adminfavorites WHERE user_id = %s AND item_id = %s",
#                                        (session['user_id'], item_id))
#                         connection.commit()
#                         flash('Item unfavorited successfully!', 'success')
#
#                 elif 'quantity' in request.form:  # Add to Basket
#                     quantity = request.form.get('quantity', 1)  # Default quantity is 1
#                     basket_query = "INSERT INTO basket (user_id, item_id, quantity) VALUES (%s, %s, %s)"
#                     cursor.execute(basket_query, (session['user_id'], item_id, quantity))
#                     connection.commit()
#                     flash("Item added to your basket!", 'success')
#                     return redirect(url_for('basket_page'))
#
#             # Check if the item is already favorited by the user
#             cursor.execute("SELECT 1 FROM adminfavorites WHERE user_id = %s AND item_id = %s",
#                            (session['user_id'], item_id))
#             is_favorited = cursor.fetchone() is not None  # Boolean check
#
#             if item:
#                 # Pass the item and its favorited status to the template
#                 return render_template('item_detail.html', item=item, is_favorited=is_favorited)
#
#             else:
#                 flash("Item not found!", 'danger')
#                 return redirect(url_for('logged_home'))
#
#         except Error as e:
#             flash(f"Database Error: {e}", 'danger')
#             return redirect(url_for('logged_home'))
#
#         finally:
#             cursor.close()
#             connection.close()
#
#     flash("Failed to connect to the database.", 'danger')
#     return redirect(url_for('logged_home'))
@app.route('/item/<int:item_id>', methods=['GET', 'POST'])
def item_detail(item_id):
    connection = connect_to_mysql()  # Establish database connection
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch the specific item by its ID
            query = "SELECT * FROM items WHERE item_id = %s"
            cursor.execute(query, (item_id,))
            item = cursor.fetchone()

            if request.method == 'POST':  # If form is submitted (Add to Basket or Favorite)
                if 'user_id' not in session:
                    flash("You need to log in to add items to your basket or favorite.", 'warning')
                    return redirect(url_for('login'))

                if 'favorite' in request.form:
                    # Toggle favorite status
                    favorite_action = request.form['favorite']
                    if favorite_action == 'favorite':
                        cursor.execute("INSERT INTO adminfavorites (user_id, item_id) VALUES (%s, %s)",
                                       (session['user_id'], item_id))
                        connection.commit()
                        flash('Item favorited successfully!', 'success')
                    elif favorite_action == 'unfavorite':
                        cursor.execute("DELETE FROM adminfavorites WHERE user_id = %s AND item_id = %s",
                                       (session['user_id'], item_id))
                        connection.commit()
                        flash('Item unfavorited successfully!', 'success')


                elif 'quantity' in request.form:
                    quantity = int(request.form.get('quantity', 1))
                    # Check if enough stock exists
                    if quantity > item['stock_quantity']:
                        flash(f"Only {item['stock_quantity']} in stock. Cannot add {quantity}.", 'danger')
                        return redirect(url_for('item_detail', item_id=item_id))
                    # Check if the item already exists in the basket
                    basket_query = """
                    SELECT quantity FROM basket WHERE user_id = %s AND item_id = %s
                    """
                    cursor.execute(basket_query, (session['user_id'], item_id))
                    existing_item = cursor.fetchone()
                    if existing_item:  # If item already exists, update quantity
                        new_quantity = existing_item['quantity'] + quantity
                        if new_quantity > item['stock_quantity']:
                            flash(
                                f"Only {item['stock_quantity']} in stock. You already have {existing_item['quantity']} in your basket.",
                                'danger')
                            return redirect(url_for('item_detail', item_id=item_id))
                        update_query = """
                        UPDATE basket
                        SET quantity = %s
                        WHERE user_id = %s AND item_id = %s
                        """
                        cursor.execute(update_query, (new_quantity, session['user_id'], item_id))
                    else:  # If item doesn't exist, insert a new row
                        insert_query = """
                        INSERT INTO basket (user_id, item_id, quantity)
                        VALUES (%s, %s, %s)
                        """
                        cursor.execute(insert_query, (session['user_id'], item_id, quantity))
                    connection.commit()
                    flash("Item added to your basket!", 'success')
                    return redirect(url_for('basket_page'))
            # Check if the item is already favorited by the user
            cursor.execute("SELECT 1 FROM adminfavorites WHERE user_id = %s AND item_id = %s",
                           (session['user_id'], item_id))
            is_favorited = cursor.fetchone() is not None  # Boolean check
            if item:
                return render_template('item_detail.html', item=item, is_favorited=is_favorited)
            else:
                flash("Item not found!", 'danger')
                return redirect(url_for('logged_home'))
        except Error as e:
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('logged_home'))
        finally:
            cursor.close()
            connection.close()
    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('logged_home'))




@app.route('/search')
def search():
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    price_min = request.args.get('price_min', '')
    price_max = request.args.get('price_max', '')
    admin_favorites = request.args.get('admin_favorites', '')

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Base query
            sql = """
                SELECT items.*, users.username 
                FROM items 
                JOIN users ON items.user_id = users.user_id
            """
            params = []

            # If viewing admin favorites, join with adminfavorites
            if admin_favorites:
                sql += " JOIN adminfavorites ON items.item_id = adminfavorites.item_id"
                sql += " WHERE adminfavorites.user_id IN (SELECT user_id FROM users WHERE is_admin = 1)"
            else:
                sql += " WHERE 1=1"

            # Filters
            if query:
                sql += " AND (items.name LIKE %s OR items.description LIKE %s)"
                params.extend([f"%{query}%", f"%{query}%"])

            if category:
                sql += " AND items.category = %s"
                params.append(category)

            if price_min:
                sql += " AND items.price >= %s"
                params.append(price_min)

            if price_max:
                sql += " AND items.price <= %s"
                params.append(price_max)

            cursor.execute(sql, params)
            items = cursor.fetchall()

            cursor.execute("SELECT DISTINCT category FROM items")
            categories = [row['category'] for row in cursor.fetchall()]

            return render_template(
                'search.html',
                items=items,
                query=query,
                categories=categories,
                show_admin_favorites=bool(admin_favorites)
            )

        except Error as e:
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('Unlogged_home'))
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('Unlogged_home'))


@app.route('/send_message', methods=['POST'])
def send_message():
    sender_id = session['user_id']
    receiver_id = request.form['receiver_id']
    item_id = request.form['item_id']
    message_text = request.form['message']


    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO messages (sender_id, receiver_id, item_id, message_text, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (sender_id, receiver_id, item_id, message_text))

            cursor.execute("SELECT username FROM users WHERE user_id = %s", (sender_id,))
            sender = cursor.fetchone()
            sender_username = sender[0] if sender else "Someone"

            # Get item name
            cursor.execute("SELECT name FROM items WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()
            item_name = item[0] if item else "an item"

            # Insert a notification for the receiver
            notification_text = f"You received a new message from {sender_username} about '{item_name}'"
            notification_query = """
                            INSERT INTO notifications (user_id, message)
                            VALUES (%s, %s)
                        """
            cursor.execute(notification_query, (receiver_id, notification_text))

            connection.commit()
            return redirect(url_for('chat', user_id=receiver_id, item_id=item_id))
        except Error as e:
            flash(f"Error sending message: {e}", "danger")
        finally:
            cursor.close()
            connection.close()

    return redirect(url_for('unlogged_home'))



@app.route('/chat/<int:user_id>/<int:item_id>', methods=['GET'])
def chat(user_id, item_id):
    if 'user_id' not in session:
        flash("You need to login first!", 'warning')
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    connection = connect_to_mysql()

    if connection:
        try:
            cursor = connection.cursor()

            # Get messages between the two users
            message_query = """
                SELECT m.sender_id, u.username, m.message_text, m.created_at
                FROM messages m
                JOIN users u ON m.sender_id = u.user_id
                WHERE ((m.sender_id = %s AND m.receiver_id = %s)
                   OR  (m.sender_id = %s AND m.receiver_id = %s))
                  AND m.item_id = %s
                ORDER BY m.created_at ASC
            """
            cursor.execute(message_query, (current_user_id, user_id, user_id, current_user_id, item_id))
            messages = cursor.fetchall()

            # Get the chat partner's name
            name_query = "SELECT username FROM users WHERE user_id = %s"
            cursor.execute(name_query, (user_id,))
            chat_partner = cursor.fetchone()

            cursor = connection.cursor(dictionary=True)
            item_query = "SELECT * FROM items WHERE item_id = %s"
            cursor.execute(item_query, (item_id,))
            item = cursor.fetchone()

            if chat_partner:
                chat_partner_name = chat_partner[0]
            else:
                chat_partner_name = "Unknown User"

            return render_template('chat.html', messages=messages, user_id=user_id, item_id=item_id, chat_partner_name=chat_partner_name, item=item)

        except Error as e:
            print(f"Database Error: {e}")
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('chat_inbox'))

        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('chat_inbox'))


@app.route('/chat_inbox', methods=['GET'])
def chat_inbox():
    if 'user_id' not in session:
        flash("You need to login first!", 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    print(f"User ID in session: {user_id}")

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT 
                    CASE 
                        WHEN sender_id = %s THEN receiver_id 
                        ELSE sender_id 
                    END AS other_user_id,
                    item_id,
                    MAX(
                        (SELECT username 
                         FROM users 
                         WHERE user_id = CASE 
                                             WHEN sender_id = %s THEN receiver_id 
                                             ELSE sender_id 
                                         END)
                    ) AS username,
                    MAX(
                        (SELECT name 
                         FROM items 
                         WHERE item_id = messages.item_id)
                    ) AS item_name
                FROM messages
                WHERE sender_id = %s OR receiver_id = %s
                GROUP BY other_user_id, item_id
                ORDER BY MAX(created_at) DESC;
            """
            cursor.execute(query, (user_id, user_id, user_id, user_id))
            conversations = cursor.fetchall()

            if not conversations:
                # Flash message and render the page with no conversations
                flash("No conversations available.", 'info')
                return render_template('chat_inbox.html', conversations=None)

            return render_template('chat_inbox.html', conversations=conversations)

        except Error as e:
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('logged_home'))

        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('logged_home'))



@app.route('/notifications_page')
def notifications_page():
    if 'user_id' not in session:
        flash("You need to log in first!", 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = connect_to_mysql()

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Fetch all notifications for the user, ordered by creation date (newest first)
            query = """
                SELECT notification_id, message, is_read, created_at 
                FROM notifications 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            """
            cursor.execute(query, (user_id,))
            notifications = cursor.fetchall()

            # Optional: Mark all notifications as read
            update_query = "UPDATE notifications SET is_read = 1 WHERE user_id = %s"
            cursor.execute(update_query, (user_id,))
            connection.commit()

            return render_template('notifications_page.html', notifications=notifications)
        except Error as e:
            flash(f"Database error: {e}", 'danger')
            return redirect(url_for('logged_home'))
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('logged_home'))




@app.route('/notifications', methods=['GET'])
def notifications():
    # Check that the user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session['user_id']
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # This query counts unread notifications for the current user
            query = """
                SELECT COUNT(*) AS unread_count 
                FROM notifications 
                WHERE user_id = %s AND is_read = 0
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            unread_count = result['unread_count'] if result else 0
            return jsonify({"unread_count": unread_count})
        except Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    return jsonify({"error": "Database connection failed"}), 500


# used for deleting notifications that the user recieves from listing items.
@app.route('/delete_notification/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    if 'user_id' not in session:
        flash("Please log in to delete notifications.", "warning")
        return redirect(url_for('login'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()

            # Make sure the notification belongs to the logged-in user
            query = "DELETE FROM notifications WHERE notification_id = %s AND user_id = %s"
            cursor.execute(query, (notification_id, session['user_id']))
            connection.commit()

            flash("Notification deleted.", "success")
        except Error as e:
            flash(f"Database Error: {e}", "danger")
        finally:
            cursor.close()
            connection.close()

    return redirect(url_for('notifications_page'))

# @app.route('/basket')
# def basket():
#     if 'user_id' not in session:
#         flash("Please log in to view your basket.", "warning")
#         return redirect(url_for('login'))
#
#     connection = connect_to_mysql()
#     basket_items = []
#
#     if connection:
#         try:
#             cursor = connection.cursor(dictionary=True)
#             query = "SELECT * FROM basket WHERE user_id = %s"
#             cursor.execute(query, (session['user_id'],))
#             basket_items = cursor.fetchall()
#         except Error as e:
#             flash(f"Error fetching basket items: {e}", "danger")
#         finally:
#             cursor.close()
#             connection.close()
#
#     return render_template('basket.html', basket_items=basket_items)

@app.route('/basket')
def basket_page():
    if 'user_id' not in session:
        flash("Please log in to view your basket.", "warning")
        return redirect(url_for('login'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Query to fetch basket items for the logged-in user, including item details
            query = """
            SELECT 
                basket.item_id, 
                SUM(basket.quantity) AS quantity, 
                items.name, 
                items.price, 
                items.image
            FROM basket
            JOIN items ON basket.item_id = items.item_id
            WHERE basket.user_id = %s
            GROUP BY basket.item_id, items.name, items.price, items.image
            """

            cursor.execute(query, (session['user_id'],))
            basket_items = cursor.fetchall()

            # If the basket is empty, show a relevant message
            if not basket_items:
                flash("Your basket is empty.", "info")

            # Debugging: Check the basket items before rendering the template
            # print(basket_items)  # Optionally, log the result to check

            return render_template('basket.html', basket_items=basket_items, )

        except Error as e:
            flash(f"Database Error: {e}", "danger")
            return redirect(url_for('home'))
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", "danger")
    return redirect(url_for('home'))

def get_basket_items(user_id):
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT i.item_id, i.name, i.price, b.quantity
                FROM basket b
                JOIN items i ON b.item_id = i.item_id
                WHERE b.user_id = %s
            """
            cursor.execute(query, (user_id,))
            basket_items = cursor.fetchall()
            return basket_items
        except Error as e:
            print(f"Database Error: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    return []

@app.route('/update_basket', methods=['POST'])
def update_basket():
    user_id = session['user_id']
    for item in get_basket_items(user_id):
        quantity_field = f'quantity_{item["item_id"]}'
        if quantity_field in request.form:
            new_quantity = int(request.form[quantity_field])
            update_item_quantity(item["item_id"], new_quantity)
    return redirect('/basket')



def update_item_quantity(item_id, new_quantity):
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                UPDATE basket
                SET quantity = %s
                WHERE user_id = %s AND item_id = %s
            """
            cursor.execute(query, (new_quantity, session['user_id'], item_id))
            connection.commit()
        except Error as e:
            print(f"Database Error (update): {e}")
        finally:
            cursor.close()
            connection.close()


@app.route('/delete_from_basket', methods=['POST'])
def delete_from_basket():
    print("Delete request received")  # Debugging line

    if 'user_id' not in session:
        flash("You must be logged in to delete items from the basket.", "warning")
        return redirect(url_for('login'))

    item_id = request.form.get('item_id')
    print(f"Item ID to delete: {item_id}")  # Debugging line

    if item_id:
        remove_item_from_basket(item_id)  # Your DB logic here
        flash("Item removed from basket.", "success")
    else:
        flash("Failed to remove item. Item ID not provided.", "danger")

    # Redirect to the updated basket page
    return redirect(url_for('basket_page'))

def remove_item_from_basket(item_id):
    print(f"Attempting to remove item with ID: {item_id}")  # Debugging line
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()

            # Print the current contents of the basket before attempting removal
            check_basket_query = """
                SELECT * FROM basket WHERE user_id = %s AND item_id = %s
            """
            cursor.execute(check_basket_query, (session['user_id'], item_id))
            item_in_basket = cursor.fetchone()
            print(f"Item in basket: {item_in_basket}")  # Debugging line

            # Proceed with deletion if the item exists in the basket
            if item_in_basket:
                query = """
                    DELETE FROM basket
                    WHERE user_id = %s AND item_id = %s
                """
                cursor.execute(query, (session['user_id'], item_id))
                connection.commit()

                # Check if the deletion was successful
                if cursor.rowcount > 0:
                    print(f"Successfully removed item with ID: {item_id}")
                else:
                    print(f"Failed to remove item with ID: {item_id}. No rows affected.")
            else:
                print(f"No item found in the basket with ID: {item_id}")

        except Error as e:
            print(f"Database Error (delete): {e}")
        finally:
            cursor.close()
            connection.close()

@app.route('/purchase', methods=['POST'])
def purchase():
    if 'user_id' not in session:
        flash('You must be logged in to make a purchase!', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch the items in the basket
    basket_items = get_basket_items(user_id)

    if not basket_items:
        flash('Your basket is empty. Please add items before proceeding.', 'warning')
        return redirect(url_for('basket_page'))

    connection = connect_to_mysql()

    if connection:
        try:
            cursor = connection.cursor()

            # Loop through the items in the basket and process the purchase
            for item in basket_items:
                item_id = item['item_id']
                quantity = item['quantity']
                price = item['price']
                total_price = price * quantity

                # Update the stock quantity in the items table
                update_stock_query = """
                    UPDATE items
                    SET stock_quantity = stock_quantity - %s
                    WHERE item_id = %s AND stock_quantity >= %s
                """
                cursor.execute(update_stock_query, (quantity, item_id, quantity))

                if cursor.rowcount == 0:
                    flash(f"Not enough stock for item '{item['name']}'. Purchase failed.", 'danger')
                    return redirect(url_for('basket_page'))

                # Insert the purchase into the purchases table
                purchase_query = """
                    INSERT INTO purchases (user_id, item_id, quantity, total_price)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(purchase_query, (user_id, item_id, quantity, total_price))

                # Insert a notification for the purchase
                notification_message = f"Your purchase of {quantity}x {item['name']} for ${total_price:.2f} was successful!"
                notification_query = """
                    INSERT INTO notifications (user_id, message, is_read)
                    VALUES (%s, %s, 0)
                """
                cursor.execute(notification_query, (user_id, notification_message))

            # Commit the changes to the database
            connection.commit()

            # Clear the user's basket (delete items from the basket)
            clear_basket_query = """
                DELETE FROM basket WHERE user_id = %s
            """
            cursor.execute(clear_basket_query, (user_id,))

            connection.commit()

            flash('Purchase successful! Check your notifications.', 'success')
            return redirect(url_for('logged_home'))

        except Error as e:
            print(f"Database Error: {e}")
            flash(f"Database Error: {e}", 'danger')
            return redirect(url_for('basket_page'))

        finally:
            cursor.close()
            connection.close()

    flash('Failed to connect to the database.', 'danger')
    return redirect(url_for('basket_page'))


@app.route('/favorite_item/<int:item_id>', methods=['POST'])
def favorite_item(item_id):
    # Check if the user is logged in and is an admin
    if 'user_id' not in session or session.get('is_admin') != 1:
        flash('You must be an admin to favorite items.', 'warning')
        return redirect(url_for('logged_home'))

    user_id = session['user_id']  # Get the logged-in user ID (admin)

    # Connect to the database
    connection = connect_to_mysql()

    if connection:
        try:
            cursor = connection.cursor()

            # Check if the item exists in the items table
            cursor.execute("SELECT 1 FROM items WHERE item_id = %s", (item_id,))
            if cursor.fetchone() is None:
                flash('Item does not exist.', 'danger')
                return redirect(url_for('item_detail', item_id=item_id))

            # Check if the item is already favorited by this user
            cursor.execute("""
                SELECT 1 FROM adminfavorites 
                WHERE user_id = %s AND item_id = %s
            """, (user_id, item_id))

            # If the item is already favorited, unfavorite it
            if cursor.fetchone():
                # Unfavorite the item by deleting it from the database
                cursor.execute("""
                    DELETE FROM adminfavorites 
                    WHERE user_id = %s AND item_id = %s
                """, (user_id, item_id))

                connection.commit()
                flash('Item has been removed from your favorites.', 'success')
            else:
                # Favorite the item
                cursor.execute("""
                    INSERT INTO adminfavorites (user_id, item_id) 
                    VALUES (%s, %s)
                """, (user_id, item_id))

                connection.commit()
                flash('Item added to favorites successfully!', 'success')

            return redirect(url_for('item_detail', item_id=item_id))

        except Error as e:
            flash(f"Error occurred while favoriting/unfavoriting the item: {e}", 'danger')
            return redirect(url_for('item_detail', item_id=item_id))

        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to the database.", 'danger')
    return redirect(url_for('item_detail', item_id=item_id))






@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Get admin's favorited items
            cursor.execute("""
                SELECT i.* FROM adminfavorites af
                JOIN items i ON af.item_id = i.item_id
                WHERE af.user_id = %s
            """, (session['user_id'],))
            favorites = cursor.fetchall()

            return render_template('admin_dashboard.html', favorites=favorites)

        except Error as e:
            flash(f"Database error: {e}", "danger")
        finally:
            cursor.close()
            connection.close()

    flash("Failed to connect to database.", "danger")
    return redirect(url_for('login'))


@app.route('/my_listings')
def my_listings():
    if 'user_id' not in session:
        flash("You must be logged in to view your listings.", 'warning')
        return redirect(url_for('login'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM items WHERE user_id = %s", (session['user_id'],))
            items = cursor.fetchall()
            return render_template("my_listings.html", items=items)
        except Error as e:
            flash(f"Database error: {e}", 'danger')
            return redirect(url_for('logged_home'))
        finally:
            cursor.close()
            connection.close()
    else:
        flash("Database connection failed.", 'danger')
        return redirect(url_for('logged_home'))


@app.route('/update_item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    if 'user_id' not in session:
        flash("You need to be logged in.", 'warning')
        return redirect(url_for('login'))

    name = request.form.get('name')
    price = request.form.get('price')
    category = request.form.get('category')
    stock_quantity = request.form.get('stock_quantity')

    if not name or not price or not category or not stock_quantity.isdigit():
        flash("Invalid input.", 'danger')
        return redirect(url_for('edit_listing', item_id=item_id))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT user_id FROM items WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()

            if item and item[0] == session['user_id']:
                cursor.execute("""
                    UPDATE items
                    SET name = %s, price = %s, category = %s, stock_quantity = %s
                    WHERE item_id = %s
                """, (name, float(price), category, int(stock_quantity), item_id))
                connection.commit()
                flash("Item updated successfully!", 'success')
            else:
                flash("Unauthorized or item not found.", 'danger')
        except Error as e:
            flash(f"Database error: {e}", 'danger')
        finally:
            cursor.close()
            connection.close()

    return redirect(url_for('my_listings'))



@app.route('/edit_my_listings/<int:item_id>', methods=['GET', 'POST'])
def edit_listing(item_id):
    if 'user_id' not in session:
        flash("You need to be logged in.", 'warning')
        return redirect(url_for('login'))

    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()

            if not item:
                flash("Item not found.", 'danger')
                return redirect(url_for('my_listings'))

            if item[1] != session['user_id']:  # Ensure the item belongs to the logged-in user
                flash("You cannot edit an item that does not belong to you.", 'danger')
                return redirect(url_for('my_listings'))

            if request.method == 'POST':
                # Handle the form submission
                new_name = request.form['name']
                new_price = request.form['price']
                new_category = request.form['category']
                new_stock_quantity = request.form['stock_quantity']

                # Update the item in the database
                cursor.execute("""
                    UPDATE items
                    SET name = %s, price = %s, category = %s, stock_quantity = %s
                    WHERE item_id = %s
                """, (new_name, new_price, new_category, new_stock_quantity, item_id))
                connection.commit()

                flash("Item updated successfully!", 'success')
                return redirect(url_for('my_listings'))

            # Map item data to variables for GET request
            item_data = {
                'item_id': item[0],
                'name': item[2],
                'price': item[3],
                'category': item[4],
                'stock_quantity': item[5],
            }

            return render_template('edit_my_listings.html', item=item_data)

        except Error as e:
            flash(f"Database error: {e}", 'danger')
        finally:
            cursor.close()
            connection.close()

    return redirect(url_for('my_listings'))

@app.route('/test')
def test_route():
    print("Test route accessed")
    return "Test route working"

if __name__ == '__main__':
    app.run(debug=True)