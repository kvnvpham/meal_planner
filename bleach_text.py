import bleach

class Bleach:
    def clean_text(self, s):
        allow_tags = [
            'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1',
            'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 's', 'span', 'strong', 'sub',
            'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'ul'
        ]
        allow_attrs = {
            "*": ['class'],
            "a": ["href", "rel", "title"],
            "abbr": ["title"],
            "acronym": ["title"],
            "img": ["alt", "src", "style", "width", "height"]
        }
        return bleach.clean(s, tags=allow_tags, attributes=allow_attrs)