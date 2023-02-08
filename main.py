from flask import Flask, render_template, redirect, request, url_for, flash, abort
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
import random
import os
from bleach_text import Bleach

app = Flask(__name__)
app.config["SECRET_KEY"] = "super secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meals.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

trie = Trie()
library = RecipeLibrary()
library.key = os.environ.get("SPOON_API")

login_manager = LoginManager(app)
Bootstrap(app)
ckeditor = CKEditor(app)
bleach_text = Bleach()


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    food_categories = db.relationship("Category", back_populates="user")
    recipes = db.relationship("Recipes", back_populates="user")
    my_week = db.relationship("WeeklyMeal", back_populates="user")
    ingredients = db.relationship("Ingredients", back_populates="user")


class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    icon_img = db.Column(db.String, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="food_categories")

    recipe = db.relationship("Recipes", back_populates="category")


class WeeklyMeal(db.Model):
    __tablename__ = "weekly_meal"
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(250), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="my_week")
    my_recipes = db.relationship("Recipes", back_populates="my_week")


recipe_to_ingredient = db.Table(
    "recipe_to_ingredient",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id")),
    db.Column("ingredient_id", db.Integer, db.ForeignKey("ingredients.id"))
)


class Recipes(db.Model):
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
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="ingredients")


@db.event.listens_for(User, "after_insert")
def insert_day(mapper, connection, target):
    week = WeeklyMeal.__table__

    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for day in days:
        connection.execute(week.insert().values(day_of_week=day,
                                                user_id=target.id))


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if current_user.id != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorator


def correct_user(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if kwargs["user_id"] != current_user.id:
            abort(403)
        return f(*args, **kwargs)
    return decorator


@app.route("/")
def home():
    if not current_user.is_authenticated:
        return render_template("index.html", user_id=0)
    return render_template("index.html", user_id=current_user.id)


@app.route("/register", methods=["GET", "POST"])
def register():
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
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("home", user_id=current_user.id))
        flash("Incorrect credentials. Please try again.")
        return redirect(url_for("login", user_id=0))
    return render_template("login.html", form=form, user_id=0)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/ingredient_library/<int:user_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def ingredient_library(user_id):
    form_upload = LibraryFileForm()
    form_add = AddIngredient()

    if form_add.cancel.data:
        return redirect(url_for("home", user_id=user_id))
    if form_add.validate_on_submit():
        trie.add_word(form_add.name.data.title())
        flash("Added to Library Successfully")
        return redirect(url_for("ingredient_library", user_id=user_id))

    if form_upload.validate_on_submit():
        file = form_upload.file.data
        filename = secure_filename(file.filename)
        return redirect(url_for("ingredient_library", user_id=user_id))

    return render_template("add_library.html", user_id=user_id, form_upload=form_upload, form_add=form_add)


@app.route("/my_week/<int:user_id>")
@login_required
@correct_user
def my_week(user_id):
    user = User.query.get(user_id)

    return render_template("my_week.html", user_id=user_id, user=user)


@app.route("/random_recipe/<int:user_id>")
@login_required
@correct_user
def random_recipe(user_id):
    user = User.query.get(user_id)

    rand = random.choice(user.recipes)
    recipe = Recipes.query.get(rand.id)
    return render_template("my_week.html", user_id=user_id, user=user, random=recipe)


@app.route("/my_recipes/<int:user_id>")
@login_required
@correct_user
def my_recipes(user_id):
    user = User.query.get(user_id)

    return render_template("my_recipes.html", user_id=current_user.id, user=user)


@app.route("/create_category/<int:user_id>", methods=["GET", "POST"])
@login_required
@correct_user
def create_category(user_id):
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
def create_recipe(user_id, category_id):
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
                " (", ")", "&", "\r\n\t", "\r\n"]
        for char in omit:
            text = text.replace(char, "-*-")

        for ingrdnt in text.title().split("-*-"):
            if trie.search(ingrdnt):
                ing = Ingredients.query.filter_by(name=ingrdnt).first()
                if ing:
                    new_recipe.ingredient.append(ing)
                else:
                    new_ingrdnt = Ingredients(
                        name=ingrdnt,
                        user_id=user_id,
                    )
                    db.session.add(new_ingrdnt)
                    new_recipe.ingredient.append(new_ingrdnt)

        db.session.commit()
        return redirect(url_for("my_recipes", user_id=user_id))
    return render_template("create_recipe.html", form=form, user_id=current_user.id, category_id=category_id)


