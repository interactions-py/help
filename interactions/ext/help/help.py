from typing import Any, Dict, List, Optional, Union

from interactions.ext.paginator import Paginator
from thefuzz.fuzz import ratio

from interactions import Client, CommandContext, DictSerializerMixin, Embed, Extension

from .settings import AdvancedSettings, PaginatorSettings, TemplateEmbed, typer_dict


class RawHelpCommand(DictSerializerMixin):
    __slots__ = (
        "_json",
        "client",
        "scope",
        "sync_commands",
        "_commands",
    )
    _json: Dict[str, Any]
    client: Client
    sync_commands: bool
    _commands: List[dict]

    def __init__(
        self,
        client: Client,
        sync_commands: bool = False,
        **kwargs,
    ):
        super().__init__(client=client, sync_commands=sync_commands, **kwargs)
        self._commands = []

    async def _get_all_commands(
        self,
        global_commands: bool = True,
        guild_commands: bool = True,
        guild: Optional[int] = None,
    ):
        result = []
        if global_commands:
            result = await self.client._http.get_application_commands(self.client.me.id)
        result = [] if result is None else result
        if guild_commands and guild:
            guild_result = await self.client._http.get_application_commands(
                self.client.me.id, guild
            )
            result.append(guild_result) if guild_result is not None else None
        result = list(filter(lambda x: x is not None, result))
        if not result:
            raise RuntimeError("No commands found")
        return result

    async def get_commands(
        self,
        global_commands: bool = True,
        guild_commands: bool = True,
        guild: Optional[int] = None,
    ):
        if self._commands and not self.sync_commands:
            return self._commands
        # get all commands
        all_commands = await self._get_all_commands(global_commands, guild_commands, guild)
        # separate by category
        commands, subcommands, menus = [], [], []
        guild_id_index = None
        await self.__sort_all_commands(all_commands, commands, subcommands, menus, guild_id_index)
        master: List[dict] = []
        for command in commands:
            command: dict
            cmd_ext: Optional[Extension] = next(
                (
                    ext_name
                    for ext_name, ext in self.client._extensions.items()
                    if isinstance(ext, Extension)
                    and f'command_{command["name"]}' in ext._commands.keys()
                ),
                None,
            )
            master.append(
                {
                    "name": command["name"],
                    "description": command["description"],
                    "options": command["options"],
                    "type": "slash command",
                    "extension": cmd_ext,
                }
            )
        for subcommand in subcommands:
            for sub in subcommand["options"]:
                sub: dict
                if sub["type"] == 1:
                    sub["options"] = sub.get("options", [])
                    cmd_ext: Optional[Extension] = next(
                        (
                            ext_name
                            for ext_name, ext in self.client._extensions.items()
                            if isinstance(ext, Extension)
                            and f'command_{subcommand["name"]}' in ext._commands.keys()
                        ),
                        None,
                    )
                    master.append(
                        {
                            "name": f'{subcommand["name"]} {sub["name"]}',
                            "description": sub["description"],
                            "options": sub["options"],
                            "type": "subcommand",
                            "extension": cmd_ext,
                        }
                    )
                else:
                    sub["options"][0]["options"] = sub["options"][0].get("options", [])
                    cmd_ext: Optional[Extension] = next(
                        (
                            ext_name
                            for ext_name, ext in self.client._extensions.items()
                            if isinstance(ext, Extension)
                            and f'command_{subcommand["name"]}' in ext._commands.keys()
                        ),
                        None,
                    )
                    master.append(
                        {
                            "name": f'{subcommand["name"]} {sub["name"]} {sub["options"][0]["name"]}',
                            "description": sub["options"][0]["description"],
                            "options": sub["options"][0]["options"],
                            "type": "subcommand group",
                            "extension": cmd_ext,
                        }
                    )
        for menu in menus:
            cmd_ext: Optional[Extension] = next(
                (
                    ext_name
                    for ext_name, ext in self.client._extensions.items()
                    if isinstance(ext, Extension)
                    and f'command_{menu["name"]}' in ext._commands.keys()
                ),
                None,
            )
            master.append(
                {
                    "name": menu["name"],
                    "description": None,
                    "type": ("user menu" if menu["type"] == 2 else "message menu"),
                    "extension": cmd_ext,
                }
            )
        for interaction in master:
            interaction: dict
            if interaction.get("options", None) is not None:
                for option in interaction["options"]:
                    option: dict
                    option["required"] = option.get("required", False)
        self._commands = master
        return master

    async def __sort_all_commands(
        self,
        all_commands: List[Union[List[dict], dict]],
        commands: list,
        subcommands: list,
        menus: list,
        guild_ids_index: Optional[int],
    ):
        # first, sort all global commands
        for command in all_commands:
            if isinstance(command, list):
                guild_ids_index = all_commands.index(command)
                break
            if command["type"] == 1:
                if "options" in command.keys() and command["options"][0]["type"] in (
                    1,
                    2,
                ):
                    subcommands.append(command)
                else:
                    if "options" not in command.keys():
                        command["options"] = []
                    commands.append(command)
            else:
                menus.append(command)
        # next, sort all guild commands if applicable
        if guild_ids_index is not None:
            for command in all_commands[guild_ids_index]:
                if command["type"] == 1:
                    if "options" in command.keys() and command["options"][0]["type"] in (
                        1,
                        2,
                    ):
                        subcommands.append(command)
                    else:
                        if "options" not in command.keys():
                            command["options"] = []
                        commands.append(command)
                else:
                    menus.append(command)


