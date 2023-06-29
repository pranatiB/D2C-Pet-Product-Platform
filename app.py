from flask import Flask, flash, redirect, render_template, request, session, jsonify,request
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
# from flask_restful import Resource, Api
# from flask_session import Session
from  flask_mysqldb  import  MySQL
import  MySQLdb.cursors
import os
from functools import wraps
import datetime
from trie import Trie
import razorpay
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

sql_password = os.getenv('sql_password')
# sql_password="sakshi123"

app.config['SECRET_KEY']  =  'supersecretkey'

mysql  =  MySQL(app) 
app.config['MYSQL_HOST']  =  'localhost' 
app.config['MYSQL_USER']  =  'root' 
app.config['MYSQL_PASSWORD']  =  sql_password
app.config['MYSQL_DB']  =  'dbms_project'


app.config["TEMPLATES_AUTO_RELOAD"] = True

razor_id="rzp_test_wLQcXe9aMJX7As"
secret_key="AG5ez7IJ9SQtJtvFWAJ312vw"


# /****************************************** Decorators and Filters *********************************************************/

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        # try: 
        data = jwt.decode(token, app.config['SECRET_KEY'],algorithms=['HS256'])
        # print(data)
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM customer WHERE cust_id=%s", [data['cust_id']])
        current_user = cursor.fetchone()
        # except:
        #     return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.template_filter()
def rupees(value):
    """Format value as Rupees"""
    #rupee =  u"\u20B9"
    return (u"\u20B9"f"{value:,.2f}")



# /**************************************************** API CALLS *******************************************************************/


# Get a list of all products
@app.route("/api/products", methods=["GET"])
def get_all_products():
    if request.method == 'GET':
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select distinct uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date from product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id;")
        records = cursor.fetchall()
        return jsonify({'products':records})
    else:
        return jsonify({'message':"Invalid method call!"})

# Get info on particular product
@app.route("/api/products/<key>", methods=["GET"])
def get_product(key):
    if request.method == 'GET':
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT DISTINCT uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date FROM product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND prod_sub.name LIKE %s;",['%' + key + '%'])
        records = cursor.fetchall()
        return jsonify({'products':records})
    else:
        return jsonify({'message':"Error invalid method call"})



# Add product to cart
@app.route("/api/add_cart", methods=["POST"])
@token_required
def add_cart(current_user):
    if request.method=="POST":
        data=request.json
        if not data['prod_sub_id']:
            return jsonify({"message":"Missing id"})
        cursor =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT prod_id FROM product WHERE prod_sub_id=%s",[data['prod_sub_id']])
        prod_id = cursor.fetchone()
        cursor.execute("SELECT * FROM cart WHERE cust_id=%s AND prod_id=%s",([current_user['cust_id']],[prod_id['prod_id']]))
        duplicate = cursor.fetchall()
        if len(duplicate) == 1:
            cursor.execute("UPDATE cart SET quantity=quantity+1 WHERE cust_id=%s AND prod_id=%s",([current_user['cust_id']],[prod_id['prod_id']]))
        else:
            cursor.execute("INSERT INTO cart(prod_id,cust_id,quantity) VALUES(%s,%s,%s);",([prod_id['prod_id']],[current_user["cust_id"]],[1]))
        mysql.connection.commit()
        return jsonify({"message":"Added to cart"})
    else:
        return jsonify({"message":"Invalid method call"})

# Remove product from cart
@app.route("/api/remove_cart/<int:id>",methods=["GET","DELETE"])
@token_required
def remove(current_user,id):
    if request.method == "DELETE":
        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT cart_id FROM cart WHERE cust_id=%s",[current_user['cust_id']])
        ids = cursor.fetchall()
        if len(ids) == 0:
            return jsonify({"message": "Cart is Empty"})
        for i in range(len(ids)):
            if ids[i]['cart_id'] == int(id):
                cursor.execute("DELETE FROM cart WHERE cart_id=%s;",[ids[i]['cart_id']])
                mysql.connection.commit()
                return jsonify({'message':'Item removed from cart'})
        return jsonify({'message':'Invalid Id entered'})
    else:
        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT cart_id FROM cart WHERE cust_id=2;")
        ids = cursor.fetchall()
        return jsonify(({'ids':ids[0]}))

