import os

from flask import Flask, render_template, redirect, request, make_response
from wtform_fields import *
import models as mds
from passlib.hash import pbkdf2_sha256
from flask_login import LoginManager, login_user, current_user, logout_user
import requests
from clarifai.errors import ApiError
import uuid
from datetime import date
from flask_restful import Api, Resource

# APP
app = Flask(__name__)
api = Api(app)
# app.secret_key = os.environ.get('SECRET')
app.secret_key = 'SECRET'

# database configs
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgres://jhivjrfwkjzlff:9c37a83349353453a04fb5ae5102d86d9b84ae8fea94b46c24e01c3d4a4a0da2@ec2-54-81-37-115.compute-1.amazonaws.com:5432/d3lm6g7l0bs75i'

# 'postgres://jhivjrfwkjzlff:9c37a83349353453a04fb5ae5102d86d9b84ae8fea94b46c24e01c3d4a4a0da2@ec2-54-81-37-115.compute-1.amazonaws.com:5432/d3lm6g7l0bs75i'
# os.environ.get('DATABASE_URL')
db = mds.SQLAlchemy(app)

# app configs
login = LoginManager()
login.init_app(app)


# load the current user
@login.user_loader
def load_user(user_id):
    return mds.User.query.get(int(user_id))


class Index(Resource):
    """
    Landing page components
    """

    def add_user(self, user):
        """
        adds new registered user to database
        :param user:
        :return:
        """
        db.session.add(user)
        db.session.commit()
        db.session.close()

    def get(self):
        reg_form = RegistrationForm()
        return make_response(render_template('index.html', form=reg_form), 200)

    def post(self):
        reg_form = RegistrationForm()
        if reg_form.validate_on_submit():
            email = reg_form.email.data
            password = reg_form.password.data

            # hash password before adding to database
            hashed_paswd = pbkdf2_sha256.hash(password)

            # define user in order to add to db
            user = mds.User(email=email, password=hashed_paswd)
            self.add_user(user)
            # redirect to login page after register
            login = Login()
            return redirect('login')


class Login(Resource):
    """
    Login Page components
    """

    def validate_login(self):
        # get the login form
        login_form = LoginForm()

        # Validating users input in login form
        if login_form.validate_on_submit():
            user_object = mds.User.query.filter_by(email=login_form.email.data).first()
            login_user(user_object)
            return True
        else:
            return False

    def get(self):
        login_form = LoginForm()
        return make_response(render_template('login.html', form=login_form), 200)

    def post(self):
        if self.validate_login():
            # redirect to pre_quiz(dashboard) page after login
            return redirect('pre_quiz')
        else:
            return 'Incorrect username or password'


class Logout(Resource):
    def get(self):
        logout_user()
        # redirect to login page after logout
        return redirect('/login')


class PreQuiz(Resource):
    try:
        # get current users email
        user_email = current_user.email

        # get the text before @ to show user id after welcome text
        user_id_arr = user_email.split("@")
        user_id = user_id_arr[0]
    except:
        user_id = 'User'

    # get available topics from API
    topics = requests.get('https://mathgen-api.herokuapp.com/topics')

    # save topics in a var
    topic_json = topics.json()

    def get(self):
        # get the keys from each topic to show in select menu
        topics_list = list(self.topic_json['topics'].keys())

        # render pre-quiz.html
        return make_response(render_template('pre_quiz.html', topics=topics_list), 200)

    def post(self):
        # get number of requested questions from form
        question_num = request.form.get('questionNumber')
        selected_topic = request.form.get('topic')
        print(selected_topic)
        # make an API call based on users choices
        if selected_topic == 'union of sets' or selected_topic == 'symmetric difference' or selected_topic == 'partition' or selected_topic == 'difference of sets' or selected_topic == 'complement' or selected_topic == 'cartesian product':
            resp = requests.get(
                'https://mathgen-api.herokuapp.com' + self.topic_json['topics'][selected_topic] + question_num + '/11')
        else:
            resp = requests.get(
                'https://mathgen-api.herokuapp.com' + self.topic_json['topics'][selected_topic] + question_num)

        # check if the API call was successful
        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiError('GET /tasks/ {}'.format(resp.status_code))

        # save response from API
        response = resp.json()

        # change quiz from json to string
        quiz_json = str(response)

        # generates a unique id for quiz
        quiz_id = uuid.uuid1().hex

        # add quiz_id and quiz_json to database
        quiz_query = mds.QuizJson(quiz_id=quiz_id, quiz_json=quiz_json)
        db.session.add(quiz_query)
        db.session.commit()
        db.session.close()

        # redirect to quiz page
        return redirect("quiz?quiz_id=" + quiz_id)


