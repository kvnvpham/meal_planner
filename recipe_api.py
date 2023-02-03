import requests
import os


class RecipeLibrary:

    def __init__(self):
        self.endpoint = "https://api.spoonacular.com"
        self.key = os.environ.get("SPOON_API")

    def get_recipe(self, query):
        params = {"query": query}
        response = requests.get(url=f"{self.endpoint}/recipes/complexSearch", params=params)
        recipes = response.json()
        return recipes