# View cart
@app.route("/api/view_cart",methods=["GET"])
@token_required
def view_cart(current_user):
    cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
    cursor.execute('SELECT cart_id, name,price,quantity,expiry_date,product.prod_id FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[current_user["cust_id"]]) 
    records = cursor.fetchall()
    
    if len(records) == 0:
        return jsonify({"message":"Your cart is empty"})
    
    cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[current_user["cust_id"]])
    total = cursor.fetchone()

    return jsonify({"cart":records,"total":str(total['total'])})

# Get JWT token
@app.route("/api/login",methods=["POST"])
def api_login():
    if request.method == "POST":
        auth = request.json

        if not auth or not auth["username"] or not auth["password"]:
            return jsonify({"message":"No username/password sent!"})

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM customer WHERE username=%s;",[auth["username"]])
        user = cursor.fetchone()

        if not user:
            return jsonify({"message":"Invalid username!"})

        if check_password_hash(user["password"], auth["password"]):
            token = jwt.encode({'cust_id' : user["cust_id"], 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
            return jsonify({'token' : token})

        return jsonify({"message":"Invalid password!"})
    else:
        return jsonify({"message":"Invalid method call"})




# Add a new product to system
@app.route("/api/add_product",methods=["GET","POST"])
# @token_required
def post_api():
    if request.method == 'POST':

            # Store json received in POST
            prod = request.json

            cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Min number of product id required 
            cursor.execute("SELECT max(prod_sub_id) AS high FROM prod_sub;")
            high = cursor.fetchall()

            # Error Handling
            if not prod.get("sub_id"):
                return jsonify({'Error': 'sub_id not entered'})
            elif not type(prod["sub_id"]) == int or int(prod["sub_id"]) != int(high[0]["high"])+1:
                return jsonify({"Error": "Invalid Sub Id"})
            elif not prod.get("category"):
                return jsonify({'Error': 'Category not entered'})
            elif not prod.get("name"):
                return jsonify({'Error': 'Name not entered'})
            elif not prod.get("price"):
                return jsonify({'Error': 'Price not entered'})
            elif not prod.get("stock"):
                return jsonify({'Error': 'Stock not entered'})
            elif not prod.get("id"):
                return jsonify({'Error': 'Id not entered'})
            elif not prod.get("pet"):
                return jsonify({'Error': 'Pet not entered'})
            elif int(prod["id"].split('p')[1]) != int(high[0]["high"])+1:
                return jsonify({'Error': 'Invalid id entered'})
            
            # Assign Pet
            if prod["pet"] == "Dog" or prod["pet"] == "dog":
                pet_id = [10]
            elif prod["pet"] == "Cat" or prod["pet"] == "cat":
                pet_id = [20]
            elif prod["pet"] == "Both" or prod["pet"] == "both":
                pet_id = [10,20]
            else:
                return jsonify({'Error':'Invalid Pet entered'})
            
            # Assign Category to product
            cursor.execute("SELECT * FROM prod_category;")
            category = cursor.fetchall()
            category_id='C0'
            for i in range(len(category)):
                if prod["category"] == category[i]["name"]:
                    category_id = 'C'+ str(i+1)
            if category_id == 'C0':
                category_id = 'C'+ str(len(category)+1)
            
            # Insert into Database
            cursor.execute("INSERT INTO prod_sub(prod_sub_id,prod_category_id,name) VALUES(%s,%s,%s);",(prod['sub_id'],category_id,prod['name']))
            cursor.execute("INSERT INTO product(prod_id,prod_sub_id,price,stock_quantity,expiry_date) VALUES(%s,%s,%s,%s,%s);", (prod['id'],prod['sub_id'],prod['price'],prod['stock'],prod.get('expiry_date')))
            for id in pet_id:
                cursor.execute("INSERT INTO uses(prod_id,pet_id) VALUES(%s,%s);",(prod["id"],id))
            mysql.connection.commit()
            return jsonify({'Message': 'Product Added Successfully'})

    else:
        cursor.execute("SELECT max(prod_sub_id) AS high FROM prod_sub;")
        high = cursor.fetchall()
        return render_template("example.html",record=high[0]['high'])
        # return jsonify({'message':"Error invalid method call"})




# /************************************************* Website Routes ********************************************************/


# User will login 
@app.route("/login", methods=["GET","POST"])
def login():

    # Clear sessions 
    session.clear()

    #If user submitted login form
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")


        # If username was not submitted
        if not username:
            return render_template("apology.html",top=400,bottom="must provide username")
        
        # If password was not submitted
        elif not password:
            return render_template("apology.html",top=400,bottom="must provide password")
        
        # Establish connection with server
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Query database
        cursor.execute("SELECT * FROM customer WHERE username = %s;",([username]))

        # Fetch query
        records = cursor.fetchall()

        # Check if user exists
        if len(records) != 1 or not check_password_hash(records[0]['password'],password):
            return render_template("apology.html",top=400,bottom="invalid username/password")
        
        # Remember user
        session["user_id"] = records[0]["cust_id"]

        # User should get home page
        return redirect("/")

    # If user visits by GET method
    else:
        return render_template("signup.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register",methods=["GET","POST"])
def register():
    """ To register user """

    if request.method == "POST":

        # Get value iserted in input field
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        username = request.form.get("username")
        email = request.form.get("email")
        contact_no = request.form.get("contact_no")
        password = request.form.get("password")

        # Test cases Error check
        if not firstname:
            return render_template("apology.html",top=400,bottom="must provide firstname")
        elif not lastname:
            return render_template("apology.html",top=400,bottom="must provide lastname")
        elif not username:
            return render_template("apology.html",top=400,bottom="must provide username")
        elif not email:
            return render_template("apology.html",top=400,bottom="must provide email")
        elif not contact_no or len(contact_no) != 10:
            return render_template("apology.html",top=400,bottom="must provide conact no.")
        elif not password:
            return render_template("apology.html",top=400,bottom="must provide password")
        elif password != request.form.get("confirm_password"):
            return render_template("apology.html",top=400,bottom="password must be same")
        
        # Establish connection with server
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get list of usernames
        cursor.execute("SELECT * FROM customer WHERE username = %s",[username])
        usernames = cursor.fetchall()

        # Check is username is unique
        if len(usernames) > 0:
            return render_template("apology.html",top=400,bottom="username already exists")
        
        # Add new user to customer table
        cursor.execute('INSERT INTO customer(firstname,lastname,contact_no,email,username,password) VALUES(%s,%s,%s,%s,%s,%s);',([firstname],[lastname],[contact_no],[email],[username],[generate_password_hash(password)]))

        # Commit changes to customer table
        mysql.connection.commit()
        
        # Send user to log in page
        return redirect("/login")
    
    # If user visist by GET method
    else:
        return render_template("register.html")
        
@app.route("/")
def index():
    """Show dog and cat choice with description"""
    return render_template("index2.html")



@app.route("/dogs",methods=["GET","POST"])
# @login_required
def dogs():
    """Show Products of Dogs"""
    if request.method == "POST":
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("SELECT prod_sub_id FROM prod_sub;")
        ids = cursor.fetchall()
        for row in ids:
            count = 0
            if int(request.form['submit_button']) == (row['prod_sub_id']):
                cursor.execute("SELECT prod_id FROM product WHERE prod_sub_id=%s",[row['prod_sub_id']])
                prod_id = cursor.fetchone()

                # Check if product in cart
                cursor.execute("SELECT * FROM cart WHERE cust_id=%s AND prod_id=%s",([session['user_id']],[prod_id['prod_id']]))
                duplicate = cursor.fetchall()
                
                # Increment qquantity by 1
                if len(duplicate) == 1:
                    cursor.execute("UPDATE cart SET quantity=quantity+1 WHERE cust_id=%s AND prod_id=%s",([session['user_id']],[prod_id['prod_id']]))
                
                # Add to cart as new product
                else:
                    cursor.execute("INSERT INTO cart(prod_id,cust_id,quantity) VALUES(%s,%s,%s);",([prod_id['prod_id']],[session["user_id"]],[1]))
                mysql.connection.commit()
                break
            
        return redirect("/cart")

    else:
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("select distinct uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date from product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND uses.pet_id=10;")
        prods = cursor.fetchall()
        return render_template("dog.html",prods=prods,name="dogs")


@app.route("/cats",methods=["GET","POST"])
def cats():
    """Show Products of Cats"""
    if request.method == "POST":
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("SELECT prod_sub_id FROM prod_sub;")
        ids = cursor.fetchall()
        for row in ids:
            if int(request.form['submit_button']) == (row['prod_sub_id']):
                cursor.execute("SELECT prod_id FROM product WHERE prod_sub_id=%s",[row['prod_sub_id']])
                prod_id = cursor.fetchone()
                cursor.execute("SELECT * FROM cart WHERE cust_id=%s AND prod_id=%s",([session['user_id']],[prod_id['prod_id']]))
                duplicate = cursor.fetchall()
                if len(duplicate) == 1:
                    cursor.execute("UPDATE cart SET quantity=quantity+1 WHERE cust_id=%s AND prod_id=%s",([session['user_id']],[prod_id['prod_id']]))
                else:
                    cursor.execute("INSERT INTO cart(prod_id,cust_id,quantity) VALUES(%s,%s,%s);",([prod_id['prod_id']],[session["user_id"]],[1]))
                mysql.connection.commit()
                break
            
        return redirect("/cart")

    else:
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("select distinct uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date from product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND uses.pet_id=20;")
        prods = cursor.fetchall()
        return render_template("cat.html",prods=prods)



@app.route("/cart",methods=["GET","POST"])
@login_required
def cart():
    """Show users their cart"""
    if request.method == "POST":
        
        # Address option
        if request.form.get('address') == "address":
            return redirect("/address")
        
        # Remove product from cart
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT cart_id FROM cart WHERE cust_id=%s;",[session["user_id"]])
        cart_id = cursor.fetchall()
        count=0
        for row in cart_id:
            if int(request.form.get("remove_button")) == row['cart_id']:
                cursor.execute("DELETE FROM cart WHERE cart_id=%s;",[row['cart_id']])
                mysql.connection.commit()
                count = 1
                break
        
        if count == 1:
            return redirect("/cart")
        
    
    # Show cart of user
    else:
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute('SELECT cart_id, name,price,quantity,expiry_date,product.prod_id FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]]) 
        records = cursor.fetchall()
        
        if len(records) == 0:
            return render_template("example.html",record="Your cart is empty",title="Cart")
        
        cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]])
        total = cursor.fetchone()
        cursor.execute('SELECT firstname FROM customer WHERE cust_id=%s',[session["user_id"]])
        name = cursor.fetchone()
        return render_template("cart.html",records=records,name=name,total=total)


