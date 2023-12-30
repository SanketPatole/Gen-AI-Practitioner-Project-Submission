from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SECRET_KEY'] = "random string"

db = SQLAlchemy(app)

class users(db.Model):
  id = db.Column('user_id', db.Integer, primary_key=True)
  username = db.Column(db.String(100), unique=True)
  password = db.Column(db.String(100))
  security_question = db.Column(db.String(200))
  security_answer = db.Column(db.String(200))

  def __init__(self, username, password, security_question, security_answer):
      self.username = username
      self.password = password
      self.security_question = security_question
      self.security_answer = security_answer


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        hashed_security_answer = generate_password_hash(request.form['security_answer'])  # Hashing the security answer

        new_user = users(username=request.form['username'], 
                         password=hashed_password,
                         security_question="What was your first pet's name?",
                         security_answer=hashed_security_answer)  # Store the hashed security answer

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')



from flask import make_response

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect logged-in users to profile page
    if 'username' in session:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        user = users.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['username'] = user.username
            return redirect(url_for('profile'))

    # Render the login page
    response = make_response(render_template('login.html'))
    # Modify and return the response to instruct the browser not to cache it
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



# Existing imports and code...


@app.route('/logout')
def logout():
    # Clear the reset_username and username when user logs out
    session.pop('reset_username', None)
    session.pop('username', None)
    return redirect(url_for('login'))



@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if user not logged in

    error_message = None  # Initialize error_message to None

    if request.method == 'POST':
        user = users.query.filter_by(username=session['username']).first()

        if not user or not check_password_hash(user.password, request.form['old_password']):
            error_message = 'Old password is incorrect.'
        elif request.form['new_password'] != request.form['confirm_new_password']:
            error_message = 'Passwords do not match.'
        else:
            user.password = generate_password_hash(request.form['new_password'])
            db.session.commit()
            # Optionally add a success message or redirect to a different page
            return redirect(url_for('profile'))  # Redirect to profile or a confirmation page

    # Render the same change_password page with the error message (if any)
    return render_template('change_password.html', error_message=error_message)





@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        provided_answer = request.form.get('security_answer')

        user = users.query.filter_by(username=username).first()

        if user:
            if check_password_hash(user.security_answer, provided_answer):
                # Set the user in session for reset password verification
                session['reset_username'] = username
                # Indicate that the user can proceed to reset the password
                session['can_reset_password'] = True
                return redirect(url_for('reset_password'))
            else:
                return render_template('error.html', message="Security answer is incorrect. Please try again.", back_url=url_for('forgot_password'))
        else:
            return render_template('error.html', message="No account found with that username. Please try again.", back_url=url_for('forgot_password'))
    else:
        return render_template('forgot_password.html')




@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Ensure the user is coming from the forgot password flow
    if 'reset_username' not in session or not session.get('reset_username') or not session.get('can_reset_password'):
        # If not, redirect them to forgot_password to restart the process
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # Ensure both fields are filled out
        if not new_password or not confirm_new_password:
            return render_template('reset_password.html', error_message="All fields are required.")

        # Check if the new passwords match
        if new_password != confirm_new_password:
            # If not, render the page again with an error message
            return render_template('reset_password.html', error_message="Passwords do not match.")

        # If passwords match, proceed to update the user's password
        user = users.query.filter_by(username=session['reset_username']).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()

            # Clear session variables for security
            session.pop('reset_username', None)
            session.pop('can_reset_password', None)

            # Redirect to the login page
            return redirect(url_for('login'))
        else:
            # If user does not exist, handle the error (this should be rare if your session management is correct)
            return render_template('reset_password.html', error_message="User not found.")

    # GET request: just display the reset password form
    return render_template('reset_password.html')






@app.route('/')
@app.route('/profile')
def profile():
    # Clear any ongoing reset process whenever user visits the profile/home page
    session.pop('reset_username', None)

    if 'username' in session:
        # Mock list of products
        products = [
            {'id': 1, 'name': 'Product 1', 'description': 'Description for product 1', 'price': 10, 'image': url_for('static', filename='images/prod1.jpg')},
            {'id': 2, 'name': 'Product 2', 'description': 'Description for product 2', 'price': 20, 'image': url_for('static', filename='images/prod2.jpg')}
            # ... add more products as needed
        ]
        return render_template('profile.html', username=session['username'], products=products)
    else:
        return redirect(url_for('login'))




@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))  # Default to 1 if not specified

    # Define a unique session key for the user's cart
    user_cart_key = 'cart_' + session['username']
    if user_cart_key not in session:
        session[user_cart_key] = {}

    # Here's a hardcoded product list for demonstration purposes.
    # Replace with your actual product retrieval logic.
    products = {
        '1': {'name': 'Product 1', 'price': 10},
        '2': {'name': 'Product 2', 'price': 20},
        # Add more products as necessary
    }

    product_details = products.get(product_id, None)
    if not product_details:
        return "Product not found", 404

    # Retrieve the user's cart from the session and update it
    cart = session[user_cart_key]
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'name': product_details['name'],
            'quantity': quantity,
            'price': product_details['price']
        }

    session[user_cart_key] = cart  # Update the session with the modified cart
    session.modified = True  # Inform the session that it has been modified
    return redirect(url_for('profile'))





@app.route('/cart')
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirects to login page if not logged in

    user_cart_key = 'cart_' + session['username']
    cart = session.get(user_cart_key, {})

    # Determine if the cart is empty to pass this information to the template
    is_cart_empty = len(cart) == 0

    # Pass the user-specific cart and the empty status to the template
    return render_template('cart.html', cart=cart, is_cart_empty=is_cart_empty)








@app.route('/go_home')
def go_home():
    # Clear the reset_username session variable
    session.pop('reset_username', None)

    # Redirect to the home page
    return redirect(url_for('index'))



@app.before_request
def before_request():
    if 'username' in session:  # Make sure user is logged in
        user_cart_key = 'cart_' + session['username']  # Create a unique cart key for each user
        if user_cart_key not in session:
            session[user_cart_key] = {}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080)
  