class Quiz(Resource):

    def get(self):
        # get quiz_id sent from pre-quiz
        quiz_id = request.args.get("quiz_id")

        # get the row with requested quiz_id
        user_object = mds.QuizJson.query.filter_by(quiz_id=quiz_id).first()

        # get the quiz in json
        quizJson = user_object.quiz_json

        # change quiz to dict and get the questions array
        questions = eval(quizJson)['questions']

        # number of questions
        question_num = len(questions)

        # get current users emaik
        user_email = current_user.email

        # get the date for today
        submit_date = str(date.today())

        # to calculate score
        question_num = len(questions)
        point = 100 / question_num
        score_int = 0

        # render quiz.html on GET request
        return make_response(
            render_template("quiz.html", quiz_id=quiz_id, questions=questions, question_num=question_num), 200)

    def post(self):
        # get quiz_id sent from pre-quiz
        quiz_id = request.args.get("quiz_id")

        # get the row with requested quiz_id
        user_object = mds.QuizJson.query.filter_by(quiz_id=quiz_id).first()

        # get the quiz in json
        quizJson = user_object.quiz_json

        # change quiz to dict and get the questions array
        questions = eval(quizJson)['questions']

        # number of questions
        question_num = len(questions)

        # get current users emaik
        user_email = current_user.email

        # get the date for today
        submit_date = str(date.today())

        # to calculate score
        question_num = len(questions)
        point = 100 / question_num
        score_int = 0

        # save users selections in an array
        user_selections = []

        for i in questions:
            questionId = i['questionID']
            selected = int(request.form.get(questionId))
            user_selections.append(selected)
            if selected == i['correctAnswer']:
                score_int = score_int + point

        # save calculated score in a var
        score = str(score_int)

        # add the quiz with users answers to database
        quiz_query = mds.Scores(quiz_id=quiz_id, user_email=user_email, user_selections=user_selections,
                                submit_date=submit_date, score=score)
        db.session.add(quiz_query)
        db.session.commit()
        db.session.close()

        return make_response(
            render_template("post_quiz.html", quiz_id=quiz_id, questions=questions, user_selections=user_selections,
                            submit_date=submit_date, user_email=user_email, score=score), 200)


class Progress(Resource):

    def get(self):
        # get current user info
        user_email = current_user.email
        quesries = mds.Scores.query.filter_by(user_email=user_email).all()
        scores = []
        dates = []
        for i in quesries:
            scores.append(i.score)
            dates.append(i.submit_date)
        score_str = (str(scores).replace("[", '').replace(']', '').replace("'", ""))
        date_str = (str(dates).replace("]", '').replace('[', '').replace("'", ""))

        table_data = []
        for i in range(len(scores)):
            arr = []
            arr.append(scores[i])
            arr.append(dates[i])
            table_data.append(arr)
        table_data.reverse()

        return make_response(
            render_template("progress.html", score_str=score_str, date_str=date_str, table_data=table_data), 200)


class About(Resource):
    def get(self):
        return make_response(
            render_template("about.html"), 200)


class Errors(Resource):

    @app.errorhandler(404)
    def page_not_found(e):
        # note that we set the 404 status explicitly
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def not_logged_in(e):
        # note that we set the 404 status explicitly
        return render_template('500.html'), 500


# Assign routes to classes
api.add_resource(Index, "/")
api.add_resource(Login, "/login")
api.add_resource(Logout, "/logout")
api.add_resource(PreQuiz, "/pre_quiz")
api.add_resource(Quiz, "/quiz")
api.add_resource(Progress, "/progress")
api.add_resource(About, "/about")

# app run
if __name__ == "__main__":
    app.run(debug=True)
