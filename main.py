from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, CreateCategory, RecipesForm
from flask_ckeditor import CKEditor
from datetime import date


app = Flask(__name__)
app.config["SECRET_KEY"] = "super secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meals.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
Bootstrap(app)
ckeditor = CKEditor(app)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    food_categories = relationship("Category", back_populates="user")
    recipes = relationship("Recipes", back_populates="user")
    my_week = relationship("WeeklyMeal", back_populates="user")


class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    icon_img = db.Column(db.String, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = relationship("User", back_populates="food_categories")

    recipe = relationship("Recipes", back_populates="category")


class WeeklyMeal(db.Model):
    __tablename__ = "weekly_meal"
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(250), unique=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = relationship("User", back_populates="my_week")

    my_recipes = relationship("Recipes", back_populates="my_week")


class Recipes(db.Model):
    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), unique=True, nullable=False)
    recipe_type = db.Column(db.String, nullable=False)
    img = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    directions = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = relationship("User", back_populates="recipes")

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    category = relationship("Category", back_populates="recipe")

    my_week_id = db.Column(db.Integer, db.ForeignKey("weekly_meal.id"))
    my_week = relationship("WeeklyMeal", back_populates="my_recipes")

    ingredient = relationship("Ingredients", back_populates="recipe")


class Ingredients(db.Model):
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), unique=True, nullable=False)

    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"))
    recipe = relationship("Recipes", back_populates="ingredient")


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
            name=form.name.data,
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


@app.route("/my_recipes/<int:user_id>")
@login_required
def my_recipes(user_id):
    if user_id == current_user.id:
        user = User.query.get(user_id)

        return render_template("my_recipes.html", user_id=current_user.id, user=user)
    else:
        abort(403)


@app.route("/create_category/<int:user_id>", methods=["GET", "POST"])
@login_required
def create_category(user_id):
    if user_id == current_user.id:
        form = CreateCategory()

        if form.cancel.data:
            return redirect(url_for("my_recipes", user_id=user_id))
        if form.validate_on_submit():
            new_cat = Category(
                name=form.name.data,
                icon_img=form.icon_img.data,
                user_id=user_id
            )
            db.session.add(new_cat)
            db.session.commit()
            return redirect(url_for("my_recipes", user_id=current_user.id))
        return render_template("create_category.html", form=form, user_id=current_user.id)
    else:
        abort(403)


@app.route("/edit_category/<int:user_id>/<int:category_id>", methods=["GET", "POST"])
@login_required
def edit_category(user_id, category_id):
    if user_id == current_user.id:
        category_info = Category.query.get(category_id)

        form = CreateCategory(
            name=category_info.name,
            icon_img=category_info.icon_img
        )
        if form.validate_on_submit():
            if form.cancel.data:
                return redirect(url_for("my_recipes", user_id=user_id))

            category_info.name = form.name.data
            category_info.icon_img = form.icon_img.data
            db.session.commit()
            return redirect(url_for("my_recipes", user_id=user_id))

        return render_template("create_category.html", form=form, user_id=user_id)
    else:
        abort(403)


@app.route("/create_recipe/<int:user_id>/<int:category_id>", methods=["GET", "POST"])
@login_required
def create_recipe(user_id, category_id):
    if user_id == current_user.id:
        form = RecipesForm()

        if form.cancel.data:
            return redirect(url_for("my_recipes", user_id=user_id))
        if form.validate_on_submit():
            new_recipe = Recipes(
                name=form.name.data,
                recipe_type=form.recipe_type.data,
                img=form.img.data,
                link=form.link.data,
                ingredients=form.ingredients.data,
                directions=form.directions.data,
                user_id=user_id,
                category_id=category_id
            )
            db.session.add(new_recipe)
            db.session.commit()
            return redirect(url_for("my_recipes", user_id=user_id))
        return render_template("create_recipe.html", form=form, user_id=current_user.id, category_id=category_id)
    else:
        abort(403)


@app.context_processor
def inj_copyright():
    return {"year": date.today().year}


if __name__ == "__main__":
    app.run(debug=True)
