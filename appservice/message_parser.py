from html.parser import HTMLParser
from typing import Optional, Tuple, List

htmltomarkdown = {"p": "\n", "strong": "**", "ins": "__", "u": "__", "b": "**", "em": "*", "i": "*", "del": "~~", "strike": "~~", "s": "~~"}
headers = {"h1": "***__", "h2": "**__", "h3": "**", "h4": "__", "h5": "*", "h6": ""}

def search_attr(attrs: List[Tuple[str, Optional[str]]], searched: str) -> Optional[str]:
    for attr in attrs:
        if attr[0] == searched:
            return attr[1]
    return None


class MatrixParser(HTMLParser):
    message: str = ""
    current_link: str = ""
    c_tags: list[str] = []
    list_num: int = 0

    def search_for_feature(self, acceptable_features: Tuple[str, ...]) -> Optional[str]:
        """Searches for certain feature in opened HTML tags for given text, if found returns the tag, if not returns None"""
        for tag in self.c_tags[::-1]:
            if tag in acceptable_features:
                return tag
        return None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self.c_tags.append(tag)
        if tag in htmltomarkdown:
            self.message += htmltomarkdown[tag]
        elif tag == "code":
            if attrs[0][0] == "class":  # What if it's not the first class?
                self.message += "```" + attrs[0][1].split("language-", 1)[-1] + "\n"
            else:
                self.message += "`"
        elif tag == "span":
            spoiler = search_attr(attrs, "data-mx-spoiler")
            if spoiler is not None:
                if spoiler:  # Spoilers can have a reason https://github.com/matrix-org/matrix-doc/pull/2010
                    self.message += f"({spoiler})"
                self.message += "||"
            self.c_tags.append("spoiler")  # Always after span tag
        elif tag == "li":
            list_type = self.search_for_feature(("ul", "ol"))
            if list_type == "ol":
                self.message += "\n{}. ".format(self.list_num)
            else:
                self.message += "\n* "
        elif tag in "br":
            self.c_tags.pop()
            self.message += "\n"
            if self.search_for_feature(("blockquote",)):
                self.message += "> "
        elif tag == "p":
            self.message += "\n"
        elif tag == "a":
            # <a href=\"https://e621.net\">test</a>
            self.current_link = search_attr(attrs, "href") or ""
        elif tag == "mx-reply":

        elif tag == "img":

        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.message += headers[tag]
        # ignore font tag

    def handle_data(self, data):
        if self.c_tags[-1] != "code":  # May IndexError!
             data = data.replace("\n", "")
        # TODO Escape Matrix characters when in code blocks
        if self.current_link:
            self.message += f"[{data}]({self.current_link})"
        else:
            self.message += data  # strip new lines, they will be mostly handled by parser

    def handle_endtag(self, tag: str):
        if tag in htmltomarkdown:
            self.message += htmltomarkdown[tag]
        if self.c_tags.pop() == "spoiler":
            self.message += "||"
            self.c_tags.pop()  # guaranteed to be a span tag
        if tag in ("ul", "li"):
            self.message += "\n"
        elif tag == "code":
            if self.c_tags[-1] == "pre":
                self.message += "\n```"
            else:
                self.message += "`"
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.message += headers[tag][::-1]

matrixparser = MatrixParser()