@app.route("/view_recipe/<int:user_id>/<recipe_id>", methods=["GET", "POST"])
@login_required
@correct_user
def view_recipe(user_id, recipe_id):
    form = AddToWeek()
    recipe = Recipes.query.get(recipe_id)

    if form.validate_on_submit():
        if form.day.data and form.day.data != "Not Scheduled":
            day = WeeklyMeal.query.filter_by(day_of_week=form.day.data, user_id=user_id).first()
            recipe.my_week_id = day.id
        else:
            recipe.my_week_id = None
        db.session.commit()

        return redirect(url_for("view_recipe", user_id=user_id, form=form, recipe_id=recipe_id))
    return render_template("view_recipe.html", user_id=user_id, form=form, recipe=recipe)


@app.route("/edit_recipe/<int:user_id>", methods=["GET", "POST"])
@login_required
@correct_user
def edit_recipe(user_id):
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
        if Category.query.filter_by(name=form.recipe_type.data.title()).first():
            category = Category.query.filter_by(name=form.recipe_type.data.title()).first()
        else:
            category = Category(
                name=form.recipe_type.data.title(),
                user_id=user_id
            )
            db.session.add(category)
            db.session.commit()

        ingredients_text = bleach_text.clean_text(form.ingredients.data)
        directions_text = bleach_text.clean_text(form.directions.data)

        text = form.ingredients.data
        omit = ["<ul>", "</ul>", "<li>", "</li>", "&nbsp", "frac12", "frac13", "frac14", "&ldquo", "&rdquo", ";", ", ",
                " (", ")", "&", "\r\n\t", "\r\n"]
        for char in omit:
            text = text.replace(char, "-*-")

        for ingrdnt in text.title().split("-*-"):
            if trie.search(ingrdnt):
                ing = Ingredients.query.filter_by(name=ingrdnt).first()
                if ing:
                    recipe.ingredient.append(ing)
                else:
                    new_ingrdnt = Ingredients(
                        name=ingrdnt,
                        user_id=user_id,
                    )
                    db.session.add(new_ingrdnt)
                    recipe.ingredient.append(new_ingrdnt)

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
    recipe = Recipes.query.get(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return redirect(url_for("my_recipes", user_id=user_id))


@app.route("/my_ingredients/<int:user_id>")
@login_required
@correct_user
def my_ingredients(user_id):
    user = User.query.get(user_id)

    return render_template("my_ingredients.html", user_id=user_id, user=user)


@app.route("/add_ingredient/<int:user_id>", methods=['GET', "POST"])
@login_required
@correct_user
def add_ingredient(user_id):
    form = AddIngredient()

    if form.cancel.data:
        return redirect(url_for("my_ingredients", user_id=user_id))
    if form.validate_on_submit():
        ingredient = Ingredients(
            name=form.name.data.title(),
            user_id=user_id
        )
        db.session.add(ingredient)
        db.session.commit()
        return redirect(url_for("my_ingredients", user_id=user_id))

    return render_template("add_ingredient.html", user_id=user_id, form=form)


@app.route("/search/<int:user_id>", methods=['GET', 'POST'])
@login_required
@correct_user
def search(user_id):
    form = SearchRecipe()

    if form.validate_on_submit():
        response = library.search_recipe_id(form.recipe.data)

        return render_template("search.html", user_id=user_id, form=form, results=response["results"])
    return render_template("search.html", user_id=user_id, form=form)


@app.route("/search_id/<int:user_id>/<int:search_id>", methods=['GET', 'POST'])
@login_required
@correct_user
def get_recipe_info(user_id, search_id):
    result = library.get_recipe(search_id)

    return render_template("recipe_information.html", user_id=user_id, search_id=search_id, result=result)


@app.context_processor
def inj_copyright():
    return {"year": date.today().year}


if __name__ == "__main__":
    app.run(debug=True)
