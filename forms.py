from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, EmailField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Email, Length
from flask_ckeditor import CKEditorField


class RegisterForm(FlaskForm):
    """ Provides fields for the user registration form """
    name = StringField(label="Name", validators=[InputRequired()])
    email = EmailField(label="Email", validators=[InputRequired(), Email()])
    password = PasswordField(label="Password", validators=[InputRequired(), Length(min=8)])
    register = SubmitField(label="Register")


class LoginForm(FlaskForm):
    """ Provides fields for the user login form """
    email = EmailField(label="Email", validators=[InputRequired(), Email()])
    password = PasswordField(label="Password", validators=[InputRequired()])
    login = SubmitField(label="Let me in!")


class CreateCategory(FlaskForm):
    """ Provides fields for the category creation form """
    name = StringField(label="Category Name", validators=[InputRequired()])
    icon_img = StringField(label="Icon Image", description="Embed Link")
    submit = SubmitField(label="Create")
    cancel = SubmitField(label="Cancel", render_kw={"formnovalidate": True})


class RecipesForm(FlaskForm):
    """ Provides fields for the recipe creation form """
    name = StringField(label="Recipe Name", validators=[InputRequired()])
    recipe_type = StringField(label="Recipe Category", validators=[InputRequired()], description="Food Category")
    img = StringField(label="Recipe Image", description="Embed Link")
    link = StringField(label="Website Link", validators=[InputRequired()])
    ingredients = CKEditorField(label="Ingredients", validators=[InputRequired()])
    directions = CKEditorField(label="Directions", validators=[InputRequired()])
    submit = SubmitField(label="Submit")
    cancel = SubmitField(label="Cancel", render_kw={"formnovalidate": True})


class AddToWeek(FlaskForm):
    """ Provides selections for users to add a specified recipe to their current week """
    day = SelectField(
        label="Assign Day:",
        choices=["", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Not Scheduled"]
    )
    submit = SubmitField(label="Schedule")


class LibraryFileForm(FlaskForm):
    """ Provides an upload field for administrators / users to upload their csv files """
    file = FileField(label="Upload",
                     validators=[FileRequired(), FileAllowed(['csv'], "CSV Files Only")])
    submit = SubmitField("Upload")


class AddIngredient(FlaskForm):
    """ Provides fields for users to add their current ingredients """
    name = StringField(label="Ingredient Name", validators=[InputRequired()])
    submit = SubmitField(label="Add")
    cancel = SubmitField(label="Cancel")


class SearchRecipe(FlaskForm):
    """ Provides fields for users to input their keywords for searching recipes """
    recipe = StringField(label="Search Recipe", validators=[InputRequired()])
    submit = SubmitField(label="Search")
