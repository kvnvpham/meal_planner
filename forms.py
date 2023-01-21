from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Email, Length
from flask_ckeditor import CKEditorField


class RegisterForm(FlaskForm):
    name = StringField(label="Name", validators=[InputRequired()])
    email = EmailField(label="Email", validators=[InputRequired(), Email()])
    password = PasswordField(label="Password", validators=[InputRequired(), Length(min=8)])
    register = SubmitField(label="Register")


class LoginForm(FlaskForm):
    email = EmailField(label="Email", validators=[InputRequired(), Email()])
    password = PasswordField(label="Password", validators=[InputRequired()])
    login = SubmitField(label="Let me in!")


class CreateCategory(FlaskForm):
    name = StringField(label="Category Name", validators=[InputRequired()])
    icon_img = StringField(label="Icon Image", description="Embed Link")
    submit = SubmitField(label="Create")
    cancel = SubmitField(label="Cancel", render_kw={"formnovalidate": True})


class RecipesForm(FlaskForm):
    name = StringField(label="Recipe Name", validators=[InputRequired()])
    recipe_type = StringField(label="Recipe Type", validators=[InputRequired()], description="Food Category")
    img = StringField(label="Recipe Image", description="Embed Link")
    link = StringField(label="Website Link", validators=[InputRequired()])
    ingredients = CKEditorField(label="Ingredients", validators=[InputRequired()])
    directions = CKEditorField(label="Directions", validators=[InputRequired()])
    submit = SubmitField(label="Submit")
    cancel = SubmitField(label="Cancel", render_kw={"formnovalidate": True})
