from flask import Flask, jsonify
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from app import con
from run import app
import re
from collections import Counter
import nltk
from nltk.corpus import sentiwordnet as swn
nltk.download('sentiwordnet')
nltk.download('wordnet')
nltk.download('punkt_tab')

app = Flask(__name__)

#____________________________________________General Routes___________________________________________________
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin():
    return render_template('admin/index.html')

@app.route('/user')
def user():
    return render_template('user/index.html')

@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        cursor = con.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password,role) VALUES (%s, %s, %s,%s)", (name, email, password,role))
            con.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists. Try logging in.', 'danger')
        finally:
            cursor.close()
    return render_template('signup.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT * FROM users WHERE email = %s AND password = %s AND role = %s',
                (email, password, role)
            )
            user = cursor.fetchone()
            if user:
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['password'] = user['password']
                session['role'] = user['role']
                flash('Login successful!', 'success')
                if user['role'] == "admin":
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('user'))
            else:
                flash('Invalid email or password!', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        finally:
            cursor.close() 
    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

#____________________________________________Admin Routes____________________________________________________

@app.route('/manage_products', methods=['GET', 'POST'])
def manage_products():
    cursor = con.cursor()

    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image'] if 'image' in request.form else None

        cursor.execute("INSERT INTO products (product_name, description, price, image) VALUES (%s, %s, %s, %s)",
                       (product_name, description, price, image))
        con.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('manage_products'))

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template('/manage_products.html', products=products)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):

    cursor = con.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    con.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('manage_products'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    cursor = con.cursor()
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        description = request.form.get('description')
        price = request.form.get('price')
        image = request.form.get('image')

        cursor.execute("""
            UPDATE products 
            SET product_name=%s, description=%s, price=%s, image=%s 
            WHERE id=%s
        """, (product_name, description, price, image, product_id))
        con.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('manage_products'))

    # GET request - show the edit form
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if not product:
        return "Product not found", 404

    return render_template('edit_product.html', product=product)


@app.route('/manage_reviews', methods=['GET', 'POST'])
def manage_reviews():
    cursor = con.cursor()
    
    cursor.execute("SELECT * FROM reviews ORDER BY review_date DESC")
    reviews = cursor.fetchall()
    cursor.close()
    
    return render_template('/manage_reviews.html', reviews=reviews)

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    cursor = con.cursor()
    
    cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
    con.commit()
    cursor.close()
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('manage_reviews'))

#____________________________________________User Routes____________________________________________________

# Route to view products
@app.route('/user_view_products', methods=['GET', 'POST'])
def user_view_products():
    cursor = con.cursor()
    
    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image'] if 'image' in request.form else None

        cursor.execute("INSERT INTO products (product_name, description, price, image) VALUES (%s, %s, %s, %s)",
                       (product_name, description, price, image))
        con.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('manage_products'))
    
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    
    return render_template('user_view_products.html', products=products)

# Route to post a review
@app.route('/post_review', methods=['POST'])
def post_review():
    product_name = request.form.get('product_name')
    review_text = request.form.get('review')

    # Get client IP (checks for proxy headers first)
    review_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if review_ip:
        review_ip = review_ip.split(',')[0].strip()  # In case of multiple IPs

    if not product_name or not review_text:
        flash('Product and review cannot be empty!', 'danger')
        return redirect(url_for('user_view_products'))

    cursor = con.cursor()
    cursor.execute("""
        INSERT INTO reviews (product_name, review, review_ip)
        VALUES (%s, %s, %s)
    """, (product_name, review_text, review_ip))
    con.commit()
    cursor.close()

    flash('Review posted successfully!', 'success')
    return redirect(url_for('user_view_products'))



# Route to fetch products for the modal dropdown
@app.route('/get_products', methods=['GET'])
def get_products():
    cursor = con.cursor()
    
    cursor.execute("SELECT product_name FROM products")
    products = cursor.fetchall()
    cursor.close()
    
    return jsonify(products)


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
