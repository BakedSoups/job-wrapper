import re
from html import unescape
from html.parser import HTMLParser


class DescriptionParser(HTMLParser):
    block_tags = {"p", "div", "li", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.parts)).strip()


def html_to_text(content):
    parser = DescriptionParser()
    parser.feed(unescape(content))
    return parser.get_text()
