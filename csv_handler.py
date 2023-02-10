import os
import csv
from ingredient_trie import Trie


class CSVHandler:

    def __init__(self, app):
        self.app = app
        self.trie = Trie()

    def load_csv(self):
        try:
            files = os.listdir(self.app.config["UPLOAD_FOLDER"])
            print(files)
        except FileNotFoundError:
            pass

    def process_csv(self, filename):
        with open(f"{self.app.config['UPLOAD_FOLDER']}/{filename}", mode="r") as file:
            read = csv.DictReader(file)

            for row in read["Ingredient"]:
                self.trie.add_word(row.title())
