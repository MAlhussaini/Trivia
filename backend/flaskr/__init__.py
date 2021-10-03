import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
    page = request.args.get("page", 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [book.format() for book in selection]
    current_questions = questions[start:end]

    return current_questions


def create_app(test_config=None):
  # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    CORS(app)

    # CORS Headers
    @app.after_request
    def after_request(response):
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization,true"
        )
        response.headers.add(
            "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
        )
        return response

    # curl http://127.0.0.1:5000/categories
    @app.route("/categories")
    def retrieve_categories():
        categories_query = Category.query.order_by(Category.id).all()
        categories = [category.format() for category in categories_query]
        if len(categories) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "categories":categories
            }
        )
  
    # curl http://127.0.0.1:5000/categories/5/questions
    @app.route("/categories/<int:category_id>/questions")
    def get_by_category(category_id):
        selection = Question.query.filter_by(category=category_id).order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)
        categories_query = Category.query.order_by(Category.id).all()
        categories = [category.format() for category in categories_query]

        if len(current_questions) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "questions": current_questions,
                "total_questions": len(selection),
                "current_category":category_id,
                "categories":categories
            }
        )
        
    # curl http://127.0.0.1:5000/questions
    @app.route("/questions")
    def retrieve_all_questions():
        selection = Question.query.order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)
        categories_query = Category.query.order_by(Category.id).all()
        categories = [category.format() for category in categories_query]
        if len(current_questions) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "questions": current_questions,
                "total_questions": len(selection),
                "categories":categories
            }
        )

    # curl -X DELETE http://127.0.0.1:5000/questions/10 
    @app.route("/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        try:
            question = Question.query.filter(Question.id == question_id).one_or_none()

            if question is None:
                abort(404)

            question.delete()
            selection = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, selection)
            categories_query = Category.query.order_by(Category.id).all()
            categories = [category.format() for category in categories_query]

            return jsonify(
                {
                    "success": True,
                    "deleted": question_id,
                    "questions": current_questions,
                    "total_questions": len(selection),
                    "categories":categories
                }
            )
        except:
            abort(422)

    # curl -X POST -H "Content-Type: application/json" -d '{"question":"test_question", "answer":"test_answer", "difficulty":"3", "category":"5"}' http://127.0.0.1:5000/questions   
    # curl -X POST -H "Content-Type: application/json" -d '{"searchTerm":"what"}' http://127.0.0.1:5000/questions   
    @app.route("/questions", methods=["POST"])
    def create_question():
        body = request.get_json()

        new_question = body.get("question", None)
        new_answer = body.get("answer", None)
        new_difficulty = body.get("difficulty", None)
        new_category = body.get("category", None)
        search = body.get("searchTerm", None)

        try:
            categories_query = Category.query.order_by(Category.id).all()
            categories = [category.format() for category in categories_query]

            if search:
                selection = Question.query.order_by(Question.id).filter(
                    Question.question.ilike("%{}%".format(search))
                )
                current_questions = paginate_questions(request, selection)
                return jsonify(
                    {
                        "success": True,
                        "questions": current_questions,
                        "total_questions": len(selection.all()),
                        "current_category":categories
                    }
                )
            else:
                question = Question(question=new_question, answer=new_answer, difficulty=new_difficulty, category=new_category)
                question.insert()

                selection = Question.query.order_by(Question.id).all()
                current_questions = paginate_questions(request, selection)
                if len(current_questions) == 0:
                    abort(404)

                return jsonify(
                    {
                        "success": True,
                        "created": question.id,
                        "questions": current_questions,
                        "total_questions": len(selection),
                        "current_category":categories
                    }
                )

        except:
            abort(422)

    # curl -X POST -H "Content-Type: application/json" -d '{"previous_questions":[] ,"quiz_category":null}' http://127.0.0.1:5000/quizzes   
    # curl -X POST -H "Content-Type: application/json" -d '{"previous_questions":["Who discovered penicillin?"] ,"quiz_category":1}' http://127.0.0.1:5000/quizzes   
    # curl -X POST -H "Content-Type: application/json" -d '{"previous_questions":["What is the heaviest organ in the human body?","Hematology is a branch of medicine involving the study of what?"] ,"quiz_category":1}' http://127.0.0.1:5000/quizzes   
    @app.route("/quizzes", methods=["POST"])
    def play():
        body = request.get_json()

        previous_questions = body.get("previous_questions", None)
        quiz_category = body.get("quiz_category", None)
        try:
            if quiz_category is None:
                question = Question.query.order_by(func.random()).first()
            else:
                question = Question.query.filter(~Question.question.in_(previous_questions)).filter_by(category=quiz_category).order_by(func.random()).first()
            if question is None:
                abort(422)
            return jsonify(
                {
                    "success": True,
                    "question": question.question,
                    "answer": question.answer,
                    # "questions": question.format(), #Not needed.
                }
            )
        except:
            abort(422)



    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify({"success": False, "error": 404, "message": "resource not found"}),
            404,
        )

    @app.errorhandler(422)
    def unprocessable(error):
        return (
            jsonify({"success": False, "error": 422, "message": "unprocessable"}),
            422,
        )

    @app.errorhandler(400)
    def bad_request(error):
        return (jsonify({"success": False, "error": 400, "message": "bad request"}), 400)



    '''
    #*Completed: 
    Set up CORS. Allow '*' for origins. Delete the sample route after completing the TODOs
    '''

    '''
    #*Completed: 
    Use the after_request decorator to set Access-Control-Allow
    '''

    '''
    #*Completed: 
    Create an endpoint to handle GET requests 
    for all available categories.
    '''


    '''
    #*Completed: 
    Create an endpoint to handle GET requests for questions, 
    including pagination (every 10 questions). 
    This endpoint should return a list of questions, number of total questions, current category, categories. 

    TEST: At this point, when you start the application
    you should see questions and categories generated,
    ten questions per page and pagination at the bottom of the screen for three pages.
    Clicking on the page numbers should update the questions. 
    '''

    '''
    #*Completed: 
    Create an endpoint to DELETE question using a question ID. 

    TEST: When you click the trash icon next to a question, the question will be removed.
    This removal will persist in the database and when you refresh the page. 
    '''

    '''
    #*Completed: 
    Create an endpoint to POST a new question, 
    which will require the question and answer text, 
    category, and difficulty score.

    TEST: When you submit a question on the "Add" tab, 
    the form will clear and the question will appear at the end of the last page
    of the questions list in the "List" tab.  
    '''

    '''
    #*Completed: 
    Create a POST endpoint to get questions based on a search term. 
    It should return any questions for whom the search term 
    is a substring of the question. 

    TEST: Search by any phrase. The questions list will update to include 
    only question that include that string within their question. 
    Try using the word "title" to start. 
    '''

    '''
    #*Completed: 
    Create a GET endpoint to get questions based on category. 

    TEST: In the "List" tab / main screen, clicking on one of the 
    categories in the left column will cause only questions of that 
    category to be shown. 
    '''


    '''
    #*Completed: 
    Create a POST endpoint to get questions to play the quiz. 
    This endpoint should take category and previous question parameters 
    and return a random questions within the given category, 
    if provided, and that is not one of the previous questions. 

    #TODO
    TEST: In the "Play" tab, after a user selects "All" or a category,
    one question at a time is displayed, the user is allowed to answer
    and shown whether they were correct or not. 
    '''

    '''
    #*Completed: 
    Create error handlers for all expected errors 
    including 404 and 422. 
    '''

    return app

    