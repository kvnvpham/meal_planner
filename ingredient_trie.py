class TrieNode:
    """ The object creates Trie nodes """

    def __init__(self):
        self.children = {}
        self.is_word = False


class Trie:
    """ The object manages Trie data by adding words to the data structure and recalling existing words/prefixes """

    def __init__(self, app):
        self.app = app
        self.root = TrieNode()

    def add_word(self, word):
        cur = self.root

        for c in word:
            if c not in cur.children:
                cur.children[c] = TrieNode()
            cur = cur.children[c]
        cur.is_word = True

    def get_prefix(self, word):
        cur = self.root

        for c in word:
            if c not in cur.children:
                return False
            cur = cur.children[c]
        return True

    def search(self, word):
        cur = self.root

        for c in word:
            if c not in cur.children:
                return False
            cur = cur.children[c]
        return cur.is_word
