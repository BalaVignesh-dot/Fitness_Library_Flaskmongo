from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os


# Load environment variables
load_dotenv()

# Create Flask application
app = Flask(__name__)

# Secret key for flash messages
app.secret_key = "fitness-library-secret-key"


# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")

client = MongoClient(mongo_uri)

db = client["fitness_library"]

exercises_collection = db["exercises"]


# Upload folders
IMAGE_FOLDER = "uploads/images"
VIDEO_FOLDER = "uploads/videos"

app.config["IMAGE_FOLDER"] = IMAGE_FOLDER
app.config["VIDEO_FOLDER"] = VIDEO_FOLDER


# Allowed file types
ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}

ALLOWED_VIDEO_EXTENSIONS = {
    "mp4",
    "webm",
    "mov"
}


def allowed_file(filename, allowed_extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


# ---------------------------------------------------
# HOME
# ---------------------------------------------------

@app.route("/")
def index():

    total_exercises = exercises_collection.count_documents({})

    categories = exercises_collection.distinct("category")

    return render_template(
        "index.html",
        total_exercises=total_exercises,
        categories=categories
    )


# ---------------------------------------------------
# VIEW ALL EXERCISES
# ---------------------------------------------------

@app.route("/exercises")
def exercises():

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", "")

    query = {}

    if search:
        query["name"] = {
            "$regex": search,
            "$options": "i"
        }

    if category:
        query["category"] = category

    if difficulty:
        query["difficulty"] = difficulty

    exercise_list = list(
        exercises_collection.find(query).sort("name", 1)
    )

    categories = exercises_collection.distinct("category")

    return render_template(
        "exercises.html",
        exercises=exercise_list,
        categories=categories,
        search=search,
        selected_category=category,
        selected_difficulty=difficulty
    )


# ---------------------------------------------------
# ADD EXERCISE
# ---------------------------------------------------

@app.route("/add", methods=["GET", "POST"])
def add_exercise():

    if request.method == "POST":

        name = request.form.get("name")
        category = request.form.get("category")
        difficulty = request.form.get("difficulty")
        equipment = request.form.get("equipment")
        target_muscles = request.form.get("target_muscles")
        description = request.form.get("description")
        instructions = request.form.get("instructions")

        image = request.files.get("image")
        video = request.files.get("video")

        image_filename = ""
        video_filename = ""

        # Save image
        if image and image.filename:

            if allowed_file(
                image.filename,
                ALLOWED_IMAGE_EXTENSIONS
            ):

                image_filename = secure_filename(
                    image.filename
                )

                image.save(
                    os.path.join(
                        app.config["IMAGE_FOLDER"],
                        image_filename
                    )
                )

        # Save video
        if video and video.filename:

            if allowed_file(
                video.filename,
                ALLOWED_VIDEO_EXTENSIONS
            ):

                video_filename = secure_filename(
                    video.filename
                )

                video.save(
                    os.path.join(
                        app.config["VIDEO_FOLDER"],
                        video_filename
                    )
                )

        # Convert target muscles to list
        muscles_list = [
            muscle.strip()
            for muscle in target_muscles.split(",")
            if muscle.strip()
        ]

        # Convert instructions into list
        instructions_list = [
            instruction.strip()
            for instruction in instructions.split("\n")
            if instruction.strip()
        ]

        exercise = {
            "name": name,
            "category": category,
            "difficulty": difficulty,
            "equipment": equipment,
            "target_muscles": muscles_list,
            "description": description,
            "instructions": instructions_list,
            "image": image_filename,
            "video": video_filename
        }

        exercises_collection.insert_one(exercise)

        flash(
            "Exercise added successfully!",
            "success"
        )

        return redirect(url_for("exercises"))

    return render_template("add_exercise.html")


# ---------------------------------------------------
# VIEW SINGLE EXERCISE
# ---------------------------------------------------

@app.route("/exercise/<id>")
def exercise_details(id):

    exercise = exercises_collection.find_one(
        {"_id": ObjectId(id)}
    )

    if exercise is None:
        flash("Exercise not found.", "danger")
        return redirect(url_for("exercises"))

    return render_template(
        "exercise_details.html",
        exercise=exercise
    )


# ---------------------------------------------------
# EDIT EXERCISE
# ---------------------------------------------------

@app.route("/edit/<id>", methods=["GET", "POST"])
def edit_exercise(id):

    exercise = exercises_collection.find_one(
        {"_id": ObjectId(id)}
    )

    if exercise is None:
        flash("Exercise not found.", "danger")
        return redirect(url_for("exercises"))

    if request.method == "POST":

        name = request.form.get("name")
        category = request.form.get("category")
        difficulty = request.form.get("difficulty")
        equipment = request.form.get("equipment")
        target_muscles = request.form.get("target_muscles")
        description = request.form.get("description")
        instructions = request.form.get("instructions")

        update_data = {
            "name": name,
            "category": category,
            "difficulty": difficulty,
            "equipment": equipment,
            "target_muscles": [
                muscle.strip()
                for muscle in target_muscles.split(",")
                if muscle.strip()
            ],
            "description": description,
            "instructions": [
                instruction.strip()
                for instruction in instructions.split("\n")
                if instruction.strip()
            ]
        }

        # New image
        image = request.files.get("image")

        if image and image.filename:

            if allowed_file(
                image.filename,
                ALLOWED_IMAGE_EXTENSIONS
            ):

                image_filename = secure_filename(
                    image.filename
                )

                image.save(
                    os.path.join(
                        app.config["IMAGE_FOLDER"],
                        image_filename
                    )
                )

                update_data["image"] = image_filename

        # New video
        video = request.files.get("video")

        if video and video.filename:

            if allowed_file(
                video.filename,
                ALLOWED_VIDEO_EXTENSIONS
            ):

                video_filename = secure_filename(
                    video.filename
                )

                video.save(
                    os.path.join(
                        app.config["VIDEO_FOLDER"],
                        video_filename
                    )
                )

                update_data["video"] = video_filename

        exercises_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )

        flash(
            "Exercise updated successfully!",
            "success"
        )

        return redirect(
            url_for(
                "exercise_details",
                id=id
            )
        )

    target_muscles = ", ".join(
        exercise.get("target_muscles", [])
    )

    instructions = "\n".join(
        exercise.get("instructions", [])
    )

    return render_template(
        "edit_exercise.html",
        exercise=exercise,
        target_muscles=target_muscles,
        instructions=instructions
    )


