import requests


class RecipeLibrary:
    """ The object calls and retrieves data from specified API """

    def __init__(self, app, key):
        self.app = app
        self.endpoint = "https://api.spoonacular.com"
        self.key = key

    def search_recipe_id(self, query):
        params = {
            "apiKey": self.key,
            "query": query
        }
        response = requests.get(url=f"{self.endpoint}/recipes/complexSearch", params=params)
        return response.json()

    def get_recipe(self, query):
        params = {
            "apiKey": self.key
        }
        response = requests.get(url=f"{self.endpoint}/recipes/{query}/information", params=params)
        return response.json()