@app.route("/address",methods = ["GET","POST"])
@login_required
def address():
    """Take address from user and confirm order"""
    if request.method == "POST":

        # Chek if dropdown is used
        if request.form.get("selected") == "selected":
            id=request.form.get("address")
            cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM delivery_location WHERE delivery_location_id=%s",[id])
            add=cursor.fetchone()
            address=f"{add['location_name']}, {add['building_name']}, {add['area_name']},{add['city']} - {add['pincode']})"
            # return render_template("example.html",record1=address)
        else:
            flat = request.form.get("flat")
            building = request.form.get("building")
            street = request.form.get("street")
            city = request.form.get("city")
            pincode = request.form.get("pincode")
            lname = request.form.get("lname")

            if not building:
                return render_template("apology.html",top=400,bottom="must enter building")
            elif not street:
                return render_template("apology.html",top=400,bottom="must enter street")
            elif not city:
                return render_template("apology.html",top=400,bottom="must enter city")
            elif not pincode or len(pincode) !=6:
                return render_template("apology.html",top=400,bottom="must enter correct pincode")
            elif not lname:
                return render_template("apology.html",top=400,bottom="must enter location name")
            elif not flat:
                return render_template("apology.html",top=400,bottom="must enter flat number")
            
            cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
            cursor.execute("INSERT INTO delivery_location(location_name,building_name,area_name,city,pincode,address_name,cust_id) VALUES(%s,%s,%s,%s,%s,%s,%s)",([flat],[building],[street],[city],[pincode],[lname],[session["user_id"]]))
            mysql.connection.commit()
            address=f"{flat} , {building}, {street},{city} - {pincode} "
            
        
        # cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]])
        # total = cursor.fetchone()
        # cursor.execute('SELECT delivery_location_id AS id FROM delivery_location WHERE address_name=%s AND cust_id=%s;',([add],[session["user_id"]]))
        # id = cursor.fetchone()
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute('SELECT cart_id, name,price,quantity,expiry_date,product.prod_id FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]]) 
        records = cursor.fetchall()
        if len(records) == 0:
            return render_template("example.html",record="Your cart is empty",title="Cart")
        cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]])
        total = cursor.fetchone()
        print(records)
        for row in records:
            cursor.execute('INSERT INTO orders(order_date,payment_mode,invoice_amt,quantity,delivery_location_id,cust_id,prod_id) VALUES(CURDATE(),%s,%s,%s,%s,%s,%s);',(["razorpay"],[row['price']*row['quantity']],[row['quantity']],[id],[session["user_id"]],[row['prod_id']]))
            mysql.connection.commit()
            cursor.execute('SELECT order_id FROM orders WHERE order_date=CURDATE() AND payment_mode=%s AND invoice_amt=%s AND quantity=%s AND delivery_location_id=%s AND cust_id=%s AND prod_id=%s;',(["razorpay"],[row['price']*row['quantity']],[row['quantity']],[id],[session["user_id"]],[row['prod_id']]))
            cur_order=cursor.fetchall()
            print(cur_order)
            cursor.execute('INSERT INTO shipment(cust_id,delivery_date,shipment_status,shipment_date,order_id) VALUES(%s,CURDATE(),%s,CURDATE()+5,%s);',([session['user_id'],['Shipped'],[cur_order[0]['order_id']]]))
            mysql.connection.commit()
        cursor.execute('DELETE FROM cart WHERE cust_id=%s',[session['user_id']])
        mysql.connection.commit()


        

        client = razorpay.Client(auth=(razor_id, secret_key))

        DATA = {
            "amount": int(total['total']*100),
            "currency": "INR",
        }
        payment = client.order.create(data=DATA)

        
        # return render_template("confirmOrderNew.html",payment=payment,razor_key=razor_id,records=records,total=total,address=address)

        return render_template("razorpay.html",payment=payment,razor_key=razor_id,records=records,total=total,address=address)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]])
        total = cursor.fetchone()
        cursor.execute('SELECT * FROM delivery_location WHERE cust_id=%s',[session['user_id']])
        address=cursor.fetchall()
        return render_template("address.html",total=total,address=address)