# ---------------------------------------------------
# DELETE EXERCISE
# ---------------------------------------------------

@app.route("/delete/<id>", methods=["POST"])
def delete_exercise(id):

    exercise = exercises_collection.find_one(
        {"_id": ObjectId(id)}
    )

    if exercise:

        # Delete image
        image = exercise.get("image")

        if image:

            image_path = os.path.join(
                app.config["IMAGE_FOLDER"],
                image
            )

            if os.path.exists(image_path):
                os.remove(image_path)

        # Delete video
        video = exercise.get("video")

        if video:

            video_path = os.path.join(
                app.config["VIDEO_FOLDER"],
                video
            )

            if os.path.exists(video_path):
                os.remove(video_path)

        # Delete MongoDB document
        exercises_collection.delete_one(
            {"_id": ObjectId(id)}
        )

        flash(
            "Exercise deleted successfully!",
            "success"
        )

    return redirect(url_for("exercises"))


# ---------------------------------------------------
# SERVE IMAGES
# ---------------------------------------------------

@app.route("/uploads/images/<filename>")
def uploaded_image(filename):

    return send_from_directory(
        app.config["IMAGE_FOLDER"],
        filename
    )


# ---------------------------------------------------
# SERVE VIDEOS
# ---------------------------------------------------

@app.route("/uploads/videos/<filename>")
def uploaded_video(filename):

    return send_from_directory(
        app.config["VIDEO_FOLDER"],
        filename
    )


# ---------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )