from flask import Flask, render_template, redirect, request, url_for, flash, abort, send_from_directory
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, CreateCategory, RecipesForm, AddToWeek, LibraryFileForm, AddIngredient, SearchRecipe
from flask_ckeditor import CKEditor
from ingredient_trie import Trie
from recipe_api import RecipeLibrary
from datetime import date
from csv_handler import CSVHandler
import random
import os
from bleach_text import Bleach

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["UPLOAD_FOLDER"] = "static/files"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meals.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

library = RecipeLibrary(app, os.environ.get("SPOON_API"))
trie = Trie(app)
csv_handler = CSVHandler(app, trie)

login_manager = LoginManager(app)
Bootstrap(app)
ckeditor = CKEditor(app)
bleach_text = Bleach(app)


class User(UserMixin, db.Model):
    """ Stores User credentials """

    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    food_categories = db.relationship("Category", back_populates="user")
    recipes = db.relationship("Recipes", back_populates="user")
    my_week = db.relationship("WeeklyMeal", back_populates="user")
    ingredients = db.relationship("Ingredients", back_populates="user")
    current_ingredients = db.relationship("CurrentIngredients", back_populates="user")


class Category(db.Model):
    """ Stores and categorizes a group recipes based on the category name assigned """

    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    icon_img = db.Column(db.String, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="food_categories")

    recipe = db.relationship("Recipes", back_populates="category")


class WeeklyMeal(db.Model):
    """ Stores and assigns a recipe to a specific day of the week """

    __tablename__ = "weekly_meal"
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(250), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="my_week")
    my_recipes = db.relationship("Recipes", back_populates="my_week")


recipe_to_ingredient = db.Table(
    "recipe_to_ingredient",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id")),
    db.Column("ingredient_id", db.Integer, db.ForeignKey("ingredients.id")),
)


class Recipes(db.Model):
    """ Stores relevant recipe information entered by the user """

    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    recipe_type = db.Column(db.String, nullable=False)
    img = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    directions = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="recipes")

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    category = db.relationship("Category", back_populates="recipe")

    my_week_id = db.Column(db.Integer, db.ForeignKey("weekly_meal.id"))
    my_week = db.relationship("WeeklyMeal", back_populates="my_recipes")

    ingredient = db.relationship("Ingredients", secondary=recipe_to_ingredient, backref="recipe")


class Ingredients(db.Model):
    """
    Stores related ingredients to a specific recipe based on what the user input in the ingredients field
    of the Recipes table
    """

    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="ingredients")

    cur_ingrdt = db.relationship("CurrentIngredients", back_populates="ingredient")


class CurrentIngredients(db.Model):
    """ Stores a list of ingredients the user has entered based on their current available ingredients """

    __tablename__ = "current_ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="current_ingredients")

    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"))
    ingredient = db.relationship("Ingredients", back_populates="cur_ingrdt")


@db.event.listens_for(User, "after_insert")
def insert_day(mapper, connection, target):
    """ Creates a list of days of the week and connects it a user when they register an account """
    week = WeeklyMeal.__table__

    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for day in days:
        connection.execute(week.insert().values(day_of_week=day,
                                                user_id=target.id))


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    """ Loads an authenticated user """
    return User.query.get(int(user_id))


def admin_only(f):
    """ Decorator to assign specific routes for administrator only """
    @wraps(f)
    def decorator(*args, **kwargs):
        if current_user.id != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorator


def correct_user(f):
    """ Decorator to ensure a specific user is only able to access data for their account only """
    @wraps(f)
    def decorator(*args, **kwargs):
        if kwargs["user_id"] != current_user.id:
            abort(403)
        return f(*args, **kwargs)
    return decorator


def load_library(f):
    """ Loads the most recent ingredient library to the Trie for ingredient recognition """
    @wraps(f)
    def decorator(*args, **kwargs):
        csv_handler.load_csv()
        return f(*args, **kwargs)
    return decorator


@app.route("/")
def home():
    """ Display the home page for users, unauthenticated users are automatically assigned an ID of 0 """
    if not current_user.is_authenticated:
        return render_template("index.html", user_id=0)
    return render_template("index.html", user_id=current_user.id)


@app.route("/register", methods=["GET", "POST"])
def register():
    """ Allows users to register an account. If a user already exists, they will be redirected to the login page """
    form = RegisterForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("User already exists. Please login.")
            return redirect(url_for("login"))

        secure_pw = generate_password_hash(
            form.password.data,
            method="pbkdf2:sha256",
            salt_length=12
        )

        new_user = User(
            name=form.name.data.title(),
            email=form.email.data,
            password=secure_pw
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home", user_id=current_user.id))

    return render_template("register.html", form=form, user_id=0)


@app.route("/login", methods=["GET", "POST"])
def login():
    """ Allows a user to login into their account """
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("home", user_id=current_user.id))
        flash("Incorrect credentials. Please try again.")
        return redirect(url_for("login", user_id=0))
    return render_template("login.html", form=form, user_id=0)


@app.route("/logout")
@login_required
def logout():
    """ Allows a user to logout of their account """
    logout_user()
    return redirect(url_for("home"))


@app.route("/ingredient_library/<int:user_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def ingredient_library(user_id):
    """
    Provides the ingredient library form which allows administrators to save their files to the system and load
    data into the Trie
    """
    form = LibraryFileForm()
    files = csv_handler.download_csv()

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        new_filename = f"{filename.split('.')[0]}_{date.today()}.csv"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
        file.save(file_path)

        csv_handler.load_csv()
        flash("Upload Successful")
        return redirect(url_for("ingredient_library", user_id=user_id, files=files))

    return render_template("add_library.html", user_id=user_id, form=form, files=files)


@app.route("/download_list/<int:user_id>")
@login_required
@admin_only
def list_downloads(user_id):
    """ Displays a list of previous uploaded csv files for administrators only """
    files = csv_handler.download_csv()
    return render_template("download.html", user_id=user_id, files=files)


@app.route("/download_file/<int:user_id>/<filename>")
@login_required
@admin_only
def download_file(user_id, filename):
    """ Enables administrators to download past uploaded csv files """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/my_week/<int:user_id>")
@login_required
@correct_user
def my_week(user_id):
    """ Displays recipes that are planned for the current week """
    user = User.query.get(user_id)

    return render_template("my_week.html", user_id=user_id, user=user)


@app.route("/random_recipe/<int:user_id>")
@login_required
@correct_user
def random_recipe(user_id):
    """ Generates a random recipe for users based on their existing recipe database """
    user = User.query.get(user_id)

    rand = random.choice(user.recipes)
    recipe = Recipes.query.get(rand.id)
    return render_template("my_week.html", user_id=user_id, user=user, random=recipe)


@app.route("/my_recipes/<int:user_id>")
@login_required
@correct_user
def my_recipes(user_id):
    """ Displays all categories and recipes associated with the user """
    user = User.query.get(user_id)

    return render_template("my_recipes.html", user_id=current_user.id, user=user)


@app.route("/create_category/<int:user_id>", methods=["GET", "POST"])
@login_required
@correct_user
def create_category(user_id):
    """ Enables users to customize the name and icon of their desired category for food/recipes """
    form = CreateCategory()

    if form.cancel.data:
        return redirect(url_for("my_recipes", user_id=user_id))
    if form.validate_on_submit():
        new_cat = Category(
            name=form.name.data.title(),
            icon_img=form.icon_img.data,
            user_id=user_id
        )
        db.session.add(new_cat)
        db.session.commit()
        return redirect(url_for("my_recipes", user_id=user_id))
    return render_template("create_category.html", form=form, user_id=user_id)


@app.route("/edit_category/<int:user_id>/<int:category_id>", methods=["GET", "POST"])
@login_required
@correct_user
def edit_category(user_id, category_id):
    """ Enables users to edit existing names and icons of their food/recipe categories """
    category_info = Category.query.get(category_id)

    form = CreateCategory(
        name=category_info.name,
        icon_img=category_info.icon_img
    )
    if form.validate_on_submit():
        if form.cancel.data:
            return redirect(url_for("my_recipes", user_id=user_id))

        category_info.name = form.name.data.title()
        category_info.icon_img = form.icon_img.data
        db.session.commit()
        return redirect(url_for("my_recipes", user_id=user_id))

    return render_template("create_category.html", form=form, user_id=user_id, category_id=category_id)


@app.route("/delete_category/<int:user_id>/<int:category_id>")
@login_required
@correct_user
def delete_category(user_id, category_id):
    """
    Enables users to delete categories they no longer desire. This will also delete all recipes under that category
    """
    user = User.query.get(user_id)

    for recipe in user.recipes:
        if recipe.category_id == category_id:
            db.session.delete(recipe)
    category = Category.query.get(category_id)
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for("my_recipes", user_id=user_id))


@app.route("/create_recipe/<int:user_id>/<int:category_id>", methods=["GET", "POST"])
@login_required
@correct_user
@load_library
def create_recipe(user_id, category_id):
    """
    Allows users to input various information for a recipe under the specified category.
    The trie will also recognize ingredient names and add it in the database to display
    """
    category = Category.query.get(category_id)
    form = RecipesForm(recipe_type=category.name)

    if form.cancel.data:
        return redirect(url_for("my_recipes", user_id=user_id))
    if form.validate_on_submit():
        ingredients_text = bleach_text.clean_text(form.ingredients.data)
        directions_text = bleach_text.clean_text(form.directions.data)

        new_recipe = Recipes(
            name=form.name.data,
            recipe_type=form.recipe_type.data.title(),
            img=form.img.data,
            link=form.link.data,
            ingredients=ingredients_text,
            directions=directions_text,
            user_id=user_id,
            category_id=category_id
        )
        db.session.add(new_recipe)

        text = form.ingredients.data
        omit = ["<ul>", "</ul>", "<li>", "</li>", "&nbsp", "frac12", "frac13", "frac14", "&ldquo", "&rdquo", ";", ", ",
                " (", ")", "&", "\r\n\t", "\r\n", "grated ", "sliced ", "skinless ", "cooked ", "kosher ", "jar ",
                "cup"]
        for char in omit:
            text = text.replace(char, "-*-")

        for ingrdnt in text.title().split("-*-"):
            if trie.search(ingrdnt):
                db_ingredient = Ingredients.query.filter_by(name=ingrdnt, user_id=user_id).first()
                db_cur_ingredient = CurrentIngredients.query.filter_by(name=ingrdnt, user_id=user_id).first()
                if not db_ingredient:
                    db_ingredient = Ingredients(
                        name=ingrdnt,
                        user_id=user_id
                    )
                    db.session.add(db_ingredient)
                new_recipe.ingredient.append(db_ingredient)
                if db_cur_ingredient:
                    db_cur_ingredient.ingredient_id = db_ingredient.id
                db.session.commit()

        db.session.commit()
        return redirect(url_for("my_recipes", user_id=user_id))
    return render_template("create_recipe.html", form=form, user_id=current_user.id, category_id=category_id)


@app.route("/view_recipe/<int:user_id>/<recipe_id>", methods=["GET", "POST"])
@login_required
@correct_user
def view_recipe(user_id, recipe_id):
    """
    Allows users to view the information they have entered and also allow them to assign the recipe to a specified
    day of the week
    """
    form = AddToWeek()
    user = User.query.get(user_id)
    recipe = Recipes.query.get(recipe_id)

    if form.validate_on_submit():
        if form.day.data and form.day.data != "Not Scheduled":
            day = WeeklyMeal.query.filter_by(day_of_week=form.day.data, user_id=user_id).first()
            recipe.my_week_id = day.id
        else:
            recipe.my_week_id = None
        db.session.commit()

        return redirect(url_for("view_recipe", user_id=user_id, user=user, form=form, recipe_id=recipe_id))
    return render_template("view_recipe.html", user_id=user_id, user=user, form=form, recipe=recipe)


@app.route("/edit_recipe/<int:user_id>", methods=["GET", "POST"])
@login_required
@correct_user
@load_library
def edit_recipe(user_id):
    """ Similar to adding a recipe, the user will be able to edit pre-existing information """
    recipe_id = request.args.get("recipe_id")
    recipe = Recipes.query.get(recipe_id)

    form = RecipesForm(
        name=recipe.name,
        recipe_type=recipe.recipe_type,
        img=recipe.img,
        link=recipe.link,
        ingredients=recipe.ingredients,
        directions=recipe.directions
    )

    if form.cancel.data:
        return redirect(url_for("view_recipe", user_id=user_id, recipe_id=recipe_id))
    if form.validate_on_submit():
        category = Category.query.filter_by(name=form.recipe_type.data.title()).first()
        if not category:
            category = Category(
                name=form.recipe_type.data.title(),
                user_id=user_id
            )
            db.session.add(category)
            db.session.commit()

        ingredients_text = bleach_text.clean_text(form.ingredients.data)
        directions_text = bleach_text.clean_text(form.directions.data)

        text = form.ingredients.data.lower()
        omit = ["<ul>", "</ul>", "<li>", "</li>", "&nbsp", "frac12", "frac13", "frac14", "&ldquo", "&rdquo", ";", ", ",
                " (", ")", "&", "\r\n\t", "\r\n", "grated ", "sliced ", "skinless ", "cooked ", "kosher ", "jar ",
                "cup"]
        for char in omit:
            text = text.replace(char, "-*-")

        for ingrdnt in text.title().split("-*-"):
            if trie.search(ingrdnt):
                db_ingredient = Ingredients.query.filter_by(name=ingrdnt, user_id=user_id).first()
                db_cur_ingredient = CurrentIngredients.query.filter_by(name=ingrdnt, user_id=user_id).first()
                if not db_ingredient:
                    db_ingredient = Ingredients(
                        name=ingrdnt,
                        user_id=user_id
                    )
                    db.session.add(db_ingredient)
                recipe.ingredient.append(db_ingredient)
                if db_cur_ingredient:
                    db_cur_ingredient.ingredient_id = db_ingredient.id
                db.session.commit()

        recipe.name = form.name.data
        recipe.recipe_type = form.recipe_type.data
        recipe.img = form.img.data
        recipe.link = form.link.data
        recipe.ingredients = ingredients_text
        recipe.directions = directions_text
        recipe.category_id = category.id
        db.session.commit()
        return redirect(url_for("view_recipe", user_id=user_id, recipe_id=recipe_id))
    return render_template("create_recipe.html",
                           user_id=user_id,
                           form=form,
                           category_id=recipe.category_id,
                           recipe_id=recipe_id,
                           edit=True)


@app.route("/delete_recipe/<int:user_id>/<int:recipe_id>")
@login_required
@correct_user
def delete_recipe(user_id, recipe_id):
    """ Enables users to delete the specified recipe from the database """
    recipe = Recipes.query.get(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return redirect(url_for("my_recipes", user_id=user_id))


@app.route("/my_ingredients/<int:user_id>")
@login_required
@correct_user
def my_ingredients(user_id):
    """ Displays a list of ingredients that the user currently possess """
    user = User.query.get(user_id)

    return render_template("my_ingredients.html", user_id=user_id, user=user)


@app.route("/add_ingredient/<int:user_id>", methods=['GET', "POST"])
@login_required
@correct_user
def add_ingredient(user_id):
    """
    Allows users to add ingredients to their current ingredient database either through a single entry
    or with a csv file. The function will not add the ingredient if it already exists within the database
    """
    form_add = AddIngredient()
    form_upload = LibraryFileForm()

    if form_add.cancel.data:
        return redirect(url_for("my_ingredients", user_id=user_id))
    if form_add.validate_on_submit():
        related_ingrdt = Ingredients.query.filter_by(name=form_add.name.data.title()).first()
        if not related_ingrdt:
            new_ingredient = CurrentIngredients(
                name=form_add.name.data.title(),
                user_id=user_id,
                ingredient=related_ingrdt.id if related_ingrdt else None
            )
            db.session.add(new_ingredient)
            db.session.commit()
        flash("Added to List Successfully")
        return redirect(url_for("my_ingredients", user_id=user_id))

    if form_upload.validate_on_submit():
        file = form_upload.file.data
        filename = secure_filename(file.filename)
        new_filename = f"{filename.split('.')[0]}_{user_id}"
        file_path = os.path.join("static/user_files", new_filename)
        file.save(file_path)

        user_set = csv_handler.process_csv(new_filename)
        for row in user_set:
            query = Ingredients.query.filter_by(name=row, user_id=user_id).first()
            current_ingredient = CurrentIngredients.query.filter_by(name=row, user_id=user_id).first()
            if current_ingredient and query:
                current_ingredient.ingredient_id = query.id
            if not current_ingredient:
                new_ingredient = CurrentIngredients(
                    name=row,
                    user_id=user_id,
                    ingredient_id=query.id if query else None
                )
                db.session.add(new_ingredient)
        db.session.commit()
        flash("Upload Successful")
        return redirect(url_for("my_ingredients", user_id=user_id))

    return render_template("add_ingredient.html", user_id=user_id, form_add=form_add, form_upload=form_upload)


@app.route("/delete_ingredient/<int:user_id>/<int:ingredient_id>")
@login_required
@correct_user
def delete_ingredient(user_id, ingredient_id):
    """ Deletes the desired ingredient from the user's current ingredient database """
    ingredient = CurrentIngredients.query.get(ingredient_id)
    db.session.delete(ingredient)
    db.session.commit()
    return redirect(url_for("my_ingredients", user_id=user_id))


@app.route("/search/<int:user_id>", methods=['GET', 'POST'])
@login_required
@correct_user
def search(user_id):
    """ Utilizes Spoonacular's API database to search for recipes related to the entered keyword """
    form = SearchRecipe()

    if form.validate_on_submit():
        response = library.search_recipe_id(form.recipe.data)

        return render_template("search.html", user_id=user_id, form=form, results=response["results"])
    return render_template("search.html", user_id=user_id, form=form)


@app.route("/search_id/<int:user_id>/<int:search_id>", methods=['GET', 'POST'])
@login_required
@correct_user
def get_recipe_info(user_id, search_id):
    """
    Retrieves the associated recipe ID from the search function to display all relevant information for the requested
    recipe
    """
    result = library.get_recipe(search_id)

    return render_template("recipe_information.html", user_id=user_id, search_id=search_id, result=result)


@app.context_processor
def inj_copyright():
    """ Displays the current year for the copyright notice """
    return {"year": date.today().year}


if __name__ == "__main__":
    app.run(debug=True)