@app.route("/orders")
@login_required
def orders():
    cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT orders. order_id,name,quantity,invoice_amt,order_date,delivery_date,shipment_status FROM orders,product,prod_sub,shipment where orders.prod_id=product.prod_id AND product.prod_sub_id=prod_sub.prod_sub_id AND orders.order_id=shipment.order_id AND orders.cust_id=%s;',[session['user_id']])
    # cursor.execute('SELECT DISTINCT O.quantity,O.invoice_amt,O.order_id,P.name AS product_name,O.order_date,S.shipment_status, date_add(O.order_date, INTERVAL 5 DAY) AS delivery_date from orders O,delivery_location D,prod_sub P,shipment S,product WHERE S.order_id=O.order_id AND O.delivery_location_id=D.delivery_location_id AND O.prod_id=product.prod_id AND product.prod_sub_id=P.prod_sub_id AND O.cust_id=%s;',[session["user_id"]]) 
    order = cursor.fetchall()
    if len(order) == 0:
        return render_template("example.html",record="You don't have any orders")
    # for row in order:
    #     if row["shipment_status"] == None:
    #         shipment = 'Delivered'
    #     else:
    #         shipment = row["shipment_status"]
    
    return render_template("orders.html",order=order,shipment=["Shipped"])

@app.route("/success",methods=['POST'])
@login_required
def success():
    if request.method=="POST":
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        return render_template("confirm.html")


