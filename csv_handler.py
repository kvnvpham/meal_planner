import os
import csv
from ingredient_trie import Trie


class CSVHandler:
    """ The object handles CSV manipulation and content """

    def __init__(self, app, trie):
        self.app = app
        self.trie = trie

    def load_csv(self):
        files = os.listdir(self.app.config["UPLOAD_FOLDER"])
        if files:
            with open(f"{self.app.config['UPLOAD_FOLDER']}/{files[-1]}", newline='') as file:
                ingredients = csv.DictReader(file)

                for row in ingredients:
                    self.trie.add_word(row["Ingredient"].title())

    def download_csv(self):
        files = os.listdir(self.app.config["UPLOAD_FOLDER"])
        return files

    def process_csv(self, filename):
        with open(f"static/user_files/{filename}", newline='') as file:
            ingredient = csv.DictReader(file)

            ingredient_set = set()
            for row in ingredient:
                ingredient_set.add(row["Ingredient"].title())
            return ingredient_set
