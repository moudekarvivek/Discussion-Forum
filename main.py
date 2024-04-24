import datetime
import io
from flask import Flask, redirect, render_template, request, jsonify, flash, url_for, send_file
import flask
from flask_wtf import FlaskForm
from sqlalchemy import Identity
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import UserMixin, login_user,logout_user,login_required,logout_user,current_user,LoginManager
import base64

app = Flask(__name__)

#Configurations
app.secret_key = 'super secret key'
#database configuration---------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DiscussionForum.db'
db = SQLAlchemy(app)
#JWT Configuration--------------------------------


#flask_login stuff
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='/login'

@login_manager.user_loader
def load_user(email_id):
    return User.query.get(email_id)

#Table structure
class User(db.Model,UserMixin):
    __tablename__ = 'user'
    email = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(12))
    questions = db.relationship('Question', back_populates = 'user')

    def __init__(self,email,username,password):
        self.email = email
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.email)
    
class Question(db.Model):
    __tablename__ = 'question'
    question_id = db.Column(db.Integer, Identity(start=1, cycle=True),primary_key=True, autoincrement=True)
    question_description = db.Column(db.String)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    question_by = db.Column(db.String, db.ForeignKey('user.email'), nullable = False)
    user = db.relationship('User', back_populates = 'questions')
    answers = db.relationship('Answer', back_populates = 'question')

class Answer(db.Model):
    answer_id = db.Column(db.Integer, Identity(start=1, cycle=True),primary_key=True, autoincrement=True)
    answer_description = db.Column(db.String)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    answer_by = db.Column(db.String, nullable = False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.question_id'))
    question = db.relationship('Question', back_populates = 'answers')
    filename = db.Column(db.String)
    data = db.Column(db.LargeBinary)


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        print('request received for login (GET)')
        return render_template('login.html')
    else:
        print('request received for login (POST)')
        email = request.form['email']
        password = request.form['password']

        try:
            user = User.query.get(email)
            if user is not None:
                if user.password == password:
                    print('-------')
                    login_user(user)
                    #
                    next = flask.request.args.get('next')
                    # url_has_allowed_host_and_scheme should check if the url is safe
                    # for redirects, meaning it matches the request host.
                    # See Django's url_has_allowed_host_and_scheme for an example.
                    # if not url_has_allowed_host_and_scheme(next, request.host):
                    #     return flask.abort(400)

                    return flask.redirect(next or flask.url_for('menupage')) 
                    #
                    
                    return redirect(url_for('menupage'))  
                else:
                    flash('Invalid password')
                    return render_template('login.html',)
            else:
                flash('email-id not found')
                return render_template('login.html')
            
        except Exception as e:
            print(e)
        
        #return render_template('home.html')

@app.route('/logout',methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/registration', methods=['POST','GET'])
def register():
    if flask.request.method == 'GET':
        print('request received for registration (GET)')
        return render_template('registration.html')    
    else:
        print('request received for registration (POST)')
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        repeate_password = request.form['repeatePassword']

        if repeate_password != password:
            flash('password did not match with repeate password')
            return render_template('registration.html')
        
        newUser = User(email=email, username=name, password=password)
        try:
            db.session.add(newUser)
            db.session.commit()
            questions = Question.query.all()
            return render_template('login.html')
        except IntegrityError as ie:
            print(ie)
            flash(f'Email-id {email} already exist !')
            return render_template('registration.html')
        except Exception as e:
            print(e)
        


@app.route("/menupage",methods=['GET','POST'])
@login_required
def menupage():
    print(current_user.email)
    print('in menupage')
    questions = Question.query.all()
    print(questions)
    return render_template('MenuPage.html', questions=questions)

# {{ question.question_id}} - {{question.question_description}} - {{question.date}} -
#                 {{question.question_by}}

# insert into question(question_description, date, question_by) values('Where is canteen2', '2023-08-03 10:30:00', 'gautam@gmail.com');

@app.route('/askQ', methods=['GET','POST'])
@login_required
def askQ():
    if flask.request.method == 'GET':
        print('request received for askQ (GET)')
        return render_template('askQ.html')
    else:
        print('request received for askQ (POST)')
        new_question_description = request.form['question_description']
        question_by = current_user.email

        new_question = Question(question_description = new_question_description, question_by = question_by)

    try:
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully !')
        return render_template('askQ.html')
    except Exception as e:
        print(e)

@app.route('/answer/<int:question_id>', methods = ['POST','GET'])
@login_required
def getQuestionId(question_id):
    if flask.request.method == 'GET':
        print(question_id)
        question = Question.query.get(question_id)
        answers = Answer.query.filter_by(question_id=question_id).all()
        return render_template('answer.html',question=question, answers = answers)
    

def convertToBase64(file):
    file_base64 = base64.b64encode(file.read())
    return file_base64
        

@app.route('/answer/addanswer/<int:question_id>',methods=['POST'])
@login_required
def addAnswer(question_id):
    answer_description = request.form['answer']
    answer_pdf = request.files['fileToUpload']

    #question_id = request.args['question_id']
    answer = Answer(answer_description=answer_description, answer_by = current_user.email, question_id = question_id, filename = answer_pdf.filename, data=convertToBase64(answer_pdf))
    print(answer.filename)
    try : 
        db.session.add(answer)
        db.session.commit()
        flash("Answer Added Successfully !")
    except Exception as e:
        print(e)
        flash("some error occured !")
    next = flask.request.args.get('next')
    return flask.redirect(next or flask.url_for('menupage'))

@app.route('/updateProfile', methods = ['GET','POST'])
@login_required
def updateProfile():
    if flask.request.method == 'GET':
        print(current_user)
        user = User.query.get(current_user.email)
        return render_template('updateProfile.html',user=user)
    else:
        #new_email = request.form['email']
        new_name = request.form['name']
        new_password = request.form['password']

        # if new_email == '':
        #     new_email = current_user.email
        if new_name == '':
            new_name = current_user.name
        if new_password == '':
            new_password = current_user.password
        
        try:
            user_to_update = User.query.get(current_user.email)
            #user_to_update.email = new_email
            user_to_update.username = new_name
            user_to_update.password = new_password

            db.session.add(user_to_update)
            db.session.commit()
            db.session.refresh(user_to_update)
            flash('User updated successfully !')
        except Exception as e:
            print(e)
            flash('User updated Error !!')
        return render_template('updateProfile.html',user=user_to_update)
        
        
@app.route('/getPdf/<int:answer_id>', methods=['GET'])
def getPdf(answer_id):
    pdf = Answer.query.get(answer_id)
    pdf_bytes = pdf.data
    #return send_file(io.BytesIO(pdf_bytes), download_name = pdf.filename, mimetype='application/pdf', as_attachment=True)

    return send_file(base64.decodebytes(pdf_bytes), download_name = pdf.filename, mimetype='application/pdf')

    #return send_file(base64.decodebytes(pdf_bytes), download_name = pdf.filename, mimetype='application/pdf')

    #return render_template('displayPdf.html', pdf=base64.decodebytes(pdf_bytes))
    


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run('0.0.0.0', debug=True)
    