@app.route("/stores",methods=["GET"])
def stores():
    return render_template("stores.html")

@app.route("/consult",methods=["GET"])
def consult():
    return render_template("consult.html")


@app.route("/blogs",methods=["GET"])
def blogs():
    req = requests.get('https://www.animalhearted.com/blogs/animal-blog')
    soup = BeautifulSoup(req.content,'html.parser')
    data = soup.find_all("article",{"class":"article-list-item"})
    resour = []
    for item in data:
        image_tag = item.img
        link = item.find("h2",{"class":"article--excerpt-title"})
        desc = item.find("div",{"class":"article--excerpt-text rte"})
        author = item.find("span",{"class":"article--excerpt-meta-item"})
        title = item.find("h2",{"class":"article--excerpt-title"})
        resour.append({"image_url":image_tag['src'],"link":link.a["href"],"title":title.text,"desc": desc.text,"author":author.text})

    return render_template("community.html",data=resour)


@app.route("/example")
def example():
    cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
    cursor.execute('SELECT cart_id, name,price,quantity,expiry_date,product.prod_id FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]]) 
    records = cursor.fetchall()
    if len(records) == 0:
        return render_template("example.html",record="Your cart is empty",title="Cart")
    cursor.execute('SELECT SUM(price*quantity) AS total FROM product JOIN prod_sub ON product.prod_sub_id = prod_sub.prod_sub_id JOIN cart ON cart.prod_id = product.prod_id WHERE cart.cust_id = %s;',[session["user_id"]])
    total = cursor.fetchone()
    return render_template("razorpay.html",records=records,total=total)

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="POST":
        """If user submits a search"""
        prods=()
        cursor  =  mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT DISTINCT prod_sub.name FROM product,prod_sub,uses,pets WHERE product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id;")
        prods = cursor.fetchall()
        keys = set()
        for i in range(len(prods)):
            keys.add(prods[i]['name'])
        
        key = request.form.get("search")
        key = key.capitalize()

        if key == "Dog" or key == "Dogs":
            return redirect("/dogs")
        
        elif key == "Cat" or key=="Cats":
            return redirect("/cats")
        
        cursor.execute('SELECT name FROM prod_category;')
        category = cursor.fetchall()
        records = -1
        for i in range(4):
            if category[i]['name'] == key:
                cursor.execute("SELECT DISTINCT uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date FROM product,prod_sub,uses,pets,prod_category WHERE product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND prod_sub.prod_category_id = (SELECT prod_category_id FROM prod_category WHERE name=%s)",[category[i]['name']])
                records=cursor.fetchall()
                break
        
        if records != -1:
            return render_template("dog.html",prods=records,name="pets",key=key)
        
        # creating trie object
        t = Trie()
        
        # creating the trie structure with the
        # given set of strings.
        t.formTrie(keys)
        
        # autocompleting the given key using
        # our trie structure.
        comp = t.printAutoSuggestions(key)
        
        if comp == -1:
            return render_template("apology.html",top=400,bottom="No other products found with this word")
        elif comp == 0:
            cursor.execute("SELECT DISTINCT uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date FROM product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND prod_sub.name LIKE %s;",['%' + key + '%'])
            records = cursor.fetchall()
            if len(records) == 0:
                return render_template("apology.html",top=400,bottom="No product found with this word")
            return render_template("dog.html",prods=records,name="pets",key=key)
        prods=[]
        for name in comp:
            cursor.execute("SELECT DISTINCT uses.pet_id,pets.pet_type,product.prod_sub_id,prod_sub.name,product.price,product.expiry_date FROM product,prod_sub,uses,pets where product.prod_sub_id= prod_sub.prod_sub_id AND pets.pet_id=uses.pet_id AND uses.prod_id=product.prod_id AND prod_sub.name LIKE %s;",[name])
            prods.append(cursor.fetchone())
        prods=tuple(prods)
        return render_template("dog.html",prods=prods,name="pets",key=key)
    else:
        return redirect("/")



if __name__ == "__main__":
    app.run(debug=True)