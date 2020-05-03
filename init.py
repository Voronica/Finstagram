from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import os
import time
import hashlib
import datetime

app = Flask(__name__)
SALT = 'cs3083'
app.config["IMAGES_DIR"] = "static"

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
    password = request.form['password']+SALT
    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed))
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
    password = request.form['password']+SALT
    lastName = request.form['lastName']
    firstName = request.form['firstName']
    email = request.form['email']
    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()

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
        cursor.execute(ins, (username, hashed, firstName, lastName, email))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor();

    query = '''
    (SELECT pID, filePath, postingDate
    FROM SharedWith NATURAL JOIN BelongTo NATURAL JOIN Photo
    WHERE username= %s)
    UNION
    (SELECT pID, filePath, postingDate
    FROM photo JOIN follow ON photo.poster = follow.followee
    WHERE follow.follower = %s AND follow.followStatus = %s AND photo.allFollowers = %s)
    ORDER BY postingDate DESC'''
    cursor.execute(query, (user, user, 1, 1))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, posts=data)


@app.route("/upload_image", methods=["GET"])
def upload_image():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT groupName, groupCreator FROM BelongTo WHERE username=%s'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template("upload.html", groups=data)


@app.route('/post', methods=['GET', 'POST'])
def post():
    user = session['username']
    cursor = conn.cursor()
    image_file = request.files['file']
    caption = request.form['caption']
    all_followers = request.form['public']
    posting_date = time.strftime('%Y-%m-%d %H:%M:%S')

    # getting pID, filePath
    query = 'INSERT INTO Photo VALUES ()'
    cursor.execute(query)
    query = 'SELECT LAST_INSERT_ID() FROM Photo'
    cursor.execute(query)
    pID = cursor.fetchone()['LAST_INSERT_ID()']
    file_path = os.path.join(app.config['IMAGES_DIR'], str(pID))
    # storing photo to local directory
    image_file.save(file_path)

    # add info to database
    query = 'UPDATE Photo SET postingDate=%s, filePath=%s, allFollowers=%s, caption=%s, poster=%s WHERE pID=%s'
    cursor.execute(query,(posting_date, file_path, all_followers, caption, user, pID))

    # updating SharedWith
    friendGroups = request.form.getlist('friendGroups')
    for group in friendGroups:
        temp = group.split('by')
        query = 'INSERT INTO SharedWith VALUES(%s, %s, %s)'
        cursor.execute(query, (pID, temp[0], temp[1]))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/show_details', methods=['GET', 'POST'])
def show_details():
    user = session['username']
    photo_ID = request.form['details']
    cursor = conn.cursor()

    #get poster
    query = "SELECT pID, firstName, lastName, postingDate FROM photo JOIN person ON photo.poster=person.username WHERE photo.pID= %s"
    cursor.execute(query,(photo_ID))
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



@app.route('/manage_follow', methods=['GET', 'POST'])
def manage_follow():
    user = session['username']
    cursor = conn.cursor()
    # find all follow requests
    query = "SELECT follower FROM follow WHERE followee = %s AND followStatus = 0"
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template("manage_follow.html", username = user, allRequests = data)

@app.route('/process_follow', methods=['GET', 'POST'])
def process_follow():
    user = session['username']
    cursor = conn.cursor()
    if (request.form.get('search')):
        follow = request.form['follow']
        if (follow != ''):
            # checking username actually exists
            query = 'SELECT * FROM Person WHERE username = %s'
            cursor.execute(query, (follow))
            data = cursor.fetchone()
            if (data):
                query = "INSERT INTO follow (follower, followee, followStatus) VALUES (%s, %s, 0)"
                cursor.execute(query, (user, follow))
                conn.commit()
                cursor.close()
                return redirect(url_for('manage_follow'))
        error = 'Please search for a valid user.'
        return render_template('manage_follow.html', error = error)

    else:
        temp = request.form['manage'].split(' ', 1)
        action = temp[0]
        follower = temp[1]
        if action == 'accept':
            query = 'UPDATE Follow SET followStatus=1 WHERE followee = %s AND follower = %s'
        else:
            query = 'DELETE FROM Follow WHERE followee = %s AND follower = %s'
        cursor.execute(query, (user, follower))
        conn.commit()
        cursor.close()
        return redirect(url_for('manage_follow'))

