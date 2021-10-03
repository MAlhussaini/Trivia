import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_cors import CORS
import random

from models import setup_db, Question, Category
# Paginate questions by a given number of questions per page
QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
    # Return a formatted list of question for the page given
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
        # Add controles to what is allowed by setting Access-Control-Allow
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
        # Get a randomized question and its answer
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
        # Retrieve all questions located in a given category divided in pages
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
        # Retrieve all questions divided in pages
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
        # Delete a question specified by ID
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
    def create_or_search_question():
        # Add a new question to the database
        body = request.get_json()
        # Get posted arguments from the requester
        new_question = body.get("question", None)
        new_answer = body.get("answer", None)
        new_difficulty = body.get("difficulty", None)
        new_category = body.get("category", None)
        search = body.get("searchTerm", None)

        try:
            # Set the list of all the categories to both post methods
            categories_query = Category.query.order_by(Category.id).all()
            categories = [category.format() for category in categories_query]

            if search:
                # Search only if a search parameter given
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
                # Other wise add a new question to the database
                question = Question(question=new_question, answer=new_answer, difficulty=new_difficulty, category=new_category)
                # Insert the new question to the database
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
        # Play a quiz using unique randomized questions 
        body = request.get_json()

        previous_questions = body.get("previous_questions", None)
        quiz_category = body.get("quiz_category", None)
        try:
            if quiz_category is None:
                # give a random for all categories
                question = Question.query.filter(~Question.question.in_(previous_questions)).order_by(func.random()).first()
            else:
                # give a random for specific categories
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
        # Handel a 404 errors
        return (
            jsonify({"success": False, "error": 404, "message": "resource not found"}),
            404,
        )

    @app.errorhandler(422)
    def unprocessable(error):
        # Handel a 422 errors
        return (
            jsonify({"success": False, "error": 422, "message": "unprocessable"}),
            422,
        )

    @app.errorhandler(400)
    def bad_request(error):
        # Handel a 400 errors
        return (jsonify({"success": False, "error": 400, "message": "bad request"}), 400)

    return app

    