class HelpCommand(RawHelpCommand):
    __slots__ = (
        "_json",
        "client",
        "sync_commands",
        "template_embed",
        "paginator_settings",
        "advanced_settings",
    )
    client: Client
    sync_commands: bool
    template_embed: TemplateEmbed
    paginator_settings: PaginatorSettings
    advanced_settings: AdvancedSettings

    def __init__(
        self,
        client: Client,
        sync_commands: bool = False,
        template_embed: TemplateEmbed = TemplateEmbed(),
        paginator_settings: PaginatorSettings = PaginatorSettings(),
        advanced_settings: AdvancedSettings = AdvancedSettings(),
    ) -> None:
        super().__init__(
            client=client,
            sync_commands=sync_commands,
            template_embed=template_embed,
            paginator_settings=paginator_settings,
            advanced_settings=advanced_settings,
        )

    async def send_help(
        self,
        ctx: CommandContext,
        search: Optional[str] = None,
        guild_id: Optional[int] = None,
    ):
        if guild_id is None:
            guild_id = ctx.guild_id

        await self.get_commands(guild=guild_id)
        data: List[dict] = self._commands.copy()

        if search is not None:
            search: str = search.lower()
            answers: dict = {}
            list_extensions: list = []
            list_commands: list = []

            # extensions
            for interaction in data:
                if self.__ext_in_blacklist(interaction):
                    continue
                percent = ratio(search, interaction["extension"])
                if interaction["extension"] not in answers:
                    answers[interaction["extension"]] = percent
                    list_extensions.append(interaction["extension"])

            # commands
            for interaction in data:
                if self.__cmd_in_blacklist(interaction):
                    continue
                percent = ratio(search, interaction["name"])
                if interaction["name"] not in answers.keys():
                    answers[interaction["name"]] = percent
                    list_commands.append(interaction["name"])

            sorted_data: list = sorted(answers, key=answers.get, reverse=True)[
                : self.advanced_settings.max_search_results
            ]
            embeds: List[Embed] = []

            for i in range(0, len(sorted_data), self.template_embed.fields_per_embed):
                page = Embed(
                    title=f"Search results for `{search}`, {i + 1} - {i + self.template_embed.fields_per_embed}",
                    color=self.template_embed.color,
                )

                for match in sorted_data[i : (i + self.template_embed.fields_per_embed)]:
                    if match in list_extensions:
                        ext: str = None
                        cmds: List[Dict[str, dict]] = []

                        for interaction in data:
                            if match == interaction["extension"]:
                                ext = interaction["extension"]
                                cmds.append({interaction["name"]: interaction})

                        if ext is not None:
                            value = "Category\nCommands:\n"
                            for cmd in cmds:
                                in_blacklist = False
                                if self.advanced_settings.blacklist:
                                    for black in self.blacklist:
                                        if black in list(cmd.keys())[0]:
                                            in_blacklist = True
                                            break
                                if in_blacklist:
                                    continue
                    elif match in list_commands:
                        for interaction in data:
                            if match == interaction["name"]:
                                break
                        options: str = ""
                        if interaction["type"] in {
                            "slash command",
                            "subcommand",
                            "subcommand group",
                        }:
                            for option in interaction["options"]:
                                the_type = typer_dict(
                                    option["type"],
                                    option["choices"] if "choices" in option.keys() else [],
                                )
                                options += f"[{option['name']}: {'' if option['required'] else 'optional '}{the_type}], "
                        elif "menu" not in interaction["type"]:
                            options += interaction["options"]
                        options = options[:-2] if options.endswith(", ") else options
                        how_to_use = f"\nHow to use:\n```\n{f'/' if interaction['type'] in {'slash command', 'subcommand', 'subcommand group'} else ('Right click on a ' + interaction['type'].replace(' menu', '')) if 'menu' in interaction['type'] else '/'}{'' if 'menu' in interaction['type'] else interaction['name']} {options}\n```"
                        page.add_field(
                            name=interaction["name"],
                            value=(
                                ""
                                if interaction["description"] is None
                                else interaction["description"]
                            )
                            + f"\n{interaction['type'].capitalize()}"
                            + how_to_use,
                            inline=False,
                        )
                if self.template_embed.footer is not None:
                    page.set_footer(text=self.template_embed.footer)
                embeds.append(page)
            return await Paginator(
                client=self.client,
                ctx=ctx,
                pages=embeds,
                timeout=self.paginator_settings.timeout,
                author_only=self.paginator_settings.author_only,
                use_select=self.paginator_settings.use_select,
                extended_buttons=self.paginator_settings.extended_buttons,
            ).run()
        else:
            first_page = (
                Embed(title="Help", color=self.template_embed.color)
                if self.template_embed.description is None
                else Embed(
                    title="Help",
                    description=self.template_embed.description,
                    color=self.template_embed.color,
                )
            )
            if self.template_embed.footer is not None:
                first_page.set_footer(text=self.template_embed.footer)
            embeds: List[Embed] = [first_page]
            exts: List[dict] = []

            for interaction in data:
                if self.__ext_in_blacklist(interaction):
                    continue
                if {
                    "name": interaction["extension"],
                    "interactions": [],
                } not in exts:
                    exts.append(
                        {
                            "name": interaction["extension"],
                            "interactions": [],
                        }
                    )
            for ext in exts:
                value = "\n"
                for interaction in data:
                    if self.__cmd_in_blacklist(interaction):
                        continue
                    if interaction["extension"] == ext["name"]:
                        ext["interactions"].append(interaction)
                        value += f"`{'/' if interaction['type'] in ['slash command', 'subcommand', 'subcommand group'] else '' if 'menu' in interaction['type'] else '/'}{interaction['name']}`, "
                value = value[:-2] if value.endswith(", ") else value
                first_page.add_field(
                    name=(
                        self.template_embed.no_category_name if ext["name"] is None else ext["name"]
                    ),
                    value=value,
                    inline=False,
                )
            for ext in exts:
                for i in range(0, len(ext["interactions"]), self.template_embed.fields_per_embed):
                    next_page = Embed(
                        title=f"{self.template_embed.no_category_name if ext['name'] is None else ext['name']} {i + 1} - {i + self.template_embed.fields_per_embed}",
                        color=self.template_embed.color,
                    )
                    for cmd in ext["interactions"][i : (i + self.template_embed.fields_per_embed)]:
                        cmd: dict
                        cmd_name: str = cmd["name"]
                        cmd_desc: str = cmd["description"]
                        cmd_opts: list = cmd.get("options", [])
                        cmd_type: str = cmd["type"]
                        desc = (
                            "No description"
                            if cmd_desc is None or cmd_desc == [] or not cmd_desc
                            else cmd_desc
                        ) + "\nHow to use:"
                        how_to_use = f"\n```\n{f'/{cmd_name}' if 'menu' not in cmd_type else ('Right click on a ' + cmd['type'].replace(' menu', ''))} "
                        if isinstance(cmd_opts, list):
                            for opt in cmd_opts:
                                opt: dict
                                _type = typer_dict(opt["type"], opt.get("choices", []))
                                how_to_use += f"[{opt['name']}: {'optional ' if not opt['required'] else ''}{_type}], "
                        elif cmd_opts is not None:
                            how_to_use += cmd_opts
                        how_to_use = how_to_use[:-2] if how_to_use.endswith(", ") else how_to_use
                        how_to_use += "\n```"
                        next_page.add_field(name=cmd_name, value=desc + how_to_use, inline=False)
                    if self.template_embed.footer is not None:
                        next_page.set_footer(text=self.template_embed.footer)
                    embeds.append(next_page)
            return await Paginator(
                client=self.client,
                ctx=ctx,
                pages=embeds,
                timeout=self.paginator_settings.timeout,
                author_only=self.paginator_settings.author_only,
                use_select=self.paginator_settings.use_select,
                extended_buttons=self.paginator_settings.extended_buttons,
            ).run()

    def __cmd_in_blacklist(self, interaction: dict):
        return (
            any(
                (black in interaction["name"]) or (black in interaction["extension"])
                for black in self.advanced_settings.blacklist
            )
            if self.advanced_settings.blacklist is not None
            else False
        )

    def __ext_in_blacklist(self, interaction: dict):
        return (
            self.__cmd_in_blacklist(interaction) if interaction["extension"] is not None else False
        )