@app.route('/manage_friendgroup_page')
def manage_friendgroup_page():
    return render_template('manage_friendgroup_page.html')

@app.route('/create_fg_page')
def create_fg_page():
    return render_template('create_fg_page.html')

@app.route('/create_friendgroup', methods=['GET', 'POST'])
def create_friendgroup():
    user = session['username']
    cursor = conn.cursor()
    groupName = request.form['name']
    groupDescription = request.form['description']

    #find the user's friendgroup
    query = "SELECT groupName FROM friendGroup WHERE groupName = %s and groupCreator = %s"
    cursor.execute(query, (groupName, user))
    data = cursor.fetchall()
    #check if groupname already exist
    if(data):
        error = "Friend group with the same name already exists."
        return render_template('manage_friendgroup_page.html', error = error)
    else:
        #create grop
        query = "INSERT INTO friendGroup (groupName, groupCreator, description) VALUES (%s, %s, %s)"
        cursor.execute(query, (groupName, user, groupDescription))
        #add group creator to the group
        query = 'INSERT INTO BelongTo(username, groupName, groupCreator) VALUES (%s, %s, %s)'
        cursor.execute(query, (user, groupName, user))
        conn.commit()
        cursor.close()
        message = 'Success!'
        return render_template('manage_friendgroup_page.html', message = message)

@app.route('/add_to_fg_page')
def add_to_fg_page():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT groupName, description FROM FriendGroup WHERE groupCreator = %s'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('add_to_fg_page.html', fgroups=data)

@app.route('/add_to_friendgroup', methods=['GET', 'POST'])
def add_to_friendgroup():
    user = session['username']
    group = request.form['fgroup']
    member = request.form['newMember']
    cursor = conn.cursor()
    # check if username actually exists
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (member))
    data = cursor.fetchall()
    if (data):
        # check if username already belongs to group
        query = 'SELECT * FROM BelongTo WHERE (groupName, groupCreator, username)=(%s, %s, %s)'
        cursor.execute(query, (group, user, member))
        data = cursor.fetchall()
        if (data):
            error = 'This person is already in selected friend group.'
            return render_template('manage_friendgroup_page.html', error=error)
        else:
            query = 'INSERT INTO BelongTo(groupName, groupCreator, username) VALUES (%s, %s, %s)'
            cursor.execute(query, (group, user, member))
            conn.commit()
            cursor.close()
            message = 'Success!'
            return render_template('manage_friendgroup_page.html', message = message)
    else:
        error = 'Please enter a valid username.'
        return render_template('manage_friendgroup_page.html', error=error)

@app.route('/manage_tags', methods=['GET', 'POST'])
def manage_tags():
    user = session['username']
    cursor = conn.cursor()
    photo_ID = request.form['search']
    tagged = request.form['tagged']
    if (tagged == user):
        query = "INSERT INTO tag (pID, username, tagStatus) VALUES (%s, %s, %s)"
        cursor.execute(query, (photo_ID, tagged, 1))
        conn.commit()
        cursor.close()
        message = 'manage tag succeed'
    else:
        #check whether tagged can see this photo
        query = "SELECT * FROM photo JOIN follow ON photo.poster = follow.followee\
                 WHERE photo.poster = %s AND follow.follower = %s AND follow.followStatus = %s"
        cursor.execute(query, (user, tagged, 1))
        data = cursor.fetchall()
        #check if data empty
        if(data):
            query = "INSERT INTO tag (pID, username, tagStatus) VALUES (%s, %s, %s)"
            cursor.execute(query, (photo_ID, tagged, 0))
            conn.commit()
            cursor.close()
            message = 'manage tag succeed'
        else:
            message = 'he/she cannot process this tag'
    return render_template('message.html', username = user, message = message)

@app.route('/manage_tag_page', methods=['GET', 'POST'])
def manage_tag_page():
    user = session['username']
    cursor = conn.cursor()
    query = "SELECT * FROM tag WHERE username = %s AND tagStatus = %s"
    cursor.execute(query, (user ,0))
    data = cursor.fetchall()

    return render_template('manage_tag_page.html', username = user, allRequests = data)

