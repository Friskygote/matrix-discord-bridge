import re
from html.parser import HTMLParser
from typing import Optional, Tuple, List, Callable

from db import DataBase
from cache import Cache

htmltomarkdown = {"p": "\n", "strong": "**", "ins": "__", "u": "__", "b": "**", "em": "*", "i": "*", "del": "~~", "strike": "~~", "s": "~~"}
headers = {"h1": "***__", "h2": "**__", "h3": "**", "h4": "__", "h5": "*", "h6": ""}


def search_attr(attrs: List[Tuple[str, Optional[str]]], searched: str) -> Optional[str]:
    for attr in attrs:
        if attr[0] == searched:
            return attr[1] or ""
    return None


class MatrixParser(HTMLParser):
    def __init__(self, db: DataBase, mention_regex: str):
        super().__init__()
        self.message: str = ""
        self.current_link: str = ""
        self.c_tags: list[str] = []
        self.list_num: int = 1
        self.db: DataBase = db
        self.snowflake_regex: str = mention_regex

    def search_for_feature(self, acceptable_features: Tuple[str, ...]) -> Optional[str]:
        """Searches for certain feature in opened HTML tags for given text, if found returns the tag, if not returns None"""
        for tag in self.c_tags[::-1]:
            if tag in acceptable_features:
                return tag
        return None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if "mx-reply" in self.c_tags:
            return
        self.c_tags.append(tag)
        if tag in htmltomarkdown:
            self.message += htmltomarkdown[tag]
        elif tag == "code":
            if attrs:  # What if it's not the first class?
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
                self.list_num += 1
            else:
                self.message += "\n• "
        elif tag in "br":
            self.c_tags.pop()
            self.message += "\n"
            if self.search_for_feature(("blockquote",)):
                self.message += "> "
        elif tag == "p":
            self.message += "\n"
        elif tag == "a":
            self.parse_mentions(attrs)
        elif tag == "mx-reply":  # we handle replies separately for best effect
            return
        elif tag == "img":  # TODO At least make it a link to Matrix URL
            emote_name = search_attr(attrs, "title")
            emote_ = Cache.cache["d_emotes"].get(emote_name)
            if emote_:
                self.message += emote_
            else:
                self.message += emote_name
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.message += headers[tag]
        elif tag == "blockquote":
            self.message += "> "
        # ignore font tag

    def parse_mentions(self, attrs):
        self.current_link = search_attr(attrs, "href")
        if self.current_link.startswith("https://matrix.to/#/"):
            target = self.current_link[20:]
            if target.startswith("@"):
                self.message += self.parse_user(target.split("?")[0])
            # Rooms will be handled by handle_data on data

    def parse_user(self, target: str):
        if self.is_discord_user(target):
            snowflake = re.search(re.compile(self.snowflake_regex), target).group(1)
            if snowflake:
                self.current_link = None  # Meaning, skip adding text
                return f"<@{snowflake}>"
        else:
            # Matrix user, not Discord appservice account
            return ""

    def is_discord_user(self, target: str) -> bool:
        return bool(self.db.fetch_user(target))

    def handle_data(self, data):
        if self.c_tags:
            if self.c_tags[-1] != "code":  # May IndexError!
                data = data.replace("\n", "")
            if "mx-reply" in self.c_tags:
                return
        # TODO Escape Matrix characters when in code blocks
        if self.current_link:
            self.message += f"[{data}](<{self.current_link}>)"
            self.current_link = ""
        elif self.current_link is None:
            self.current_link = ""
        else:
            self.message += data  # strip new lines, they will be mostly handled by parser

    def handle_endtag(self, tag: str):
        if "mx-reply" in self.c_tags and tag != "mx-reply":
            return
        if tag in htmltomarkdown:
            self.message += htmltomarkdown[tag]
        last_tag = self.c_tags.pop()
        if last_tag == "spoiler":
            self.message += "||"
            self.c_tags.pop()  # guaranteed to be a span tag
        if tag == "ol":
            self.list_num = 1
        elif tag == "code":
            if self.c_tags:
                self.message += "\n```"
            else:
                self.message += "`"
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.message += headers[tag][::-1]