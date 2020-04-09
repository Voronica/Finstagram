from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import os
import time


app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password='root',
                       db='finstagram',
                       charset='utf8',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def index():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')


#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    lastName = request.form['lastName']
    firstName = request.form['firstName']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, password, firstName, lastName, ''))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor();
    #query on testing
    query = "SELECT pID, filePath, postingDate FROM Photo WHERE poster= %s ORDER BY postingdate DESC"
    
    #later on will use query:
    #query = "(SELECT pID, filePath, postingDate FROM photo JOIN follow ON photo.poster=follow.followee" \
            #"WHERE allFollowers=1 AND followStatus=1 AND follower= %s)" \
            #"UNION " \
            #"(SELECT pID, filePath, postingDate FROM sharedWith NATURAL JOIN belongTo NATURAL JOIN photo WHERE)" \
            #"username = %s) ORDER BY postingDate DESC"
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, posts=data)


@app.route("/upload_image", methods=["GET"])
def upload_image():
    return render_template("upload.html")

app.config["IMAGES_DIR"] = "/Users/voronica/Desktop/Finstagram/static"

@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = conn.cursor()
    image_file = request.files['file']
    file_name = image_file.filename
    file_path = os.path.join(app.config["IMAGES_DIR"], file_name)
    all_followers = request.form['public']
    image_file.save(file_path)
    #add info to database
    query = "INSERT INTO photo (poster,postingDate, filePath, allFollowers) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (username, time.strftime('%Y-%m-%d %H:%M:%S'), file_path, all_followers))
    conn.commit()

    query = "SELECT pID, filePath, postingDate FROM Photo WHERE poster= %s ORDER BY postingdate DESC"
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close() 
    
    return render_template('home.html', username=username, posts=data)

@app.route('/show_details', methods=['GET', 'POST'])
def show_details():
    user = session['username']
    photo_ID = request.form['details']
    cursor = conn.cursor()

    #get posts
    query = "SELECT pID, firstName, lastName, postingDate FROM photo JOIN person ON photo.poster=person.username WHERE photo.poster= %s AND photo.pID= %s ORDER BY postingdate DESC"
    cursor.execute(query,(user, photo_ID))
    poster = cursor.fetchall()

    #get tagged
    query = "SELECT username, firstName, lastName FROM tag NATURAL JOIN Person WHERE tag.pID = %s AND tag.tagStatus=1"
    cursor.execute(query, (photo_ID))
    tag = cursor.fetchall()

    #get reactions
    query = "SElECT username, emoji, comment FROM reactTo WHERE pID= %s"
    cursor.execute(query, (photo_ID))
    reaction = cursor.fetchall()

    cursor.close()
    return render_template("show_details.html", username=user, posts=poster, tagged=tag, reactions=reaction)

#still working on type_follow
@app.route('/type_follow', methods=['GET', 'POST'])
def type_follow():
    user = session['username']
    follow = request.form['follow']
    cursor = conn.cursor()
    query = "INSERT INTO follow (follower, followee, followStatus) VALUES (%s, %s, 0)"
    cursor.execute(query, (user, follow))
    conn.commit()
    cursor.close()

    return render_template('home.html', username=user)

#still working on show_following
@app.route('/show_following', methods=['GET', 'POST'])
def show_following():
    user = session['username']
    
    cursor = conn.cursor()
    query = "SELECT username, firstName, lastName , followStatus FROM follow JOIN person ON follow.followee=person.username WHERE follow.follower = %s"
    cursor.execute(query, (user))
    following = cursor.fetchall()
    cursor.close()

    return render_template("show_following.html", username=user, followings = following)
    

app.secret_key = 'some key that you will never guess'

if __name__ == '__main__':
    app.run('127.0.0.1', 5000, debug = True)

