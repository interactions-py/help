from typing import List, Optional

from interactions import MISSING, DictSerializerMixin


def typer_dict(_type, choices=None) -> str:
    _typer_dict = {
        1: "sub_command",
        2: "sub_command_group",
        3: "string",
        4: "integer",
        5: "boolean",
        6: "user",
        7: "channel",
        8: "role",
        9: "mentionable",
        10: "float",
    }
    return _typer_dict[_type] if choices in ([], None, MISSING) else "choices"


class TemplateEmbed(DictSerializerMixin):
    __slots__ = (
        "color",
        "description",
        "no_category_name",
        "fields_per_embed",
        "footer",
    )
    color: int
    description: Optional[str]
    no_category_name: str
    fields_per_embed: int
    footer: Optional[str]

    def __init__(
        self,
        color: int = 0,
        description: Optional[str] = None,
        no_category_name: str = "No Category",
        fields_per_embed: int = 3,
        footer: Optional[str] = None,
    ):
        self.color = color
        self.description = description
        self.no_category_name = no_category_name
        self.fields_per_embed = fields_per_embed
        self.footer = footer


class PaginatorSettings(DictSerializerMixin):
    __slots__ = ("timeout", "extended_buttons", "use_select", "author_only")
    timeout: int
    extended_buttons: bool
    use_select: bool
    author_only: bool

    def __init__(
        self,
        timeout: int = 60,
        extended_buttons: bool = True,
        use_select: bool = True,
        author_only: bool = False,
    ):
        self.timeout = timeout
        self.extended_buttons = extended_buttons
        self.use_select = use_select
        self.author_only = author_only


class AdvancedSettings(DictSerializerMixin):
    __slots__ = ("max_search_results", "blacklist", "auto_create")
    max_search_results: int
    blacklist: Optional[List[str]]
    auto_create: bool

    def __init__(
        self,
        max_search_results: int = 15,
        blacklist: Optional[List[str]] = None,
        auto_create: bool = True,
    ):
        self.max_search_results = max_search_results
        self.blacklist = blacklist
        self.auto_create = auto_create