@app.route('/process_tag', methods=['GET', 'POST'])
def process_tag():
    user = session['username']
    cursor = conn.cursor()
    temp = request.form['process'].split(' ', 1)
    action = temp[0]
    photo_ID = temp[1]

    if(action == 'accept'):
        query = "UPDATE tag SET tagStatus=1 WHERE pID = %s AND username = %s"

    elif(action == 'deny'):
        query = "DELETE FROM tag WHERE pID = %s AND username = %s"

    cursor.execute(query, (photo_ID ,user))
    conn.commit()
    cursor.close()
    return redirect(url_for('manage_tag_page'))

@app.route('/add_reactions_page', methods=['GET', 'POST'])
def add_reactions_page():
    user = session['username']
    pID = request.form['reactTo']
    # check if user has already reacted to the same photo
    query = "SELECT * FROM ReactTo WHERE (username, pID)=(%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (user, pID))
    data = cursor.fetchall()
    if (data):
        error = "You have alread reacted to this photo. You can go back and click on 'show details' to see your reactions."
        return render_template('add_reactions_page.html', error=error)
    else:
        query = "SELECT pID, filePath, poster FROM Photo WHERE pID = %s"
        cursor.execute(query, (pID))
        data = cursor.fetchall()
        return render_template('add_reactions_page.html', data=data)

@app.route('/add_reactions', methods=['GET', 'POST'])
def add_reactions():
    user = session['username']
    pID = request.form['reactions']
    comment = request.form['comment']
    emoji = request.form['emoji']
    reactionTime = str(datetime.datetime.now())

    cursor = conn.cursor()
    # change column collation to store emoji
    query = "ALTER TABLE ReactTo MODIFY emoji VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    cursor.execute(query, ())
    query = "ALTER TABLE ReactTo MODIFY comment VARCHAR(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    cursor.execute(query, ())
    # store data into database
    query = "INSERT INTO ReactTo(username, pID, reactionTime, comment, emoji) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(query, (user, pID, reactionTime, comment, emoji))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

  # search posts by a certain poster's name
@app.route('/search_by_poster', methods=['GET', 'POST'])
def search_by_poster():
    user = session['username']
    cursor = conn.cursor()
    if request.method=='POST':
        keyword=request.form['keyword']
        # the displayed photo have to be either posted by the person
        # or it is shared by someone with a group that person in
        # or it is posted by the person he follows
        # it's displayed in time descending order
        sql="SELECT * " \
            "FROM Photo " \
            "WHERE poster=%s AND " \
            "pID IN (SELECT pID FROM Photo JOIN person ON Photo.poster=person.username " \
            "WHERE (pID IN (SELECT pID FROM belongto NATURAL JOIN sharedwith WHERE username = %s)) " \
            "OR (poster = %s) " \
            "OR (poster IN (SELECT followee FROM Follow WHERE follower = %s and followstatus = 1) and allFollowers = 1)) " \
            "ORDER BY postingDate DESC"
        cursor.execute(sql, (keyword, user, user, user))
        data=cursor.fetchall()
        return render_template('search_result.html', user=user, posts=data)
    return render_template('home.html')


# search posts by a certain tag name
@app.route('/search_by_tag', methods=['GET', 'POST'])
def search_by_tag():
    user = session['username']
    cursor = conn.cursor()
    if request.method=='POST':
        keyword=request.form['keyword']
        # the displayed photo have to be either posted by the person
        # or it is shared by someone with a group that person in
        # or it is posted by the person he follows
        # in all three cases, the person also needs to be tagged
        # It's displayed in time descending order
        sql="SELECT * " \
            "FROM Photo NATURAL JOIN tag " \
            "WHERE tagstatus=true AND username=%s AND " \
            "pID IN (SELECT pID FROM Photo JOIN person ON Photo.poster=person.username " \
            "WHERE (poster = %s) " \
            "OR  (poster IN (SELECT followee FROM follow WHERE " \
            "follower = %s and followstatus = 1) and allFollowers = 1) " \
            "OR (pID IN (SELECT pID FROM belongto NATURAL JOIN sharedwith WHERE username = %s))) " \
            "ORDER BY postingDate DESC"
        cursor.execute(sql, (keyword, user, user, user))
        data=cursor.fetchall()
        return render_template('search_result.html', user=user, posts=data)
    return render_template('home.html')


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')


app.secret_key = 'some key that you will never guess'

if __name__ == '__main__':
    app.run('127.0.0.1', 5000, debug = True)
